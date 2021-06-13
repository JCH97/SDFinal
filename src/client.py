import zmq as zmq
import threading
from queue import Queue
import base64 
import sys

class Client:
    def __init__(self, ip, port):
        self.socket = self.build(ip, port)
        self.send = False
        self.resultQueue = Queue()

    def build(self,ip, port):
        context = zmq.Context()
        zmq_req_socket = context.socket(zmq.REQ)
        zmq_req_socket.connect(f"tcp://{ip}:{port}")
        return zmq_req_socket


    def ScanResult(self):
        old_std = sys.stdout
        while True:
            url, Html = self.resultQueue.get()
            r = base64.b64decode(Html)
            if r != b'-1':       
                sys.stdout  = open('Html of '+ url[8:] + '.html', 'w') 
                r = base64.b64decode(Html)
                print(r)
                sys.stdout = old_std
            else:
                print("There was an error trying to retrive de html")
                print('')

    def Send(self):
        while True:
            url = input('url to get HTML: ')
            # self.send = True
            self.socket.send_string(url)
            result = self.socket.recv_json()
            self.resultQueue.put((url,result['data']))

def main():
    ip = str(input('ip to connect to: '))
    port = 5555
    c = Client(ip, port)
    t1 = threading.Thread(target=c.ScanResult,daemon=True)
    t1.start()
    c.Send()


if __name__ == "__main__":
    main()





