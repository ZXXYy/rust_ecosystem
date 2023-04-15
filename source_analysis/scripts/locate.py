import sys
import pandas as pd
import re
import click
sys.path.append('/home/xiaoyez/rust_vulnerabilities/utils')
import database as db
from database import write_database

from pydriller import Git
import os
import logging

ordered_colum = ["cve_id",
                "hash", 
                "unsafe_func", 
                "safe_func" ,
                "unsafe_block", 
                "unsafe_func_fix", 
                "safe_func_fix",
                "unsafe_block_fix",]
def locate_modified_lines(file_path, modified_lines, df_func, df_unsafe_block):
    unsafe_func = 0
    safe_func = 0
    unsafe_block = 0
    unsafe_func_name = list()
    safe_func_name = list()
    if "test" not in file_path:
        # file_path = file_path[file_path.index("src/"):]
        df_temp = df_func[df_func["path"]==file_path]
        # Function level
        if not df_temp.empty:
            df_temp = df_temp.assign(modified=False)
            # df_temp["modified"] = False

            for d in modified_lines:
                # get line number
                line = d[0]
                # if lines inside function is modified, set function to modified.
                df_temp["modified"] = df_temp.apply(lambda x: True if x.modified==True else (True if line>=int(x.span_start.split(":")[0]) and line<=int(x.span_end.split(":")[0]) else False) , axis=1)

            df_temp = df_temp[df_temp["modified"].values]
            unsafe_func += len(df_temp[df_temp["unsafety"]=='True'].index)
            # print(list(df_temp[df_temp["unsafety"]=='True'].name))
            unsafe_func_name.extend(list(df_temp[df_temp["unsafety"]=='True'].name))
            safe_func += len(df_temp[df_temp["unsafety"]=='False'].index)
            safe_func_name.extend(list(df_temp[df_temp["unsafety"]=='False'].name))

        # block level
        df_temp = df_unsafe_block[df_unsafe_block["path"]==file_path]
        if not df_temp.empty:
            df_temp = df_temp.assign(modified=False)
            # df_temp["modified"] = False
            for d in modified_lines:
                # get line number
                line = d[0]
                # if lines inside function is modified, set function to modified.
                df_temp["modified"] = df_temp.apply(lambda x: True if x.modified==True else (True if line>=int(x.span_start.split(":")[0]) and line<=int(x.span_end.split(":")[0]) else False) , axis=1)
            df_temp = df_temp[df_temp["modified"].values]
            unsafe_block += len(df_temp)

    return unsafe_func, safe_func, unsafe_block, safe_func_name, unsafe_func_name


@click.command()
@click.argument("commitfile", type=click.STRING) # /home/xiaoyez/rust_vulnerabilities/data_collection/data/fix_commits_final.csv
def main(commitfile):
    mycursor = db.conn.cursor()
    mycursor.execute("DROP TABLE IF EXISTS vul_safe_unsafe;")
    
    df = pd.read_csv(commitfile)
    df.drop_duplicates(subset =['hash', 'repo_url'], keep = 'first', inplace = True)
    ordered_columns = ["cve_id",
                "hash", 
                "unsafe_func", 
                "safe_func" ,
                "unsafe_block", 
                "unsafe_func_fix", 
                "safe_func_fix",
                "unsafe_block_fix",]
    df_result = pd.DataFrame(columns=ordered_columns)
    no_modified_file = 0
    compile_failure_before = 0
    compile_failure_after = 0
    df_error = pd.DataFrame()

    for index, row in df.iterrows():
        cve_id = row['cve_id']
        commit_hash = row['hash']
        repo_url = row["repo_url"]
        print(repo_url)
        # try:  
        # get file diff, meta information about VEC and VFC
        df_file = pd.read_sql("SELECT old_path, new_path, diff_parsed FROM file_change WHERE hash=\""+commit_hash+"\"", con=db.conn)
        # df_file = pd.read_sql("SELECT hash, old_path, new_path, diff_parsed FROM file_change", con=db.conn)
        # df_file = df_file[df_file["hash"]==commit_hash]

        # df_file.drop_duplicates(subset=['old_path', 'new_path', 'diff_parsed'], inplace=True)

        df_func = pd.read_sql("SELECT * FROM function WHERE hash=\""+commit_hash+"\" and cve_id=\""+cve_id+"\"", con=db.conn)
        df_unsafe_block = pd.read_sql("SELECT * FROM unsafe_block WHERE hash=\""+commit_hash+"\" and cve_id=\""+cve_id+"\"", con=db.conn)

        df_func_fix = pd.read_sql("SELECT * FROM function_fix WHERE hash=\""+commit_hash+"\" and cve_id=\""+cve_id+"\"", con=db.conn)
        df_unsafe_block_fix = pd.read_sql("SELECT * FROM unsafe_block_fix WHERE hash=\""+commit_hash+"\" and cve_id=\""+cve_id+"\"", con=db.conn)

        # VEC or VFC compilation failed, do nothing... manual get its info
        if df_file.empty:
            no_modified_file +=1
            # print(commit_hash)
            # print(repo_url)
            df_error = df_error.append({"cve_id":cve_id,
            "hash": repo_url+"/commit/"+commit_hash
            }, ignore_index=True)
            continue
        
        if df_func.empty:
            compile_failure_before +=1

        if df_func_fix.empty:
            compile_failure_after += 1
            
        if df_func.empty and df_func_fix.empty:
            df_error = df_error.append({"cve_id":cve_id,
            "hash": repo_url+"/commit/"+commit_hash
            }, ignore_index=True)
            continue
        vul_unsafe_func = 0
        vul_safe_func = 0
        vul_unsafe_block = 0
        fix_unsafe_func = 0
        fix_safe_func = 0
        fix_unsafe_block = 0
        safe_func_names = list()
        unsafe_func_names = list()
        
        # iterate modified lines in files
        for index2, row_file in df_file.iterrows():
            if re.compile(r".*\.rs").match(row_file["old_path"]):
                # code version before fix commit 
                file_path = row_file["old_path"]
                line_deleted = eval(row_file["diff_parsed"])["deleted"]
                unsafe_func, safe_func, unsafe_block, safe_func_name, unsafe_func_name = locate_modified_lines(file_path, line_deleted, df_func, df_unsafe_block)
                vul_unsafe_func += unsafe_func
                vul_safe_func += safe_func
                vul_unsafe_block += unsafe_block
                safe_func_names.extend(safe_func_name)
                unsafe_func_names.extend(unsafe_func_name)

            if re.compile(r".*\.rs").match(row_file["new_path"]):
                # code version after fix commit
                file_path = row_file["new_path"]
                line_added = eval(row_file["diff_parsed"])["added"]
                unsafe_func_fix, safe_func_fix, unsafe_block_fix, safe_func_name, unsafe_func_name = locate_modified_lines(file_path, line_added, df_func_fix, df_unsafe_block_fix)
                fix_unsafe_func += unsafe_func_fix
                fix_safe_func += safe_func_fix
                fix_unsafe_block += unsafe_block_fix
                safe_func_names.extend(safe_func_name)
                unsafe_func_names.extend(unsafe_func_name)

                
        # fix commit both add & delete count
        # print(safe_func_names)
        # print(unsafe_func_names)
        safe_func_names = len(set(safe_func_names))
        unsafe_func_names = len(set(unsafe_func_names))
        if vul_unsafe_func==0 and vul_safe_func==0 and vul_unsafe_block==0 and fix_unsafe_func==0 and fix_unsafe_block==0 and fix_unsafe_block==0:
            df_error = df_error.append({"cve_id":cve_id,
            "hash": repo_url+"/commit/"+commit_hash
            }, ignore_index=True)
        else:
            df_result = df_result.append({"cve_id":cve_id,
                    "hash": commit_hash, 
                    "unsafe_func": vul_unsafe_func, 
                    "safe_func": vul_safe_func ,
                    "unsafe_block": vul_unsafe_block, 
                    "unsafe_func_fix": fix_unsafe_func, 
                    "safe_func_fix": fix_safe_func,
                    "unsafe_block_fix": fix_unsafe_block,
                    "total_unsafe_func": unsafe_func_names,
                    "total_safe_func": safe_func_names,
                    "total_unsafe_block": max(vul_unsafe_block, fix_unsafe_block)
                    }, ignore_index=True)
        # except Exception as e:
        #     logging.warning(e)
        #     logging.warning(f'Could not retrieve commit information\n')
        #     exit()
        
        
    print(no_modified_file)
    print(compile_failure_before)
    print(compile_failure_after)
    write_database("vul_safe_unsafe", df_result[ordered_columns])
    df_error.to_csv("manual.csv")

if __name__ == '__main__':
    main()