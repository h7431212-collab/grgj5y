import os
import requests
import time
import random
import threading
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================
# ENVIRONMENT VARIABLES
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

def save_progress(bot_name, current_id, deleted, status="running"):
    with open(f"progress_{bot_name}.json", "w") as f:
        json.dump({
            "current_id": current_id,
            "deleted": deleted,
            "status": status,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, f)

def log(bot_name, msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{bot_name}] {msg}"
    print(line, flush=True)
    with open(f"log_{bot_name}.txt", "a") as f:
        f.write(line + "\n")

# ============================================
# TELEGRAM API - with retry logic
# ============================================

def delete_chunk(token, chat_id, message_ids):
    url = f"https://api.telegram.org/bot{token}/deleteMessages"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "message_ids": message_ids}, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e), "retry": True}

# ============================================
# MAIN BOT - DESCENDING with retry
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
    consecutive_errors = 0

    log(bot_name, f"Range: {start_id:,} → {end_id:,} ({total_ids:,} IDs)")

    i = current
    while i >= end_id:
        chunk = [x for x in range(i, i - 100, -1) if x >= end_id]
        if not chunk:
            break

        result = delete_chunk(token, GROUP_ID, chunk)
        calls += 1

        # Success
        if result and result.get("ok"):
            deleted += len(chunk)
            consecutive_errors = 0
            i -= 100  # Move to next chunk

        # Flood wait (rate limit)
        elif result and result.get("error_code") == 429:
            wait = result.get("parameters", {}).get("retry_after", 30)
            log(bot_name, f"⏳ FloodWait: {wait}s")

            # If wait is too long (>5 min), pause and retry same chunk later
            if wait > 300:
                log(bot_name, f"⚠️ Long wait ({wait}s). Pausing 5 min then retrying...")
                time.sleep(300)
                continue  # Retry same chunk
            else:
                time.sleep(wait + 5)
                continue  # Retry same chunk

        # Other error
        elif result and result.get("error"):
            consecutive_errors += 1
            log(bot_name, f"⚠️ Error: {result.get('error')} (consecutive: {consecutive_errors})")

            if consecutive_errors > 10:
                log(bot_name, "❌ Too many errors. Stopping.")
                save_progress(bot_name, i, deleted, "error")
                break

            time.sleep(5)
            continue  # Retry same chunk

        # Unknown response
        else:
            log(bot_name, f"⚠️ Unknown response: {result}")
            time.sleep(5)
            continue

        # Progress log every 100 calls
        if calls % 100 == 0:
            elapsed = time.time() - t0
            speed = deleted / elapsed if elapsed > 0 else 0
            pct = (start_id - i) / total_ids * 100
            eta = (total_ids - (start_id - i)) / speed / 3600 if speed > 0 else 0
            log(bot_name, f"📊 {i:,} ({pct:.1f}%) | Deleted: {deleted:,} | Speed: {speed:.0f}/s | ETA: {eta:.1f}h")
            save_progress(bot_name, i, deleted)

        # SAFE DELAY: 1.5s + random 0-1s = 1.5-2.5s per call
        # Same IP se 2 bots = ~0.5-0.7 calls/sec per bot = SAFE
        time.sleep(1.5 + random.uniform(0, 1.0))

    save_progress(bot_name, i, deleted, "done")
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
    print("🚀 TELEGRAM DELETE - FIXED v2")
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
