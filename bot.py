import os
import requests
import time
import random
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT1_TOKEN = os.environ.get("BOT1_TOKEN", "")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

if not BOT1_TOKEN or not GROUP_ID:
    print("ERROR: Set BOT1_TOKEN, GROUP_ID")
    exit(1)

BOT_START = 34650554
BOT_END = 31799674

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)

def delete_chunk(token, chat_id, message_ids):
    url = f"https://api.telegram.org/bot{token}/deleteMessages"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "message_ids": message_ids}, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def delete_single(token, chat_id, msg_id):
    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "message_id": msg_id}, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_bot(token, start_id, end_id):
    log(f"Start: {start_id} → {end_id}")

    deleted = 0
    skipped = 0
    t0 = time.time()
    last_log = time.time()

    i = start_id
    while i >= end_id:
        chunk = list(range(i, max(i - 100, end_id - 1), -1))
        
        # Try bulk delete first
        result = delete_chunk(token, GROUP_ID, chunk)
        
        # Bulk success
        if result and result.get("ok"):
            deleted += len(chunk)
            i -= 100
        
        # Bulk failed - try single IDs
        else:
            single_deleted = 0
            for msg_id in chunk:
                single_result = delete_single(token, GROUP_ID, msg_id)
                
                if single_result and single_result.get("ok"):
                    deleted += 1
                    single_deleted += 1
                else:
                    skipped += 1
            
            # Move forward regardless
            i -= 100
        
        # Log every 5 seconds
        now = time.time()
        if now - last_log >= 5:
            elapsed = now - t0
            speed = deleted / elapsed if elapsed > 0 else 0
            total = start_id - end_id + 1
            done = start_id - i
            pct = done / total * 100
            eta = (total - done) / speed / 3600 if speed > 0 else 0
            log(f"ID:{i} ({pct:.1f}%) | Del:{deleted} | Skip:{skipped} | Spd:{speed:.0f}/s | ETA:{eta:.1f}h")
            last_log = now
        
        # 0.5s delay
        time.sleep(0.5)

    elapsed = time.time() - t0
    log(f"DONE! Del:{deleted} | Skip:{skipped} | Time:{elapsed/3600:.1f}h")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK\n")
    def log_message(self, *args): pass

def start_server():
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), DummyHandler).serve_forever()

if __name__ == "__main__":
    print("=" * 60)
    print("TELEGRAM DELETE - BULK + SINGLE FALLBACK")
    print("=" * 60)
    print(f"Range: {BOT_START} → {BOT_END}")
    print("=" * 60)

    t = threading.Thread(target=run_bot, args=(BOT1_TOKEN, BOT_START, BOT_END), daemon=True)
    t.start()
    start_server()
