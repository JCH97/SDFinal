import zmq as zmq
import threading
from queue import Queue
import base64 
import sys
import time
import urllib
import re
import os

class Client:
    def __init__(self, ipList, port):
        self.socket = self.build(ipList, port)
        self.send = False
        self.resultQueue = Queue()
        

    def build(self, ipList, port):
        context = zmq.Context()
        zmq_req_socket = context.socket(zmq.DEALER)

        for ip in ipList:
            print(ip)
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
                            url = result[0].decode().replace('/', '').replace(':', '.')
                            Html = result[1].decode()

                            pattern = re.compile('[^a-zA-Z0-9]')
                            file = re.sub(pattern, '.', url)

                            if Html != '-1':   
                                with open(f'{os.getcwd()}/htmls/{file}.html', 'w') as file:
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
    try:
        urllib.request.urlopen("https://google.com", timeout = 1)
    except Exception:
        print("Check your internet connection.")

    # ip = str(input('ip to connect to: '))
    regex = "^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"

    print('Set ips to connect, by default are avaliable 10.0.0.7 and 10.0.0.8')
    
    ipList = []
    while 1:
        ip = input("IP -- Press ENTER to continue: ")

        if ip == "":
            break

        if re.search(regex, ip):
            ipList.append(ip)
        else:
            print('Wrong ip. Try again. Press ENTER to continue.')

    port = 5555
    c = Client(ipList, port)
    t1 = threading.Thread(target = c.Send, daemon = True)
    t2 = threading.Thread(target = c.Recv)
    t1.start()
    t2.start()
    time.sleep(3)

if __name__ == "__main__":
    main()





