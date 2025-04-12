import os
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import logging
import phonenumbers
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Logging RGPD
logging.basicConfig(filename='rgpd_requests.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# === RGPD Risk Level ===
def rgpd_risk_level(email):
    generic = ['contact', 'info', 'hello', 'support', 'service', 'commercial', 'admin', 'sales']
    personal = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com', 'live.com']
    try:
        local, domain = email.lower().split('@')
        if domain in personal:
            return "❌ Élevé"
        elif any(k in local for k in generic):
            return "✅ Faible"
        return "⚠️ Modéré"
    except:
        return "❌ Élevé"

# === Numéro FR avec Regex + phonenumbers ===
def extract_phone_numbers(text, region="FR"):
    try:
        seen, results = set(), []
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
                    if formatted not in seen:
                        seen.add(formatted)
                        results.append(formatted)
            except:
                continue
        return results
    except Exception as e:
        print(f"[⚠️ Erreur parsing numéro] {e}")
        return []

# === Recherche LinkedIn URLs ===
def extract_linkedin_urls(text):
    return list(set(re.findall(r'https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9\-_]+', text)))

# === Scrape site ===
def extract_info_from_website(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        mailtos = [a.get("href") for a in soup.find_all("a", href=True) if "mailto:" in a.get("href")]
        mail_emails = [m.replace("mailto:", "").split("?")[0] for m in mailtos]
        body_emails = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", soup.get_text())
        phones = extract_phone_numbers(soup.get_text())
        linkedins = extract_linkedin_urls(str(soup))
        emails = list(set(mail_emails + body_emails))
        emails = [e for e in emails if not e.lower().endswith(('.png', '.jpg', '.jpeg'))]
        return emails, phones, linkedins
    except Exception as e:
        print(f"[❌ Erreur site] {url} : {e}")
        return [], [], []

# === Facebook checker ===
def is_facebook_url(url):
    return "facebook.com" in url.lower()

# === Facebook via Selenium ===
def extract_from_facebook(url):
    print(f"🌐 Facebook : {url}")
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        text = soup.get_text(separator=' ')
        emails = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", text)
        phones = extract_phone_numbers(text)
        linkedins = extract_linkedin_urls(text)
        emails = [e for e in set(emails) if len(e) < 100 and not e.endswith(('.png', '.jpg'))]
        return emails, phones, linkedins
    except Exception as e:
        print(f"[❌ Facebook Selenium] {url} : {e}")
        return [], [], []

# === Lire fichier ===
def read_urls(file_path):
    _, ext = os.path.splitext(file_path)
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    elif ext == ".csv":
        return pd.read_csv(file_path).iloc[:, 0].dropna().tolist()
    elif ext in [".xlsx", ".xls"]:
        return pd.read_excel(file_path).iloc[:, 0].dropna().tolist()
    else:
        raise ValueError("Format non supporté (.txt, .csv, .xlsx)")

# === MAIN ===
def extract_all(filepath, gui=None):
    urls = read_urls(filepath)
    results = []

    for url in urls:
        if is_facebook_url(url):
            emails, phones, linkedins = extract_from_facebook(url)
        else:
            emails, phones, linkedins = extract_info_from_website(url)

        for email in emails:
            results.append({
                "URL": url,
                "Email": email,
                "Téléphone(s)": ", ".join(phones),
                "RGPD": rgpd_risk_level(email),
                "LinkedIn(s)": ", ".join(linkedins)
            })
            logging.info(f"Consultation - {email}")

    df = pd.DataFrame(results).drop_duplicates()
    df.to_excel("emails_and_phones.xlsx", index=False)
    df.to_csv("emails_and_phones.csv", index=False)
    df.to_csv("emails_and_phones.txt", sep="\t", index=False)

    if gui:
        gui.show_data(df)
    else:
        print(df)

# === GUI ===
class ChocobonApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🍫 Chocobon Scraper")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Logo
        logo_path = "chocobon_logo.png"
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).resize((100, 100))
            logo_img = ImageTk.PhotoImage(logo)
            self.logo_label = ctk.CTkLabel(self, image=logo_img, text="")
            self.logo_label.image = logo_img
            self.logo_label.pack(pady=10)

        self.label = ctk.CTkLabel(self, text="Importer un fichier d'URLs (.txt, .csv, .xlsx)", font=("Helvetica", 18))
        self.label.pack(pady=10)

        self.button = ctk.CTkButton(self, text="📁 Choisir un fichier", command=self.browse_file)
        self.button.pack(pady=10)

        self.frame = ctk.CTkFrame(self)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox = ctk.CTkTextbox(self.frame, height=400)
        self.textbox.pack(fill="both", expand=True)

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Fichiers", "*.txt *.csv *.xlsx")])
        if path:
            self.textbox.delete("1.0", "end")
            self.textbox.insert("end", f"Fichier sélectionné : {path}\n")
            self.textbox.insert("end", "Lancement de l'extraction...\n")
            self.update()
            extract_all(path, self)

    def show_data(self, df):
        self.textbox.insert("end", f"\n✅ Extraction terminée. {len(df)} ligne(s) trouvée(s).\n")
        self.textbox.insert("end", df.to_string(index=False))
        messagebox.showinfo("Terminé", "Export effectué :\n- emails_and_phones.xlsx\n- .csv\n- .txt")

# === Launch GUI ===
if __name__ == "__main__":
    app = ChocobonApp()
    app.mainloop()