FROM python

RUN pip install Pyro4 pyzmq requests beautifulsoup4

WORKDIR /chord