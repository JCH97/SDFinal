import requests as req
import zmq
import time

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
            # print(r)
            #send reply back to client
            socket.send_json(r)

    # def recv(self):
    #     while 1:
    #         print('wait')
    #         url = self.sock.recv()
    #         # self.sock.send_string("check")

    #         Thread(target = self.scrapp, args = (url,), daemon = True).start()

    #         time.sleep(5)

    def scrapp(self, url):
        ans = req.get(url)
        return ans.text

        # print(ans.text)

if __name__ == '__main__':
    # a = req.get("https://google.com")
    # print('after')

    ScrapperNode()