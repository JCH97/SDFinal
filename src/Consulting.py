import Pyro4
import Pyro4.util
from Pyro4.errors import PyroError, CommunicationError
import time
import threading
import zmq
import sys
import base64 

sys.excepthook = Pyro4.util.excepthook

class RouterNode:
    def __init__(self,port):
        self.BuildConn(port)
    
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
            threading.Thread(target=self.worker_routine, args=(url_worker,), daemon = True).start()

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
        socketForScraper.connect(f"tcp://127.0.0.1:{9091}")
        socketForScraper.connect(f"tcp://127.0.0.1:{9092}")#no se pueden poner puerto e ip fijos
        socketForScraper.connect(f"tcp://127.0.0.1:{9095}")
        socketForScraper.connect(f"tcp://127.0.0.1:{9096}")
        socketForScraper.connect(f"tcp://127.0.0.1:{9098}")
        socketForScraper.connect(f"tcp://127.0.0.1:{9099}")
        socketForScraper.connect(f"tcp://127.0.0.1:{8095}")
        socketForScraper.connect(f"tcp://127.0.0.1:{9596}")

        poller = zmq.Poller()
        poller.register(socketForScraper, zmq.POLLIN)
        poller.register(socket,zmq.POLLIN)

        while True:
            socks = dict(poller.poll())
            if socket in socks and socks[socket] == zmq.POLLIN:
                url  = socket.recv_string()
                print("Received request: [ %s ]" % (url))
                
                r = self.CheckInChord(url,socketForScraper)
                if not r:
                    socketForScraper.send_string(url)

                    socks = dict(poller.poll(2000))
                    if socks:
                        if socks.get(socketForScraper) == zmq.POLLIN:
                            r = socketForScraper.recv_json(zmq.NOBLOCK)
                            # print("got message ",work_receiver.recv(zmq.NOBLOCK))

                    # r = socketForScraper.recv_json()
                            socket.send_json(r)

                            result = base64.b64decode(r['data'])
                            if result != b'-1':
                                self.SaveInChord(url, r['data'])
                    
                else:
                    socket.send_json(r)
                

    def CheckInChord(self,url,socketForScraper):
        hashedUrl = hash(url)
        # try:
        s = self.LookUrlInChord(hashedUrl,url) 
        print(s)
        return s
        # except :
        #     print("Error")
            
    def SaveInChord(self, url, html):
        try:
            id = hash(url) % 2 ** 5
            entry_point = Pyro4.Proxy(f"PYRONAME:Node.{8}")#aki hay q poner mas de uno por si falla
            chord_node_id = entry_point.LookUp(id)
            chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
            chord_node_with_html.Save(url,html)
        except CommunicationError:
            print('ERRRRRROORRRRR')
            #probar otro entry point
            pass

    def LookUrlInChord(self,hashedUrl,url):
        try:
            id = hashedUrl % 2 ** 5
            print('nodo donde deberia estar ', id)
            entry_point = Pyro4.Proxy(f"PYRONAME:Node.{8}")#aki hay q poner mas de uno por si falla
           
            chord_node_id = entry_point.LookUp(id)
            print('nodo en el que voy a buscar', chord_node_id)

            chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
            c = chord_node_with_html.GetUrl(url)
            return c

        except CommunicationError:
            print('ERRRRRROORRRRR')
            #probar otro entry point
            pass


def main():
    r = RouterNode(5555)

if __name__ == '__main__':
    main()#ver si hacen falata argumentos, como el puerto

