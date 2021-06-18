import requests
from bs4 import BeautifulSoup

baseURL = ''
page = requests.get(baseURL)

soup = BeautifulSoup(page.content, 'html.parser')

urls = []
for link in soup.find_all('a'):
    href: str = link.get('href')
    if href.startswith(baseURL):
        urls.append(href)

uniqueURLs = set(urls)

for u in uniqueURLs:
    #scrapp u
    print(u)