import os
import requests
import time
import random
import threading
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================
# CONFIGURATION - Set in Render Dashboard Environment
# ============================================
BOT1_TOKEN = os.environ.get("BOT1_TOKEN", "")
BOT2_TOKEN = os.environ.get("BOT2_TOKEN", "")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

if not BOT1_TOKEN or not BOT2_TOKEN or not GROUP_ID:
    print("❌ ERROR: Missing environment variables!")
    print("Set BOT1_TOKEN, BOT2_TOKEN, and GROUP_ID in Render dashboard.")
    exit(1)

# ============================================
# RANGES - 34.6 Million Total
# Render handles first half: 1 to 17,300,000
# ============================================
BOT1_START = 1
BOT1_END = 8650000

BOT2_START = 8650001
BOT2_END = 17300000

# ============================================
# PROGRESS TRACKING
# ============================================

def load_progress(bot_name):
    filename = f"progress_{bot_name}.json"
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                return data.get("last_id", 0)
        except:
            pass
    return 0

def save_progress(bot_name, last_id, deleted_count):
    filename = f"progress_{bot_name}.json"
    data = {
        "last_id": last_id,
        "deleted_count": deleted_count,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(filename, "w") as f:
        json.dump(data, f)

def log(bot_name, message):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{bot_name}] {message}"
    print(line, flush=True)
    with open(f"log_{bot_name}.txt", "a") as f:
        f.write(line + "\n")

# ============================================
# TELEGRAM API
# ============================================

def delete_chunk(token, chat_id, message_ids):
    url = f"https://api.telegram.org/bot{token}/deleteMessages"
    payload = {"chat_id": chat_id, "message_ids": message_ids}
    try:
        r = requests.post(url, json=payload, timeout=30)
        return r.json()
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================================
# MAIN BOT WORKER
# ============================================

def run_bot(token, start_id, end_id, bot_name):
    resume_id = load_progress(bot_name)
    current = resume_id if (resume_id > 0 and resume_id >= start_id) else start_id

    total = end_id - start_id + 1
    deleted = 0
    calls = 0
    t0 = time.time()

    log(bot_name, f"Range: {start_id:,} to {end_id:,} ({total:,} messages)")
    if current != start_id:
        log(bot_name, f"Resuming from ID: {current}")

    for i in range(current, end_id + 1, 100):
        chunk = list(range(i, min(i + 100, end_id + 1)))
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
            log(bot_name, f"⚠️ Error: {result.get('error')}")

        if calls % 50 == 0:
            save_progress(bot_name, i, deleted)

        if calls % 1000 == 0:
            elapsed = time.time() - t0
            speed = deleted / elapsed if elapsed > 0 else 0
            pct = (i - start_id) / total * 100
            eta = (total - (i - start_id)) / speed / 3600 if speed > 0 else 0
            log(bot_name, f"📊 {i:,}/{end_id:,} ({pct:.1f}%) | Deleted: {deleted:,} | Speed: {speed:.0f}/s | ETA: {eta:.1f}h")

        time.sleep(1 + random.uniform(0.5, 1.5))

    save_progress(bot_name, end_id, deleted)
    elapsed = time.time() - t0
    log(bot_name, f"✅ DONE! Deleted {deleted:,} messages in {elapsed/3600:.1f} hours")

# ============================================
# DUMMY HTTP SERVER - Keeps Render Web Service alive
# ============================================

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Bot is running\n")

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs to keep console clean

def start_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    print(f"🌐 Dummy server running on port {port}")
    server.serve_forever()

# ============================================
# START EVERYTHING
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TELEGRAM BULK DELETE - RENDER")
    print("=" * 60)
    print(f"Group: {GROUP_ID}")
    print(f"Bot1: {BOT1_START:,} → {BOT1_END:,}")
    print(f"Bot2: {BOT2_START:,} → {BOT2_END:,}")
    print("=" * 60)

    # Start delete bots in background threads
    t1 = threading.Thread(target=run_bot, args=(BOT1_TOKEN, BOT1_START, BOT1_END, "Bot1"), daemon=True)
    t2 = threading.Thread(target=run_bot, args=(BOT2_TOKEN, BOT2_START, BOT2_END, "Bot2"), daemon=True)
    t1.start()
    t2.start()

    # Start dummy HTTP server in main thread (keeps Render happy)
    start_server()
