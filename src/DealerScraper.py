from __future__ import print_function
import threading
import time
import zmq
from queue import Queue
import requests
import re

from bs4 import BeautifulSoup
from threading import Thread

class ScrapperNode:
    def __init__(self,ip='127.0.0.1', port = 9092):
        # Queue of available workers
        self.workers_queue = Queue()
        self.available_workers = 0
        self.build(port,ip)

    def build(self, port,ip):
        """Server routine"""
        NBR_WORKERS = 3

        url_worker = "inproc://workers"
       
        # Prepare our context and sockets
        context = zmq.Context()
       

        frontend = context.socket(zmq.ROUTER)
        frontend.connect(f"tcp://{ip}:%s" % port)

        backend = context.socket(zmq.DEALER)
        backend.bind(url_worker)

        # create workers and clients threads
        for i in range(NBR_WORKERS):
            thread = threading.Thread(target=self.worker_thread,
                                    args=(url_worker, context, i, ))
            thread.start()


        # Logic of FIFo loop
        # - Poll backend always, frontend only if 1+ worker ready
        # - If worker replies, queue worker as ready and forward reply
        # to client if necessary
        # - If client requests, pop next worker and send request to it
       

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

                # Queue worker address for FIFO routing
                message = backend.recv_multipart()
                
                # assert available_workers < NBR_WORKERS

                worker_addr = message[0]

                # add worker back to the list of workers
                self.available_workers += 1

                # quitar el with si da palo
                with threading.Lock():
                    self.workers_queue.put(worker_addr)

                # Third frame is READY or else a client reply address
                response1 = message[3]

                # If client reply, send rest back to frontend
                if response1 != b'READY':
                    broker_addr = message[1]
                    client_addr = message[2]

                    response2 = message[4]
                    print('sending-> ' + response1.decode())

                    frontend.send_multipart([broker_addr,client_addr, response1,response2])

                   
            # poll on frontend only if workers are available
            if self.available_workers > 0:

                if (frontend in socks and socks[frontend] == zmq.POLLIN):
                    # Now get next client request, route to LRU worker
                    # Client request is [address][empty][request]

                    [broker_addr,client_addr ,request] = frontend.recv_multipart()

                    baseURL = request.decode()
                    page = self.scrapp(baseURL)

                    if page == '-1':
                        frontend.send_multipart([broker_addr,client_addr, 
                                            request,b'-1'])
                        
                    else:
                        html = page.text

                        soup = BeautifulSoup(page.content, 'html.parser')

                        urls = []
                        for link in soup.find_all('a'):
                            href: str = link.get('href')
                            if href != None and (href.startswith(baseURL) or re.match('^/.+', href)):
                                urls.append(href)
                        #revisar que no este ahi BaseUrl
                        #preguntarle a jose como es q comprueba q no este Baseurl en el
                        #set, o como mira q no se coja nuevamente en el html

                        not_repeted_urls = []
                        for u in set(urls):
                            not_repeted_urls.append(baseURL + u)
                        
                        encoded_urls=[]
                        for u in not_repeted_urls:
                            encoded_urls.append(u.encode())
                        
                        #ver si se bloquea
                        frontend.send_multipart([broker_addr,client_addr, 
                                                request,html.encode()] + encoded_urls)
                        
                        t1 = threading.Thread(target=self.BalanceWork,
                            args=[backend,not_repeted_urls,baseURL,
                                 broker_addr,client_addr,],daemon=True)

                        t1.start()
                    

        #out of infinite loop: do some housekeeping
        time.sleep(1)

        frontend.close()
        backend.close()
        context.term()

    def BalanceWork(self,backend,not_repeted_urls,baseURL,broker_addr,client_addr):
        for url in not_repeted_urls:
                        self.available_workers += -1
                        worker_id = self.workers_queue.get() 
                        # scraped_url = baseURL + url
                        backend.send_multipart([worker_id,
                                            broker_addr, client_addr, url.encode()])

    def worker_thread(self,worker_url, context, i):
        """ Worker using DEALER socket to do LRU routing """

        socket = context.socket(zmq.DEALER)

        # set worker identity
        socket.identity = (u"Worker-%d" % (i)).encode('ascii')

        socket.connect(worker_url)

        # Tell the broker we are ready for work
        socket.send_multipart([socket.identity,b'',b'',b"READY"])

        try:
            while True:
                # a = socket.recv_multipart()
                worker_addr, broker_address,client_address, request = socket.recv_multipart()

                url = request.decode('ascii')

                print("%s: %s\n" % (socket.identity.decode('ascii'),
                                url ), end='')

                r = self.scrapp(url) #ver si no da palo

                if r != '-1':
                    r = r.text

                socket.send_multipart([worker_addr,broker_address,
                        client_address,request, r.encode()])

        except zmq.ContextTerminated:
            # context terminated so quit silently
            return


    def scrapp(self, url):
        try:
            return requests.get(url)   
        except:  
            print(f'An error occurr while retriaving HTML from {url}.') 
            return '-1'        
            


if __name__ == '__main__':
    ScrapperNode()