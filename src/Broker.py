import zmq

class Broker():
    # Prepare our context and sockets
    def __init__(self, port_for_clients = 9091, port_for_scrapers = 9092 ):
        self.port_for_clients = port_for_clients
        self.port_for_scrapers = port_for_scrapers
        self.bind()

    def bind(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        backend = context.socket(zmq.DEALER)
        frontend.bind(f"tcp://*:{self.port_for_clients}")
        backend.bind(f"tcp://*:{self.port_for_scrapers}")

        backend.setsockopt(zmq.IDENTITY, b'A')
        zmq.proxy(frontend, backend)

        # We never get here...
        frontend.close()
        backend.close()
        context.term()

def main():
    Broker()

if __name__ == '__main__':
    main()
