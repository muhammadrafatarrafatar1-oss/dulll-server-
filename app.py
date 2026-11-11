from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random
import string
import requests
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
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    formatted_args = [_to_arg(a) for a in args] if args else []
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": formatted_args}},
            {"type": "close"}
        ]
    }
    response = requests.post(f"{TURSO_URL}/v2/pipeline", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def init_db():
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS valid_keys (
                key TEXT PRIMARY KEY,
                owner TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except Exception as e:
        print(f"Gagal inisialisasi tabel: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_key():
    data = request.json
    prefix = data.get('prefix', '').upper().strip()
    if not prefix:
        return jsonify({"status": "error", "message": "Prefix kosong"}), 400

    chars = string.ascii_uppercase + string.digits
    blocks = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    final_key = f"{prefix}-{'-'.join(blocks)}"

    try:
        execute_query("INSERT INTO valid_keys (key, owner) VALUES (?, ?)", [final_key, "public"])
        return jsonify({"status": "success", "key": final_key})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/validate', methods=['POST'])
def validate_key():
    data = request.json
    key_input = data.get('key', '').strip()
    if not key_input: return jsonify({"valid": False, "message": "Key kosong"}), 400

    try:
        result = execute_query("SELECT owner FROM valid_keys WHERE key = ?", [key_input])
        rows = result['results'][0]['response']['result']['rows']
        if rows:
            return jsonify({"valid": True, "owner": rows[0][0]['value']})
        return jsonify({"valid": False})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500

# === FITUR: WEB TO CODE (SCRAPER) ===
@app.route('/api/web_to_code', methods=['POST'])
def web_to_code():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({"status": "error", "message": "URL kosong"}), 400
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        return jsonify({"status": "success", "html": res.text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# === FITUR: SFL BYPASS (VERSI UPGRADE) ===
@app.route('/api/sfl_bypass', methods=['POST'])
def sfl_bypass():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({"status": "error", "message": "URL kosong"}), 400
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }
        
        # Ambil halaman (requests otomatis ngikutin redirect)
        res = requests.get(url, headers=headers, timeout=15)
        
        # 1. Cek kalau URL akhirnya udah MediaFire (berhasil redirect)
        if 'mediafire.com' in res.url:
             return jsonify({"status": "success", "link": res.url})
             
        html = res.text
        
        # 2. Kumpulan Regex buat nyari link MediaFire di HTML atau JS
        patterns = [
            r'(https?://[^"\'\s]*mediafire\.com/file[^"\'\s]*)',
            r'(https?://[^"\'\s]*mediafire\.com/download[^"\'\s]*)',
            r'(https?://[^"\'\s]*mediafire\.com/\?[^"\'\s]*)',
            r'window\.location\.href\s*=\s*["\']([^"\']*mediafire\.com[^"\']*)["\']',
            r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;\s*url=([^"\']*mediafire\.com[^"\']*)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                link = match.group(1)
                link = link.replace('\\/', '/') # Bersihin escape JS
                return jsonify({"status": "success", "link": link})
                
        # 3. Kalau gak nemu sama sekali
        return jsonify({"status": "error", "message": "Link MediaFire tidak ditemukan. Mungkin web pakai Cloudflare atau link SFL udah mati."})
        
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"Koneksi ditolak: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
