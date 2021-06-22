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
    def __init__(self,ip = '127.0.0.1', port = 9092):
        # Queue of available urls
        self.urls_queue = Queue()
        # Queue of available workers
        self.workers_queue = Queue()
        self.available_workers = 0
        self.url_worker = "inproc://workers"
        self.backend,self.frontend,context =  self.build(port,ip)
        self.start(context)

    def build(self, port,ip):        

        # Prepare our context and sockets
        context = zmq.Context()

        frontend = context.socket(zmq.ROUTER)
        frontend.connect(f"tcp://10.0.0.3:9092")
        frontend.connect(f"tcp://10.0.0.4:9092")

        backend = context.socket(zmq.DEALER)
        backend.bind(self.url_worker)

        return backend,frontend,context

    def start(self,context):
        
        NBR_WORKERS = 3

        t1 = threading.Thread(target=self.BalanceWork,daemon=True)
        t1.start()


        # create workers and clients threads
        for i in range(NBR_WORKERS):
            thread = threading.Thread(target=self.worker_thread,
                                    args=(self.url_worker, context, i, ))
            thread.start()

        # Logic of FIFO balance loop   

        # init poller
        poller = zmq.Poller()

        # Always poll for worker activity on backend
        poller.register(self.backend, zmq.POLLIN)

        # Poll front-end only if we have available workers
        poller.register(self.frontend, zmq.POLLIN)

        while True:

            socks = dict(poller.poll())

            # Handle worker activity on backend
            if (self.backend in socks and socks[self.backend] == zmq.POLLIN):

                # Queue worker address for FIFO routing
                message = self.backend.recv_multipart()
                worker_addr = message[0]

                # add worker back to the list of workers
                self.available_workers += 1

                # quitar el with si da palo
                with threading.Lock():
                    self.workers_queue.put(worker_addr)
                
                   
            # poll on frontend only if workers are available
            if self.available_workers > 0:

                if (self.frontend in socks and socks[self.frontend] == zmq.POLLIN):
                    # Now get next client request, route to LRU worker
                    # Client request is [address][empty][request]

                    [broker_addr,client_addr,request,Baseinchord] = self.frontend.recv_multipart()

                    baseURL = request.decode()
                    page = self.scrapp(baseURL)
                    
                   
                    self.FirstLevelSrcap(baseURL, broker_addr, client_addr,
                                        Baseinchord ,request, page)

        #out of infinite loop: do some housekeeping
        time.sleep(1)

        self.frontend.close()
        self.backend.close()
        context.term()

    #scrapeo del html y urls
    def FirstLevelSrcap(self,baseURL,broker_addr,
                        client_addr,Baseinchord,request,page):
        if page == '-1':
            self.frontend.send_multipart([broker_addr,client_addr, 
                                request,b'-1',Baseinchord])
                        
        else:
            html = page.text

            soup = BeautifulSoup(page.content, 'html.parser')

            self.frontend.send_multipart([broker_addr,client_addr, 
                                    request,html.encode(), Baseinchord])

            urls = []
            for link in soup.find_all('a'):
                href: str = link.get('href')
                if href != None and (href.startswith(baseURL) or re.match('^/.+', href)):
                    urls.append(href)

            not_repeted_urls = []
            for u in set(urls):
                url_to_procces = baseURL + u
                self.urls_queue.put((broker_addr,client_addr,url_to_procces.encode()))
            

    def BalanceWork(self):
       while True:
            broker_addr, client_addr, url = self.urls_queue.get()
            self.available_workers += -1
            worker_id = self.workers_queue.get() 
            self.backend.send_multipart([worker_id,
                                broker_addr, client_addr, url])

    def worker_thread(self,worker_url, context, i):
        """ Worker using DEALER socket to do FIFO routing """

        socket = context.socket(zmq.DEALER)

        # set worker identity
        socket.identity = (u"Worker-%d" % (i)).encode('ascii')
        socket.connect(worker_url)

        # Tell the broker we are ready for work
        socket.send_multipart([socket.identity,b"READY"])

        try:
            while True:
                
                worker_addr, broker_address,client_address, request = socket.recv_multipart()

                url = request.decode('ascii')

                print("%s: %s\n" % (socket.identity.decode('ascii'),
                                url ), end='')

                r = '-1'
                
                try:
                    r = self.LookUrlInChord(getHash(url), url)          
                except CommunicationError:
                    r = self.scrapp(url)
                    if r != '-1':
                        r = r.text
                        self.SaveInChord(url, r,0)

                socket.send_multipart([socket.identity,b"READY"])

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
            chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
            html = chord_node_with_html.GetUrl(url)
            if html:
                return html
            raise CommunicationError
            
        else:
            raise CommunicationError

    def SaveInChord(self, url, html,was_scraped):
        try:
            id = getHash(url)
            entry_point = self.FindEntryPoint()
            if entry_point:
                chord_node_id = entry_point.LookUp(id)
                chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
                chord_node_with_html.Save(url,html,was_scraped)
            else: 
                return None
        except CommunicationError:
            print('ERRRRRROORRRRR')
            pass
            

    def scrapp(self, url):
        try:
            return requests.get(url)   
        except:  
            print(f'An error occurr while retriaving HTML from {url}.') 
            return '-1'        
            


if __name__ == '__main__':
    ScrapperNode()