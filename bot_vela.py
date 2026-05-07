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

# --- [ DAFTAR BLACKLIST ] ---
# Tambahkan kata-kata yang ingin diblokir di sini
KATA_KASAR = ['anjing', 'bangsat', 'memek', 'kontol', 'goblok', 'tolol'] 

# Keyword situs terlarang
WEB_TERLARANG = [
    'slot', 'gacor', 'deposit', 'jp', 'casino', 'poker', 'porn', 
    'bokep', 'sex', 'togel', 'linkaja.vip', 'bit.ly/slot-gacor'
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
    
    # Jika ada link, tambahkan tombol
    if link:
        payload['reply_markup'] = {
            "inline_keyboard": [[
                {"text": "🚀 Lamar Sekarang", "url": link}
            ]]
        }
        
    try:
        r = requests.post(url, json=payload, timeout=15) # Gunakan json= untuk struktur tombol
        return r.json().get("ok")
    except:
        return False

def cek_pesan_masuk():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        res = requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5).json()
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                update_id = update["update_id"]
                
                # JALANKAN PROTEKSI GRUP
                if proteksi_grup(update):
                    requests.get(url, params={'offset': update_id + 1})
                    continue

                # Deteksi link apapun (kecuali dikirim bot sendiri)
    if "http" in text or "www." in text or ".com" in text:
        # Hapus jika bukan bot/admin (opsional, tapi disarankan)
        url_del = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
        requests.post(url_del, data={'chat_id': chat_id, 'message_id': message_id})
        kirim_telegram(f"⚠️ @{user}, dilarang share link di grup ini!")
        return True

                # Cek Perintah 'tes'
                message = update.get("message", {})
                text = message.get("text", "").lower()
                if "tes" in text:
                    kirim_telegram("✅ *Bot VELA Guardian Aktif!* \nMode: Proteksi Loker & Anti-Spam aktif. 🛡️")
                
                # Geser offset agar tidak membaca pesan yang sama
                requests.get(url, params={'offset': update_id + 1})
    except: pass

# --- [ SCRAPERS LOKER REGULAR ] ---
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

# --- [ SCRAPERS FREELANCE & PROJECT ] ---
def scrape_projects_id():
    """Scrape project terbaru dari Projects.co.id"""
    jobs = []
    try:
        res = requests.get("https://projects.co.id/public/browse_projects/listing", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for row in soup.find_all('div', class_='row')[1:6]:
            h2 = row.find('h2')
            if h2 and h2.find('a'):
                a = h2.find('a')
                jobs.append({
                    "judul": f"Project: {a.text.strip()}",
                    "link": a['href'],
                    "sumber": "Projects.co.id"
                })
    except: pass
    return jobs

def scrape_sribulancer():
    """Scrape freelance jobs dari Sribulancer"""
    jobs = []
    try:
        res = requests.get("https://www.sribulancer.com/id/jobs", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for job in soup.select('.job-list-item')[:5]:
            a = job.select_one('h3 a')
            if a:
                jobs.append({
                    "judul": f"Freelance: {a.text.strip()}",
                    "link": "https://www.sribulancer.com" + a['href'],
                    "sumber": "Sribulancer"
                })
    except: pass
    return jobs

def scrape_glints_freelance():
    """Scrape khusus tipe Freelance di Glints"""
    jobs = []
    try:
        # Menambahkan filter jobTypes=FREELANCE
        res = requests.get("https://glints.com/api/v1/search/jobs?location=Indonesia&limit=5&jobTypes=FREELANCE", headers=HEADERS, timeout=10)
        data = res.json()
        for item in data.get('data', []):
            jobs.append({
                "judul": f"Freelance: {item.get('title')}", 
                "link": f"https://glints.com/id/opportunities/jobs/{item.get('id')}", 
                "sumber": "Glints Freelance"
            })
    except: pass
    return jobs

def scrape_linkedin_freelance():
    """Cari freelance via Google Search (LinkedIn)"""
    jobs = []
    try:
        query = urllib.parse.quote('site:id.linkedin.com/jobs/view "Indonesia" "freelance" "remote"')
        res = requests.get(f"https://www.google.com/search?q={query}", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for g in soup.find_all('div', class_='tF2Cxc')[:3]:
            link = g.find('a')['href']
            if "linkedin.com/jobs" in link:
                jobs.append({"judul": "Loker Freelance LinkedIn", "link": link, "sumber": "LinkedIn"})
    except: pass
    return jobs

def proteksi_grup(update):
    """Fungsi untuk memoderasi pesan dari member"""
    message = update.get("message", {})
    text = message.get("text", "").lower()
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user = message.get("from", {}).get("username", "User")

    # Cek apakah ada kata kasar atau link judi
    found_bad_word = any(word in text for word in KATA_KASAR)
    found_bad_link = any(link in text for link in WEB_TERLARANG)

    if found_bad_word or found_bad_link:
        # Hapus pesan pelanggar
        url_del = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
        requests.post(url_del, data={'chat_id': chat_id, 'message_id': message_id})
        
        # Kirim peringatan (opsional)
        peringatan = f"⚠️ @{user}, dilarang mengirim pesan kasar atau link terlarang!"
        kirim_telegram(peringatan)
        return True
    return False

# --- [ MAIN ENGINE ] ---
if __name__ == "__main__":
    print("🚀 BOT VELA ULTRA FREELANCE + REDIS ONLINE!")
    loker_counter = 0

    while True:
        cek_pesan_masuk()
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Memindai loker & freelance...")
        
        # Gabungkan semua sumber
        semua_loker = (
            scrape_jora() + 
            scrape_karir() + 
            scrape_projects_id() + 
            scrape_sribulancer() + 
            scrape_glints_freelance() + 
            scrape_linkedin_freelance()
        )
        
        ditemukan_baru = 0
        for job in semua_loker:
            # Mode Anti-Spam: Maksimal 3 konten baru per putaran agar tidak di-ban Telegram
            if ditemukan_baru >= 3: break
                
            if any(bad in job['judul'].lower() for bad in KATA_KASAR + WEB_TERLARANG):
                print(f"🚫 Loker diblokir karena tidak pantas: {job['judul']}")
                continue
                
            # Cek di Redis
            is_new = False
            if db:
                        # Bersihkan link dari parameter tambahan (seperti ?utm_source=...)
                        link_bersih = job['link'].split('?')[0]
                        db.setex(link_bersih, 604800, "sent")
            else:
                is_new = True 

            if is_new:
                # Format Pesan
                emoji = "💼" if "Project" in job['judul'] else "📢"
                msg = (f"{emoji} *LOWONGAN/PROJECT BARU*\n\n"
                       f"📌 *Posisi:* {job['judul']}\n"
                       f"🌐 *Sumber:* {job['sumber']}\n\n"
                       f"🔗 [Klik untuk Detail]({job['link']})\n\n"
                       f"#loker #freelance #kerjaan #indonesia")
                
                if kirim_telegram(msg):
                    if db:
                        # Simpan ke Redis (kadaluarsa 7 hari)
                        db.setex(job['link'], 604800, "sent")
                    
                    ditemukan_baru += 1
                    loker_counter += 1
                    print(f"    ✅ Terkirim: {job['judul'][:30]}...")
                    
                    # Cek jika sudah saatnya kirim iklan (setiap 12 post)
                    if loker_counter >= 12:
                        time.sleep(5)
                        kirim_telegram(random.choice(IKLAN_LIST))
                        loker_counter = 0
                
                time.sleep(10) # Jeda antar pengiriman pesan

        print(f"✨ Selesai. Ditemukan {ditemukan_baru} item baru.")
        
        # Standby 10 menit (600 detik)
        print("😴 Standby mode (10 mins)...")
        for _ in range(60): 
            cek_pesan_masuk() # Tetap cek pesan 'tes' saat tidur
            time.sleep(10)
