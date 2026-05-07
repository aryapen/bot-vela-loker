import requests
from bs4 import BeautifulSoup
import time
import os
import urllib.parse
import random
import redis
import json
import re

# --- [ KONFIGURASI ] ---
TOKEN = '8741502539:AAFHqzudVXD8C2m2xVudWJNs6ABu4V_YRz0'
CHAT_ID = '-1003997113925' 
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

REDIS_URL = os.getenv('REDIS_URL', 'redis://default:JLZspxuVQdJlGmpjTmzHFJvfxWWAJTEe@redis.railway.internal:6379')

# --- [ DAFTAR BLACKLIST & PROTEKSI ] ---
KATA_KASAR = ['anjing', 'bangsat', 'memek', 'kontol', 'goblok', 'tolol', 'idiot'] 
WEB_TERLARANG = [
    'slot', 'gacor', 'deposit', 'jp', 'casino', 'poker', 'porn', 
    'bokep', 'sex', 'togel', 'linkaja.vip', 'bit.ly/slot-gacor', 'pola-gacor'
]

IKLAN_LIST = [
    "🎨 *BUTUH LOGO PROFESIONAL?*\n\nBikin identitas bisnismu makin berkelas di *Luxcreativeee*.\n📸 *Cek:* [Instagram @luxcreativeee](https://www.instagram.com/luxcreativeee)",
    "🚀 *JASA PROMOSI GRUP / BISNIS*\n\nMau loker atau bisnismu dipromosikan otomatis?\n📩 *Hubungi Owner:* [Chat FELIXDEV](https://t.me/felixdev_owner)"
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

# --- [ AI ENGINE: OPENROUTER ] ---
def analisa_loker_ai(judul, sumber):
    """Menganalisis loker untuk ringkasan, kategori, dan skor keamanan"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    prompt = (
        f"Analisa loker: '{judul}' dari {sumber}. Berikan output JSON mentah "
        "(tanpa markdown) dengan key: 'ringkasan' (maks 15 kata), "
        "'kategori' (SMA/SMK, S1/Diploma, atau Umum), 'skor_aman' (0-100), "
        "dan 'catatan' (tips singkat keamanan)."
    )
    payload = {
        "model": "google/gemini-flash-1.5-8b:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        konten = res.json()['choices'][0]['message']['content']
        clean_json = konten.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except:
        return {"ringkasan": judul, "kategori": "Umum", "skor_aman": 70, "catatan": "Selalu waspada penipuan."}

# --- [ CORE FUNCTIONS : TELEGRAM & PROTEKSI ] ---
def kirim_telegram(pesan, link=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': pesan, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
    if link:
        payload['reply_markup'] = {"inline_keyboard": [[{"text": "🚀 Lamar Sekarang", "url": link}]]}
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json().get("ok")
    except: return False

def proteksi_grup(update):
    """MENGHAPUS pesan kasar atau link luar (Fitur Guardian)"""
    message = update.get("message", {})
    text = message.get("text", "").lower()
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    user = message.get("from", {}).get("username", "User")

    if not text: return False
    found_bad = any(word in text for word in KATA_KASAR + WEB_TERLARANG)
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
                if proteksi_grup(update):
                    requests.get(url, params={'offset': update_id + 1})
                    continue
                message = update.get("message", {})
                if "tes" in message.get("text", "").lower():
                    kirim_telegram("✅ *VELA Ultra Guardian v3.0 Aktif!* \nMode: AI Analis & Proteksi On. 🛡️")
                requests.get(url, params={'offset': update_id + 1})
    except: pass

# --- [ SEMUA SCRAPERS : CAKUPAN LUAS ] ---
def scrape_all_sources():
    jobs = []
    # 1. Loker.id (SMA/SMK/Umum)
    try:
        res = requests.get("https://www.loker.id/cari-lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.select('.job-box')[:3]:
            a = card.select_one('h3 a')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Loker.id"})
    except: pass

    # 2. Indojob (Operasional/Staf)
    try:
        res = requests.get("https://www.indojob.com/lowongan-kerja", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.job-list')[:3]:
            a = item.select_one('h4 a')
            if a: jobs.append({"judul": a.text.strip(), "link": a['href'], "sumber": "Indojob"})
    except: pass

    # 3. Jora (Agregator Nasional)
    try:
        res = requests.get("https://id.jora.com/j?q=&l=Indonesia&st=date", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for card in soup.find_all('div', class_='job-card')[:3]:
            a = card.find('a', class_='job-link')
            if a: jobs.append({"judul": a.text.strip(), "link": "https://id.jora.com" + a['href'].split('?')[0], "sumber": "Jora"})
    except: pass

    # 4. Projects.co.id (Freelance)
    try:
        res = requests.get("https://projects.co.id/public/browse_projects/listing", headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for row in soup.find_all('div', class_='row')[1:3]:
            h2 = row.find('h2')
            if h2 and h2.find('a'):
                a = h2.find('a')
                jobs.append({"judul": f"Freelance: {a.text.strip()}", "link": a['href'], "sumber": "Projects.co.id"})
    except: pass
    
    return jobs

# --- [ MAIN ENGINE ] ---
if __name__ == "__main__":
    print("🚀 BOT VELA ULTRA GUARDIAN AI ONLINE!")
    loker_counter = 0

    while True:
        cek_pesan_masuk()
        print(f"🔄 [{time.strftime('%H:%M:%S')}] Memindai loker...")
        
        semua_loker = scrape_all_sources()
        random.shuffle(semua_loker)
        
        ditemukan_baru = 0
        for job in semua_loker:
            if ditemukan_baru >= 3: break # Anti-flood per putaran

            if any(bad in job['judul'].lower() for bad in KATA_KASAR + WEB_TERLARANG): continue

            link_id = job['link'].split('?')[0]
            if db and db.get(link_id): continue

            # --- [ PROSES AI ] ---
            print(f"🤖 AI Menganalisa: {job['judul'][:30]}...")
            ai = analisa_loker_ai(job['judul'], job['sumber'])
            
            skor = ai.get('skor_aman', 70)
            shield = "🟢" if skor > 75 else "🟡" if skor > 45 else "🔴"

            msg = (
                f"🌟 *INFO LOKER TERBARU*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 *Posisi:* {job['judul']}\n"
                f"🎓 *Pendidikan:* {ai.get('kategori')}\n"
                f"🏢 *Sumber:* {job['sumber']}\n\n"
                f"📝 *Ringkasan:* _{ai.get('ringkasan')}_\n\n"
                f"{shield} *Rating Aman:* {skor}/100\n"
                f"⚠️ *Catatan:* {ai.get('catatan')}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"#loker #infocepet #aiguardian"
            )

            if kirim_telegram(msg, job['link']):
                if db: db.setex(link_id, 604800, "sent")
                ditemukan_baru += 1
                loker_counter += 1
                
                # Fitur Iklan Berkala
                if loker_counter >= 12:
                    time.sleep(5)
                    kirim_telegram(random.choice(IKLAN_LIST))
                    loker_counter = 0
                
                time.sleep(15) # Jeda antar kiriman

        print(f"✨ Selesai. Menemukan {ditemukan_baru} loker baru.")
        print("😴 Standby 10 menit (Pantau Chat)...")
        for _ in range(60): 
            cek_pesan_masuk()
            time.sleep(10)
