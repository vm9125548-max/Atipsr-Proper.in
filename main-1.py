# Kritanshi Secure Engine
# Python 3.11+
# IMPORTANT: Put secrets in environment variables; never hard-code them.

import os
import io
import json
import time
import hmac
import hashlib
import logging
import threading
import sqlite3

from flask import Flask, request, jsonify, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes
)
from google import genai
from google.genai import types
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PORT = int(os.getenv("PORT", "8080"))

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

BASE_FULL_PRICE = int(os.getenv("BASE_FULL_PRICE", "250"))
BASE_SAMPLE_PRICE = int(os.getenv("BASE_SAMPLE_PRICE", "60"))
MAX_TELEGRAM_FILE_MB = int(os.getenv("MAX_TELEGRAM_FILE_MB", "49"))
DB_PATH = os.getenv("DB_PATH", "kritanshi.sqlite3")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kritanshi")

SYSTEM_PROMPT = """
तुम्हारा नाम 'Kritanshi' (कृतांशी) है।
तुम friendly Hindi music assistant हो। बातचीत प्राकृतिक और विनम्र हो।
तुम्हारे मुख्य काम:
1. DJ remix/music की जानकारी देना।
2. उपलब्ध music library में से tracks सुझाना।
3. सामान्य GK/knowledge questions का स्पष्ट उत्तर देना।
4. Payment के बारे में केवल verified server status बताना।
5. OTP, bank password, API secret या private credentials कभी नहीं मांगना।
6. Payment verified हुए बिना कभी यह मत कहना कि पैसा आ गया।
7. File तभी release होती है जब server-side payment verification सफल हो।
"""

# ---------------- DATABASE ----------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        track_id TEXT NOT NULL,
        amount_paise INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'created',
        payment_id TEXT,
        created_at INTEGER NOT NULL,
        paid_at INTEGER,
        delivered_at INTEGER
    );

    CREATE TABLE IF NOT EXISTS processed_events (
        event_id TEXT PRIMARY KEY,
        processed_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        created_at INTEGER NOT NULL
    );
    """)
    conn.commit()
    conn.close()

# ---------------- GEMINI ----------------

gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("Gemini initialized.")
    except Exception:
        logger.exception("Gemini initialization failed.")

# ---------------- GOOGLE DRIVE ----------------
# The service account should have READ-ONLY access to the library folder.
# It cannot move/delete/edit files with this scope.

drive_service = None
if GOOGLE_SERVICE_ACCOUNT_JSON and DRIVE_FOLDER_ID:
    try:
        info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        drive_service = build(
            "drive", "v3",
            credentials=credentials,
            cache_discovery=False
        )
        logger.info("Google Drive read-only access initialized.")
    except Exception:
        logger.exception("Google Drive initialization failed.")

AUDIO_MIMES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/flac", "audio/ogg", "audio/mp4", "audio/aac"
}

def parse_description(description: str):
    data = {}
    for part in description.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            data[k.strip().lower()] = v.strip()
    return data

def list_library_tracks():
    if not drive_service or not DRIVE_FOLDER_ID:
        return []

    q = (
        f"'{DRIVE_FOLDER_ID}' in parents and trashed = false "
        f"and mimeType != 'application/vnd.google-apps.folder'"
    )
    response = drive_service.files().list(
        q=q,
        pageSize=1000,
        fields="files(id,name,mimeType,size,description,modifiedTime)"
    ).execute()

    tracks = []
    for f in response.get("files", []):
        mime = f.get("mimeType", "")
        name = f.get("name", "")
        if mime not in AUDIO_MIMES and not name.lower().endswith(
            (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg")
        ):
            continue

        # Optional Drive description metadata:
        # price=250; sample_price=60; category=bhojpuri,dj; quality=high; sellable=true
        meta = parse_description(f.get("description", ""))
        try:
            price = int(meta.get("price", BASE_FULL_PRICE))
        except ValueError:
            price = BASE_FULL_PRICE
        try:
            sample_price = int(meta.get("sample_price", BASE_SAMPLE_PRICE))
        except ValueError:
            sample_price = BASE_SAMPLE_PRICE

        sellable = meta.get("sellable", "true").lower() == "true"
        quality = meta.get("quality", "unknown")
        category = meta.get("category", "")
        tags = [x.strip().lower() for x in category.split(",") if x.strip()]

        tracks.append({
            "id": f["id"],
            "name": name,
            "mimeType": mime,
            "size": int(f.get("size", 0) or 0),
            "price": price,
            "sample_price": sample_price,
            "sellable": sellable,
            "quality": quality,
            "tags": tags,
            "modifiedTime": f.get("modifiedTime"),
        })
    return tracks

def download_drive_file(file_id: str):
    if not drive_service:
        raise RuntimeError("Google Drive is not configured.")

    media_request = drive_service.files().get(fileId=file_id, alt="media")
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, media_request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer

# ---------------- RAZORPAY ----------------

def razorpay_client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay credentials are not configured.")
    import razorpay
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_razorpay_order(user_id: int, track_id: str, amount_rupees: int):
    client = razorpay_client()
    receipt = f"k_{user_id}_{int(time.time())}"
    order = client.order.create({
        "amount": amount_rupees * 100,
        "currency": "INR",
        "receipt": receipt,
        "notes": {
            "telegram_user_id": str(user_id),
            "track_id": track_id
        },
    })

    conn = db()
    conn.execute(
        "INSERT INTO orders(order_id,user_id,track_id,amount_paise,status,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (
            order["id"], user_id, track_id,
            amount_rupees * 100, "created", int(time.time())
        )
    )
    conn.commit()
    conn.close()
    return order

def verify_webhook_signature(raw_body: bytes, signature: str):
    if not RAZORPAY_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

def mark_event_once(event_id: str):
    if not event_id:
        return False
    conn = db()
    try:
        conn.execute(
            "INSERT INTO processed_events(event_id, processed_at) VALUES(?,?)",
            (event_id, int(time.time()))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def process_payment_captured(payload: dict):
    entity = payload["payload"]["payment"]["entity"]
    order_id = entity.get("order_id")
    payment_id = entity.get("id")
    amount = int(entity.get("amount", 0))
    status = entity.get("status")

    if status != "captured" or not order_id or not payment_id:
        return False

    conn = db()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?",
        (order_id,)
    ).fetchone()

    if not row:
        conn.close()
        logger.warning("Unknown order: %s", order_id)
        return False

    # Never trust the amount supplied by the customer.
    if amount != row["amount_paise"]:
        conn.close()
        logger.warning("Amount mismatch for order %s", order_id)
        return False

    if row["status"] == "paid":
        conn.close()
        return True

    conn.execute(
        "UPDATE orders SET status='paid', payment_id=?, paid_at=? WHERE order_id=?",
        (payment_id, int(time.time()), order_id)
    )
    conn.commit()
    conn.close()

    # The webhook handler is synchronous, while Telegram delivery is async.
    # Start delivery only after the database has accepted the captured payment.
    threading.Thread(
        target=deliver_paid_order_sync,
        args=(order_id,),
        daemon=True
    ).start()

    return True

def deliver_paid_order_sync(order_id: str):
    """Run the async Telegram delivery worker outside Flask's event loop."""
    try:
        import asyncio
        from telegram import Bot
        asyncio.run(deliver_paid_order(Bot(BOT_TOKEN), order_id))
    except Exception:
        logger.exception("Background delivery failed for order %s", order_id)

# ---------------- FLASK ----------------

flask_app = Flask(__name__)

@flask_app.get("/")
def home():
    return "Kritanshi Secure Engine is running."

@flask_app.post("/razorpay/webhook")
def razorpay_webhook():
    raw = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature", "")
    event_id = request.headers.get("x-razorpay-event-id", "")

    if not verify_webhook_signature(raw, signature):
        return jsonify({"ok": False, "error": "invalid signature"}), 401

    # Reject very old signed payloads to reduce replay risk.
    try:
        payload_preview = request.get_json(force=True)
        created_at = int(payload_preview.get("created_at", 0) or 0)
        if created_at and abs(int(time.time()) - created_at) > 300:
            return jsonify({"ok": False, "error": "stale event"}), 400
    except Exception:
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    # Duplicate webhook protection.
    if not mark_event_once(event_id):
        return jsonify({"ok": True, "duplicate": True}), 200

    try:
        payload = request.get_json(force=True)
        event = payload.get("event", "")

        if event == "payment.captured":
            process_payment_captured(payload)
        elif event == "payment.failed":
            logger.info("Payment failed event received.")
        elif event == "order.paid":
            logger.info("order.paid received; payment.captured is used for release.")

        return jsonify({"ok": True}), 200
    except Exception:
        logger.exception("Webhook processing error")
        return jsonify({"ok": False}), 500

CHECKOUT_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Kritanshi Payment</title></head>
<body>
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script>
const options = {
  key: {{ key_id|tojson }},
  amount: {{ amount|tojson }},
  currency: "INR",
  name: "Kritanshi Music",
  description: {{ description|tojson }},
  order_id: {{ order_id|tojson }},
  handler: function () {
    document.body.innerHTML =
      "<h3>Payment submitted.</h3><p>Server-side verification is in progress. Return to Telegram.</p>";
  },
  modal: {
    ondismiss: function () {
      document.body.innerHTML = "<p>Payment window closed.</p>";
    }
  }
};
new Razorpay(options).open();
</script>
</body>
</html>
"""

@flask_app.get("/pay/<order_id>")
def payment_page(order_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id=?",
        (order_id,)
    ).fetchone()
    conn.close()

    if not row or row["status"] != "created":
        return "Invalid or already processed order.", 404

    return render_template_string(
        CHECKOUT_HTML,
        key_id=RAZORPAY_KEY_ID,
        amount=row["amount_paise"],
        description=f"Kritanshi track {row['track_id']}",
        order_id=order_id
    )

def run_flask():
    flask_app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )

# ---------------- TELEGRAM ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO users(user_id, first_name, created_at) VALUES(?,?,?)",
        (user.id, user.first_name or "", int(time.time()))
    )
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("🎵 Library देखें", callback_data="library")],
        [InlineKeyboardButton("🧠 GK / जानकारी पूछें", callback_data="info")],
    ]

    await update.message.reply_text(
        f"नमस्ते {user.first_name or 'जी'}! 😊\n\n"
        "मैं Kritanshi Music Assistant हूँ। मैं library से tracks ढूँढ सकती हूँ, "
        "music/GK जानकारी दे सकती हूँ और verified payment के बाद authorised file "
        "release कर सकती हूँ।\n\n"
        "⚠️ केवल कोई confirmation button दबाने से payment सफल नहीं माना जाएगा।",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tracks = list_library_tracks()
    sellable = [t for t in tracks if t["sellable"]]

    if not sellable:
        await update.effective_message.reply_text(
            "अभी library में कोई sellable track उपलब्ध नहीं है।"
        )
        return

    lines = ["🎵 **My Kritanshi Library**\n"]
    keyboard = []

    for t in sellable[:20]:
        lines.append(f"• {t['name']} — ₹{t['price']}")
        keyboard.append([
            InlineKeyboardButton(
                f"🎵 {t['name'][:35]} — ₹{t['price']}",
                callback_data=f"buy:{t['id']}"
            )
        ])

    await update.effective_message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, track_id: str):
    user_id = update.effective_user.id
    tracks = {t["id"]: t for t in list_library_tracks()}
    track = tracks.get(track_id)

    if not track or not track["sellable"]:
        await update.effective_message.reply_text(
            "यह track अभी उपलब्ध नहीं है।"
        )
        return

    try:
        order = create_razorpay_order(
            user_id,
            track_id,
            track["price"]
        )
    except Exception:
        logger.exception("Could not create payment order")
        await update.effective_message.reply_text(
            "Payment order अभी नहीं बन पाया। थोड़ी देर बाद प्रयास करें।"
        )
        return

    if not PUBLIC_BASE_URL:
        await update.effective_message.reply_text(
            "Payment server का public URL configure नहीं है।"
        )
        return

    pay_url = f"{PUBLIC_BASE_URL}/pay/{order['id']}"

    await update.effective_message.reply_text(
        f"💳 **{track['name']}**\n\n"
        f"राशि: ₹{track['price']}\n\n"
        "Payment खोलें। Payment के बाद server खुद verification करेगा। "
        "Verified payment से पहले file release नहीं होगी।",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Secure Payment", url=pay_url)]
        ]),
        parse_mode="Markdown"
    )

async def deliver_paid_order(bot, order_id: str):
    conn = db()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id=?",
        (order_id,)
    ).fetchone()
    conn.close()

    if not row or row["status"] != "paid" or row["delivered_at"]:
        return

    tracks = {t["id"]: t for t in list_library_tracks()}
    track = tracks.get(row["track_id"])

    if not track or not track["sellable"]:
        logger.error("Paid order points to unavailable track: %s", order_id)
        return

    size_mb = track["size"] / (1024 * 1024)
    if size_mb > MAX_TELEGRAM_FILE_MB:
        await bot.send_message(
            chat_id=row["user_id"],
            text=(
                "Payment verified है, लेकिन यह master file configured Telegram "
                "upload सीमा से बड़ी है। इसे बड़े-file delivery method से देना होगा।"
            )
        )
        return

    try:
        data = download_drive_file(track["id"])
        await bot.send_document(
            chat_id=row["user_id"],
            document=InputFile(data, filename=track["name"])
        )

        conn = db()
        conn.execute(
            "UPDATE orders SET delivered_at=? WHERE order_id=?",
            (int(time.time()), order_id)
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Delivery failed for order %s", order_id)
        await bot.send_message(
            chat_id=row["user_id"],
            text=(
                "Payment verified है, लेकिन file delivery में technical समस्या आई है। "
                "File को automatically दोबारा release नहीं किया गया है।"
            )
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "library":
        await show_library(update, context)
        return

    if query.data == "info":
        await query.message.reply_text(
            "आप music, DJ remix, GK या किसी सामान्य विषय के बारे में पूछ सकते हैं।"
        )
        return

    if query.data.startswith("buy:"):
        await create_payment(
            update,
            context,
            query.data.split(":", 1)[1]
        )

async def shop_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    lower = text.lower()

    if any(x in lower for x in [
        "call", "कॉल", "video call", "नंबर", "phone number"
    ]):
        await update.message.reply_text(
            "मैं कॉल या निजी नंबर साझा नहीं करती। यहीं चैट पर बात करें। 😊"
        )
        return

    if lower in {
        "library", "गाना", "song", "track", "remix", "रीमिक्स"
    }:
        await show_library(update, context)
        return

    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                )
            )
            answer = getattr(response, "text", None)
            if answer:
                await update.message.reply_text(answer)
                return
        except Exception:
            logger.exception("Gemini error")

    await update.message.reply_text(
        "मैं अभी सामान्य उत्तर देने में असमर्थ हूँ। कृपया सवाल दोबारा लिखें।"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram handler error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "अभी technical समस्या आई है। कृपया थोड़ी देर बाद फिर प्रयास करें।"
            )
        except Exception:
            pass

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required.")

    init_db()

    threading.Thread(
        target=run_flask,
        daemon=True
    ).start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, shop_assistant)
    )
    application.add_error_handler(error_handler)

    logger.info("Kritanshi Secure Engine starting.")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
