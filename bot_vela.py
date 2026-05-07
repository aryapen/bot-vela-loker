import requests
from bs4 import BeautifulSoup
import time
import os
import urllib.parse
import random
import redis
import re

# --- [ KONFIGURASI ] ---
TOKEN = '8741502539:AAFHqzudVXD8C2m2xVudWJNs6ABu4V_YRz0'
CHAT_ID = '-1003997113925' 

# URL Redis (Pastikan ini sesuai dengan environment Railway kamu)
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:JLZspxuVQdJlGmpjTmzHFJvfxWWAJTEe@redis.railway.internal:6379')

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

# --- [ UTILITY FUNCTIONS ] ---

def deteksi_kategori(judul):
    """Fitur Canggih: Otomatis deteksi kualifikasi pendidikan"""
    judul = judul.lower()
    if any(k in judul for k in ['sma', 'smk', 'stm', 'sederajat', 'driver', 'kurir', 'security', 'satpam', 'operator', 'ob', 'cleaning']):
        return "🎓 *Kualifikasi:* SMA/SMK / Sederajat / Umum"
    elif any(k in judul for k in ['s1', 'd3', 'd4', 'sarjana', 'diploma', 'manager', 'lead', 'specialist']):
        return "🎓 *Kualifikasi:* Diploma / Sarjana (D3/S1)"
    else:
        return "🎓 *Kualifikasi:* Semua Jenjang / Umum"

def kirim_telegram(pesan, link=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': pesan, 
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    if link:
        payload['reply_markup'] = {
            "inline_keyboard": [[{"text": "🚀 Lamar Sekarang / Cek Detail", "url": link}]]
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
    # Proteksi link luar agar grup tidak spam
    found_link = any(x in text for x in ["http://", "https://", "www.", ".com", ".link", ".xyz"])

    if found_bad or (found_link and str(chat_id) == CHAT_ID):
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
                if proteksi_grup(update):
                    requests.get(url, params={'offset': update_id + 1})
                    continue
                message = update.get("message", {})
                text = message.get("text", "").lower()
                if "/start" in text or "tes" in text:
                    kirim_telegram("✅ *Bot VELA Guardian Aktif!* \nMode: Proteksi Loker & Anti-Link Aktif. 🛡️")
                requests.get(url, params={'offset': update_id + 1})
    except: pass

# --- [ SEMUA SCRAPERS ] ---

def scrape_loker_id():
    """Jangkauan Luas: SMA/SMK - S1"""
    jobs = []
    try:
        res = requests.get("https://www.loker.id/cari-lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.select('.job-box')[:5]:
            a = card.select_one('h3 a')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Loker.id"})
    except: pass
    return jobs

def scrape_indojob():
    """Jangkauan Luas: Staf & Operasional"""
    jobs = []
    try:
        res = requests.get("https://www.indojob.com/lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.job-list')[:5]:
            a = item.select_one('h4 a')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Indojob"})
    except: pass
    return jobs

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

def scrape_glints_freelance():
    jobs = []
    try:
        res = requests.get("https://glints.com/api/v1/search/jobs?location=Indonesia&limit=5&jobTypes=FREELANCE", headers=HEADERS, timeout=10)
        data = res.json()
        for item in data.get('data', []):
            jobs.append({"judul": f"Freelance: {item.get('title')}", "link": f"https://glints.com/id/opportunities/jobs/{item.get('id')}", "sumber": "Glints"})
    except: pass
    return jobs

# --- [ MAIN ENGINE ] ---
if __name__ == "__main__":
    print("🚀 BOT VELA ULTRA GUARDIAN ONLINE!")
    loker_counter = 0

    while True:
        cek_pesan_masuk()
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Memindai semua jenis loker...")
        
        # Gabungkan semua sumber (S1 + SMA/SMK + Freelance)
        semua_loker = (
            scrape_loker_id() + scrape_indojob() + 
            scrape_jora() + scrape_projects_id() + scrape_glints_freelance()
        )
        
        random.shuffle(semua_loker) # Acak urutan agar sumber tidak membosankan
        ditemukan_baru = 0
        
        for job in semua_loker:
            if ditemukan_baru >= 4: break 

            # Proteksi judul dari kata terlarang
            if any(bad in job['judul'].lower() for bad in KATA_KASAR + WEB_TERLARANG):
                continue

            link_bersih = job['link'].split('?')[0]
            
            is_new = False
            if db:
                if not db.get(link_bersih):
                    is_new = True
            else:
                is_new = True 

            if is_new:
                # Deteksi kategori pendidikan
                kategori = deteksi_kategori(job['judul'])
                
                emoji = "💼" if "Project" in job['judul'] or "Freelance" in job['judul'] else "📢"
                msg = (f"{emoji} *LOWONGAN TERBARU*\n\n"
                       f"📌 *Posisi:* {job['judul']}\n"
                       f"{kategori}\n"
                       f"🌐 *Sumber:* {job['sumber']}\n\n"
                       f"⚠️ *Peringatan:* Waspada penipuan! Loker resmi tidak memungut biaya apapun.\n"
                       f"#loker #freelance #kerjaterbaru #indonesia")
                
                if kirim_telegram(msg, link_bersih):
                    if db:
                        db.setex(link_bersih, 604800, "sent") # Simpan 7 hari
                    
                    ditemukan_baru += 1
                    loker_counter += 1
                    print(f"    ✅ Terkirim: {job['judul'][:30]}...")
                    
                    # Iklan berkala setiap 12 postingan
                    if loker_counter >= 12:
                        time.sleep(5)
                        kirim_telegram(random.choice(IKLAN_LIST))
                        loker_counter = 0
                
                time.sleep(15) # Jeda agar tidak terkena rate limit Telegram

        print(f"✨ Selesai. Ditemukan {ditemukan_baru} item baru.")
        print("😴 Standby mode (10 mins)...")
        
        # Idle selama 10 menit sambil tetap memantau chat masuk
        for _ in range(60): 
            cek_pesan_masuk()
            time.sleep(10)
