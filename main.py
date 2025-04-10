import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os

def extract_email_from_website(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        mailto_links = [a.get("href") for a in soup.find_all("a", href=True) if "mailto:" in a.get("href")]
        mailto_emails = [link.replace("mailto:", "").split("?")[0] for link in mailto_links]
        text_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", soup.get_text())

        all_emails = list(set(mailto_emails + text_emails))
        all_emails = [email for email in all_emails if not email.endswith(('.png', '.jpg', '.jpeg'))]

        return all_emails

    except Exception as e:
        print(f"[Erreur] {url} : {e}")
        return []

def read_urls_from_file(file_path):
    _, ext = os.path.splitext(file_path)

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    elif ext == ".csv":
        df = pd.read_csv(file_path)
        urls = df.iloc[:, 0].dropna().tolist()
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
        urls = df.iloc[:, 0].dropna().tolist()
    else:
        raise ValueError("Format de fichier non pris en charge. Utilise .txt, .csv ou .xlsx")

    return urls


fichier_input = "urls.txt" 

urls = read_urls_from_file(fichier_input)
results = []

for url in urls:
    emails = extract_email_from_website(url)
    print(f"✅ {url} : {emails}")
    for email in emails:
        results.append({"url": url, "email": email})

with open("emails.txt", "w", encoding="utf-8") as f:
    for item in results:
        f.write(f"{item['url']}\t{item['email']}\n")

df = pd.DataFrame(results)
df.to_excel("emails.xlsx", index=False)

print("\n✅ Extraction terminée ! Résultats dans 'emails.txt' et 'emails.xlsx'")