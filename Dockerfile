FROM python

# RUN apk update && apk add build-base libzmq musl-dev python3 python3-dev zeromq-dev

RUN pip install Pyro4

RUN pip install pyzmq

RUN pip install requests

WORKDIR /chord