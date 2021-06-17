# from http.client import HTTPConnection
from __future__ import print_function
import threading
import time
import zmq
# import urllib3
import requests

from threading import Thread

class ScrapperNode:
    def __init__(self,ip='127.0.0.1', port = 9091):
        self.build(port,ip)

    def build(self, port,ip):
        """Server routine"""
        NBR_WORKERS = 1
        # url_worker = "inproc://workers"
        # url_client = f"tcp://*:{port}"

        # # Prepare our context and sockets
        # context = zmq.Context.instance()

        # # Socket to talk to clients
        # frontend = context.socket(zmq.ROUTER)
        # # clients.connect(f"tcp://{ip}:%s" % port)
        # frontend.bind(url_client)

        # # Socket to talk to workers
        # backend = context.socket(zmq.ROUTER)
        # backend.bind(url_worker)

        # Launch pool of worker threads
        # for i in range(5):
        #     Thread(target = self.worker_routine, args=(url_worker,), daemon = True).start()

        url_worker = "inproc://workers"
        url_client = f"tcp://*:{port}"
        # client_nbr = NBR_CLIENTS

        # Prepare our context and sockets
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind(url_client)
        backend = context.socket(zmq.DEALER)
        backend.bind(url_worker)

        # create workers and clients threads
        for i in range(NBR_WORKERS):
            thread = threading.Thread(target=self.worker_thread,
                                    args=(url_worker, context, i, ))
            thread.start()

        # for i in range(NBR_CLIENTS):
        #     thread_c = threading.Thread(target=client_thread,
        #                                 args=(url_client, context, i, ))
        #     thread_c.start()

        # Logic of LRU loop
        # - Poll backend always, frontend only if 1+ worker ready
        # - If worker replies, queue worker as ready and forward reply
        # to client if necessary
        # - If client requests, pop next worker and send request to it

        # Queue of available workers
        available_workers = 0
        workers_list = []

        # init poller
        poller = zmq.Poller()

        # Always poll for worker activity on backend
        poller.register(backend, zmq.POLLIN)

        # Poll front-end only if we have available workers
        poller.register(frontend, zmq.POLLIN)

        while True:

            socks = dict(poller.poll())

            # Handle worker activity on backend
            if (backend in socks and socks[backend] == zmq.POLLIN):

                # Queue worker address for LRU routing
                message = backend.recv_multipart()
                assert available_workers < NBR_WORKERS

                worker_addr = message[0]

                # add worker back to the list of workers
                available_workers += 1
                workers_list.append(worker_addr)

                #   Second frame is empty
                # empty = message[0]
                # assert empty == b""

                # Third frame is READY or else a client reply address
                response = message[2]

                # If client reply, send rest back to frontend
                if response != b'READY':
                    client_addr = message[0]
                    # Following frame is empty
                    empty = message[1]
                    assert empty == b""

                    reply = message[2]

                    frontend.send_multipart([client_addr, b"", reply])

                    # client_nbr -= 1

                    # if client_nbr == 0:
                    #     break  # Exit after N messages

            # poll on frontend only if workers are available
            if available_workers > 0:

                if (frontend in socks and socks[frontend] == zmq.POLLIN):
                    # Now get next client request, route to LRU worker
                    # Client request is [address][empty][request]

                    [client_addr, empty, request] = frontend.recv_multipart()

                    assert empty == b""

                    #  Dequeue and drop the next worker address
                    available_workers += -1
                    worker_id = workers_list.pop()

                    backend.send_multipart([worker_id,
                                            client_addr, request])

        #out of infinite loop: do some housekeeping
        time.sleep(1)

        frontend.close()
        backend.close()
        context.term()


# if __name__ == "__main__":
#     main()


    def worker_thread(self,worker_url, context, i):
        """ Worker using REQ socket to do LRU routing """

        socket = context.socket(zmq.DEALER)

        # set worker identity
        socket.identity = (u"Worker-%d" % (i)).encode('ascii')

        socket.connect(worker_url)

        # Tell the broker we are ready for work
        socket.send_multipart([socket.identity,b'',b"READY"])

        try:
            while True:
                # a = socket.recv_multipart()
                _, address, request = socket.recv_multipart()

                url = request.decode('ascii')

                print("%s: %s\n" % (socket.identity.decode('ascii'),
                                url ), end='')

                r = self.scrapp(url)

                socket.send_multipart([address, b'', r.encode()])

        except zmq.ContextTerminated:
            # context terminated so quit silently
            return


    def worker_routine(self, worker_url, context = None):
        """Worker routine"""
        context = context or zmq.Context.instance()
        # Socket to talk to dispatcher
        socket = context.socket(zmq.REQ)
        socket.connect(worker_url)

        while True:

            addr  = socket.recv_multipart()
            # url = data.decode()
            print("Received request: [ %s ]" % (url))
            
            # do some 'work'
            r = self.scrapp(url)
            # print(r)
            # a = {'data': r}
            socket.send_multipart(addr,b'',r)

    def scrapp(self, url):
        try:
            return requests.get(url).text   
        except:  
            print(f'An error occurr while retriaving HTML from {url}.') 
            return '-1'        
            


if __name__ == '__main__':
    ScrapperNode()