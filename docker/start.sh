#!/usr/bin/env bash

source /venv/bin/activate
cd /usr/vcycle
git pull
python setup.py install
python vcycle/main.py
deactivate

#docker run -it -v /etc/vcycle:/etc/vcycle -v /var/log/vcycle:/var/log/vcycle lvillazo/vcycle