#!/usr/bin/env bash

cd ..

docker run --name vnpy_data_recording \
    --add-host="www.okex.com:104.25.20.25" \
    --add-host="real.okex.com:47.90.109.236" \
    --memory="4g" \
    --restart unless-stopped \
    -v `pwd`:/srv/vnpy \
    -v $HOME/strategy_live:/srv/strategy_live \
    -d vnpy:latest  \
    /bin/bash -c \
    "python setup.py install && cd /srv/strategy_live/DataRecording && python runDataRecording.py"