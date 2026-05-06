import requests
from bs4 import BeautifulSoup
import time
import os
import urllib.parse
import random
import redis

# --- [ KONFIGURASI ] ---
TOKEN = '8741502539:AAFHqzudVXD8C2m2xVudWJNs6ABu4V_YRz0'
CHAT_ID = '-1003997113925' 

# URL Redis yang kamu kasih tadi
REDIS_URL = 'redis://default:JLZspxuVQdJlGmpjTmzHFJvfxWWAJTEe@redis.railway.internal:6379'

try:
    db = redis.from_url(REDIS_URL, decode_responses=True)
    print("✅ Berhasil terhubung ke database Redis!")
except Exception as e:
    db = None
    print(f"❌ Gagal koneksi Redis: {e}")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
}

IKLAN_LIST = [
    "🎨 *BUTUH LOGO PROFESIONAL?*\n\nBikin identitas bisnismu makin berkelas di *Luxcreativeee*.\n📸 *Cek:* [Instagram @luxcreativeee](https://www.instagram.com/luxcreativeee)",
    "🚀 *JASA PROMOSI GRUP / BISNIS*\n\nMau loker atau bisnismu dipromosikan otomatis?\n📩 *Hubungi Owner:* [Chat FELIXDEV](https://t.me/felixdev_owner)"
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
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        res = requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5).json()
        if res.get("ok") and res.get("result"):
            update = res["result"][0]
            update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "").lower()
            if "tes" in text:
                kirim_telegram("✅ *Bot VELA Aktif (Database: REDIS)!* \nSedang memantau loker... 🚀")
                requests.get(url, params={'offset': update_id + 1})
    except: pass

# --- [ SCRAPERS ] ---
def scrape_jora():
    jobs = []
    try:
        res = requests.get("https://id.jora.com/j?q=&l=Indonesia&st=date", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('div', class_='job-card')[:5]:
            a = card.find('a', class_='job-link')
            if a: jobs.append({"judul": a.text.strip(), "link": "https://id.jora.com" + a['href'].split('?')[0], "sumber": "Jora"})
    except: pass
    return jobs

def scrape_karir():
    jobs = []
    try:
        res = requests.get("https://www.karir.com/search", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('article', class_='row')[:5]:
            a = card.find('a', class_='opportunity-card-title')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Karir.com"})
    except: pass
    return jobs

def scrape_glints():
    jobs = []
    try:
        res = requests.get("https://glints.com/api/v1/search/jobs?location=Indonesia&limit=5", headers=HEADERS, timeout=10)
        data = res.json()
        for item in data.get('data', []):
            jobs.append({"judul": item.get('title'), "link": f"https://glints.com/id/opportunities/jobs/{item.get('id')}", "sumber": "Glints"})
    except: pass
    return jobs

def scrape_linkedin():
    jobs = []
    try:
        query = urllib.parse.quote('site:id.linkedin.com/jobs/view "Indonesia" "1 day ago"')
        res = requests.get(f"https://www.google.com/search?q={query}", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for g in soup.find_all('div', class_='tF2Cxc')[:3]:
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
        for card in soup.find_all('div', class_='job-box')[:5]:
            a = card.find('h3').find('a') if card.find('h3') else None
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Loker.id"})
    except: pass
    return jobs

# --- [ MAIN ENGINE ] ---
if __name__ == "__main__":
    print("🚀 BOT VELA ULTRA + REDIS DATABASE ONLINE!")
    loker_counter = 0

    while True:
        cek_pesan_masuk()
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Memindai loker...")
        
        semua_loker = (scrape_jora() + scrape_karir() + scrape_glints() + 
                       scrape_linkedin() + scrape_loker_id())
        
        ditemukan_baru = 0
        for job in semua_loker:
            # Mode Anti-Spam: Maksimal 3 loker baru per putaran
            if ditemukan_baru >= 3: break

            # Cek di Redis
            is_new = False
            if db:
                if not db.get(job['link']):
                    is_new = True
            else:
                # Fallback kalau Redis mati (jarang terjadi)
                is_new = True 

            if is_new:
                msg = (f"📢 *LOWONGAN TERBARU*\n\n📌 *Posisi:* {job['judul']}\n🌐 *Sumber:* {job['sumber']}\n\n"
                       f"🔗 [Klik untuk Detail]({job['link']})\n\n#loker #indonesia")
                
                if kirim_telegram(msg):
                    if db:
                        # Simpan ke Redis (kadaluarsa 7 hari)
                        db.setex(job['link'], 604800, "sent")
                    
                    ditemukan_baru += 1
                    loker_counter += 1
                    print(f"   ✅ Terkirim: {job['judul'][:30]}...")
                    
                    if loker_counter >= 12:
                        time.sleep(10)
                        kirim_telegram(random.choice(IKLAN_LIST))
                        loker_counter = 0
                
                time.sleep(10)

        print(f"✨ Selesai. Ditemukan {ditemukan_baru} loker baru.")
        
        # Standby 10 menit
        print("😴 Standby mode (10 mins)...")
        for _ in range(60): 
            cek_pesan_masuk()
            time.sleep(10)
