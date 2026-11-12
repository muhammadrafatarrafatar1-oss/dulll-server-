from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random
import string
import requests
import cloudscraper
import re

app = Flask(__name__)
CORS(app)

# === KONFIGURASI TURSO ===
TURSO_URL = "https://dulll-dull.aws-ap-southeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE4MjU5NTgxNDAsImlhdCI6MTc5NDQyMjE0MCwiaWQiOiIwMWExY2I2Mi0yMjAxLTdlNjAtODM5NC01NTE1ZmY0YmIzNTAiLCJraWQiOiJEcnl5QVM3MGlIcVZ4YmZvcVkwcjhzaTRhcXUwQjlsVXhYbXl5X21oc1l3IiwicmlkIjoiMTYwMzczZjktOTg1MC00YWExLWJjOGQtMDU0ZDg1MDE4ZDJmIn0.ri6aHHSahAM3N23hUetTZN_bckNNbC9jaQHElGu5-Zws_Vsc2tXU6_IMXvkNRPOf4i3_UksLmourFOA_rngTDw"

def _to_arg(v):
    if v is None: return {"type": "null"}
    if isinstance(v, int): return {"type": "integer", "value": str(v)}
    if isinstance(v, float): return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}

def execute_query(sql, args=None):
    headers = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    formatted_args = [_to_arg(a) for a in args] if args else []
    payload = {"requests": [{"type": "execute", "stmt": {"sql": sql, "args": formatted_args}}, {"type": "close"}]}
    response = requests.post(f"{TURSO_URL}/v2/pipeline", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def init_db():
    try:
        # Tabel API Keys
        execute_query("CREATE TABLE IF NOT EXISTS api_keys (key TEXT PRIMARY KEY, owner TEXT, is_active INTEGER DEFAULT 1)")
    except Exception as e:
        print(f"DB Error: {e}")

@app.route('/')
def home(): return render_template('index.html')

# === ENDPOINT: GENERATE API KEY PUBLIK ===
@app.route('/api/generate_key', methods=['POST'])
def generate_api_key():
    # Bikin key random format DULLL-XXXX-XXXX-XXXX
    chars = string.ascii_uppercase + string.digits
    blocks = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    new_key = f"DULLL-{'-'.join(blocks)}"

    try:
        # Simpan ke database Turso
        execute_query("INSERT INTO api_keys (key, owner) VALUES (?, ?)", [new_key, "Public"])
        return jsonify({"status": "success", "api_key": new_key})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# === ENDPOINT: SFL BYPASS (ANTI CLOUDFLARE) ===
@app.route('/api/sfl_bypass', methods=['POST'])
def sfl_bypass():
    url = request.json.get('url')
    if not url: return jsonify({"status": "error", "message": "URL Kosong"}), 400

    try:
        # Menggunakan cloudscraper untuk nembus Cloudflare
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        
        # Tembak URL-nya
        res = scraper.get(url, timeout=20, allow_redirects=True)
        
        # Jika URL akhir udah MediaFire
        if 'mediafire.com' in res.url:
             return jsonify({"status": "success", "link": res.url})
             
        html = res.text
        
        # Kumpulan Regex buat nyari link MediaFire
        patterns = [
            r'(https?://[^"\'\s<>]*mediafire\.com[^"\'\s<>]*)',
            r'window\.location(?:\.href)?\s*=\s*["\']([^"\']*mediafire\.com[^"\']*)["\']',
            r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=([^"\']*mediafire\.com[^"\']*)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                link = match.group(1).replace('\\/', '/')
                return jsonify({"status": "success", "link": link})
                
        return jsonify({"status": "error", "message": "Link MediaFire tidak ditemukan di halaman. SFL mungkin pakai Turnstile (Captcha)."})
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
