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

# Tambahkan username Instagram yang mau dipantau di sini
TARGET_ACCOUNTS = [
    "loker_jakarta",
    "kemenaker",
    "disnaker",
    "loker_my_id"
]

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


# --- [ 1. FUNGSI SCRAPER INSTAGRAM ] ---
def scrap_instagram(url):
    """Mengambil data Instagram Reels menggunakan API RapidAPI"""
    api_url = "https://instagram-reels-downloader-api.p.rapidapi.com/download"
    
    headers = {
        "x-rapidapi-host": "instagram-reels-downloader-api.p.rapidapi.com",
        "x-rapidapi-key": "084b4c8d9dmshe2c908f5a8c27dep185c91jsn6cf76429d2e6",
        "Content-Type": "application/json"
    }
    
    querystring = {"url": url}
    
    try:
        print(f"📡 Menghubungi API Instagram untuk: {url}")
        response = requests.get(api_url, headers=headers, params=querystring, timeout=15)
        data = response.json()
        
        res_data = data.get("data", {})
        caption = res_data.get("description") or res_data.get("title") or "Postingan Instagram Reels"
        
        judul = caption[:80] + "..." if len(caption) > 80 else caption
        return judul, url, "Instagram Reels"
        
    except Exception as e:
        print(f"❌ Error saat scrap IG: {e}")
        return "Loker Instagram (Klik Link)", url, "Instagram"

# --- [ 2. FUNGSI SCRAPER UNIVERSAL ] ---
# Letakkan ini DI BAWAH scrap_instagram tapi DI ATAS cek_pesan_masuk
def scrap_universal(url):
    """Fungsi pembungkus untuk membedakan link IG atau Web Biasa"""
    clean_url = url.split('?')[0]
    
    # Jika link Instagram, gunakan fungsi scrap_instagram di atas
    if "instagram.com" in clean_url:
        return scrap_instagram(clean_url)
    
    # Jika link web biasa, gunakan BeautifulSoup
    try:
        r = requests.get(clean_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        judul = soup.find('h1').text.strip() if soup.find('h1') else soup.title.text.strip()
        return judul, clean_url, "Web Loker"
    except:
        return "Lowongan Kerja Baru", clean_url, "Web"

# --- [ 3. FUNGSI CEK PESAN MASUK ] ---
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
                    # Kirim notif progres
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  json={'chat_id': chat_id_asal, 'text': "⏳ Sedang memproses link..."})
                    
                    # Memanggil scrap_universal (Sekarang sudah terdefinisi di atas)
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
                    
                    # Kirim ke GRUP
                    kirim_telegram(msg, link)
                    
                    # Balas ke kamu
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  json={'chat_id': chat_id_asal, 'text': "✅ Berhasil diteruskan ke grup!"})
                    
                    requests.get(url, params={'offset': update_id + 1})
                    continue

                # --- FITUR PROTEKSI GRUP ---
                if chat_type in ["group", "supergroup"]:
                    if proteksi_grup(update):
                        requests.get(url, params={'offset': update_id + 1})
                        continue

                requests.get(url, params={'offset': update_id + 1})
    except Exception as e:
        print(f"Error di cek_pesan_masuk: {e}")


def monitor_semua_ig():
    """Mengecek postingan terbaru dari semua akun di TARGET_ACCOUNTS"""
    # Gunakan endpoint 'user_posts' atau 'posts' sesuai API kamu
    api_url = "https://instagram-reels-downloader-api.p.rapidapi.com/user_posts" 
    headers = {
        "x-rapidapi-host": "instagram-reels-downloader-api.p.rapidapi.com",
        "x-rapidapi-key": "084b4c8d9dmshe2c908f5a8c27dep185c91jsn6cf76429d2e6",
    }

    for username in TARGET_ACCOUNTS:
        try:
            print(f"🔄 Checking @{username}...")
            res = requests.get(api_url, headers=headers, params={"username": username}, timeout=15)
            data = res.json()
            
            # Ambil post terbaru
            posts = data.get("data", [])
            if not posts:
                continue
            
            top_post = posts[0]
            post_id = top_post.get("id")
            shortcode = top_post.get("shortcode")
            post_link = f"https://www.instagram.com/p/{shortcode}/"
            caption = top_post.get("description") or "Cek postingan terbaru!"

            # CEK DATABASE (Wajib pakai Redis agar tidak spam)
            db_key = f"last_id_{username}"
            if db and db.get(db_key) == post_id:
                continue # Skip kalau ID masih sama dengan yang lama

            # Format Pesan Cantik
            msg = (
                f"📢 *UPDATE TERBARU: @{username}*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📝 {caption[:250]}...\n\n"
                f"🔗 *Cek Selengkapnya di IG*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"#loker #update #monitor"
            )

            kirim_telegram(msg, post_link)
            
            # Simpan ID baru ke Redis
            if db:
                db.set(db_key, post_id)
            
            # Jeda sebentar antar akun biar API nggak curiga
            time.sleep(5)

        except Exception as e:
            print(f"❌ Error monitor @{username}: {e}")


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
    
    loker_counter = 0    # Untuk hitung kapan kirim iklan
    timer_ig = 0         # Untuk jeda monitor akun target (IG)
    timer_web = 0        # Untuk jeda scraper web (Loker.id dll)

    while True:
        # --- 1. HANDLE REALTIME (Proteksi Grup & Link Japri) ---
        # Fungsi ini dijalankan setiap awal loop (sangat sering)
        cek_pesan_masuk()

        # --- 2. MONITOR AKUN TARGET INSTAGRAM (Setiap 2 Jam) ---
        # 720 loop * 10 detik = 7200 detik = 120 menit
        if timer_ig >= 720:
            print(f"📸 [{time.strftime('%H:%M:%S')}] Monitoring Akun Instagram Target...")
            monitor_semua_ig()
            timer_ig = 0 # Reset timer

        # --- 3. SCRAPER WEB OTOMATIS (Setiap 30 Menit) ---
        # Kita jalankan jika timer_web sudah mencapai 180 (180 * 10 detik = 30 menit)
        if timer_web >= 180:
            print(f"🔄 [{time.strftime('%H:%M:%S')}] Scanning Loker Web (Loker.id, dll)...")
            
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
                if db: db.setex(link_id, 604800, "sent") # Simpan 7 hari
                
                sent_this_round += 1
                loker_counter += 1
                
                # Kirim Iklan setiap 10 loker yang terkirim
                if loker_counter >= 10:
                    time.sleep(5)
                    kirim_telegram(random.choice(IKLAN_LIST))
                    loker_counter = 0
                
                time.sleep(20) # Jeda antar postingan agar tidak spam/limit
            
            print(f"✅ Selesai Scanning Web. Standby...")
            timer_web = 0 # Reset timer

        # --- 4. STANDBY MODE (10 Detik) ---
        # Loop kecil ini supaya bot tidak memakan CPU tinggi tapi tetap responsif
        time.sleep(10)
        timer_ig += 1
        timer_web += 1
