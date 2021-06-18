import requests
from bs4 import BeautifulSoup

baseURL = ''
page = requests.get(baseURL)

soup = BeautifulSoup(page.content, 'html.parser')

urlsTemp = []
for link in soup.find_all('a'):
    href: str = link.get('href')
    if href.startswith(baseURL):
        urlsTemp.append(href)

# con esto tienes una lista de las urls
# urls = set(urlsTemp)

for u in set(urlsTemp):
    #scrapp u
    print(u)