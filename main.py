import os
import re
import time
import pandas as pd
import requests
import phonenumbers
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from tkinter import *
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

logging.basicConfig(filename='rgpd_requests.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# === Fonctions de scraping ===
def rgpd_risk_level(email):
    generic_keywords = ['contact', 'info', 'hello', 'support', 'service', 'commercial', 'admin', 'sales']
    personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com', 'live.com']
    try:
        local_part, domain = email.lower().split('@')
    except ValueError:
        return "❌ Élevé"
    if domain in personal_domains:
        return "❌ Élevé"
    if any(keyword in local_part for keyword in generic_keywords):
        return "✅ Faible"
    return "⚠️ Modéré"

def extract_phone_numbers(text, region="FR"):
    seen = set()
    results = []
    pattern = r"(?:(?:\+33\s?|0)[1-9])(?:[\s\-\.]?\d{2}){4}"
    matches = re.findall(pattern, text, re.VERBOSE)
    for raw in matches:
        cleaned = re.sub(r"[^\d+]", "", raw)
        if cleaned.startswith("0"):
            cleaned = "+33" + cleaned[1:]
        try:
            number_obj = phonenumbers.parse(cleaned, region)
            if phonenumbers.is_valid_number(number_obj):
                formatted = phonenumbers.format_number(number_obj, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                results.append(formatted)
        except:
            continue
    return list(set(results))

def extract_email_phone_linkedin(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        text = soup.get_text()
        mailto_links = [a.get("href") for a in soup.find_all("a", href=True) if "mailto:" in a.get("href")]
        mailto_emails = [link.replace("mailto:", "").split("?")[0] for link in mailto_links]
        text_emails = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", text)
        all_emails = list(set(mailto_emails + text_emails))
        all_emails = [email for email in all_emails if not email.endswith(('.png', '.jpg', '.jpeg'))]

        phone_numbers = extract_phone_numbers(text)
        linkedin_links = list(set([a['href'] for a in soup.find_all('a', href=True) if 'linkedin.com/in/' in a['href']]))

        return all_emails, phone_numbers, linkedin_links
    except Exception as e:
        return [], [], []

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
        raise ValueError("Format non supporté")
    return urls

def log_request(email, action):
    logging.info(f"{action} - {email}")

def run_scraping(file_path, status_label, progress_bar, result_box):
    urls = read_urls_from_file(file_path)
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        emails, phones, linkedins = extract_email_phone_linkedin(url)
        rgpd_infos = [f"{email} ({rgpd_risk_level(email)})" for email in emails]

        result = {
            "URL": url,
            "Emails": ", ".join(emails),
            "Téléphones": ", ".join(phones),
            "LinkedIn": ", ".join(linkedins),
            "Filtre_RGPD": ", ".join(rgpd_infos)
        }
        results.append(result)
        result_box.insert(END, f"{result['URL']}\nEmails: {result['Emails']}\nTél: {result['Téléphones']}\nLinkedIn: {result['LinkedIn']}\n\n")
        result_box.see(END)

        for email in emails:
            log_request(email, "Consultation")

        progress_bar['value'] = (i+1) / total * 100
        status_label.config(text=f"Progression: {i+1}/{total}")
        status_label.update()

    df = pd.DataFrame(results)
    df.to_excel("emails_and_phones.xlsx", index=False)
    df.to_csv("emails_and_phones.csv", index=False, encoding="utf-8-sig")
    with open("emails_and_phones.txt", "w", encoding="utf-8") as f:
        f.write("URL\tEmails\tTéléphones\tLinkedIn\tFiltre_RGPD\n")
        for row in results:
            f.write(f"{row['URL']}\t{row['Emails']}\t{row['Téléphones']}\t{row['LinkedIn']}\t{row['Filtre_RGPD']}\n")

    status_label.config(text="✅ Extraction terminée !", fg="#3c763d")

# === Interface graphique ===
def launch_gui():
    root = Tk()
    root.title("Chocobon Extractor 🍫")
    root.geometry("650x700")
    root.configure(bg="#f9f3e9")

    def select_file():
        file_path = filedialog.askopenfilename(
            filetypes=[("Fichiers texte", "*.txt"), ("Fichiers CSV", "*.csv"), ("Fichiers Excel", "*.xlsx *.xls")]
        )
        if file_path:
            path_label.config(text=file_path)
            start_button.config(state=NORMAL)

    def launch():
        status_label.config(text="⏳ Traitement en cours...", fg="#996515")
        root.update_idletasks()
        result_box.delete(1.0, END)
        run_scraping(path_label.cget("text"), status_label, progress_bar, result_box)

    if os.path.exists("chocobon_logo.png"):
        img = Image.open("chocobon_logo.png")
        img = img.resize((100, 100), Image.ANTIALIAS)
        logo = ImageTk.PhotoImage(img)
        logo_label = Label(root, image=logo, bg="#f9f3e9")
        logo_label.image = logo
        logo_label.pack(pady=10)

    Label(root, text="Chocobon Extractor 🍫", font=("Arial", 16, "bold"), bg="#f9f3e9", fg="#6e4c1e").pack()
    Button(root, text="📁 Charger un fichier", command=select_file, bg="#d6b48f", fg="white", font=("Arial", 12)).pack(pady=10)
    path_label = Label(root, text="", bg="#f9f3e9", fg="#6e4c1e", wraplength=400)
    path_label.pack()

    start_button = Button(root, text="🚀 Lancer l'extraction", command=launch, bg="#996515", fg="white", font=("Arial", 12), state=DISABLED)
    start_button.pack(pady=10)

    progress_bar = ttk.Progressbar(root, orient=HORIZONTAL, length=400, mode='determinate')
    progress_bar.pack(pady=10)

    status_label = Label(root, text="", bg="#f9f3e9", fg="#996515", font=("Arial", 12))
    status_label.pack(pady=10)

    result_box = Text(root, height=20, width=80, wrap=WORD, bg="#fff8f0")
    result_box.pack(padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()
