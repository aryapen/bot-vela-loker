import requests
from bs4 import BeautifulSoup
import time
import os
import urllib.parse
import random

# --- KONFIGURASI ---
TOKEN = '8741502539:AAFHqzudVXD8C2m2xVudWJNs6ABu4V_YRz0'
CHAT_ID = '-1003997113925' 
DB_FILE = "database_loker.txt"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- KONTEN IKLAN OTOMATIS (CUAN) ---
IKLAN_LIST = [
    (
        "🎨 *BUTUH LOGO PROFESIONAL?*\n\n"
        "Bikin identitas bisnismu makin berkelas di *Luxcreativeee*.\n"
        "Desain modern, cepat, dan berkualitas! ✨\n\n"
        "📸 *Cek Portofolio:* [Instagram @luxcreativeee](https://www.instagram.com/luxcreativeee)\n"
        "--------------------------------------"
    ),
    (
        "🚀 *JASA PROMOSI GRUP / BISNIS*\n\n"
        "Mau loker atau bisnismu dipromosikan otomatis seperti ini?\n"
        "Jangkau audiens tepat sasaran sekarang juga!\n\n"
        "📩 *Hubungi Owner:* [Chat FELIXDEV](https://t.me/felixdev_owner)\n"
        "--------------------------------------"
    )
]

def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': pesan, 'parse_mode': 'Markdown', 'disable_web_page_preview': False}
    try:
        r = requests.post(url, data=payload, timeout=15)
        return r.json().get("ok")
    except:
        return False

# --- KUMPULAN SCRAPER (5 SUMBER) ---

def scrape_jora():
    jobs = []
    try:
        url = "https://id.jora.com/j?q=&l=Indonesia&st=date"
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('div', class_='job-card'):
            a_tag = card.find('a', class_='job-link')
            if a_tag:
                jobs.append({
                    "judul": a_tag.text.strip(),
                    "link": "https://id.jora.com" + a_tag['href'].split('?')[0],
                    "sumber": "Jora"
                })
    except: pass
    return jobs

def scrape_karir():
    jobs = []
    try:
        url = "https://www.karir.com/search"
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('article', class_='row'):
            a_tag = card.find('a', class_='opportunity-card-title')
            if a_tag:
                jobs.append({"judul": a_tag.text.strip(), "link": a_tag['href'], "sumber": "Karir.com"})
    except: pass
    return jobs

def scrape_glints():
    jobs = []
    try:
        url = "https://glints.com/api/v1/search/jobs?location=Indonesia&limit=10&offset=0"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        for item in data.get('data', []):
            jobs.append({
                "judul": item.get('title'),
                "link": f"https://glints.com/id/opportunities/jobs/{item.get('id')}",
                "sumber": "Glints"
            })
    except: pass
    return jobs

def scrape_linkedin():
    jobs = []
    try:
        query = 'site:id.linkedin.com/jobs/view "Indonesia" "1 day ago"'
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for g in soup.find_all('div', class_='tF2Cxc'):
            link = g.find('a')['href']
            title = g.find('h3').text if g.find('h3') else "Loker LinkedIn"
            if "linkedin.com/jobs" in link:
                jobs.append({"judul": title.replace(" - LinkedIn", ""), "link": link, "sumber": "LinkedIn"})
    except: pass
    return jobs

def scrape_loker_id():
    jobs = []
    try:
        url = "https://www.loker.id/cari-lowongan-kerja"
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('div', class_='job-box'):
            a_tag = card.find('h3').find('a') if card.find('h3') else None
            if a_tag:
                jobs.append({"judul": a_tag.text.strip(), "link": a_tag['href'], "sumber": "Loker.id"})
    except: pass
    return jobs

# --- MAIN ENGINE ---

if __name__ == "__main__":
    print("🚀 Bot VELA ULTRA Aktif! Memantau 5 Sumber & Menjalankan Iklan Jasa.")
    if not os.path.exists(DB_FILE): open(DB_FILE, "w").close()

    loker_counter = 0 # Untuk hitung kapan iklan muncul

    while True:
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Memulai pemindaian masal...")
        
        # Menggabungkan semua sumber tanpa ada yang dibuang
        daftar_loker = (scrape_jora() + scrape_karir() + scrape_glints() + 
                        scrape_linkedin() + scrape_loker_id())
        
        # Baca database link yang sudah terkirim
        with open(DB_FILE, "r") as f:
            db_content = f.read()

        ditemukan_baru = 0
        for job in daftar_loker:
            if job['link'] not in db_content:
                pesan = (
                    f"📢 *LOWONGAN TERBARU*\n\n"
                    f"📌 *Posisi:* {job['judul']}\n"
                    f"🌐 *Sumber:* {job['sumber']}\n\n"
                    f"🔗 [Klik untuk Detail/Lamar]({job['link']})\n\n"
                    f"#loker #indonesia #lokermu #{job['sumber'].lower().replace('.','')}"
                )
                
                if kirim_telegram(pesan):
                    with open(DB_FILE, "a") as f:
                        f.write(job['link'] + "\n")
                    
                    ditemukan_baru += 1
                    loker_counter += 1
                    print(f"✅ Terkirim: {job['judul']} ({job['sumber']})")
                    
                    # --- FITUR IKLAN OTOMATIS SETIAP 10 LOKER ---
                    if loker_counter >= 10:
                        time.sleep(5) # Jeda sedikit sebelum iklan
                        iklan_acak = random.choice(IKLAN_LIST)
                        kirim_telegram(iklan_acak)
                        loker_counter = 0 # Reset hitungan
                
                time.sleep(3) # Jeda antar pesan agar tidak kena spam limit

        if ditemukan_baru == 0:
            print("📭 Belum ada loker baru di semua sumber.")
        
        print("😴 Selesai satu putaran. Standby 15 menit...")
        time.sleep(900)
