import Pyro4
# import zmq
from Pyro4.errors import PyroError, CommunicationError
import time
import threading
import zmq
# import threading
# from queue import Queue
# import socket

# url = 'example.com'

# # clients={}
# # replay_lock = threading.Lock()

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

        while True:

            url  = socket.recv_string()

            print("Received request: [ %s ]" % (url))
            
            # do some 'work'
            r = self.SaveClient(url)
            print(r)
            #send reply back to client
            socket.send_json(r)


    def SaveClient(self,url):
        hashedUrl = hash(url)
        try:
            return self.LookUrlInChord(hashedUrl,url) 
        except :
            print("Error")
            
                
    def LookUrlInChord(self,hashedUrl,url):
        try:
            id = hashedUrl % 2 ** 5
            entry_point = Pyro4.Proxy(f"PYRONAME:Node.{8}")#aki hay q poner mas de uno por si falla
            chord_node_id = entry_point.LookUp(id)
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

