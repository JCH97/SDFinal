import Pyro4
import Pyro4.util
from Pyro4.errors import PyroError, CommunicationError
import time
import threading
import zmq
import sys
import base64 

sys.excepthook = Pyro4.util.excepthook


def tprint(msg):
    """like print, but won't get newlines confused with multiple threads"""
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()

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

        workers = []
        for i in range(5):
            worker = ServerWorker(context)
            worker.start()
            workers.append(worker)

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
        socketForScraper.connect(f"tcp://127.0.0.1:{9091}") #no se pueden poner puerto e ip fijos
       

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
                r = self.CheckInChord(url,socketForScraper)
                if not r:
                    socketForScraper.send(url)
                else:
                    worker.send_multipart([ident,url,r.encode()])

            if (socketForScraper in socks and socks[socketForScraper] == zmq.POLLIN):
                r1,r2 = socketForScraper.recv_multipart(zmq.NOBLOCK)
                tprint('Worker received %s from scraper' % r1)
                url = r1.decode()
                data = r2.decode()
                
                worker.send_multipart([ident,r1,r2])
               

                if data != '-1':
                    self.SaveInChord(url, data)
             
            #     time.sleep(1. / (randint(1,10)))
           
        worker.close()


    def CheckInChord(self,url,socketForScraper):
        hashedUrl = hash(url)
        return self.LookUrlInChord(hashedUrl,url) 
        
      
            
    def SaveInChord(self, url, html):
        try:
            id = hash(url) % 2 ** 5
            entry_point = self.FindEntryPoint() 
            if entry_point:
                chord_node_id = entry_point.LookUp(id)
                chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
                chord_node_with_html.Save(url,html)
            else: 
                return None
        except CommunicationError:
            print('ERRRRRROORRRRR')
            #probar otro entry point
            pass

    def FindEntryPoint(self):
        with Pyro4.locateNS() as ns:
            for _,node_uri in ns.list(prefix=f"Node").items():
                try:
                    n = Pyro4.Proxy(node_uri)
                    n.IsAlive()
                    return n#si no sirve mandar el id
                except CommunicationError:
                    continue
            return None

    def LookUrlInChord(self,hashedUrl,url):
        try:
            id = hashedUrl % 2 ** 5
            print('nodo donde deberia estar ', id)
            entry_point = self.FindEntryPoint() 
            if entry_point:
                chord_node_id = entry_point.LookUp(id)
                print('nodo en el que voy a buscar', chord_node_id)

                chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
                c = chord_node_with_html.GetUrl(url.decode())
                return c
            else:
                return None

        except CommunicationError:
            print('ERRRRRROORRRRR')
            return None
            #probar otro entry point
            pass



def main():
   
    server = ServerTask()
    server.start()
    server.join()

if __name__ == '__main__':
    main()#ver si hacen falata argumentos, como el puerto

