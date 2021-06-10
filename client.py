import zmq as zmq
import threading
from queue import Queue

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

    # def Recive(self):
    #     while True:
    #         # try:
    #         if self.send:
    #             result = self.socket.recv_string()
    #             if result != 'ack':
    #                 print(result)
    #         # except:
    #         #     print('An error occurred')
    #         #     break

    def ScanResult(self):
        while True:
            Html = self.resultQueue.get()
            print(Html)

    def Send(self):
        while True:
            url = input('url to get HTML: ')
            # self.send = True
            self.socket.send_string(url)
            result = self.socket.recv_json()
            self.resultQueue.put(result['data'])

def main():
    ip = str(input('ip to connect to: '))
    port = 5559
    c = Client(ip, port)
    t1 = threading.Thread(target=c.ScanResult,daemon=True)
    
    # t2 = threading.Thread(target=c.Send,daemon=True)
    t1.start()
    # t2.start()
    c.Send()
    # t2.join()

if __name__ == "__main__":
    main()





