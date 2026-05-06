import requests
from bs4 import BeautifulSoup
import time
import os
import urllib.parse
import random

# --- [ KONFIGURASI ] ---
TOKEN = '8741502539:AAFHqzudVXD8C2m2xVudWJNs6ABu4V_YRz0'
CHAT_ID = '-1003997113925' 
DB_FILE = "database_loker.txt"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- [ KONTEN IKLAN CUAN ] ---
IKLAN_LIST = [
    "🎨 *BUTUH LOGO PROFESIONAL?*\n\nBikin identitas bisnismu makin berkelas di *Luxcreativeee*.\n📸 *Cek Portofolio:* [Instagram @luxcreativeee](https://www.instagram.com/luxcreativeee)\n--------------------------------------",
    "🚀 *JASA PROMOSI GRUP / BISNIS*\n\nMau loker atau bisnismu dipromosikan otomatis?\n📩 *Hubungi Owner:* [Chat FELIXDEV](https://t.me/felixdev_owner)\n--------------------------------------"
]

def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': pesan, 'parse_mode': 'Markdown', 'disable_web_page_preview': False}
    try:
        r = requests.post(url, data=payload, timeout=15)
        return r.json().get("ok")
    except:
        return False

def cek_pesan_masuk():
    """Fitur Tes: Bot akan membalas jika ada pesan mengandung kata 'tes'"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        # Ambil update terakhir
        res = requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5).json()
        if res.get("ok") and res.get("result"):
            last_msg = res["result"][0].get("message", {})
            text = last_msg.get("text", "").lower()
            if "tes" in text:
                kirim_telegram("✅ *Bot VELA Aktif, Bos!* \nSedang memantau loker dari 5 sumber raksasa (Jora, Karir, Glints, LinkedIn, LokerID)... 🚀")
                print(">>> Membalas pesan tes dari user.")
    except:
        pass

# --- [ KUMPULAN SCRAPER ] ---

def scrape_jora():
    jobs = []
    try:
        res = requests.get("https://id.jora.com/j?q=&l=Indonesia&st=date", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('div', class_='job-card'):
            a = card.find('a', class_='job-link')
            if a: jobs.append({"judul": a.text.strip(), "link": "https://id.jora.com" + a['href'].split('?')[0], "sumber": "Jora"})
    except: pass
    return jobs

def scrape_karir():
    jobs = []
    try:
        res = requests.get("https://www.karir.com/search", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('article', class_='row'):
            a = card.find('a', class_='opportunity-card-title')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Karir.com"})
    except: pass
    return jobs

def scrape_glints():
    jobs = []
    try:
        res = requests.get("https://glints.com/api/v1/search/jobs?location=Indonesia&limit=10", headers=HEADERS, timeout=10)
        data = res.json()
        for item in data.get('data', []):
            jobs.append({"judul": item.get('title'), "link": f"https://glints.com/id/opportunities/jobs/{item.get('id')}", "sumber": "Glints"})
    except: pass
    return jobs

def scrape_linkedin():
    jobs = []
    try:
        query = urllib.parse.quote('site:id.linkedin.com/jobs/view "Indonesia" "1 day ago"')
        res = requests.get(f"https://www.google.com/search?q={query}", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for g in soup.find_all('div', class_='tF2Cxc'):
            link = g.find('a')['href']
            if "linkedin.com/jobs" in link:
                jobs.append({"judul": g.find('h3').text if g.find('h3') else "Loker LinkedIn", "link": link, "sumber": "LinkedIn"})
    except: pass
    return jobs

def scrape_loker_id():
    jobs = []
    try:
        res = requests.get("https://www.loker.id/cari-lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('div', class_='job-box'):
            a = card.find('h3').find('a') if card.find('h3') else None
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Loker.id"})
    except: pass
    return jobs

# --- [ MAIN ENGINE ] ---

if __name__ == "__main__":
    print("🚀 BOT VELA STARTING UP...")
    if not os.path.exists(DB_FILE): open(DB_FILE, "w").close()
    loker_counter = 0

    while True:
        # Cek update pesan tes
        cek_pesan_masuk()

        print(f"🔄 [{time.strftime('%H:%M:%S')}] Scanning jobs...")
        # Gabungkan semua sumber
        semua_loker = scrape_jora() + scrape_karir() + scrape_glints() + scrape_linkedin() + scrape_loker_id()
        
        with open(DB_FILE, "r") as f:
            db_content = f.read()

        ditemukan_baru = 0
        for job in semua_loker:
            if job['link'] not in db_content:
                msg = (
                    f"📢 *LOWONGAN TERBARU*\n\n"
                    f"📌 *Posisi:* {job['judul']}\n"
                    f"🌐 *Sumber:* {job['sumber']}\n\n"
                    f"🔗 [Detail/Lamar]({job['link']})\n\n"
                    f"#loker #indonesia #{job['sumber'].lower().replace('.','')}"
                )
                
                if kirim_telegram(msg):
                    with open(DB_FILE, "a") as f: f.write(job['link'] + "\n")
                    ditemukan_baru += 1
                    loker_counter += 1
                    
                    # Iklan setiap 10 loker
                    if loker_counter >= 10:
                        time.sleep(5)
                        kirim_telegram(random.choice(IKLAN_LIST))
                        loker_counter = 0
                
                time.sleep(3) # Anti-spam

        print(f"✅ Selesai. Ditemukan {ditemukan_baru} loker baru.")
        
        # Standby 10 menit sambil tetap memantau perintah 'tes'
        print("😴 Standby mode (10 mins)...")
        for _ in range(60):
            cek_pesan_masuk()
            time.sleep(10)
