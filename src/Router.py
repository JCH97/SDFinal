import Pyro4
import Pyro4.util
from Pyro4.errors import PyroError, CommunicationError
import time
import threading
import zmq
import sys
import base64 
import hashlib
import const

sys.excepthook = Pyro4.util.excepthook  

class RouterNode:
    def __init__(self, port):
        self.BuildConn(port)
    
    def getHash(self, key):
        result = hashlib.sha1(key.encode())
        return int(result.hexdigest(), 16) % const.MAX_NODES
    
    def BuildConn(self,port):
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
            threading.Thread(name=f'hilo-{i}', target=self.worker_routine, args=(url_worker,), daemon = True).start()

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

        socketForScraper = context.socket(zmq.REQ)
        socketForScraper.connect(f"tcp://10.0.0.3:9091") 
        socketForScraper.connect(f"tcp://10.0.0.4:9091")
       

        poller = zmq.Poller()
        poller.register(socketForScraper, zmq.POLLIN)

        while True:
            url  = socket.recv_string()
            print("Received request: [ %s ]" % (url))
            print(threading.current_thread().getName())
            
            r = self.CheckInChord(url,socketForScraper)
            if not r:
                socketForScraper.send_string(url)

                socks = dict(poller.poll(4000))
                if socks:
                    if socks.get(socketForScraper) == zmq.POLLIN:
                        r = socketForScraper.recv(zmq.NOBLOCK)
                        # print(r['data'])
                        data = r.decode()
                        
                        socket.send_json({'data':data})
                        # result = r['data']

                        if data != '-1':
                            self.SaveInChord(url, data)
                else:
                    socket.send_json({'data': '-1'})
                
            else:
                # decoded = base64.b64decode(r['data'])

                socket.send_json({'data':r})
                

    def CheckInChord(self,url,socketForScraper):
        hashedUrl = self.getHash(url)
        # try:
        s = self.LookUrlInChord(hashedUrl,url) 
        return s
        # except :
        #     print("Error")
            
    def SaveInChord(self, url, html):
        try:
            id = self.getHash(url)
            entry_point = self.FindEntryPoint() #Pyro4.Proxy(f"PYRONAME:Node.{8}")#aki hay q poner mas de uno por si falla
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
            id = hashedUrl % const.MAX_NODES 
            print('nodo donde deberia estar ', id)
            entry_point = self.FindEntryPoint() #Pyro4.Proxy(f"PYRONAME:Node.{8}")#aki hay q poner mas de uno por si falla
            if entry_point:
                chord_node_id = entry_point.LookUp(id)
                print('nodo en el que voy a buscar', chord_node_id)

                chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
                c = chord_node_with_html.GetUrl(url)
                return c
            else:
                return None

        except CommunicationError:
            print('ERRRRRROORRRRR')
            return None
            #probar otro entry point
            pass


def main():
    RouterNode(5555)

if __name__ == '__main__':
    main()

