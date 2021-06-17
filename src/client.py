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
        zmq_req_socket = context.socket(zmq.REQ)
        zmq_req_socket.connect(f"tcp://{ip}:{port}")
        return zmq_req_socket

    def ScanResult(self):
        # old_std = sys.stdout
        while True:
            url, Html = self.resultQueue.get()
            # print(Html)
            # print(Html)
            # r = base64.b64decode(Html)
            # print(r)
            url = url.replace('/', '')
            if Html != '-1':   
                with open('Html of '+ url + '.html', 'w') as file:
                    file.write(Html)
                    # sys.stdout  = 
                    # print(Html.encode('utf-8'))
                    # sys.stdout = old_std
            else:
                print("There was an error trying to retrive de html")
                print('')

    def Send(self):
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)

        # for i in range(1):
        time.sleep(0.2)
        # url = input('url to get HTML: ')
        # print('')
        url = 'https://facebook.com'
        self.socket.send_string(url)
        socks = dict(poller.poll(5000))
        if socks:
            if socks.get(self.socket) == zmq.POLLIN:
                result = self.socket.recv_json(zmq.NOBLOCK)
                # print(result['data'])
                self.resultQueue.put((url,result['data']))
        else:
            print('Seems like there is a problem reaching out the router')

def main():
    # ip = str(input('ip to connect to: '))
    port = 5555
    c = Client('127.0.0.1', port)
    t1 = threading.Thread(target=c.ScanResult,daemon=True)
    t1.start()
    c.Send()
    time.sleep(3)


if __name__ == "__main__":
    main()





