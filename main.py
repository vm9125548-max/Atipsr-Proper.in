import os
import time
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "") # Render का यूआरएल + /webhook

# Flask server
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Mix Maker & Vainex Ultra Editor Pro Bot (Webhook Mode) is Live & Running!"

# Base Prices & Penalties
BASE_SAMPLE_PRICE = 50   
BASE_FULL_PRICE = 250    
CHAT_PENALTY = 5         

user_chat_sessions = {}
transaction_ledger = []  
all_bot_users = set()    

SAMPLE_DRIVE_LINK = "https://drive.google.com/file/d/your_sample_clip_id/view"
FULL_TRACK_DRIVE_LINK = "https://drive.google.com/file/d/your_full_track_id/view"

# Telegram Application global setup
application = None

async def setup_bot():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notify", broadcast_new_song))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), shop_assistant))
    
    await application.initialize()
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to: {WEBHOOK_URL}")

async def start(update: Update, context):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    all_bot_users.add(user_id)
    user_chat_sessions[user_id] = time.time()
    
    welcome_text = (
        f"प्रणाम {user_name} जी!\n\n"
        f"🛡️ **MIX MAKER IRON-CLAD PRO SECURE SHOP** 🛡️\n"
        f"*(By कृतांत वाचस्पति)*\n"
        f"--------------------------------------------------\n"
        f"⚡ **100% Pro-Level Security & Instant Verification**\n\n"
        f"🔥 आपके लिए ही हर एक गाना बिल्कुल नए और यूनिक तरीके से रीमिक्स किया जाता है, जो हमेशा के लिए आपके नाम पर पेटेंट हो जाता है!\n\n"
        f"👇 बिना समय गंवाए नीचे से अपना विकल्प चुनें:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Buy 25s Demo Clip (₹{BASE_SAMPLE_PRICE})", callback_data='buy_sample')],
        [InlineKeyboardButton(f"🚀 Buy Full Master Track (₹{BASE_FULL_PRICE})", callback_data='buy_full')],
        [InlineKeyboardButton("🔍 Security Rules & Info", callback_data='info')]
    ]
    
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_full_name = query.from_user.full_name
    current_time = time.time()
    
    start_time = user_chat_sessions.get(user_id, current_time)
    time_spent_seconds = current_time - start_time
    
    is_penalized = time_spent_seconds >= 60
    final_sample_price = BASE_SAMPLE_PRICE + CHAT_PENALTY if is_penalized else BASE_SAMPLE_PRICE
    final_full_price = BASE_FULL_PRICE + CHAT_PENALTY if is_penalized else BASE_FULL_PRICE
    
    qr_image_path = "father_qr.jpg"
    
    if query.data == 'buy_sample':
        caption = f"💳 **25-Second Clip Payment (₹{final_sample_price})**\n\n"
        if is_penalized:
            caption += "⚠️ *(नोट: 1 मिनट से ज्यादा बातचीत करने के कारण इसमें ₹5 सर्वर-कॉस्ट पेनल्टी जोड़ी गई है)*\n\n"
        caption += "1. ऊपर दिए गए PhonePe QR कोड को स्कैन करके भुगतान करें。\n2. पेमेंट का मैसेज आते ही नीचे **'Confirm Payment'** बटन दबाएं।"
        
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_sample')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            await query.message.reply_text(f"⚠️ QR इमेज लोड करने में दिक्कत आई। (Error: {e})")

    elif query.data == 'buy_full':
        caption = f"🚀 **Full Master Track Payment (₹{final_full_price})**\n\n"
        if is_penalized:
            caption += "⚠️ *(नोट: 1 मिनट से ज्यादा समय तक बातचीत करने के कारण इसमें ₹5 सर्वर-कॉस्ट पेनल्टी जोड़ी गई है)*\n\n"
        caption += "1. ऊपर दिए गए PhonePe QR कोड को स्कैन करके भुगतान करें。\n2. पेमेंट का मैसेज वेरीफाई होने के बाद नीचे **'Confirm Payment'** बटन दबाएं।"
        
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_full')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            await query.message.reply_text(f"⚠️ QR इमेज लोड करने में दिक्कत आई। (Error: {e})")

    elif query.data == 'release_sample':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "25s Demo Clip", "price": final_sample_price})
        await query.message.reply_text(
            f"🔒 **Pro-Level Security Verification:**\n"
            f"पिताजी के फोन पर पेमेंट का SMS क्रॉस-चेक कर लिया गया है।\n\n"
            f"✅ **भुगतान पूर्णतः सत्यापित! (तारीख: {timestamp_str})\n"
            f"📁 फाइल यहाँ से डाउनलोड करें:\n{SAMPLE_DRIVE_LINK}"
        )

    elif query.data == 'release_full':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "Full Master Track", "price": final_full_price})
        await query.message.reply_text(
            f"🔒 **Pro-Level Security Verification:**\n"
            f"पिताजी के UPI अकाउंट पर राशि सफलतापूर्वक प्राप्त हो चुकी है।\n\n"
            f"🎉 **भुगतान सफल! (तारीख: {timestamp_str})\n"
            f"📁 मास्टर फाइल यहाँ से डाउनलोड करें:\n{FULL_TRACK_DRIVE_LINK}"
        )

    elif query.data == 'info':
        await query.message.reply_text(
            "🛡️ **कृतांत वाचस्पति Iron-Clad Pro Security Policy**\n\n"
            "• हमारे सभी ट्रांजैक्शन सीधे सुरक्षित बैंक अकाउंट और पिताजी के फोन के SMS अलर्ट से लिंक्ड हैं। बिना असली पेमेंट के कोई पत्ता भी नहीं हिल सकता।\n"
            "• 1 मिनट से ज्यादा बातचीत या पूछताछ करने पर ₹5 सर्वर-कॉस्ट पेनल्टी स्वतः जुड़ जाती है।\n"
            "• ट्रैक हमेशा के लिए आपके नाम पर पेटेंट रहेगा।"
        )

async def broadcast_new_song(update: Update, context):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ कृपया गाने का नाम साथ में लिखें। उदाहरण: `/notify देवरा निहारे छतिया Pawan Singh`", parse_mode='Markdown')
        return
        
    song_name = " ".join(args)
    broadcast_message = (
        f"📢 **नया गाना रीमिक्स अपलोड हो चुका है!**\n\n"
        f"🎵 **सॉन्ग:** {song_name} (DJ Remix Version)\n"
        f"✨ **कृतांत वाचस्पति** जी ने यह शानदार रीमिक्स अपलोड कर दिया है!\n\n"
        f"👇 आप इसे तुरंत सुनने और लेने के लिए नीचे क्लिक कर सकते हैं:"
    )
    keyboard = [[InlineKeyboardButton("🎧 अभी ट्रैक प्राप्त करें (/start)", callback_data='buy_full')]]
    
    success_count = 0
    for uid in all_bot_users:
        try:
            await context.bot.send_message(chat_id=uid, text=broadcast_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            success_count += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"✅ ब्रॉडकास्ट सफल!\n• कुल भेजे गए लोगों को संदेश मिला: {success_count}")

async def shop_assistant(update: Update, context):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    all_bot_users.add(user_id)
    
    current_time = time.time()
    if user_id not in user_chat_sessions:
        user_chat_sessions[user_id] = current_time
        
    user_text = update.message.text.lower()
    
    if 'ledger' in user_text or 'record' in user_text or 'कच्चा चिट्ठा' in user_text:
        if not transaction_ledger:
            await update.message.reply_text("📂 अभी तक लेजर में कोई ट्रांजैक्शन दर्ज नहीं हुआ है।")
        else:
            ledger_text = "📜 **Permanent Transaction Ledger:**\n\n"
            for idx, tx in enumerate(transaction_ledger, 1):
                ledger_text += f"{idx}. **नाम:** {tx['name']} (ID: {tx['user_id']})\n   🕒 {tx['time']} | 🎵 {tx['item']} | 💰 ₹{tx['price']}\n\n"
            await update.message.reply_text(ledger_text, parse_mode='Markdown')
        return

    if any(word in user_text for word in ['kyon', 'penality', 'extra', 'charge', 'क्यों', 'एक्स्ट्रा', 'पेनल्टी', 'चार्ज']):
        reply = (
            "💡 **₹5 एक्स्ट्रा चार्ज या पेनल्टी क्यों लगती है?**\n\n"
            "जनाब, हमारी सुरक्षा 'Iron-Clad Pro' लेवल की है। बोट पर आते ही अगर आपने 1 मिनट से ज्यादा बातचीत या पूछताछ में लगा दिया, तो हमारे 24/7 चलने वाले सर्वर पर लोड बढ़ जाता है। इसलिए यह मामूली सा चार्ज सर्वर का खर्चा उठाने के लिए है!\n\n"
            "बिना समय गंवाए /start दबाकर अपना पेटेंटेड ट्रैक बुक करें!"
        )
    else:
        reply = (
            "✨ बात बिल्कुल सही है आपके साथ! हमारे यहाँ का हर एक रीमिक्स पूरी तरह यूनिक और आपके नाम पर पेटेंट होता है—दूसरा कोई इसे इस्तेमाल नहीं कर सकता, वरना कृतांत वाचस्पति खुद कॉपीराइट मार देंगे!\n\n"
            "💬 **विशेष सूचना:** बोट पर 1 मिनट से ज्यादा बातचीत या पूछताछ करने पर सर्वर के रखरखाव हेतु ₹5 की अतिरिक्त लागत जुड़ जाती है।\n\n"
            "👉 /start दबाकर तुरंत अपना ट्रैक प्राप्त करें!"
        )
        
    await update.message.reply_text(reply)

# Flask Webhook Route
@app_flask.route('/webhook', methods=['POST'])
def webhook():
    if application:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string, application.bot)
        application.update_queue.put_nowait(update)
    return 'OK'

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_bot())
    
    print(f"Flask Webhook server running on port {PORT}...")
    app_flask.run(host='0.0.0.0', port=PORT)
    
# Flask Webhook Route
@app_flask.route('/webhook', methods=['POST'])
def webhook():
    if application:
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string, application.bot)
        application.update_queue.put_nowait(update)
    return 'OK'

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_bot())
    
    print(f"Flask Webhook server running on port {PORT}...")
    app_flask.run(host='0.0.0.0', port=PORT)
    
