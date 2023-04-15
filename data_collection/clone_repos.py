import logging
import requests
import time
import shutil
import os
import sys
import pandas as pd

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(f'{ROOT_PATH}/../utils')
import database as db
from utils import get_full_project_name, is_git_repo

dest  = f"{ROOT_PATH}/../repos_mirror"

def filter_urls(urls):
    """
    returns the non-existing urls
    """
    sleeptime = 0
    non_exist_urls = []
    for url in urls:
        print(url)
        code = requests.head(url).status_code
        while code == 429:
            sleeptime += 10
            time.sleep(sleeptime)
            code = requests.head(url).status_code

        if code >= 400:
            non_exist_urls.append(url + ',' + str(code))

        sleeptime = 0

    return non_exist_urls

def get_ref_links():
    """
    retrieves reference links from CVE records to populate 'fixes' table
    """
    df_fixes = pd.read_sql("SELECT repo_url FROM cve", con=db.conn)

    print('Checking if references still exist...')
    unique_urls = set(list(df_fixes.repo_url))

    unfetched_urls = []
    # unfetched_urls = filter_urls(unique_urls)

    if len(unfetched_urls) > 0:
        logging.debug('The following URLs are not accessible:')
        logging.debug(unfetched_urls)

    # filtering out non-existing repo_urls
    df_fixes = df_fixes[~df_fixes['repo_url'].isin(unfetched_urls)]

    return df_fixes

def clone_repo(repo_url, repo_dest_path):
    try:
        logging.info("Cloning from remote...")
        if ".git" not in repo_url:
            os.system("git clone --mirror "+repo_url+".git"+" "+repo_dest_path)
        else:
            os.system("git clone --mirror "+repo_url+" "+repo_dest_path)
            # Repo.clone_from(repo_url, repo_dest_path)
        logging.info("Cloning done!")
        
    except Exception as e:
        raise e
    
def handle_url(url):
    if "github" in url:
        if len(url.split('/')) > 5:
            words = url.split('/')
            url = "https://github.com/"+words[3]+"/"+words[4]
        elif ".git" in url:
            url = url[:-4]
    return url

def clone_repos(df_fixes):
    """
    Clone repos
    """
    
    repo_urls = df_fixes["repo_url"].apply(lambda x: handle_url(x)).unique()

    pcount = 0
    cnt = 0
    num_repos = len(repo_urls)
    for repo_url in repo_urls:
        # repo_url = "https://github.com/pyrossh/rust-embed"
        if "git" not in repo_url:
            continue
        pcount += 1
        logging.info('-' * 70)
        logging.info("[{}/{}] About to clone {}".format(pcount, num_repos, repo_url))
        full_project_name = get_full_project_name(repo_url)
        repo_dest_path = os.path.join(dest, full_project_name)
        if os.path.exists(repo_dest_path):
            if is_git_repo(repo_dest_path):
                # logging.info("Repository already clone. Skipping.")
                continue
            else:
                shutil.rmtree(repo_dest_path)
        try:
            _ = clone_repo(repo_url, repo_dest_path)
        except Exception as e:
            # logging.info('-' * 70)
            logging.warning("Problem occurred while retrieving the project: {}\n {}".format(repo_url, e))
            cnt += 1
            pass
    print(cnt)

def get_num_vul_has_repo():
    vul_cnt = 0
    df_master = pd.read_sql("SELECT repo_url, package FROM cve", con=db.conn)
    urls = list()
    for url in df_master['repo_url']:
        if url != 'None':
            full_project_name = get_full_project_name(handle_url(url))
            repo_dest_path = os.path.join(dest, full_project_name)
            if os.path.exists(repo_dest_path):
                if is_git_repo(repo_dest_path):
                    urls.append(url)    
    packages = df_master["repo_url"].unique()
    print(f"# of Vulnerabilities: {len(df_master)}")
    print(f"# of Vulnerabilities that have repos: {len(urls)}")
    print(f"# of vulnerable packages: {len(packages)}")
    print(f"# of vulnerable packages that have repos: {len(set(urls))}")

    

if __name__=='__main__':
    # clone_repos(get_ref_links())
    get_num_vul_has_repo()

# git worktree add ../test2
# cd ../test2 
# git checkout <commit-hash>
# git reset --soft HEAD@{1}
