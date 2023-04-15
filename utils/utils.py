import re
from git import Repo, exc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def adjust_message(message):
    message_no_carriage = message.replace("\r", "\n")
    one_newline_message = re.sub(r"\n+", "\n", message_no_carriage)
    clear_message = one_newline_message.replace("\n", ". ").replace("\t", " ").replace(",", " ").replace("\"", "'")
    stripped_message = clear_message.strip()
    return re.sub(r" +", " ", stripped_message)

def get_full_project_name(repo_url):
    org_name = repo_url.rsplit('/', 2)[1]
    project_name = repo_url.rsplit('/', 2)[2]
    return org_name + "_" + project_name

def is_git_repo(path):
    try:
        _ = Repo(path).git_dir
        return True
    except exc.InvalidGitRepositoryError:
        return False
    
def plot_evolution(x, y, ylabel, savepath, evol=True, xlog=False, ylog=False):
    plt.ioff()
    plt.style.use('seaborn-colorblind') 
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    ax.plot(x, y,color='navy')
    ax.set(ylabel=ylabel)
    ax.tick_params(labelsize=25)
    ax.yaxis.label.set_size(25)
    ax.title.set_size(20)
    if evol:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        fig.autofmt_xdate()
    if xlog:
        ax.set_xscale('symlog')
    ax.grid(True, linestyle='--', which="major")
    fig.savefig(savepath, facecolor='white', dpi=200) 