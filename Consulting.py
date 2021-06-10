import Pyro4
import zmq
from Pyro4.errors import PyroError, CommunicationError
import threading
from queue import Queue
import socket

url = 'example.com'

# clients={}
# replay_lock = threading.Lock()

class RouterNode:
    def __init__(self,port):
        self.clients = {}
        self.replay_lock = threading.Lock()
        self.socket = self.BindPort(port)
        self.tcp_queue = Queue()
    
    def BindPort(self,port):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://localhost:%s" % port)
        # context = zmq.Context()
        # socket = context.socket(zmq.REP)
        # socket.bind("tcp://*:%s" % port)   
        return socket


    def SaveClient(self, address, url):
        print("Recibi la url en SaveClient 1")
        with threading.Lock():
            print("Recibi la url en SaveClient 1121")
            hashedUrl = hash(url)
            print("Recibi la url en SaveClient 2")
            try:
                print("Recibi la url en SaveClient 3")
                self.clients[hashedUrl].append(address)
            except KeyError:
                print("como no tego la url voy a crear la nueva lista")
                self.clients[hashedUrl] = [address]
                r = self.LookUrlInChord(hashedUrl,url)
                self.ProccessReplay(hashedUrl,r)

    def LookUrlInChord(self, hashedUrl, url):
        try:
            id = hashedUrl % 2 ** 5
            entry_point = Pyro4.Proxy(f"PYRONAME:Node.{8}")#aki hay q poner mas de uno por si falla
            chord_node_id = entry_point.LookUp(id)
            chord_node_with_html = Pyro4.Proxy(f"PYRONAME:Node.{chord_node_id}")
            c = chord_node_with_html.GetUrl(url)
            print('url q kiero buscar ' + url)
            return c
        except CommunicationError:
            print('ERRRRRROORRRRR')
            #probar otro entry point
            pass

    def ProccessReplay(self, hashedUrl, result):
        print("hasta aki llego")
        with threading.Lock():
            for s in self.clients[hashedUrl]:
                s.send_json({'data':'hola'})

    def RecvMesgWorker(self):
        while 1:
            with threading.Lock():
                try:
                    data = self.socket.recv()
                    self.tcp_queue.put(data)
                except:
                    print("error al recibir msg")

    def SenderWorker(self):
        while True:
            if tcp_queue.size() > 0:
                url = self.tcp_queue.get()
                print(url)
                self.SaveClient(url)

    def InitiateToSend(self, thread_worker_numbers = 1):
        for _ in range(thread_worker_numbers):
            threading.Thread(target = self.SenderWorker, daemon = True).start()

    def InitiateToRecv(self, thread_worker_numbers = 1):
        for _ in range(thread_worker_numbers):
            threading.Thread(target = self.RecvMesgWorker, daemon = True).start()

    def Start(self):   
        self.InitiateToRecv()
        self.InitiateToSend(self.socket)
        while 1:
            if threading.activeCount() > 1:
                continue
            else:
                break

def main():
    r = RouterNode(5560)
    # tcp_queue = Queue()
    r.Start()

if __name__ == '__main__':
    main()#ver si hacen falata argumentos, como el puerto
