import pandas as pd
import datetime
import logging
import sys
import os
from pydriller import Git
from git import Repo
sys.path.append('../utils')
import database as db
from utils import get_full_project_name, is_git_repo

# get commit blamed for deleted lines in the fix commit
def get_git_blame(repo, commit_hash, filepath, lines):
    buggy_commits = set()
    args = ['-w', commit_hash + '^']
    blame = repo.git.blame(*args, '--', filepath).split('\n')
    for num_line, line in lines:
        if 'test' in line.strip():
            continue
        buggy_commit = blame[num_line - 1].split(' ')[0].replace('^', '')
         # Skip unblamable lines.
        if buggy_commit.startswith("*"):
            continue
        buggy_commits.add(buggy_commit)
    return buggy_commits


# get introduced date of deleted lines in fix commit
def get_introduced_date(repo_dest_path, modified_files, commit_hash):
    repo = Repo(repo_dest_path)
    buggy_commits = set()
    for _, rrow in modified_files.iterrows():
        deleted_lines = eval(rrow['diff_parsed'])['deleted']
        fname = rrow['old_path']
        # skip added files
        if fname == 'None' or 'test' in fname:
            continue
        commits = get_git_blame(repo, commit_hash, fname, deleted_lines)
        buggy_commits = buggy_commits.union(commits)
    # get earilest introduced date of buggy commits
    earliest_commiter_date = None
    for commit in buggy_commits:
        commiter_date = Git(repo_dest_path).get_commit(commit).committer_date
        if earliest_commiter_date is None or commiter_date < earliest_commiter_date:
            earliest_commiter_date = commiter_date
    # only add lines in the fix commit, no deleted lines
    if earliest_commiter_date is None:
        logging.warning(f"No buggy commit found for {commit_hash}")
    return earliest_commiter_date


def main():
    dest = "../repos_mirror"
    df = pd.read_sql("SELECT cve_id, hash, repo_url FROM commits", con=db.conn)
    df_files = pd.read_sql("SELECT hash, old_path, diff_parsed FROM file_change", con=db.conn)
    print(len(df['cve_id'].unique()))
    print(len(df_files['hash'].unique()))
    commit_retrieve = 0
    commit_not_retrieve = 0
    fix_dates = []
    introduced_dates = []
    print(len(df))
    for index, row in df.iterrows():
        repo_url = row["repo_url"]
        commit_hash = row["hash"]
        cve_id = row["cve_id"]
        full_project_name = get_full_project_name(repo_url)
        repo_dest_path = os.path.join(dest, full_project_name)
        fix_date = None
        introduced_date = None

        if os.path.exists(repo_dest_path):
            if is_git_repo(repo_dest_path):
                # get fixed date
                commit = Git(repo_dest_path).get_commit(commit_hash)
                fix_date = commit.committer_date
                # get introduced commits
                modified_files = df_files[df_files['hash'] == commit_hash]
                introduced_date = get_introduced_date(repo_dest_path, modified_files, commit_hash)
                commit_retrieve += 1
            else:
                logging.warning(f"Repo {repo_dest_path} is not a git repo")
        fix_dates.append(fix_date)
        introduced_dates.append(introduced_date)
    df['fix_date'] = fix_dates
    df['introduced_date'] = introduced_dates
    # write to db
    df.to_sql('commit_life_spans', con=db.conn, if_exists='replace', index=False)
    print(commit_retrieve)
    print(commit_not_retrieve)

if __name__ == "__main__":
    main()