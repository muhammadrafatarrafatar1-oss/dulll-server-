from flask import Flask, request, jsonify
from flask_cors import CORS
import libsql_client
import random
import string
import os

app = Flask(__name__)
CORS(app)

# === KONFIGURASI TURSO ===
# URL di bawah ini udah sesuai screenshot lo:
TURSO_URL = "libsql://dulll-dull.aws-ap-southeast-1.turso.io"

# PERHATIAN: GANTI STRING DI BAWAH INI PAKE TOKEN LENGKAP DARI TURSO LO!
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3..." 

def get_db():
    return libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

# Inisialisasi tabel otomatis saat pertama kali diakses
def init_db():
    client = get_db()
    client.execute("""
        CREATE TABLE IF NOT EXISTS valid_keys (
            key TEXT PRIMARY KEY,
            owner TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    client.close()

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Server Z×ice lanz dulll Aktif!"})

@app.route('/generate', methods=['POST'])
def generate_key():
    data = request.json
    prefix = data.get('prefix', '').upper().strip()
    if not prefix:
        return jsonify({"status": "error", "message": "Prefix kosong"}), 400

    chars = string.ascii_uppercase + string.digits
    blocks = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    final_key = f"{prefix}-{'-'.join(blocks)}"

    client = get_db()
    try:
        client.execute("INSERT INTO valid_keys (key, owner) VALUES (?, ?)", (final_key, "public"))
        return jsonify({"status": "success", "key": final_key})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        client.close()

@app.route('/validate', methods=['POST'])
def validate_key():
    data = request.json
    key_input = data.get('key', '').strip()
    
    if not key_input:
         return jsonify({"valid": False, "message": "Key kosong"}), 400

    client = get_db()
    try:
        result = client.execute("SELECT * FROM valid_keys WHERE key = ?", (key_input,))
        if result.rows:
            return jsonify({"valid": True, "owner": result.rows[0][1]})
        else:
            return jsonify({"valid": False})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500
    finally:
        client.close()

# Init DB dipanggil pas file di-load Vercel
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)