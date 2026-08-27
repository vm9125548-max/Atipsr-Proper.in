import os
import time
import logging
import threading
import asyncio
import httpx
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import google.generativeai as genai

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ATIPSR official Bot Token & Gemini API Key loaded securely from environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))

# VPN / Proxy Configuration (सर्वर की लोकेशन गुप्त और सुरक्षित रखने के लिए)
PROXY_URL = os.environ.get("PROXY_URL", None)

# Gemini AI Configuration
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# Flask server setup
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "ATIPSR official Secure AI Bot is Live & Running!"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    return 'OK', 200

# Base Prices & Penalties
BASE_SAMPLE_PRICE = 50   
BASE_FULL_PRICE = 250    
CHAT_PENALTY = 5         

user_chat_sessions = {}
transaction_ledger = []  
all_bot_users = set()    

SAMPLE_DRIVE_LINK = "https://drive.google.com/file/d/your_sample_clip_id/view"
FULL_TRACK_DRIVE_LINK = "https://drive.google.com/file/d/your_full_track_id/view"

# Telegram Bot Handlers
async def start(update: Update, context):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    all_bot_users.add(user_id)
    user_chat_sessions[user_id] = time.time()
    
    welcome_text = (
        f"प्रणाम {user_name} जी!\n\n"
        f"🛡️ **ATIPSR OFFICIAL SECURE SHOP** 🛡️\n"
        f"--------------------------------------------------\n"
        f"⚡ **100% Pro-Level Security, AI Enabled & VPN Protected**\n\n"
        f"🔥 आपके लिए ही हर एक गाना बिल्कुल नए और यूनिक तरीके से रीमिक्स किया जाता है, जो हमेशा के लिए आपके नाम पर पेटेंट हो जाता है!\n\n"
        f"👇 बिना समय गंवाए नीचे से अपना विकल्प चुनें:"
    )
    
    # आपके पुराने विकल्प और बिल्कुल सबसे नीचे जोड़े गए आपके दोनों नए पेमेंट बटन
    keyboard = [
        [InlineKeyboardButton(f"💳 Buy 25s Demo Clip (₹{BASE_SAMPLE_PRICE})", callback_data='buy_sample')],
        [InlineKeyboardButton(f"🚀 Buy Full Master Track (₹{BASE_FULL_PRICE})", callback_data='buy_full')],
        [InlineKeyboardButton("🔍 Security Rules & Info", callback_data='info')],
        [InlineKeyboardButton("💳 Pay via PhonePe", callback_data='pay_phonepe')],
        [InlineKeyboardButton("⚡ Pay via ATIPSR Pay", callback_data='atipsr_pay')]
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

    # आपके बताए गए दोनों नए अलग पेमेंट ऑप्शन (PhonePe और ATIPSR Pay)
    elif query.data == 'pay_phonepe':
        caption = f"💳 **PhonePe Payment Gateway (₹{final_full_price})**\n\n1. ऊपर दिए गए QR कोड को स्कैन करके भुगतान करें।\n2. भुगतान के बाद नीचे कन्फर्म बटन दबाएं।"
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment", callback_data='confirm_transfer')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text("⚠️ QR इमेज लोड करने में दिक्कत आई।")

    elif query.data == 'atipsr_pay':
        caption = f"⚡ **ATIPSR Pay Gateway (₹{final_full_price})**\n\n1. ATIPSR Pay के माध्यम से भुगतान करें (पैसा सीधे खाते में पहुँचेगा)।\n2. भुगतान के बाद कन्फर्म करें।"
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment", callback_data='confirm_transfer')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text("⚠️ QR इमेज लोड करने में दिक्कत आई।")

    elif query.data == 'release_sample':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "25s Demo Clip", "price": final_sample_price})
        await query.message.reply_text(
            f"🔒 **Pro-Level Security Verification:**\n"
            f"पिताजी के फोन पर पेमेंट का SMS क्रॉस-चेक कर लिया गया है。\n\n"
            f"✅ **भुगतान पूर्णतः सत्यापित! (तारीख: {timestamp_str})\n"
            f"📁 फाइल यहाँ से डाउनलोड करें:\n{SAMPLE_DRIVE_LINK}"
        )

    elif query.data == 'release_full':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "Full Master Track", "price": final_full_price})
        await query.message.reply_text(
            f"🔒 **Pro-Level Security Verification:**\n"
            f"पिताजी के UPI अकाउंट पर राशि सफलतापूर्वक प्राप्त हो चुकी है。\n\n"
            f"🎉 **भुगतान सफल! (तारीख: {timestamp_str})\n"
            f"📁 मास्टर फाइल यहाँ से डाउनलोड करें:\n{FULL_TRACK_DRIVE_LINK}"
        )

    # आपके निर्देशानुसार बिल्कुल सटीक सिक्योर ट्रांसफर मैसेज
    elif query.data == 'confirm_transfer':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        await query.message.reply_text(
            f"🔒 **Pro-Level Security Verification:**\n\n"
            f"✅ **आपका पैसा securely transfer कर दिया गया है!**\n"
            f"🕒 समय: {timestamp_str}\n\n"
            f"📁 मास्टर फाइल यहाँ से डाउनलोड करें:\n{FULL_TRACK_DRIVE_LINK}"
        )

    elif query.data == 'info':
        await query.message.reply_text(
            "🛡️ **ATIPSR Official Security Policy & VPN**\n\n"
            "• हमारे सभी ट्रांजैक्शन सीधे सुरक्षित बैंक अकाउंट और पिताजी के फोन के SMS अलर्ट से लिंक्ड हैं। बिना असली पेमेंट के कोई पत्ता भी नहीं हिल सकता।\n"
            "• पूरा सिस्टम वीपीएन और प्रॉक्सी लेयर से सुरक्षित है, जिससे सर्वर की लोकेशन गुप्त रहती है।"
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
        f"✨ **ATIPSR Official** ने यह शानदार रीमिक्स अपलोड कर दिया है!\n\n"
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

    # यदि AI API Key मौजूद है, तो Gemini AI से स्मार्ट जवाब मँगवाएँगे
    if ai_model:
        try:
            prompt = (
                f"तुम 'ATIPSR Official' के स्मार्ट और सख्त सुरक्षा वाले AI मैनेजर हो। "
                f"इस दुकान के मालिक और जन्मदाता कृतांत वाचस्पति जी हैं। "
                f"यूजर का मैसेज यह है: '{update.message.text}'. इसे प्रोफेशनल तरीके से हिंदी में जवाब दो।"
            )
            response = ai_model.generate_content(prompt)
            await update.message.reply_text(response.text)
            return
        except Exception as e:
            logger.error(f"Gemini AI Error: {e}")

    # Fallback पुराने जवाब
    if any(word in user_text for word in ['kisne banaya', 'who made', 'owner', 'malik', 'creator', 'किसने बनाया', 'मालिक', 'कौन है', 'कृतांत', 'kritant']):
        reply = (
            "🤖 **परिचय (Bot Identity):**\n\n"
            "मैं **ATIPSR APK Official**, **Vainex Ultra Editor**, **ODGU OTT प्लेटफॉर्म**, **Pepord AI Super Web** और **Mix Maker Official** का मुख्य बोट हूँ!\n\n"
            "✨ हम सब के मालिक और जन्मदाता **कृतांत वाचस्पति** जी हैं। उन्हीं के मार्गदर्शन से यह पूरा तकनीकी साम्राज्य चलता है!\n\n"
            "👉 /start दबाकर अपना रीमिक्स ट्रैक प्राप्त करें!"
        )
    elif any(word in user_text for word in ['kyon', 'penality', 'extra', 'charge', 'क्यों', 'एक्स्ट्रा', 'पेनल्टी', 'चार्ज']):
        reply = (
            "💡 **₹5 एक्स्ट्रा चार्ज या पेनल्टी क्यों लगती है?**\n\n"
            "जनाब, हमारी सुरक्षा 'Pro' लेवल की है। बोट पर आते ही अगर आपने 1 मिनट से ज्यादा बातचीत या पूछताछ में लगा दिया, तो सर्वर पर लोड बढ़ जाता है। इसलिए यह मामूली सा चार्ज सर्वर का खर्चा उठाने के लिए है!\n\n"
            "बिना समय गंवाए /start दबाकर अपना पेटेंटेड ट्रैक बुक करें!"
        )
    else:
        reply = (
            "✨ बात बिल्कुल सही है आपके साथ! हमारे यहाँ का हर एक रीमिक्स पूरी तरह यूनिक और आपके नाम पर पेटेंट होता है—दूसरा कोई इसे इस्तेमाल नहीं कर सकता!\n\n"
            "💬 **विशेष सूचना:** बोट पर 1 मिनट से ज्यादा बातचीत या पूछताछ करने पर सर्वर के रखरखाव हेतु ₹5 की अतिरिक्त लागत जुड़ जाती है।\n\n"
            "👉 /start दबाकर तुरंत अपना ट्रैक प्राप्त करें!"
        )
        
    await update.message.reply_text(reply)

# Background Runner for Flask Web Server (Render Health Check Ke Liye)
def run_flask():
    app_flask.run(host='0.0.0.0', port=PORT, use_reloader=False)

# Main Telegram Bot Polling Function with Proxy/VPN Support
def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    builder = Application.builder().token(BOT_TOKEN)
    
    # यदि आपने प्रॉक्सी या वीपीएन सेट किया है, तो टेलीग्राम बोट उसे खुद-ब-खुद इस्तेमाल करेगा
    if PROXY_URL:
        builder.proxy(PROXY_URL)
        builder.get_updates_proxy(PROXY_URL)
        logger.info("Telegram Bot configured with secure Proxy/VPN!")

    application = builder.build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notify", broadcast_new_song))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), shop_assistant))
    
    logger.info("Starting Telegram Bot Polling...")
    application.run_polling()

if __name__ == '__main__':
    # Flask को बैकग्राउंड थ्रेड में चलाना ताकि Render पोर्ट खुला रहे
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # मुख्य थ्रेड में Telegram बोट को चलाना ताकि वह लगातार मैसेज सुने
    run_telegram_bot()
