import zmq as zmq
import threading
from queue import Queue
import base64 
import sys
import time

class Client:
    def __init__(self, ip, port):
        self.socket = self.build(ip, port)
        self.send = False
        self.resultQueue = Queue()
        

    def build(self,ip, port):
        context = zmq.Context()
        zmq_req_socket = context.socket(zmq.DEALER)
        zmq_req_socket.connect(f"tcp://{ip}:{port}")
        return zmq_req_socket

    def ScanResult(self):
        while True:
            url, Html = self.resultQueue.get()
            
            url = url.replace('/', '')
            if Html != '-1':   
                with open('Html of '+ url + '.html', 'w') as file:
                    file.write(Html)
            else:
                print("There was an error trying to retrive de html")
                print('')

    def Recv(self):
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        time.sleep(0.2)

        while True:
            try:
                with threading.Lock():
                    socks = dict(poller.poll(5000))
                    if socks:
                        if socks.get(self.socket) == zmq.POLLIN:
                            result = self.socket.recv_multipart()
                            url = result[0].decode().replace('/', '')
                            Html = result[1].decode()

                            if Html != '-1':   
                                with open('Html of '+ url + '.html', 'w') as file:
                                    file.write(Html)
                            else:
                                print("There was an error trying to retrive de html")
                                print('')
                    # else:
                    #     print('Seems like there is a problem reaching out the router')
            except Exception as e:
                raise e

    def Send(self):
        while True:
            url = input('url to be scraped: ')
            self.socket.send(url.encode())

def main():
    # ip = str(input('ip to connect to: '))
    port = 5555
    c = Client('127.0.0.1', port)
    t1 = threading.Thread(target=c.Send,daemon=True)
    t2 = threading.Thread(target=c.Recv)
    t1.start()
    t2.start()
    time.sleep(3)


if __name__ == "__main__":
    main()





