# ****************************************************************************** #
#                                                                                #
#                              Thomas Moreilhon                                  #
#                                                                                #
#                                                                        %%*,    #
#                                                 *%%&%%%*               (,*/*&, #
#                      @##               ,&(**************&,            /%,%/,/& #
#           % #&.&****%.           ,&/*********************&         &/,(*       #
#         @*,**,/,%*******%   ../&********&/   %#*************% #,,&,,@          #
#         @***,*,,*&/*******&&**********&  .@@/   (/************%*@/#.           #
#         *&&&...##,*,##*&/************%  (@@@@@@   %*******@/#**&@@             #
#                 /**(&/,,#%***********&  &@@@@@@%   %*****%**#**/@@             #
#                ,/*******%(*,/&(******(. /@@@@@@@   (*****#***%**(@             #
#                 (*******/***#%*,,&/***(.  %@&@/   %*****%****&**%              #
#                %*********##****(%,*#***#/      #(*****%*******/,               #
#                 %********%*..#/*******************************/#               #
#                 ,(****(%       ,&****************************%*                #
#                  ,&&#               &/**********************&                  #
#                                     *&&(***********(&&                         #
#                                      **,,(       ,/(                           #
#                                      **,,%       ,*(,                          #
#                                      **,,&       (,(                           #
#                                      /*,,&       /*#                           #
#                                      **,,&       **#                           #
#                                      /*,,&       (,(                           #
#                                      **,,&       (,#                           #
#                                      **,,&       (,#                           #
#                                       ,*,,&       (,#                          #
#                                       /*,&       (,,,,,,%,                     #
#                                       /,,(                                     #
#                                                                                #
#   File: my_script.py                                                           #
#   By: Thomas Moreilhon <thmoreil@student.42.fr>                                #
#   Created: 2025/04/13                                                          #
#   Updated: 2025/04/13                                                          #
# ****************************************************************************** #

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

# Initialisation des logs
logging.basicConfig(filename='rgpd_requests.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def analyze_rgpd_email(email):
    generic_keywords = ['contact', 'info', 'hello', 'support', 'service', 'commercial', 'admin', 'sales']
    personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com', 'live.com']

    result = {
        "email": email,
        "score": 0,
        "category": "Non défini",
        "emoji": "❓"
    }

    try:
        local_part, domain = email.lower().split('@')
    except ValueError:
        result.update({"score": 0, "category": "Non valide", "emoji": "❌"})
        return result

    # Cas personnel
    if domain in personal_domains:
        result.update({"score": 20, "category": "Personnel", "emoji": "❌"})
    # Cas générique d'entreprise
    elif any(keyword in local_part for keyword in generic_keywords):
        result.update({"score": 100, "category": "Générique Entreprise", "emoji": "✅"})
    # Cas email pro identifiable
    elif '.' in local_part and len(domain) > 3:
        result.update({"score": 75, "category": "Professionnel", "emoji": "✅"})
    else:
        result.update({"score": 50, "category": "Non défini", "emoji": "⚠️"})

    return result

def extract_linkedin_urls(text):
    linkedin_regex = r"(https?://(?:www\.)?linkedin\.com/[^\s\"'<>]+)"
    return list(set(re.findall(linkedin_regex, text)))

def detect_from_meta(soup):
    title = soup.title.string.lower() if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag["content"].lower() if description_tag else ""
    combined = title + " " + description
    return detect_activity(combined)

# === Fonctions principales ===

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
        
        # Scroll pour charger la page
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Parse le contenu de la page avec BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        
        # Extraire le texte complet de la page
        text = soup.get_text(separator=' ')
        emails = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA0-9-.]+\b", text)
        phones = extract_phone_numbers(text)
        linkedins = extract_linkedin_urls(text)
        emails = [e for e in set(emails) if len(e) < 100 and not e.endswith(('.png', '.jpg'))]

        # Chercher l'activité directement dans les sections pertinentes
        activity = "Activité inconnue"

        # Chercher dans la section "À propos" si elle existe
        about_section = soup.find('div', {'class': 'aboutSection'})  # Section "À propos"
        if about_section:
            description = about_section.get_text(separator=" ", strip=True)
            print("Section À propos trouvée :", description)  # Log du texte trouvé
            activity = detect_activity(description)  # Passer le texte à detect_activity

        # Si l'activité n'a pas été trouvée, chercher dans les posts récents
        if activity == "Activité inconnue":
            posts = soup.find_all('div', {'class': 'userContent'})
            if posts:
                for post in posts[:5]:  # Limiter à 5 derniers posts
                    post_text = post.get_text().lower()
                    print(f"Post trouvé : {post_text}")  # Log du texte du post
                    post_activity = detect_activity(post_text)
                    if post_activity != "Activité inconnue":  # Si une activité est trouvée, l'utiliser
                        activity = post_activity
                        break  # Stopper dès qu'une activité est trouvée
        
        # Si l'activité est toujours inconnue, rechercher dans d'autres sections comme la bio
        if activity == "Activité inconnue":
            bio_section = soup.find('div', {'class': 'bio'})
            if bio_section:
                bio_text = bio_section.get_text(separator=" ", strip=True)
                print(f"Bio trouvée : {bio_text}")  # Log de la bio
                activity = detect_activity(bio_text)

        # Afficher les résultats de la détection
        print(f"Activité trouvée : {activity}")

        return emails, phones, linkedins, activity

    except Exception as e:
        print(f"[❌ Facebook Selenium] {url} : {e}")
        return [], [], [], None


def validate_email_address(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def extract_useful_text(soup):
    parts = []

    # Meta tags utiles
    for meta_name in ['description', 'og:description', 'keywords']:
        tag = soup.find("meta", attrs={"name": meta_name}) or soup.find("meta", attrs={"property": meta_name})
        if tag and tag.get("content"):
            parts.append(tag["content"])

    # Titre de la page
    if soup.title and soup.title.string:
        parts.append(soup.title.string)

    # Titres ou paragraphes avec des indices
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
        txt = tag.get_text(strip=True)
        if any(kw in txt.lower() for kw in ['à propos', 'qui sommes', 'notre mission']):
            parts.append(txt)

    return " ".join(parts)

def detect_activity(text):
    text = text.lower()

    secteurs = {
        "Agence de communication": ["communication", "marketing", "réseaux sociaux"],
        "Cabinet d'avocats": ["avocat", "droit", "juridique", "litige"],
        "Restaurant": ["restaurant", "cuisine", "menu", "chef", "gastronomie"],
        "Immobilier": ["immobilier", "location", "appartement", "syndic", "agence"],
        "Informatique / Développement": ["développement", "web", "application", "logiciel", "site internet"],
        "Santé / Médical": ["médical", "santé", "clinique", "docteur", "hôpital"],
        "Éducation / Formation": ["formation", "école", "cours", "enseignement", "pédagogie"],
    }

    for secteur, keywords in secteurs.items():
        if any(kw in text for kw in keywords):
            return secteur

    return "Activité inconnue"

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
        if is_facebook_url(url):
            return extract_from_facebook(url)

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

        valid_emails = [email for email in all_emails if validate_email_address(email)]
        phone_numbers = extract_phone_numbers(text)
        linkedin_links = [a.get("href") for a in soup.find_all("a", href=True) if a.get("href") and "linkedin.com" in a.get("href")]

        # Nouvelle détection activité
        useful_text = extract_useful_text(soup)
        activity = detect_activity(useful_text)

        return valid_emails, phone_numbers, linkedin_links, activity
    except Exception as e:
        print(f"Erreur lors de l'extraction pour {url}: {e}")
        # Retourner un tuple avec 4 valeurs même en cas d'erreur
        return [], [], [], None  #
    
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

def run_scraping(file_path, status_label, progress_bar, result_box, save_directory, open_button):
    urls = read_urls_from_file(file_path)
    results = []
    total = len(urls)

    if not os.path.exists(save_directory):
        os.makedirs(save_directory)

    for i, url in enumerate(urls):
        emails, phones, linkedins, activity = extract_email_phone_linkedin(url)

        rgpd_infos = []
        for email in emails:
            analysis = analyze_rgpd_email(email)
            info = f"{email} ({analysis['emoji']} {analysis['category']} - {analysis['score']}/100)"
            rgpd_infos.append(info)

        result = {
            "URL": url,
            "Emails": ", ".join(emails),
            "Téléphones": ", ".join(phones),
            "LinkedIn": ", ".join(linkedins),
            "Activité": activity,
            "Filtre_RGPD": ", ".join(rgpd_infos)
        }
        results.append(result)

        result_box.insert(END, f"🔗 {result['URL']}\n")
        for email in emails:
            risk = rgpd_risk_level(email)
            result_box.insert(END, f"📧 {email} ({risk})\n")
            if "❌" in risk:
                result_box.tag_add("high", "insert linestart", "insert lineend")
            elif "⚠️" in risk:
                result_box.tag_add("moderate", "insert linestart", "insert lineend")
            else:
                result_box.tag_add("low", "insert linestart", "insert lineend")
        if phones:
            result_box.insert(END, f"📞 {result['Téléphones']}\n")
        if linkedins:
            result_box.insert(END, f"💼 {result['LinkedIn']}\n")
        if activity:
            result_box.insert(END, f"🏷️ {activity}\n")
        result_box.insert(END, "\n")
        result_box.see(END)

        for email in emails:
            log_request(email, "Consultation")

        pourcentage = int((i + 1) / total * 100)
        progress_bar['value'] = pourcentage
        status_label.config(text=f"Progression: {i+1}/{total} ({pourcentage}%)")
        status_label.update()

    df = pd.DataFrame(results)
    excel_file = os.path.join(save_directory, "emails_and_phones.xlsx")
    csv_file = os.path.join(save_directory, "emails_and_phones.csv")
    txt_file = os.path.join(save_directory, "emails_and_phones.txt")

    df.to_excel(excel_file, index=False)
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("URL\tEmails\tTéléphones\tLinkedIn\tActivité\tFiltre_RGPD\n")
        for row in results:
            f.write(f"{row['URL']}\t{row['Emails']}\t{row['Téléphones']}\t{row['LinkedIn']}\t{row['Activité']}\t{row['Filtre_RGPD']}\n")

    status_label.config(text="✅ Extraction terminée !", fg="#3c763d")
    open_button.config(state=NORMAL)

    from tkinter import messagebox
    messagebox.showinfo("Succès", "Extraction terminée avec succès !")
# === Interface Graphique Pastel Chocolat ===

def launch_gui():
    root = Tk()
    root.title("ChocoScrap 🍫")
    root.geometry("700x750")
    root.configure(bg="#f9f3e9")

    selected_directory = StringVar()

    def select_file():
        file_path = filedialog.askopenfilename(
            filetypes=[("Fichiers texte", "*.txt"), ("Fichiers CSV", "*.csv"), ("Fichiers Excel", "*.xlsx *.xls")]
        )
        if file_path:
            path_label.config(text=file_path)
            start_button.config(state=NORMAL)

    def select_save_directory():
        folder = filedialog.askdirectory()
        if folder:
            save_dir = os.path.join(folder, "Dossier d'extraction")
            selected_directory.set(save_dir)
            status_label.config(text=f"Dossier sélectionné: {save_dir}", fg="#996515")

    def launch():
        if not selected_directory.get():
            status_label.config(text="❗ Veuillez sélectionner un dossier pour l'export.", fg="red")
            return
        status_label.config(text="⏳ Traitement en cours...", fg="#996515")
        open_folder_button.config(state=DISABLED)
        root.update_idletasks()
        result_box.delete(1.0, END)
        run_scraping(path_label.cget("text"), status_label, progress_bar, result_box, selected_directory.get(), open_folder_button)

    def open_export_folder():
        import subprocess
        subprocess.Popen(f'explorer "{selected_directory.get()}"')

    # Logo si dispo
    if os.path.exists("chocobon_logo.png"):
        img = Image.open("chocobon_logo.png")
        img = img.resize((100, 100), Image.Resampling.LANCZOS)
        logo = ImageTk.PhotoImage(img)
        logo_label = Label(root, image=logo, bg="#f9f3e9")
        logo_label.image = logo
        logo_label.pack(pady=10)

    Label(root, text="ChocoScrap 🍫", font=("Arial", 16, "bold"), bg="#f9f3e9", fg="#6e4c1e").pack()

    Button(root, text="📁 Charger un fichier", command=select_file, bg="#d6b48f", fg="white", font=("Arial", 12)).pack(pady=10)
    path_label = Label(root, text="", bg="#f9f3e9", fg="#6e4c1e", wraplength=400)
    path_label.pack()

    Button(root, text="📂 Choisir l'emplacement du dossier d'extraction", command=select_save_directory, bg="#d6b48f", fg="white", font=("Arial", 12)).pack(pady=10)

    start_button = Button(root, text="🚀 Lancer l'extraction", command=launch, bg="#996515", fg="white", font=("Arial", 12), state=DISABLED)
    start_button.pack(pady=10)

    progress_bar = ttk.Progressbar(root, orient=HORIZONTAL, length=400, mode='determinate')
    progress_bar.pack(pady=10)

    status_label = Label(root, text="", bg="#f9f3e9", fg="#996515", font=("Arial", 12))
    status_label.pack(pady=10)

    # Scrollable result box
    frame = Frame(root)
    frame.pack(padx=10, pady=10)
    scrollbar = Scrollbar(frame)
    scrollbar.pack(side=RIGHT, fill=Y)

    result_box = Text(frame, height=20, width=80, wrap=WORD, bg="#fff8f0", yscrollcommand=scrollbar.set)
    result_box.pack()
    scrollbar.config(command=result_box.yview)

    # Tags RGPD colorés
    result_box.tag_config("high", foreground="red")
    result_box.tag_config("moderate", foreground="orange")
    result_box.tag_config("low", foreground="green")

    # Bouton pour ouvrir le dossier
    open_folder_button = Button(root, text="📂 Ouvrir le dossier d'extraction", command=open_export_folder, bg="#d6b48f", fg="white", font=("Arial", 12), state=DISABLED)
    open_folder_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()