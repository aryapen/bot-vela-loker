import requests
from bs4 import BeautifulSoup
import time
import os
import random
import redis
import re

# --- [ KONFIGURASI ] ---
# Ganti dengan token kamu atau biarkan menggunakan Environment Variables
TOKEN = os.getenv('TELEGRAM_TOKEN', '8741502539:AAFHqzudVXD8C2m2xVudWJNs6ABu4V_YRz0')
CHAT_ID = os.getenv('CHAT_ID', '-1003997113925')
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:JLZspxuVQdJlGmpjTmzHFJvfxWWAJTEe@redis.railway.internal:6379')

# --- [ DATABASE SETUP ] ---
try:
    db = redis.from_url(REDIS_URL, decode_responses=True)
    print("✅ VELA Database Connected!")
except:
    db = None
    print("⚠️ Running without Redis")

# --- [ DAFTAR KATA KASAR & IKLAN ] ---
# Regex untuk menangkap kata kasar (bisa kamu tambah sendiri di dalam kurung)
POLA_KASAR = r"(anjing|anjg|anj|kntol|kontol|memek|mmk|bgst|bangsat|goblok|gblk|tolol|idiot|peler|pler|asu|jancok|bajingan)"

IKLAN_LIST = [
    "🎨 *BUTUH LOGO PROFESIONAL?*\n\nBikin identitas bisnismu makin berkelas di *Luxcreativeee*.\n📸 *Cek:* [Instagram @luxcreativeee](https://www.instagram.com/luxcreativeee)",
    "🚀 *JASA PROMOSI GRUP / BISNIS*\n\nMau loker atau bisnismu dipromosikan otomatis?\n📩 *Hubungi Owner:* [Chat FELIXDEV](https://t.me/felixdev_owner)"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- [ FUNGSI CORE ] ---

def kirim_telegram(pesan, link=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': pesan, 
        'parse_mode': 'Markdown', 
        'disable_web_page_preview': True
    }
    if link:
        payload['reply_markup'] = {"inline_keyboard": [[{"text": "🚀 LAMAR SEKARANG", "url": link}]]}
    
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def proteksi_grup(update):
    """Menghapus pesan toxic & link luar secara instan"""
    message = update.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user = message.get("from", {}).get("username", "User")

    if not text: return False

    # Cek Kata Kasar & Link
    found_bad = re.search(POLA_KASAR, text.lower())
    found_link = any(x in text.lower() for x in ["http://", "https://", "www.", ".com", ".link", ".xyz", "bit.ly"])

    if found_bad or found_link:
        url_del = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
        requests.post(url_del, data={'chat_id': chat_id, 'message_id': message_id})
        
        alasan = "KATA KASAR" if found_bad else "LINK LUAR"
        kirim_telegram(f"⚠️ @{user}, pesan kamu dihapus karena mengandung *{alasan}*!")
        return True
    return False


def scrap_instagram(url):
    """Mengambil data Instagram Reels menggunakan API yang kamu dapatkan"""
    api_url = "https://instagram-reels-downloader-api.p.rapidapi.com/download"
    
    # Header sesuai dengan curl yang kamu berikan
    headers = {
        "x-rapidapi-host": "instagram-reels-downloader-api.p.rapidapi.com",
        "x-rapidapi-key": "084b4c8d9dmshe2c908f5a8c27dep185c91jsn6cf76429d2e6", # Key kamu
        "Content-Type": "application/json"
    }
    
    # Parameter URL instagram yang mau di-scrap
    querystring = {"url": url}
    
    try:
        print(f"📡 Menghubungi API Instagram untuk: {url}")
        response = requests.get(api_url, headers=headers, params=querystring, timeout=15)
        data = response.json()
        
        # Logika pengambilan caption (biasanya di field 'description' atau 'title')
        # Kita pakai .get() supaya tidak error kalau field-nya kosong
        res_data = data.get("data", {})
        caption = res_data.get("description") or res_data.get("title") or "Postingan Instagram Reels"
        
        # Potong caption biar jadi judul ringkas
        judul = caption[:80] + "..." if len(caption) > 80 else caption
        return judul, url, "Instagram Reels"
        
    except Exception as e:
        print(f"❌ Error saat scrap IG: {e}")
        return "Loker Instagram (Klik Link)", url, "Instagram"

def cek_pesan_masuk():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        res = requests.get(url, params={'offset': -1, 'timeout': 1}, timeout=5).json()
        
        if res.get("ok") and res.get("result"):
            for update in res["result"]:
                update_id = update["update_id"]
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id_asal = message.get("chat", {}).get("id")
                chat_type = message.get("chat", {}).get("type")
                user_sender = message.get("from", {}).get("username", "")

                # --- FITUR JAPRI (PRIVATE CHAT) ---
                if chat_type == "private" and text.startswith("http"):
                    # Kirim notif ke kamu kalau bot lagi kerja
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  json={'chat_id': chat_id_asal, 'text': "⏳ Sedang memproses link..."})
                    
                    judul, link, sumber = scrap_universal(text)
                    
                    msg = (
                        f"🚀 *LOKER PILIHAN ADMIN*\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📌 *Posisi:* {judul}\n"
                        f"🏢 *Sumber:* {sumber}\n"
                        f"🛡️ *Verifikasi:* Admin Verified\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"#loker #rekomendasi #vela"
                    )
                    
                    # Kirim hasil scraping ke GRUP (CHAT_ID)
                    kirim_telegram(msg, link)
                    
                    # Balas ke kamu kalau sudah sukses
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  json={'chat_id': chat_id_asal, 'text': "✅ Berhasil diteruskan ke grup!"})
                    
                    requests.get(url, params={'offset': update_id + 1})
                    continue

                # --- PROTEKSI GRUP TETAP JALAN ---
                if chat_type in ["group", "supergroup"]:
                    if proteksi_grup(update):
                        requests.get(url, params={'offset': update_id + 1})
                        continue
                
                requests.get(url, params={'offset': update_id + 1})
    except Exception as e:
        print(f"Error: {e}")

# --- [ SCRAPER LOKER (SEMUA SUMBER) ] ---

def get_all_jobs():
    jobs = []
    
    # 1. Loker.id
    try:
        r = requests.get("https://www.loker.id/cari-lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('.job-box')[:3]:
            a = item.select_one('h3 a')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Loker.id"})
    except: pass

    # 2. Indojob
    try:
        r = requests.get("https://www.indojob.com/lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('.job-list')[:3]:
            a = item.select_one('h4 a')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Indojob"})
    except: pass

    # 3. Projects.co.id (Freelance)
    try:
        r = requests.get("https://projects.co.id/public/browse_projects/listing", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        for row in soup.find_all('div', class_='row')[1:3]:
            h2 = row.find('h2')
            if h2 and h2.find('a'):
                a = h2.find('a')
                jobs.append({"judul": f"Freelance: {a.text.strip()}", "link": a['href'], "sumber": "Projects.co.id"})
    except: pass

    return jobs

# --- [ MAIN RUNNER ] ---

if __name__ == "__main__":
    print("🔥 VELA GUARDIAN v4.0 STARTED (STABLE MODE) 🔥")
    loker_counter = 0

    while True:
        cek_pesan_masuk()
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Scanning Loker...")
        
        jobs = get_all_jobs()
        random.shuffle(jobs)
        
        sent_this_round = 0
        for job in jobs:
            if sent_this_round >= 3: break
            
            # Cek Duplikat di Redis
            link_id = job['link'].split('?')[0]
            if db and db.get(link_id): continue

            # Format Pesan
            msg = (
                f"🌟 *INFO LOKER TERVALID*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Posisi:* {job['judul']}\n"
                f"🏢 *Sumber:* {job['sumber']}\n"
                f"🛡️ *Status:* Terverifikasi Sistem\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"#loker #infocepet #guardian #vela"
            )

            kirim_telegram(msg, job['link'])
            if db: db.setex(link_id, 604800, "sent")
            
            sent_this_round += 1
            loker_counter += 1
            
            # Kirim Iklan setiap 10 loker
            if loker_counter >= 10:
                time.sleep(5)
                kirim_telegram(random.choice(IKLAN_LIST))
                loker_counter = 0
            
            time.sleep(20) # Jeda antar postingan agar tidak spam

        print(f"✅ Selesai. Standby 10 menit...")
        # Standby 10 menit sambil tetap pantau chat grup
        for _ in range(60): 
            cek_pesan_masuk()
            time.sleep(10)
