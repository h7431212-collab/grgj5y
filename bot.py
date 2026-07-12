import os
import requests
import time
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT1_TOKEN = os.environ.get("BOT1_TOKEN", "")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

if not BOT1_TOKEN or not GROUP_ID:
    print("ERROR: Set BOT1_TOKEN, GROUP_ID")
    exit(1)

# Sirf 1 bot, pura range
BOT_START = 34652705
BOT_END = 31799674

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)

def delete_chunk(token, chat_id, message_ids):
    url = f"https://api.telegram.org/bot{token}/deleteMessages"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "message_ids": message_ids}, timeout=10)
        return r.json()
    except:
        return None

def run_bot(token, start_id, end_id):
    log(f"Start: {start_id} → {end_id}")

    deleted = 0
    skipped = 0
    t0 = time.time()
    last_log = time.time()

    for i in range(start_id, end_id - 1, -100):
        chunk = list(range(i, max(i - 100, end_id - 1), -1))
        
        result = delete_chunk(token, GROUP_ID, chunk)
        
        # SUCCESS
        if result and result.get("ok"):
            deleted += len(chunk)
        
        # 400 = not found, skip
        elif result and result.get("error_code") == 400:
            skipped += len(chunk)
        
        # 429 = rate limit, wait & retry
        elif result and result.get("error_code") == 429:
            wait = result.get("parameters", {}).get("retry_after", 30)
            log(f"RateLimit: {wait}s")
            time.sleep(wait + 5)
            continue  # Retry same chunk
        
        # Other error, skip
        else:
            skipped += len(chunk)
        
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
        
        # 1.0s delay
        time.sleep(1.0)

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
    print("TELEGRAM DELETE - 1 BOT ONLY")
    print("=" * 60)
    print(f"Range: {BOT_START} → {BOT_END}")
    print("=" * 60)

    t = threading.Thread(target=run_bot, args=(BOT1_TOKEN, BOT_START, BOT_END), daemon=True)
    t.start()
    start_server()
