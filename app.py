from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import random
import string
import requests

app = Flask(__name__)
CORS(app)

# === KONFIGURASI TURSO (UDAH DIISI OTOMATIS) ===
TURSO_URL = "https://dulll-dull.aws-ap-southeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE4MjU5NTgxNDAsImlhdCI6MTc5NDQyMjE0MCwiaWQiOiIwMWExY2I2Mi0yMjAxLTdlNjAtODM5NC01NTE1ZmY0YmIzNTAiLCJraWQiOiJEcnl5QVM3MGlIcVZ4YmZvcVkwcjhzaTRhcXUwQjlsVXhYbXl5X21oc1l3IiwicmlkIjoiMTYwMzczZjktOTg1MC00YWExLWJjOGQtMDU0ZDg1MDE4ZDJmIn0.ri6aHHSahAM3N23hUetTZN_bckNNbC9jaQHElGu5-Zws_Vsc2tXU6_IMXvkNRPOf4i3_UksLmourFOA_rngTDw"

def execute_query(sql, args=None):
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": args or []}},
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
        execute_query(
            "INSERT INTO valid_keys (key, owner) VALUES (?, ?)",
            [final_key, "public"]
        )
        return jsonify({"status": "success", "key": final_key})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/validate', methods=['POST'])
def validate_key():
    data = request.json
    key_input = data.get('key', '').strip()
    
    if not key_input:
         return jsonify({"valid": False, "message": "Key kosong"}), 400

    try:
        result = execute_query(
            "SELECT owner FROM valid_keys WHERE key = ?",
            [key_input]
        )
        rows = result['results'][0]['response']['result']['rows']
        if rows:
            return jsonify({"valid": True, "owner": rows[0][0]['value']})
        else:
            return jsonify({"valid": False})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
