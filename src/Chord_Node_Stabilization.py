import Pyro4
import sys
import Pyro4.util
from Pyro4.errors import PyroError, CommunicationError
import threading
import random
import sched
import time
from collections import deque
from http.client import HTTPConnection
import base64


Pyro4.config.SERIALIZER = 'serpent'
sys.excepthook = Pyro4.util.excepthook

def recover_from_failure(func):
    def wrapper(self, *args, **kwargs):
        while True:
            try:
                return func(self, *args, **kwargs)
            except CommunicationError:
                with self._successor_lock:
                    self.OutSuccessor()
    return wrapper

class KeyOutOfRange(BaseException):
    def __str__(self):
        return 'A key used in a lookup was outside the allowed kay space'


@Pyro4.expose
class Node:
    def __init__(self,id = None, Daemon = None):
        self._bitsKey = None
        self._id = id
        self._fingerTable = None
        self._successorList = deque(maxlen=4)
        self._predecesor = None
        self._node_uri = None
        self._successors_uri = None
        self._successor_lock = threading.Lock()
        self._predeccesor_lock = threading.Lock()
        self.alive = False
        self.previousSucc = None
        self.urls = {}
    
        if Daemon:
            self.uri = Daemon.register(self)
            if id == None:
                self.fixKey()
                self.key = hash(self.uri) % 2**self._bitsKey

            with Pyro4.locateNS() as ns:
                ns.register(f"Node.{self.key}", self.uri)

    def fixKey(self):
        try:
            mediator = Pyro4.Proxy(f"PYRONAME:Mediator")
            self._bitsKey = mediator.mbits
        except CommunicationError:
            print("Entry point broken try another")
            return

    @property
    def GetUrls(self):
        return self.urls

    @property
    def SuccLock(self):
        return self._successor_lock
    
    @property
    def uri(self):
        return self._node_uri

    @uri.setter
    def uri(self, value):
        self._node_uri = value

    @property
    def bitsKey(self):
        return self._bitsKey

    @bitsKey.setter
    def bitsKey(self, value):
        self._bitsKey = value

    @property
    def getFt(self):
        return self._fingerTable

    @getFt.setter
    def getFt(self, value):
        self._fingerTable = value

    @property
    def key(self):
        return self._id

    @key.setter
    def key(self, value):
        self._id = value

    @property
    def succesor(self):
        return self._fingerTable[1]
        
    @succesor.setter
    def succesor(self,value):
        self._fingerTable[1] = value

    @property
    def predecesor(self):
        return self._predecesor

    @predecesor.setter
    def predecesor(self,value):
        self._predecesor = value

    @property
    def Status(self):
        return self.key, self.uri,\
            self.predecesor if self.predecesor else None, self._successorList,\
                self._fingerTable, self.alive

    def Start(self, i):
        return (self.key + 2**(i-1)) % 2**self._bitsKey

    def OutSuccessor(self):
        nodeout =  self._successorList.popleft()
        self.succesor = self._successorList[0]
        if self.predecesor == nodeout:
            self.predecesor = None
        self.previousSucc = nodeout
      
    def LookUp(self,key):
        if key < 0 or key >= 2**self._bitsKey:
            print('key out of range')
            return

        if key == self.key:
            return key
        return self.FindSuccessor(key)

    def FindSuccessor(self, key):
        with self._successor_lock:
            nId = self.FindPredeccessor(key)     
            n = Pyro4.Proxy(f"PYRONAME:Node.{nId}")
            return n.succesor

    def FindPredeccessor(self, key):
        n = self
        while not self.inbetween(key, n.key + 1, n.succesor + 1):
            nId = n.ClosestToKey(key)
            n = Pyro4.Proxy(f"PYRONAME:Node.{nId}")          
        return n.key

    def ClosestToKey(self,key):
        for i in range(1, self._bitsKey):
            if self.inbetween(self._fingerTable[i], self.key + 1 ,key):
                return self._fingerTable[i]
        return self.key

    def Join(self,uri=None):
        n = None

        if not uri:
            try:
                mediator = Pyro4.Proxy(f"PYRONAME:Mediator")
                n_uri = mediator.GetUriNode(self.uri)
                if n_uri == '-1':
                    raise Exception('Node already en chord\n')
                if n_uri != '':
                    n = Pyro4.Proxy(n_uri)
                self._bitsKey = mediator.mbits
            except CommunicationError:
                raise Exception("Entry point broken try another\n")
                return
        else:
            try:
                n = Pyro4.Proxy(uri)
                n_uri = n.uri 
                self._bitsKey = n.bitsKey
            except CommunicationError:
                raise Exception("Entry point broken try another\n")
                
        
        if self.key<0 or self.key>2**self._bitsKey-1:
            raise Exception(f"Node out of range, the id must be between [{0}, {2**self._bitsKey-1}]\n")


        self._fingerTable = [None]*(self.bitsKey + 1)

        if n_uri != '':
            try:
                self.succesor = n.FindSuccessor(self.key)
                self._successorList.append(self.key)
                self.GetUrlsFromSuccesor()   
                if n.key == self.key:
                    raise Exception('Node already in chord\n')

            except CommunicationError:
                print("Successor broken \n")
        else:
            self.succesor = self.key

        self._successorList.appendleft(self.succesor)
        self.InitiateNode()

    @recover_from_failure
    def Stabilize(self):
        # try:
        succesor = Pyro4.Proxy(f"PYRONAME:Node.{self.succesor}")
        if succesor.predecesor == self.previousSucc:
            succesor.predecesor = None
        if succesor.predecesor and self.inbetween(succesor.predecesor, self.key + 1, succesor.key,stabilizing=True):
            with self._successor_lock:
                self.succesor = succesor.predecesor
                self._successorList.appendleft(self.succesor)
                self.GetUrlsFromSuccesor()              
    
        succesor.Notify(self._id)
        # except:
        #     pass
        #    succesor.Notify(self._id)
     

    def Notify(self,id):
        try:
            if not self.predecesor or self.inbetween(id,self.predecesor + 1 , self.key):            
                self.predecesor = id
        except:
            pass
       
    
    def Fix_Fingers(self):
        try:
            i = random.randint(1,self._bitsKey)
            self._fingerTable[i] = self.FindSuccessor(self.Start(i))
        except:
            pass

    def InitiateNode(self):
        self.alive = True
        t1 = threading.Thread(target=self.RunStabilize)
        t2 = threading.Thread(target=self.RunFixFt)
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()

    def Leave(self):  
        succesor = Pyro4.Proxy(f"PYRONAME:Node.{self.succesor}")
        with succesor.SuccLock:
            succesor.predecesor = None

            if self.predecesor:
                predeccesor = Pyro4.Proxy(f"PYRONAME:Node.{self.predecesor}")
                predeccesor.OutSuccessor()

        self.alive = False

    def RunStabilize(self):
        while self.alive:
            self.ExecInBG(self.Stabilize, time.time()+5)

    def RunFixFt(self):
        while self.alive:
            self.ExecInBG(self.Fix_Fingers, time.time()+9)

    def ExecInBG(self,func,timeToWait):
        timeTask =  sched.scheduler(time.time,time.sleep)
        timeTask.enterabs(timeToWait,1,func)
        timeTask.run()

    
    def inbetween(self, key, lwb, upb,stabilizing = False):       
        if lwb == upb and not stabilizing:
            return True                                  
        if lwb <= upb:                                                            
            return lwb <= key and key < upb                                         
        else:                                                                     
            return (lwb <= key and key < upb + 2**self._bitsKey) or (lwb <= key + 2**self._bitsKey and key < upb)   

    def GetUrl(self, url):
        try:
            r = self.urls[url]
            print(f'Node {self._id} tiene '+url)
            return r
        except KeyError:
            print(f'Node {self._id} todavia no tiene '+url)
            return None
    
    def Save(self, url,html):
            print(f'Node {self._id} saving '+url)
            self.urls[url] = base64.b64decode(html)
    
    def GetUrlsFromSuccesor(self):
        try:
            succ = Pyro4.Proxy(f"PYRONAME:Node.{self.succesor}")
            succ_dict = succ.GetUrls
            print('')
            print(f'URLS de mi successor -> {succ_dict}')
            for k in succ_dict:
                if hash(k)<=self.key:
                    self.urls[k]= succ_dict[k]
                    del succ_dict[k]#si no sirve pasarle un nuevo dict con los cambios
            succ = Pyro4.Proxy(f"PYRONAME:Node.{self.succesor}")
            succ_dict = succ.GetUrls
            print(f'URLS de mi successor dsps de eliminar -> {succ_dict}')
        except CommunicationError:
            raise Exception("error al comunicarse con succesor")



def PrintStatus(status):
    s = ['key','uri','predeccessor',"successor's list",'ft','alive']
    for i,stat in enumerate(status):
        print(f'{s[i]} ->  {stat}')
    print('')

def process_loop(node,uriEntryPoint = None):
    while True:
        input_string = input('Enter command or help for list of commands:\n').split()

        command = input_string[0]
        if len(input_string) == 2 and command == 'lookup':
            argument = input_string[1]
            try:
                argument = int(argument)
                print(node.LookUp(argument))
            # except ValueError:
            #     print(dht.lookup_key(argument.encode())[1])

            except KeyOutOfRange:
                print('Key argument is out of range')

        # elif command == 'exit':
        #     node.Leave()
        #     break

        elif command == 'join':
            node.Join(uri = uriEntryPoint)

        elif command == 'status':
            PrintStatus(node.Status)

        # elif command == 'leave':
        #     node.Leave()

        elif command == 'help':
            print('\nstatus\nlookup key\njoin\nhelp')

        else:
            print('Unrecognized command')

        print('\n')


def StartServerLoop(daemon):
    daemon.requestLoop()

def init(daemon):
    t = threading.Thread(target=StartServerLoop,args=(daemon,))
    t.setDaemon(True)
    t.start()


def main(argv):
    while True:
        uri = input('Enter uri of node in chord if you want, if not press enter:\n')
        try:
            if uri == '':
                uri = None
                break
            else:
                Pyro4.Proxy(uri)
                break   
        except:
            print('Wrong Uri!!')
            
    
    while True:
        id = input('Give a id to your node, if not prees enter:\n')
        try:
            id = int(id)
            break
        except:
            if id == '':
                id = None
                break
            else:
                print('Wrong id!!')
                
    daemon = Pyro4.Daemon()    
    node = Node(id, daemon)

    
    try:
        init(daemon)
        process_loop(node,uri)
    finally:
        daemon.close()


if __name__ == '__main__':
    main(sys.argv[1:])
