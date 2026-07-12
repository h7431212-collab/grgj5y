import os
import requests
import time
import random
import threading
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT1_TOKEN = os.environ.get("BOT1_TOKEN", "")
BOT2_TOKEN = os.environ.get("BOT2_TOKEN", "")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

if not BOT1_TOKEN or not BOT2_TOKEN or not GROUP_ID:
    print("ERROR: Set BOT1_TOKEN, BOT2_TOKEN, GROUP_ID")
    exit(1)

BOT1_START = 34652654
BOT1_END = 33226165
BOT2_START = 33226164
BOT2_END = 31799674

def log(bot_name, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{bot_name}] {msg}"
    print(line, flush=True)

def delete_single(token, chat_id, msg_id):
    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "message_id": msg_id}, timeout=30)
        return r.json()
    except:
        return {"ok": False}

def run_bot(token, start_id, end_id, bot_name):
    log(bot_name, f"Starting from ID: {start_id} → {end_id}")

    deleted = 0
    skipped = 0
    errors = 0
    t0 = time.time()
    last_log = time.time()

    # Go one by one - slow but guaranteed
    for msg_id in range(start_id, end_id - 1, -1):
        result = delete_single(token, GROUP_ID, msg_id)

        if result and result.get("ok"):
            deleted += 1
        elif result and result.get("error_code") == 400:
            skipped += 1
        elif result and result.get("error_code") == 429:
            wait = result.get("parameters", {}).get("retry_after", 30)
            log(bot_name, f"RateLimit: {wait}s")
            time.sleep(wait + 5)
            continue  # Retry same ID
        else:
            errors += 1

        # Log every 5 seconds
        now = time.time()
        if now - last_log >= 5:
            elapsed = now - t0
            speed = deleted / elapsed if elapsed > 0 else 0
            total = start_id - end_id + 1
            done = start_id - msg_id
            pct = done / total * 100
            eta = (total - done) / speed / 3600 if speed > 0 else 0
            log(bot_name, f"ID:{msg_id} ({pct:.2f}%) | Deleted:{deleted} | Skipped:{skipped} | Err:{errors} | Speed:{speed:.1f}/s | ETA:{eta:.1f}h")
            last_log = now

        # 1.5s delay
        time.sleep(1.5)

    elapsed = time.time() - t0
    log(bot_name, f"DONE! Deleted:{deleted} | Skipped:{skipped} | Time:{elapsed/3600:.1f}h")

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
    print("TELEGRAM DELETE - SINGLE ID MODE")
    print("=" * 60)
    print(f"Bot1: {BOT1_START:,} → {BOT1_END:,}")
    print(f"Bot2: {BOT2_START:,} → {BOT2_END:,}")
    print("=" * 60)

    t1 = threading.Thread(target=run_bot, args=(BOT1_TOKEN, BOT1_START, BOT1_END, "Bot1"), daemon=True)
    t2 = threading.Thread(target=run_bot, args=(BOT2_TOKEN, BOT2_START, BOT2_END, "Bot2"), daemon=True)

    t1.start()
    t2.start()
    start_server()
