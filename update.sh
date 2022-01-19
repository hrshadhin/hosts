#!/bin/bash
#title           :update.sh
#description     :Generate hosts files & push to git remote
#author          :H.R. Shadhin <dev@hrshadhin.me>
#date            :2022-01-18
#version         :1.0
#usage           :update.sh
#bash_version    :4.4.20(1)-release
#==============================================================

source venv/bin/activate
echo "*********** + ***********"
make pull
echo "*********** + ***********"
make build-for-hrs
echo "*********** + ***********"
make push
echo "*********** 0 ***********"
