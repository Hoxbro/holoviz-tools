#!/usr/bin/env bash

TOOLS=~/Repos/holoviz-tools/scripts

ccd() {
    cd $HOLOVIZ_DEV

    # For activating conda environment
    CONDA_PATH=$(conda info | grep -i 'base environment' | awk '{print $4}')
    source $CONDA_PATH/etc/profile.d/conda.sh
    conda activate holoviz
}

if [[ (-z $1 && -z $(pgrep code -a | grep holoviz)) || ($1 == "code") ]]; then
    ccd
    code $HOLOVIZ_DEV/holoviz.code-workspace
elif [[ $1 == "lab" ]]; then
    ccd
    if [[ $(jupyter server list 2>&1 | grep -o "localhost:8888" | wc -l) -eq 0 ]]; then
        BOKEH_RESOURCES=inline jupyter lab --port 8888 $HOLOVIZ_DEV &>/tmp/jupyter_server.log & disown
    else
        firefox localhost:8888
    fi
elif [[ $1 == "save" ]]; then
    conda run -n holoviz python $TOOLS/save.py $2
elif [[ $1 == "fetch" ]]; then
    bash $TOOLS/fetch.sh
elif [[ $1 == "setup" ]]; then
    bash $TOOLS/setup.sh "CLEAN"
elif [[ $1 == "update" ]]; then
    bash $TOOLS/setup.sh "UPDATE"
elif [[ $1 == "sync" ]]; then
    bash $TOOLS/setup.sh "SYNC"
elif [[ $1 == "clean" ]]; then
    ccd
    python $TOOLS/cleanup.py
elif [[ $1 == "action-status" ]]; then
    python $TOOLS/action_status.py
elif [[ $1 == "version-finder" ]]; then
    python $TOOLS/version_finder.py
elif [[ $1 == "autocomplete" ]]; then
    sudo cp $TOOLS/../completion/holoviz-completion.bash /etc/bash_completion.d/holoviz-completion.bash
    sudo cp $TOOLS/../completion/holoviz-completion.zsh /usr/share/zsh/functions/Completion/Base/_holoviz
elif [[ $1 == "changelog" ]]; then
    python $TOOLS/changelog.py
fi
