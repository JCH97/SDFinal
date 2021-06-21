from __future__ import print_function
import threading
import time
import zmq
from queue import Queue
import requests
import re
import Pyro4
import Pyro4.util
from Pyro4.errors import PyroError, CommunicationError
import hashlib
import const

from bs4 import BeautifulSoup
from threading import Thread

def getHash(key):
    result = hashlib.sha1(key.encode())
    return int(result.hexdigest(), 16) % const.MAX_NODES


class ScrapperNode:
    def __init__(self, ip = '10.0.0.3', port = 9092):
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
        frontend.connect(f"tcp://{ip}:{port}")
        frontend.connect(f"tcp://10.0.0.4:9092")

        backend = context.socket(zmq.DEALER)
        backend.bind(url_worker)

        # create workers and clients threads
        for i in range(NBR_WORKERS):
            thread = threading.Thread(target=self.worker_thread,
                                    args=(url_worker, context, i, ))
            thread.start()


        # Logic of FIFO balance loop   

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

                    [broker_addr,client_addr ,request,depth] = frontend.recv_multipart()

                    baseURL = request.decode()
                    page = self.scrapp(baseURL)
                    
                    if depth == b'1':
                        self.FirstLevelSrcap(frontend, backend, baseURL,
                                             broker_addr, client_addr, request, page)

                    else:
                        self.available_workers += -1
                        worker_id = self.workers_queue.get()
                        backend.send_multipart([worker_id,broker_addr, 
                                                client_addr, baseURL.encode()])
           

        #out of infinite loop: do some housekeeping
        time.sleep(1)

        frontend.close()
        backend.close()
        context.term()
        

    # def DepthScrap(self,baseURL,current_depth,top_depth):
    #     self.available_workers += -1
    #     worker_id = self.workers_queue.get()
    #     backend.send_multipart([worker_id,broker_addr, 
    #                             client_addr, baseURL.encode()])

    #     if current_depth == top_depth:
    #         return

    #     for scraped_url in FindUrls(baseURL):
    #         for found_url in self.DepthScrap(scraped_url, current_depth + 1, top_depth):
    #             yield found_url

    # def FindUrls(url):


    # def ParseHtml(url):


    #scrapeo del html y urls
    def FirstLevelSrcap(self,frontend,backend,baseURL,broker_addr,
                        client_addr,request,page):
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


    def BalanceWork(self,backend,not_repeted_urls,baseURL,broker_addr,client_addr):
        for url in not_repeted_urls:
                        self.available_workers += -1
                        worker_id = self.workers_queue.get() 
                        # scraped_url = baseURL + url
                        backend.send_multipart([worker_id,
                                            broker_addr, client_addr, url.encode()])

    def worker_thread(self,worker_url, context, i):
        """ Worker using DEALER socket to do FIFO routing """

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

                r = '-1'
                try:
                    r,_ = self.LookUrlInChord(getHash(url), url)
                except CommunicationError:
                    r = self.scrapp(url)
                    if r != '-1':
                        r = r.text

                socket.send_multipart([worker_addr,broker_address,
                        client_address,request, r.encode()])

        except zmq.ContextTerminated:
            # context terminated so quit silently
            return

    def FindEntryPoint(self):
        with Pyro4.locateNS() as ns:
            for _,node_uri in ns.list(prefix=f"Node").items():
                try:
                    n = Pyro4.Proxy(node_uri)
                    n.IsAlive()
                    return n
                except CommunicationError:
                    continue
            return None

    def LookUrlInChord(self,hashedUrl,url):
        id = hashedUrl  
        entry_point = self.FindEntryPoint() 
        if entry_point:
            chord_node_id = entry_point.LookUp(id)
            print('nodo en el que voy a buscar', chord_node_id)

            chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
            html,hashed_scraped_urls = chord_node_with_html.GetUrl(url)
            print(chord_node_with_html.GetUrls.keys())
            return (html,hashed_scraped_urls)
            
        else:
            raise CommunicationError


            


    def scrapp(self, url):
        try:
            return requests.get(url)   
        except:  
            print(f'An error occurr while retriaving HTML from {url}.') 
            return '-1'        
            


if __name__ == '__main__':
    ScrapperNode()