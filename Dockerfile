FROM python:3.7-alpine

RUN apk update && apk add build-base libzmq musl-dev python3 python3-dev zeromq-dev

RUN pip install Pyro4

RUN pip install pyzmq

WORKDIR /chord