FROM python:3.7-alpine

RUN pip install Pyro4

WORKDIR /chord