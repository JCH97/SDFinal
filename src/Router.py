import Pyro4
import Pyro4.util
from Pyro4.errors import PyroError, CommunicationError
import time
import threading
import zmq
import hashlib
import const
import sys

sys.excepthook = Pyro4.util.excepthook  
    
def tprint(msg):
    """like print, but won't get newlines confused with multiple threads"""
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()

def getHash(key):
    result = hashlib.sha1(key.encode())
    return int(result.hexdigest(), 16) % const.MAX_NODES

class ServerTask(threading.Thread):
    """ServerTask"""
    def __init__(self):
        threading.Thread.__init__ (self)


    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind('tcp://*:5555')

        backend = context.socket(zmq.DEALER)
        backend.bind('inproc://backend')

        for i in range(5):
            worker = ServerWorker(context)
            worker.start()

        zmq.proxy(frontend, backend)

        frontend.close()
        backend.close()
        context.term()

class ServerWorker(threading.Thread):
    """ServerWorker"""
    def __init__(self, context):
        threading.Thread.__init__ (self)
        self.context = context

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')
        tprint('Worker started')

        context = zmq.Context.instance()
        socketForScraper = context.socket(zmq.DEALER)
       
        socketForScraper.connect(f"tcp://10.0.0.3:9091")
        socketForScraper.connect(f"tcp://10.0.0.4:9091")

        poller = zmq.Poller()
        poller.register(socketForScraper, zmq.POLLIN)
        poller.register(worker, zmq.POLLIN)
        r = None
        url = None
        ident = None

        while True:
            socks = dict(poller.poll(4000))
            if (worker in socks and socks[worker] == zmq.POLLIN):
                ident, url = worker.recv_multipart(zmq.NOBLOCK)
                 
                r = self.CheckInChord(url.decode())
                if r:
                    worker.send_multipart([ident,url,r[0].encode()])

                    if r[1] == 0:
                        socketForScraper.send_multipart([url,b'1'])
                else:
                     socketForScraper.send_multipart([url,b'0'])


            if (socketForScraper in socks and socks[socketForScraper] == zmq.POLLIN):
                    result = socketForScraper.recv_multipart(zmq.NOBLOCK)
                    tprint('Worker received %s from scraper' % result[0])
                    url = result[0].decode()
                    data = result[1].decode()
                    
                    worker.send_multipart([ident,result[0],result[1]])
                       
        worker.close()

    def CheckInChord(self,url):
        hashedUrl = getHash(url)
        return self.LookUrlInChord(hashedUrl,url) 
       

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
        try:
            id = hashedUrl  
            print('nodo donde deberia estar ', id)
            entry_point = self.FindEntryPoint() 
            if entry_point:
                chord_node_id = entry_point.LookUp(id)
                print('nodo en el que voy a buscar', chord_node_id)

                chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
                return chord_node_with_html.GetUrl(url)
            else:
                return None

        except CommunicationError as e:
            print(e)
            return None


def main():
   
    server = ServerTask()
    server.start()
    server.join()

if __name__ == '__main__':
    main()

