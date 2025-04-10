import requests
from bs4 import BeautifulSoup
import re

def extract_email_from_website(url):
    try:
        response = requests.get(url, timeout=5)
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", response.text)
        return list(set(emails))
    except:
        return []
