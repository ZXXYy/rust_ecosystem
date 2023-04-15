import os
import re
import logging
import click
import pandas as pd
import sys
from pydriller import Git
sys.path.append('../../utils')
from utils import get_full_project_name, is_git_repo
from database import write_database
import database as db
from compile import get_worktree

dest = "../../repos_mirror"
dest_work= "../../repos_worktree"
regex_result = "../../regex_result"
check_head = "../../source_analysis/scripts/check_head.sh"
compiler_result = "../../compiler_result_v2"
ordered_columns_num = ['cve_id', 'hash', 'safe_func', 'unsafe_func', 'unsafe_block']

def list_rs_files(path):
    #we shall store all the file names in this list
    filelist = []
    for root, dirs, files in os.walk(path):
        for file in files:
            #append the file name to the list
            filename = os.path.join(root,file)
            if filename[-3:] == ".rs" and "test" not in filename and "example" not in filename:
                filelist.append(filename)
    return filelist

def count_unsafe_fn(file):
    cnt = 0
    pre_line = ""
    with open(file) as f:
        for line in f.readlines():
            if re.search(r'unsafe fn\s+.*\(.*\)(->)?.*', line) and "#[test]" not in pre_line and line.lstrip()[0:2]!='//' and "extern \"C\"" not in pre_line:
                cnt += 1
            pre_line = line
    return cnt

def count_unsafe_block(file, outfile):
    cnt = 0
    pre_line = ""
    with open(file) as f:
        test_flag = False
        for index, line in enumerate(f.readlines()):
            # if re.search(r'impl\s+.*\s+for\s+.*{', line.lstrip()) :
            #     outfile.write(f"{index}: {line}\n")
            #     cfg_flag = True if "#[cfg" in pre_line else False
            # get the owner function of the unsafe block
            if re.search(r'fn\s+.*\(.*\)(->)?.*', line.lstrip()) and line.lstrip()[0:2]!='//' and "extern \"C\"" not in pre_line:
                test_flag = False if "#[test]" not in pre_line  else True
            if "unsafe{" in line.replace(" ", "") and line.lstrip()[0:2]!='//' and not test_flag:
                cnt += 1
                outfile.write(f"{index}: {line}\n")
            pre_line = line
    return cnt

def count_fn(file, outfile):
    cnt = 0
    pre_line = ""
    with open(file) as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if re.search(r'fn\s+.*\(.*\)(->)?.*', line.lstrip()) and "#[test]" not in pre_line and line.lstrip()[0:2]!='//' and "extern \"C\"" not in pre_line:
                # outfile.write(f"{line}\n")
                cnt += 1
            pre_line = line
    return cnt

def regex_crate(path, analysis_dir, cve_id, hash): 
    files = list_rs_files(path)
    with open(analysis_dir+"/regex", "a+") as f:
        f.write(f"{path}\n")
        f.write(f"{cve_id}\n")
        f.write(f"{hash}\n")
        total_fn = 0
        total_unsafe_fn = 0
        total_unsafe_block = 0
        for file in files:
            f.write(f"{file}\n")
            total_fn += count_fn(file, f)
            total_unsafe_fn += count_unsafe_fn(file)
            total_unsafe_block += count_unsafe_block(file, f)
        f.write(f"{total_fn-total_unsafe_fn}\n")
        f.write(f"{total_unsafe_fn}\n")
        f.write(f"{total_unsafe_block}\n")
    return total_fn-total_unsafe_fn, total_unsafe_fn, total_unsafe_block

@click.command()
@click.argument("datafile", type=click.File("r+"))
def main(datafile):
    mycursor = db.conn.cursor()
    mycursor.execute("DROP TABLE IF EXISTS total_safe_unsafe_regex;")
    # mycursor.execute("DROP TABLE IF EXISTS total_safe_unsafe_regex_success;")
    # ../../data_collection/data/fix_commits_final.csv
    df_fixes = pd.read_csv(datafile)
    df_fixes.drop_duplicates(subset =['hash', 'repo_url'], keep = 'first', inplace = True)
    cnt = 0
    df = pd.DataFrame()
    print(df_fixes)
    for index, row in df_fixes.iterrows():
        repo_url = row["repo_url"]
        cve_id = row["cve_id"]
        hash = row["hash"]
        
        full_project_name = get_full_project_name(repo_url)
        repo_dest_path = os.path.join(dest, full_project_name)
        work_tree_path = os.path.join(dest_work, full_project_name)
        if os.path.exists(repo_dest_path):
            if is_git_repo(repo_dest_path):
                try:
                    commit = Git(repo_dest_path).get_commit(hash)
                    get_worktree(repo_dest_path, work_tree_path)

                    analysis_dir = f"{regex_result}/{full_project_name}/{cve_id}/{hash}"
                    compile_dir =  f"{compiler_result}/{full_project_name}/{cve_id}/{hash}"
                    # if compile faile try to regex the file
                    if not os.path.exists(compile_dir):
                        if not os.path.exists(analysis_dir):
                            os.makedirs(analysis_dir) 
                        print("git check ", commit.parents[0])
                        os.system(check_head+" "+work_tree_path+" "+commit.parents[0])
                        # run the regex
                        total_safe_fn, total_unsafe_fn, total_unsafe_block = regex_crate(work_tree_path, "./temp", cve_id, hash)
                        df = df.append({"cve_id": cve_id, 
                            "hash":hash, 
                            "safe_func":total_safe_fn, 
                            "unsafe_func":total_unsafe_fn, 
                            "unsafe_block":total_unsafe_block}, ignore_index=True)
                        cnt += 1
                    
                except Exception as e:
                    logging.warning('Problem while fetching the commits!')
                    print(e)
                    pass
            
            else:
                logging.warning('Repos not cloned!')
    print(cnt)
    df = df[ordered_columns_num]
    write_database("total_safe_unsafe_regex",df)
        # break
if __name__ == '__main__':
    
    main()