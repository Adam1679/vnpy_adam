#!/usr/bin/env bash
# 以 shell 方式启动容器，环境如同 Linux 命令行

cd ..

## Run docker container, mapping the ssh and vnc ports, then run bash terminal:
docker run --name vnpy_bash --rm \
    --add-host="docker.host:172.17.0.1" \
    -v `pwd`:/srv/vnpy \
    -p 2222:22 \
    -it vnpy:latest \
    /bin/bash


# docker run --name vnpy_bash --rm -v c:/vnpy:/srv/vnpy  -p 2222:22   -it vnpy:latest   /bin/bash