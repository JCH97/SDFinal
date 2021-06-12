from http.client import HTTPConnection
import zmq
import time
import base64

from threading import Thread

class ScrapperNode:
    def __init__(self, port = 9091):
        self.build(port)

    def build(self, port):
        """Server routine"""

        url_worker = "inproc://workers"
        url_client = f"tcp://*:{port}"

        # Prepare our context and sockets
        context = zmq.Context.instance()

        # Socket to talk to clients
        clients = context.socket(zmq.ROUTER)
        clients.bind(url_client)

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
            socket.send_json({'data':base64.b64encode(str(r).encode())})

    def scrapp(self, url):
        conexion = HTTPConnection(url)
        try:   
            conexion.request('GET', '/')
            result = conexion.getresponse()
            content = result.read()
            return content
        except Exception as e:            
            print(f'An error occurr while retriaving HTML from {url}. {e}')


if __name__ == '__main__':
    # a = req.get("https://google.com")
    # print('after')

    ScrapperNode()