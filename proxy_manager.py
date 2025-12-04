import requests
from bs4 import BeautifulSoup
import random
import logging

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def fetch_proxies(self):
        """Fetches free proxies from sslproxies.org and free-proxy-list.net"""
        urls = [
            "https://www.sslproxies.org/",
            "https://free-proxy-list.net/"
        ]
        
        found_proxies = set()

        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    table = soup.find('table', class_='table table-striped table-bordered')
                    if table:
                        for row in table.tbody.find_all('tr'):
                            columns = row.find_all('td')
                            if columns:
                                ip = columns[0].text.strip()
                                port = columns[1].text.strip()
                                https = columns[6].text.strip()
                                
                                # We prefer HTTPS proxies for Amazon
                                if https == 'yes':
                                    proxy = f"http://{ip}:{port}"
                                    found_proxies.add(proxy)
            except Exception as e:
                self.logger.error(f"Error fetching proxies from {url}: {e}")

        self.proxies = list(found_proxies)
        self.logger.info(f"Fetched {len(self.proxies)} proxies.")
        return self.proxies

    def get_random_proxy(self):
        """Returns a random proxy from the list."""
        if not self.proxies:
            self.fetch_proxies()
        
        if self.proxies:
            return random.choice(self.proxies)
        return None

    def remove_proxy(self, proxy):
        """Removes a bad proxy from the list."""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.logger.info(f"Removed bad proxy: {proxy}")

if __name__ == "__main__":
    pm = ProxyManager()
    proxies = pm.fetch_proxies()
    print(f"Fetched {len(proxies)} proxies")
    if proxies:
        print(f"Random proxy: {pm.get_random_proxy()}")
