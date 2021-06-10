import zmq
import threading
import time
import socket
import selectors
import sys
import types

class RouterNode: 
    def __init__(self, host, port):
        self.sel = selectors.DefaultSelector()

        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((host, port))
        lsock.listen()
        lsock.setblocking(False)

        self.sel.register(lsock, selectors.EVENT_READ, data = None)

        threading.Thread(target = recv, daemon = True).start()
    
    def accept_wrapper(self, sock):
        conn, addr = sock.accept()
        print("accepted connection from", addr)
        conn.setblocking(False)
        data = types.SimpleNamespace(addr = addr, inb = b"", outb = b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data = data)

    def service_connection(self, key, mask):
        sock, data = key.fileobj, key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                data.outb += recv_data
            else:
                print("closing connection to", data.addr)
                self.sel.unregister(sock)
                sock.close()
            
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                # send answer
                print("echoing", repr(data.outb), "to", data.addr)
                data.outb = b""

    def recv(self):
        try:
            while True:
                events = self.sel.select(timeout = None)
                for key, mask in events:
                    if key.data is None:
                        accept_wrapper(key.fileobj)
                    else:
                        service_connection(key, mask)
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

def main(host, port):
    contextBroadcast = zmq.Context()
    socketBroadcast = contextBroadcast.socket(zmq.PUB)
    socketBroadcast.bind("tcp://*:3001")

if __name__ == '__main__':
    try: 
        host, port = sys.argv[1].split(':')
    except IndexError: 
        raise "Please, pass host and port in format -> host:port"
    
    main(host, int(port))