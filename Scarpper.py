from http.client import HTTPConnection
import sys

url = 'example.com'

def ScrapUrl(url):
    old_std = sys.stdout
    conexion = HTTPConnection(url)
    try:   
        conexion.request('GET', '/')
        sys.stdout = open('Html of ' + url+'.txt', 'w') 
        result = conexion.getresponse()
        content = result.read()
        print(content)
        sys.stdout = old_std
        print(content)
    except:
        print( sys.exc_info()[0])
        print('An error occurr while retriaving HTML from '+ url)

    

ScrapUrl(url)