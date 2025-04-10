import requests
from bs4 import BeautifulSoup
import re

def extract_email_from_website(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding  # pour bien décoder les caractères

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Recherche dans les liens mailto
        mailto_links = [a.get("href") for a in soup.find_all("a", href=True) if "mailto:" in a.get("href")]
        mailto_emails = [link.replace("mailto:", "").split("?")[0] for link in mailto_links]

        # 2. Recherche dans tout le texte visible
        text_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", soup.get_text())

        # 3. Fusion + nettoyage
        all_emails = list(set(mailto_emails + text_emails))
        all_emails = [email for email in all_emails if not email.endswith(('.png', '.jpg', '.jpeg'))]

        return all_emails

    except Exception as e:
        print(f"Erreur pour {url} : {e}")
        return []

# Liste de sites à tester
urls = [
    "https://www.lerelaisgastronomique.fr",
    "https://www.latableduchef.com",
    "https://www.aunomdelarose.fr",
    "https://www.restaurant-auberge.com",
    "https://www.facebook.com/biscotto54/?locale=fr_FR&checkpoint_src=any"
]

# Affichage des résultats
for url in urls:
    emails = extract_email_from_website(url)
    print(f"Emails trouvés sur {url} : {emails}")