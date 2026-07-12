import os
import requests
import time
import threading
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================
# ENVIRONMENT VARIABLES - Set in Render Dashboard
# ============================================
BOT1_TOKEN = os.environ.get("BOT1_TOKEN", "")
BOT2_TOKEN = os.environ.get("BOT2_TOKEN", "")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

if not BOT1_TOKEN or not BOT2_TOKEN or not GROUP_ID:
    print("❌ ERROR: Set BOT1_TOKEN, BOT2_TOKEN, GROUP_ID in Render Environment")
    exit(1)

# ============================================
# EXACT RANGE: 31,799,674 → 34,652,654
# ============================================
# Bot 1: 34,652,654 → 33,226,165 (1,426,490 messages)
# Bot 2: 33,226,164 → 31,799,674 (1,426,491 messages)
BOT1_START = 34652654
BOT1_END = 33226165

BOT2_START = 33226164
BOT2_END = 31799674

# ============================================
# PROGRESS SAVE/LOAD
# ============================================

def load_progress(bot_name):
    file = f"progress_{bot_name}.json"
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f).get("current_id", 0)
        except:
            pass
    return 0

def save_progress(bot_name, current_id, deleted):
    with open(f"progress_{bot_name}.json", "w") as f:
        json.dump({
            "current_id": current_id,
            "deleted": deleted,
            "time": datetime.now().strftime("%H:%M:%S")
        }, f)

def log(bot_name, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{bot_name}] {msg}"
    print(line, flush=True)
    with open(f"log_{bot_name}.txt", "a") as f:
        f.write(line + "\n")

# ============================================
# TELEGRAM API
# ============================================

def delete_chunk(token, chat_id, message_ids):
    url = f"https://api.telegram.org/bot{token}/deleteMessages"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "message_ids": message_ids}, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================
# MAIN BOT - DESCENDING
# ============================================

def run_bot(token, start_id, end_id, bot_name):
    resume = load_progress(bot_name)
    if resume > 0 and resume <= start_id and resume >= end_id:
        current = resume
        log(bot_name, f"Resuming from ID: {current}")
    else:
        current = start_id
        log(bot_name, f"Starting from ID: {current}")

    total_ids = start_id - end_id + 1
    deleted = 0
    calls = 0
    t0 = time.time()

    log(bot_name, f"Range: {start_id:,} → {end_id:,} ({total_ids:,} IDs)")

    for i in range(current, end_id - 1, -100):
        chunk = [x for x in range(i, i - 100, -1) if x >= end_id]
        if not chunk:
            break

        result = delete_chunk(token, GROUP_ID, chunk)
        calls += 1

        if result and result.get("ok"):
            deleted += len(chunk)
        elif result and result.get("error_code") == 429:
            wait = result.get("parameters", {}).get("retry_after", 30)
            log(bot_name, f"⏳ FloodWait: {wait}s")
            time.sleep(wait + 5)
            continue
        elif result and result.get("error"):
            log(bot_name, f"⚠️ {result.get('error')}")

        if calls % 1000 == 0:
            elapsed = time.time() - t0
            speed = deleted / elapsed if elapsed > 0 else 0
            pct = (start_id - i) / total_ids * 100
            eta = (total_ids - (start_id - i)) / speed / 3600 if speed > 0 else 0
            log(bot_name, f"📊 {i:,} ({pct:.1f}%) | Deleted: {deleted:,} | Speed: {speed:.0f}/s | ETA: {eta:.1f}h")
            save_progress(bot_name, i, deleted)

        time.sleep(0.8)

    save_progress(bot_name, end_id, deleted)
    elapsed = time.time() - t0
    log(bot_name, f"✅ DONE! Deleted {deleted:,} in {elapsed/3600:.1f}h")

# ============================================
# DUMMY HTTP SERVER
# ============================================

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Deleting\n")
    def log_message(self, *args): pass

def start_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    print(f"🌐 Server on port {port}")
    server.serve_forever()

# ============================================
# START
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TELEGRAM DELETE - 2 BOTS")
    print("=" * 60)
    print(f"Group: {GROUP_ID}")
    print(f"Bot1: {BOT1_START:,} → {BOT1_END:,}")
    print(f"Bot2: {BOT2_START:,} → {BOT2_END:,}")
    print("=" * 60)

    t1 = threading.Thread(target=run_bot, args=(BOT1_TOKEN, BOT1_START, BOT1_END, "Bot1"), daemon=True)
    t2 = threading.Thread(target=run_bot, args=(BOT2_TOKEN, BOT2_START, BOT2_END, "Bot2"), daemon=True)

    t1.start()
    t2.start()
    start_server()
