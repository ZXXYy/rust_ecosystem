import pandas as pd
from pydriller import Git
import logging
import uuid
import os
import click
import re
import sys

sys.path.append('../utils')
import database as db
from utils import get_full_project_name, is_git_repo


dest = "../repos_mirror"

commit_columns = [
    'cve_id',
    'hash',
    'repo_url',
    'msg',
    'merge',
    'parents',
    'num_files',
    'num_lines_added',
    'num_lines_deleted'
]

file_columns = [
    'file_change_id',
    'hash',
    'old_path',
    'new_path',
    'change_type',
    'diff',
    'diff_parsed',
    'num_lines_added',
    'num_lines_deleted',
    'nloc'
]

def is_src_file(file):
    config_file = ["cargo.toml", "readme.md"]
    if file.filename.lower() in config_file:
        return False
    if "test" in file.new_path.lower() or "example" in file.new_path.lower() or "doc" in file.new_path.lower():
        return False
    return True

def eliminate_comment_diff(diff_parsed):
    added = diff_parsed['added']
    added_new = list()
    deleted = diff_parsed['deleted']
    deleted_new = list()
    for add in added:
        if add[1].replace(' ', '').replace('\t', '')[:2] != "//" and add[1].replace('\n', '').replace('\t', '').replace(' ', '') != "":
            added_new.append(add)
    for d in deleted:
        if d[1].replace(' ', '').replace('\t', '')[:2] != "//" and d[1].replace('\n', '').replace('\t', '').replace(' ', '') != "":
            if "test" not in d:
                deleted_new.append(d)
    diff = {"added": added_new, "deleted": deleted_new }
    
    return diff

# ---------------------------------------------------------------------------------------------------------
# extracting file_change data of each commit
def get_files(commit, commit_hash):
    """
    returns the list of files of the commit.
    """
    commit_files = []
    modified_files = []
    try:
        # logging.info(f'Extracting files for {commit.hash}')
        if commit.modified_files:
            for file in commit.modified_files:
                # get the source file of modified files
                pattern = re.compile(r".*\.rs")
                if not pattern.match(file.filename):
                    logging.debug(f'Filtering out non-source file {file.filename} in {commit.hash}')
                    continue

                logging.debug(f'Processing file {file.filename} in {commit.hash}')
                file_change_id = uuid.uuid4().fields[-1]
                file_parsed_diff = eliminate_comment_diff(file.diff_parsed)
                file_row = {
                    'file_change_id': file_change_id,       # filename: primary key
                    'hash': commit_hash,                    # hash: foreign key
                    'old_path': file.old_path,
                    'new_path': file.new_path,
                    'change_type': file.change_type,        # i.e. added, deleted, modified or renamed
                    'diff': file.diff,                      # diff of the file as git presents it (e.g. @@xx.. @@)
                    'diff_parsed': file_parsed_diff,        # diff parsed in a dict containing added and deleted lines lines
                    'num_lines_added': len(file_parsed_diff['added']),        # number of lines added
                    'num_lines_deleted': len(file_parsed_diff['deleted']),    # number of lines removed
                    'nloc': file.nloc,
                }

                if file_row["num_lines_added"]!= 0 or file_row["num_lines_deleted"]!= 0:
                    commit_files.append(file_row)
                    modified_files.append(file)
        else:
            logging.info(f'Extracting files for {commit.hash}')
            logging.info('The list of modified_files is empty')

        return commit_files

    except Exception as e:
        logging.warning('Problem while fetching the files!', e)
        pass


# ---------------------------------------------------------------------------------------------------------
def drop_tables():
    # drop all commit related tables
    cursor = db.conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS commits;")
    cursor.execute("DROP TABLE IF EXISTS file_change;")

# @click.command()
# @click.argument("datafile", type=click.File("r+"))
def main():
    # ../data_collection/data/fix_commits_final.csv
    df_fixes = pd.read_sql("SELECT cve_id, hash, repo_url FROM commits", con=db.conn)
    df_fixes.drop_duplicates(subset =['hash', 'repo_url'], keep = 'first', inplace = True)
    # drop_tables()

    repo_not_download = 0
    commit_not_retrieve = 0
    invalid_modification = 0
    
    for index, row in df_fixes.iterrows():
        repo_url = row["repo_url"]
        hash = row["hash"]
        cve_id = row["cve_id"]

        full_project_name = get_full_project_name(repo_url)
        repo_dest_path = os.path.join(dest, full_project_name)
        
        if os.path.exists(repo_dest_path):
            if is_git_repo(repo_dest_path):
                
                try:
                    commit = Git(repo_dest_path).get_commit(hash)
                    commit_files = get_files(commit, hash)
                    # logging.info('Processing {}: {}'.format(cve_id, commit.hash))
                    # buggy_commits = Git(repo_dest_path).get_commits_last_modified_lines(commit)
                    # for k, values in buggy_commits.items():
                    #     for v in values:
                    #         print(Git(repo_dest_path).get_commit(v).committer_date)
                    # print()
                    
                    commit_row = {
                        'cve_id': cve_id,
                        'hash': hash,
                        'repo_url': repo_url,
                        'msg': commit.msg,
                        'merge': commit.merge,
                        'parents': commit.parents,
                        'num_files': len(commit_files),
                        'num_lines_added': commit.insertions,
                        'num_lines_deleted': commit.deletions
                    }
                    df_commit = pd.DataFrame.from_dict(commit_row)
                    df_commit = df_commit[commit_columns]  # ordering the columns
                    if len(commit_files) > 0:
                        df_files = pd.DataFrame.from_dict(commit_files)
                        df_files = df_files[file_columns]  # ordering the columns
                    else:
                        invalid_modification += 1
                        df_files = None
                        df_commit = None

                    if df_commit is not None:
                        with db.conn:
                            # ----------------appending each project data to the tables-------------------------------
                            df_commit = df_commit.applymap(str)
                            # df_commit.to_sql(name="commits", con=db.conn, if_exists="append", index=False)
                            # logging.info(f'#Commits :{len(df_commit)}')

                            if df_files is not None:
                                df_files = df_files.applymap(str)
                                df_files.to_sql(name="file_change", con=db.conn, if_exists="append", index=False)
                                # logging.info(f'#Files   :{len(df_files)}')
                except:
                    # "This commit does not belong to any branch on this repository, and may belong to a fork outside of the repository."
                    commit_not_retrieve += 1
                    logging.info(f'Extracting files for {commit.hash}')
                    logging.warning(f'Could not retrieve commit information from: {repo_dest_path}\n')
        else:
            repo_not_download += 1
            logging.info(f'Extracting files for {commit.hash}')
            logging.info(f"Repository {repo_url} not cloned. Skipping.")
    print(f"# of fix commits: {len(df_fixes)}")
    print(f"# of repos not downloaded: {repo_not_download}")
    print(f"# of commits not retrieved: {commit_not_retrieve}")
    print(f"# of commit with invalid modifications: {invalid_modification}")


if __name__ == '__main__':
    main()