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

REDIS_URL = 'redis://default:JLZspxuVQdJlGmpjTmzHFJvfxWWAJTEe@redis.railway.internal:6379'

# --- [ DAFTAR BLACKLIST & PROTEKSI ] ---
KATA_KASAR = ['anjing', 'bangsat', 'memek', 'kontol', 'goblok', 'tolol', 'idiot'] 
WEB_TERLARANG = [
    'slot', 'gacor', 'deposit', 'jp', 'casino', 'poker', 'porn', 
    'bokep', 'sex', 'togel', 'linkaja.vip', 'bit.ly/slot-gacor', 'pola-gacor'
]

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

# --- [ CORE FUNCTIONS ] ---
def kirim_telegram(pesan, link=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': pesan, 
        'parse_mode': 'Markdown',
        'disable_web_page_preview': False
    }
    if link:
        payload['reply_markup'] = {
            "inline_keyboard": [[{"text": "🚀 Lamar Sekarang", "url": link}]]
        }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json().get("ok")
    except:
        return False

def proteksi_grup(update):
    """Menghapus pesan kasar atau link dari member"""
    message = update.get("message", {})
    text = message.get("text", "").lower()
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user = message.get("from", {}).get("username", "User")

    if not text: return False

    found_bad = any(word in text for word in KATA_KASAR + WEB_TERLARANG)
    # Proteksi link luar (agar grup tidak spam)
    found_link = any(x in text for x in ["http://", "https://", "www.", ".com", ".link", ".xyz"])

    if found_bad or found_link:
        url_del = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
        requests.post(url_del, data={'chat_id': chat_id, 'message_id': message_id})
        kirim_telegram(f"⚠️ @{user}, dilarang mengirim pesan kasar atau link luar!")
        return True
    return False

def cek_pesan_masuk():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        res = requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5).json()
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                update_id = update["update_id"]
                
                # Jalankan proteksi moderasi grup
                if proteksi_grup(update):
                    requests.get(url, params={'offset': update_id + 1})
                    continue

                message = update.get("message", {})
                text = message.get("text", "").lower()
                if "tes" in text:
                    kirim_telegram("✅ *Bot VELA Guardian Aktif!* \nMode: Proteksi Loker & Anti-Link Aktif. 🛡️")
                
                requests.get(url, params={'offset': update_id + 1})
    except: pass

# --- [ SEMUA SCRAPERS ] ---
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

def scrape_projects_id():
    jobs = []
    try:
        res = requests.get("https://projects.co.id/public/browse_projects/listing", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for row in soup.find_all('div', class_='row')[1:6]:
            h2 = row.find('h2')
            if h2 and h2.find('a'):
                a = h2.find('a')
                jobs.append({"judul": f"Project: {a.text.strip()}", "link": a['href'], "sumber": "Projects.co.id"})
    except: pass
    return jobs

def scrape_sribulancer():
    jobs = []
    try:
        res = requests.get("https://www.sribulancer.com/id/jobs", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for job in soup.select('.job-list-item')[:5]:
            a = job.select_one('h3 a')
            if a: jobs.append({"judul": f"Freelance: {a.text.strip()}", "link": "https://www.sribulancer.com" + a['href'], "sumber": "Sribulancer"})
    except: pass
    return jobs

def scrape_glints_freelance():
    jobs = []
    try:
        res = requests.get("https://glints.com/api/v1/search/jobs?location=Indonesia&limit=5&jobTypes=FREELANCE", headers=HEADERS, timeout=10)
        data = res.json()
        for item in data.get('data', []):
            jobs.append({"judul": f"Freelance: {item.get('title')}", "link": f"https://glints.com/id/opportunities/jobs/{item.get('id')}", "sumber": "Glints Freelance"})
    except: pass
    return jobs

def scrape_linkedin_freelance():
    jobs = []
    try:
        query = urllib.parse.quote('site:id.linkedin.com/jobs/view "Indonesia" "freelance"')
        res = requests.get(f"https://www.google.com/search?q={query}", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for g in soup.find_all('div', class_='tF2Cxc')[:3]:
            link = g.find('a')['href']
            if "linkedin.com/jobs" in link:
                jobs.append({"judul": "Loker Freelance LinkedIn", "link": link, "sumber": "LinkedIn"})
    except: pass
    return jobs

# --- [ MAIN ENGINE ] ---
if __name__ == "__main__":
    print("🚀 BOT VELA ULTRA GUARDIAN ONLINE!")
    loker_counter = 0

    while True:
        cek_pesan_masuk()
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Memindai loker & freelance...")
        
        # Gabungkan semua sumber loker & freelance
        semua_loker = (
            scrape_jora() + scrape_karir() + scrape_projects_id() + 
            scrape_sribulancer() + scrape_glints_freelance() + scrape_linkedin_freelance()
        )
        
        ditemukan_baru = 0
        for job in semua_loker:
            if ditemukan_baru >= 3: break # Anti-spam per putaran

            # Proteksi: Jangan posting loker jika judul mengandung kata terlarang
            if any(bad in job['judul'].lower() for bad in KATA_KASAR + WEB_TERLARANG):
                continue

            # Bersihkan link untuk Redis
            link_bersih = job['link'].split('?')[0]
            
            is_new = False
            if db:
                if not db.get(link_bersih):
                    is_new = True
            else:
                is_new = True 

            if is_new:
                emoji = "💼" if "Project" in job['judul'] or "Freelance" in job['judul'] else "📢"
                msg = (f"{emoji} *LOWONGAN TERBARU*\n\n"
                       f"📌 *Posisi:* {job['judul']}\n"
                       f"🌐 *Sumber:* {job['sumber']}\n\n"
                       f"#loker #freelance #kerja #indonesia")
                
                # Kirim ke Telegram dengan tombol lamar
                if kirim_telegram(msg, link_bersih):
                    if db:
                        db.setex(link_bersih, 604800, "sent") # Ingat selama 7 hari
                    
                    ditemukan_baru += 1
                    loker_counter += 1
                    print(f"    ✅ Terkirim: {job['judul'][:30]}...")
                    
                    # Iklan berkala setiap 12 postingan
                    if loker_counter >= 12:
                        time.sleep(5)
                        kirim_telegram(random.choice(IKLAN_LIST))
                        loker_counter = 0
                
                time.sleep(10) # Jeda antar kiriman agar tidak kena flood limit

        print(f"✨ Selesai. Ditemukan {ditemukan_baru} item baru.")
        print("😴 Standby mode (10 mins)...")
        for _ in range(60): 
            cek_pesan_masuk()
            time.sleep(10)
