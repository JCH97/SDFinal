FROM python:3.7

RUN pip install Pyro4 pyzmq requests beautifulsoup4

WORKDIR /chord