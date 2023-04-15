import pandas as pd
from pydriller import Git
import sys
import os
import logging
import click
import toml

sys.path.append('../../utils')
from utils import get_full_project_name, is_git_repo
# success_cnt_fix = 186
# total = 221
# success:  186
# fail:  35
# success_fix:  186
# fail_fix:  35

dest = "../../repos_mirror"
dest_work= "../../repos_worktree"
compiler_result = "../../compiler_result_v2"
compile_script = "compile_single.sh"
check_head = "check_head.sh"
worktree = "worktree.sh"


def get_worktree(repo_dest_path, work_tree_path):
    if not os.path.exists(work_tree_path):
        if os.system(worktree+" "+repo_dest_path+" "+work_tree_path):
            print(repo_dest_path)


@click.command()
@click.argument("datafile", type=click.File("r+"))
def main(datafile):
    # ../../data_collection/data/fix_commits_final.csv
    df_fixes = pd.read_csv(datafile)
    df_fixes.drop_duplicates(subset =['hash', 'repo_url'], keep = 'first', inplace = True)

    fail_list = []
    success_list = []
    success_cnt = 0
    fail_cnt = 0
    success_cnt_fix = 0
    fail_cnt_fix = 0

    for index, row in df_fixes.iterrows():
        repo_url = row["repo_url"]
        cve_id = row["cve_id"]
        hash = row["hash"]
        # if repo_url != "https://github.com/paritytech/frontier":
        #     continue
        # outpath = compiler_result+package+"/"+cve_id
        # outpath_fix = compiler_result+package+"/"+cve_id+"_fix"
        full_project_name = get_full_project_name(repo_url)
        repo_dest_path = os.path.join(dest, full_project_name)
        work_tree_path = os.path.join(dest_work, full_project_name)
        if os.path.exists(repo_dest_path):
            if is_git_repo(repo_dest_path):
                try:
                    commit = Git(repo_dest_path).get_commit(hash)
                    get_worktree(repo_dest_path, work_tree_path)

                    # deal with exceptions
                    features = ""
                    # if repo_url == "https://github.com/hyperium/hyper":
                    #     features = "--features \"full\""
                    # elif repo_url == "https://github.com/rusqlite/rusqlite":
                    #     features = "--features \"functions,vtab,trace,unlock_notify,array,csvtab\""
                    # elif repo_url == "https://github.com/RustCrypto/block-ciphers":
                    #     features = "-C target_feature+=aes,sse2 target_arch=x86"
                    # elif repo_url == "https://github.com/dylni/os_str_bytes":
                    #     features = "-C target_os=\"windows\""

                    analysis_dir = f"{compiler_result}/{full_project_name}/{cve_id}/{hash}"
                    if not os.path.exists(analysis_dir):
                        print("git check ", commit.parents[0])
                        os.system(check_head+" "+work_tree_path+" "+commit.parents[0]+" "+features)
                        # run the compiler script
                        if os.system(compile_script+" "+work_tree_path+" "+cve_id+" "+commit.parents[0]+" "+analysis_dir)==0:
                            success_cnt += 1
                            success_list.append(full_project_name)
                            # remove_dependency_crate(work_tree_path, analysis_dir)
                        else:
                            os.system(f"rm -rf {analysis_dir}")
                            fail_cnt += 1
                            fail_list.append(full_project_name)
                        
                        print("success_cnt =", success_cnt)
                        print("total =", success_cnt+fail_cnt)
                    else:
                        print("{}: Vunerablility existing already compiled!".format(cve_id))
                        success_list.append(full_project_name)
                        success_cnt += 1

                    analysis_dir = f"{compiler_result}/{full_project_name}/{cve_id}_fix/{hash}"
                    if not os.path.exists(analysis_dir):
                        print("git check ", commit.hash)
                        os.system(check_head+" "+work_tree_path+" "+commit.hash)
                        # run the compiler script
                        if os.system(compile_script+" "+work_tree_path+" "+cve_id+"_fix"+" "+commit.hash+" "+analysis_dir)==0:
                            success_cnt_fix += 1
                            # remove_dependency_crate(work_tree_path, analysis_dir)
                        else:
                            fail_cnt_fix += 1
                            os.system(f"rm -rf {analysis_dir}")
                        
                        print("success_cnt_fix =", success_cnt_fix)
                        print("total =", fail_cnt_fix+success_cnt_fix)
                    else:
                        print("{}: Vunerablility fixing commit already compiled!".format(cve_id))
                        success_cnt_fix += 1

                except Exception as e:
                    logging.warning('Problem while fetching the commits!')
                    print(e)
                    pass
            
            else:
                logging.warning('Repos not cloned!')
    print("success: ",success_cnt)
    print("fail: ",fail_cnt)
    print("success_fix: ",success_cnt_fix)
    print("fail_fix: ",fail_cnt_fix)
    
    with open("fail", "w") as f:
        for l in fail_list:
            f.write(l+"\n")

    with open("success", "w") as f:
        for l in success_list:
            f.write(l+"\n")
if __name__ == '__main__':
    main()

# 1. failed to select a version for the requirement `aes = "~0.3.2"`
# 2. System problem
# 3. Compiler Syntax error