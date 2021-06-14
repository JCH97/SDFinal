from http.client import HTTPConnection
import zmq
import time
import base64
import urllib3
import requests

from threading import Thread

class ScrapperNode:
    def __init__(self,ip='127.0.0.1', port = 9092):
        self.build(port,ip)

    def build(self, port,ip):
        """Server routine"""

        url_worker = "inproc://workers"
        # url_client = f"tcp://*:{port}"

        # Prepare our context and sockets
        context = zmq.Context.instance()

        # Socket to talk to clients
        clients = context.socket(zmq.ROUTER)
        clients.connect(f"tcp://{ip}:%s" % port)
        # clients.bind(url_client)

        # Socket to talk to workers
        workers = context.socket(zmq.DEALER)
        workers.bind(url_worker)

        # Launch pool of worker threads
        for i in range(5):
            Thread(target = self.worker_routine, args=(url_worker,), daemon = True).start()

        zmq.proxy(clients, workers)

        # We never get here but clean up anyhow
        clients.close()
        workers.close()
        context.term()

    def worker_routine(self, worker_url, context = None):
        """Worker routine"""
        context = context or zmq.Context.instance()
        # Socket to talk to dispatcher
        socket = context.socket(zmq.REP)
        socket.connect(worker_url)

        while True:

            url  = socket.recv_string()

            print("Received request: [ %s ]" % (url))
            
            # do some 'work'
            r = self.scrapp(url)
            print(r)
            a = {'data':base64.b64encode(str(r).encode())}
            socket.send_json(a)

    def scrapp(self, url):
        try:
            return requests.get(url).text   
        except:  
            print(f'An error occurr while retriaving HTML from {url}.') 
            return -1        
            


if __name__ == '__main__':
    ip =input("ip to connect to broker: ")
    p=None
    try:
        p =int(input("Port to connect to broker: "))
    except:
        pass

    ScrapperNode(ip,p)