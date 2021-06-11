import zmq
from threading import Thread
import time

def main():
    urls = ["https://google.com"]

    context = zmq.Context()
    socket = context.socket(zmq.REQ)

    socket.connect("tcp://localhost:%s" % 9090)
    socket.connect("tcp://localhost:%s" % 9091)

    while 1:
        time.sleep(2)
        
        for i in urls:
            try:
                # Thread(target = worker, args = (i,), daemon = True).start()
                worker(i, socket)
            except Exception as e:
                print('error')
                print(e)

def worker(url, socket):
    print('into worker')

    socket.send_string(url)
    print('after send')
    
    time.sleep(1)

    ans = socket.recv_json()
    print('after recv')
    # print(ans)

if __name__ == '__main__':
    main()

    # ans = socket.recv(#
    # print(ans)