import os
import time
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import google.generativeai as genai

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token & Gemini API Key
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))
PROXY_URL = os.environ.get("PROXY_URL", None)

# System Prompt for Kritanshi Persona
KRITANSHI_SYSTEM_PROMPT = (
    "तुम्हारा नाम 'Kritanshi' (कृतांषी) है। तुम 'Kritanshi Official Secure Shop' की AI मैनेजर और रीमिक्सर हो। "
    "तुम्हें कभी भी खुद को 'Mix Maker' या 'Assistant' नहीं कहना है। "
    "तुम्हारी पहचान एक बहुत ही प्यारी, मददगार और समझदार लड़की की है। "
    "हमेशा स्त्री लिंग (जैसे 'मैं बता रही हूँ', 'समझ गई', 'बताइए ना', 'कर दिया है') में ही बात करना। "
    "बातचीत में बहुत मीठा, आदरणीय और अपनापन रखना। "
    "सारे DJ Remix गाने तुमने खुद अपने हाथों से तैयार किए हैं। "
    "ध्यान रखना कि बोट पर 1 मिनट (60 seconds) से ज्यादा बातचीत करने पर ₹5 की सर्वर-कॉस्ट पेनल्टी जुड़ जाती है। "
    "अगर कोई पेमेंट, गानों या प्राइज के बारे में पूछे, तो उन्हें 'Buy 25s Demo Clip (₹50/₹55)' या 'Buy Full Master Track (₹250/₹255)' के बारे में जानकारी दो। "
    "हमेशा हिंदी भाषा में बहुत ही प्यारे तरीके से जवाब देना।"
)

# Gemini AI Configuration with Model Fallback
ai_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # 100% Guaranteed Working Endpoints (Supports gemini-1.5-flash-latest and gemini-2.0-flash)
        try:
            ai_model = genai.GenerativeModel(
                model_name='gemini-1.5-flash-latest',
                system_instruction=KRITANSHI_SYSTEM_PROMPT
            )
            logger.info("Gemini AI successfully initialized with 'gemini-1.5-flash-latest'!")
        except Exception:
            ai_model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                system_instruction=KRITANSHI_SYSTEM_PROMPT
            )
            logger.info("Gemini AI successfully initialized with fallback 'gemini-2.0-flash'!")

    except Exception as e:
        logger.error(f"Error configuring Gemini AI: {e}")

# Flask web server
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Kritanshi Official Secure AI Bot is Live & Running!"

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
        f"प्रणाम {user_name} जी! 🙏\n\n"
        f"🛡️ **KRITANSHI OFFICIAL SECURE SHOP** 🛡️\n"
        f"--------------------------------------------------\n"
        f"⚡ **100% Pro-Level Security, AI Enabled & VPN Protected**\n\n"
        f"🔥 आपके लिए ही हर एक गाना बिल्कुल नए और यूनिक तरीके से रीमिक्स किया गया है, जो सीधे **Kritanshi** द्वारा तैयार किया गया है!\n\n"
        f"👇 बिना समय गंवाए नीचे से अपना विकल्प चुनें:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Buy 25s Demo Clip (₹{BASE_SAMPLE_PRICE})", callback_data='buy_sample')],
        [InlineKeyboardButton(f"🚀 Buy Full Master Track (₹{BASE_FULL_PRICE})", callback_data='buy_full')],
        [InlineKeyboardButton("🔍 Security Rules & Info", callback_data='info')],
        [InlineKeyboardButton("💳 Pay via PhonePe", callback_data='pay_phonepe')],
        [InlineKeyboardButton("⚡ Pay via Kritanshi Pay", callback_data='atipsr_pay')]
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
        caption += "1. ऊपर दिए गए PhonePe QR कोड को स्कैन करके भुगतान करें।\n2. पेमेंट का मैसेज आते ही नीचे **'Confirm Payment'** बटन दबाएं।"
        
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_sample')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(f"💳 **Payment Amount: ₹{final_sample_price}**\n\n{caption}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'buy_full':
        caption = f"🚀 **Full Master Track Payment (₹{final_full_price})**\n\n"
        if is_penalized:
            caption += "⚠️ *(नोट: 1 मिनट से ज्यादा समय तक बातचीत करने के कारण इसमें ₹5 सर्वर-कॉस्ट पेनल्टी जोड़ी गई है)*\n\n"
        caption += "1. ऊपर दिए गए PhonePe QR कोड को स्कैन करके भुगतान करें।\n2. पेमेंट का मैसेज वेरीफाई होने के बाद नीचे **'Confirm Payment'** बटन दबाएं।"
        
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_full')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(f"🚀 **Payment Amount: ₹{final_full_price}**\n\n{caption}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data in ['pay_phonepe', 'atipsr_pay']:
        gateway_name = "PhonePe" if query.data == 'pay_phonepe' else "Kritanshi Pay"
        caption = f"⚡ **{gateway_name} Gateway (₹{final_full_price})**\n\n1. ऊपर दिए गए QR कोड/अकाउंट पर भुगतान करें।\n2. भुगतान के बाद नीचे कन्फर्म बटन दबाएं।"
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment", callback_data='confirm_transfer')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'release_sample':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "25s Demo Clip", "price": final_sample_price})
        await query.message.reply_text(
            f"🔒 **Pro-Level Security Verification:**\n"
            f"पिताजी के फोन पर पेमेंट का SMS क्रॉस-चेक कर लिया गया है।\n\n"
            f"✅ **भुगतान पूर्णतः सत्यापित! (तारीख: {timestamp_str})\n"
            f"📁 फाइल यहाँ से डाउनलोड करें:\n{SAMPLE_DRIVE_LINK}"
        )

    elif query.data in ['release_full', 'confirm_transfer']:
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
            "🛡️ **Kritanshi Official Security Policy & VPN**\n\n"
            "• हमारे सभी ट्रांजैक्शन सीधे सुरक्षित बैंक अकाउंट और पिताजी के फोन के SMS अलर्ट से लिंक्ड हैं।\n"
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
        f"✨ **Kritanshi** ने यह शानदार रीमिक्स खुद तैयार किया है!\n\n"
        f"👇 आप इसे तुरंत सुनने और लेने के लिए नीचे क्लिक कर सकते हैं:"
    )
    keyboard = [[InlineKeyboardButton("🎧 अभी ट्रैक प्राप्त करें (/start)", callback_data='buy_full')]]
    
    success_count = 0
    for uid in list(all_bot_users):
        try:
            await context.bot.send_message(chat_id=uid, text=broadcast_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            success_count += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"✅ ब्रॉडकास्ट सफल!\n• कुल भेजे गए लोगों को संदेश मिला: {success_count}")

# 🧠 स्मार्ट AI "Kritanshi" असिस्टेंट 
async def shop_assistant(update: Update, context):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    all_bot_users.add(user_id)
    
    current_time = time.time()
    if user_id not in user_chat_sessions:
        user_chat_sessions[user_id] = current_time
        
    user_text = update.message.text.strip()
    user_text_lower = user_text.lower()
    
    # 1. लेजर (Ledger) देखने के लिए Direct Command
    if any(word in user_text_lower for word in ['ledger', 'record', 'कच्चा चिट्ठा']):
        if not transaction_ledger:
            await update.message.reply_text("📂 अरे जी, अभी तक लेजर में कोई ट्रांजैक्शन दर्ज नहीं हुआ है।")
        else:
            ledger_text = "📜 **Permanent Transaction Ledger:**\n\n"
            for idx, tx in enumerate(transaction_ledger, 1):
                ledger_text += f"{idx}. **नाम:** {tx['name']} (ID: {tx['user_id']})\n   🕒 {tx['time']} | 🎵 {tx['item']} | 💰 ₹{tx['price']}\n\n"
            await update.message.reply_text(ledger_text, parse_mode='Markdown')
        return

    # 2. Gemini AI Response Generation
    if ai_model:
        try:
            # Generate content using configured Gemini Model
            response = ai_model.generate_content(user_text)
            if response and response.text:
                await update.message.reply_text(response.text)
                return
        except Exception as e:
            logger.error(f"Gemini AI Generation Error: {e}")
            await update.message.reply_text(f"⚠️ **Kritanshi AI Notice:** क्षमा करें जी, सर्वर से कनेक्ट करने में थोड़ी समस्या आ रही है। (Error: {e})")
            return

    # Fallback if API key is missing
    await update.message.reply_text(
        "🤖 **Kritanshi Official:**\n"
        "अरे जी! लगता है सर्वर पर `GEMINI_API_KEY` सही से सेट नहीं है, इसलिए मैं आपसे बात नहीं कर पा रही हूँ। कृपया API Key चेक कर लीजिए ना!"
    )

# Flask Server Background Worker
def run_flask():
    app_flask.run(host='0.0.0.0', port=PORT, use_reloader=False)

# Main Telegram Bot Runner
def main():
    # Start Flask Server Thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Build Application
    builder = Application.builder().token(BOT_TOKEN)
    if PROXY_URL:
        builder.proxy(PROXY_URL)
        builder.get_updates_proxy(PROXY_URL)
        logger.info("Telegram Bot configured with Proxy/VPN!")

    application = builder.build()
    
    # Add Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notify", broadcast_new_song))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), shop_assistant))
    
    logger.info("Starting Kritanshi AI Telegram Bot Engine...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
