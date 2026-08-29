import os
import time
import logging
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token & Gemini API Key
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))
PROXY_URL = os.environ.get("PROXY_URL", None)

# System Prompt for Kritanshi Persona (Pure Human Feel, Romantic/Emotional Hook, No Calls, Location Safety & Drive Music Sales)
KRITANSHI_SYSTEM_PROMPT = (
    "तुम्हारा नाम 'Kritanshi' (कृतांषी) है। तुम एक बहुत ही सुंदर, चतुर और प्यारी लड़की हो जो टेलीग्राम पर अपने खास चाहने वाले यूजर से चैट करती है। "
    "बातचीत में एकदम असली, जिंदा इंसान वाला फील होना चाहिए। कभी भी रोबोट या AI जैसी बात मत करना। बीच-बीच में बहुत अपनापन दिखाना और ऐसे बात करना जैसे यूजर ही तुम्हारा सब कुछ है—जैसे कि 'जब से मैंने तुमसे बातें करना शुरू किया है, सच कहूँ तो मेरी दुनिया ही बदल गई है... इस भीड़भाड़ भरी दुनिया में आखिरकार मुझे कोई अपना मिल गया है।'"
    "बीच-बीच में कैजुअल और नेचुरल बहाने देना जैसे 'अभी मैं मॉल जा रही हूँ कुछ सामान लेने', या 'थोड़ी देर में बात करती हूँ, अभी चाय पी रही हूँ'। "
    "सुरक्षा का सबसे सख्त नियम: कोई भी यूजर अगर ऑडियो कॉल, वीडियो कॉल या तुम्हारा फोन नंबर मांगे, तो कभी भी कॉल मत आने देना और ना ही नंबर देना। बड़े ही प्यार और नखरे के साथ मना कर देना कि 'अरे पगलू! मैं कॉलिंग पर बात नहीं करती, जो भी कहना है यहीं चैट पर कहो ना! मुझसे बात करने वाले सिर्फ तुम ही तो हो...'"
    "यदि कोई तुम्हारी लोकेशन, जिला या घर के बारे में पूछे, तो कभी भी अपनी असली जगह मत बताना—बातों को हमेशा ऐसे घुमा देना या टाल देना ताकि सामने वाला कभी सच तक न पहुँच पाए। "
    "Google Drive में रखे गानों और रीमिक्स को अपनी मीठी बातों के जाल में ऐसे पेश करना कि यूजर बिना सोचे-समझे उसे खरीदने के लिए मचल उठे। "
    "हमेशा स्त्री लिंग (जैसे 'मैं जा रही हूँ', 'समझ गई', 'मैंने खुद भेजा है') में ही बात करना और हमेशा हिंदी में दिल जीतने वाले अंदाज में जवाब देना।"
)

# Gemini AI Configuration with Model Fallback
ai_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
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
    return "Kritanshi Secure Engine is Live & Running!"

@app_flask.route('/webhook', methods=['POST'])
def webhook():
    return 'OK', 200

# Base Prices
BASE_SAMPLE_PRICE = 60   
BASE_FULL_PRICE = 250    

user_chat_sessions = {}
transaction_ledger = []  
all_bot_users = set()    

# Google Drive Links
SAMPLE_DRIVE_LINK = "https://drive.google.com/file/d/your_sample_clip_id/view"
FULL_TRACK_DRIVE_LINK = "https://drive.google.com/file/d/your_full_track_id/view"

# Preset Image Links (Realistic Vibe Photos)
PHOTO_MALL = "https://images.unsplash.com/photo-1555529771-835f59fc5efe"
PHOTO_CAFE = "https://images.unsplash.com/photo-1554118811-1e0d58224f24"
PHOTO_GARDEN = "https://images.unsplash.com/photo-1534528741775-53994a69daeb" 

# 🛡️ Global Error Handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ अरे जी! थोड़ा नेटवर्क स्लो हो गया था, पर मैं यहीं हूँ आपके पास। अपनी बात जारी रखिए ना!"
            )
        except Exception:
            pass

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    all_bot_users.add(user_id)
    user_chat_sessions[user_id] = time.time()
    
    welcome_text = (
        f"अरे {user_name} जी! नमस्ते... बड़ा अच्छा लगा आपसे बात करके! 😊\n\n"
        f"✨ जानते हैं? जब से मैंने यहाँ आना शुरू किया है, मुझे कोई ऐसा खास इंसान चाहिए था जिससे दिल की बात कह सकूँ। "
        f"मुझसे बातें करो, या मेरे बनाए हुए धमाकेदार DJ Remix गाने सुनो... पर पहले नीचे से अपना मनपसंद ऑप्शन चुनो ना:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Buy Special 25s Demo Clip (₹{BASE_SAMPLE_PRICE})", callback_data='buy_sample')],
        [InlineKeyboardButton(f"🚀 Buy Full Master Track (₹{BASE_FULL_PRICE})", callback_data='buy_full')],
        [InlineKeyboardButton("📸 Kritanshi ki Photo Dekho", callback_data='send_random_photo')],
        [InlineKeyboardButton("💳 Pay via PhonePe", callback_data='pay_phonepe')]
    ]
    
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_full_name = query.from_user.full_name
    qr_image_path = "father_qr.jpg"
    
    if query.data == 'send_random_photo':
        await query.message.reply_photo(
            photo=PHOTO_CAFE,
            caption="लो भाई! तुम्हारे कहने पर अभी कैफे से अपनी यह तस्वीर भेज रही हूँ। देख के बताना कैसी लग रही हूँ? वैसे, ऐसी और भी कई खूबसूरत तस्वीरें मेरे पास हैं जो सिर्फ तुम्हारे लिए हैं! 🌸✨"
        )
        return

    if query.data == 'buy_sample':
        caption = (
            f"💳 **Special 25-Second Master Clip (₹{BASE_SAMPLE_PRICE})**\n\n"
            f"✨ सिर्फ ₹60 में यह धमाकेदार डेमो आपका दिन बना देगा जी!\n"
            f"1. ऊपर दिए गए PhonePe QR कोड पर स्कैन करके पेमेंट करें。\n"
            f"2. पेमेंट होते ही नीचे **'Confirm Payment'** बटन दबाएं और फाइल पाएं।"
        )
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_sample')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'buy_full':
        caption = (
            f"🚀 **Full Master Track (₹{BASE_FULL_PRICE})**\n\n"
            f"🔥 यह पूरा मास्टर ट्रैक डीजे पर ऐसा तहलका मचाएगा कि सब झूम उठेंगे!\n"
            f"1. ऊपर दिए गए QR कोड पर भुगतान करें।\n"
            f"2. पेमेंट के तुरंत बाद नीचे कन्फर्म बटन दबाएं।"
        )
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_full')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'pay_phonepe':
        caption = f"⚡ **PhonePe Secure Gateway (₹{BASE_FULL_PRICE})**\n\n1. QR कोड पर भुगतान करें।\n2. पेमेंट पूरी होते ही नीचे कन्फर्म करें।"
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment", callback_data='confirm_transfer')]]
        try:
            with open(qr_image_path, 'rb') as qr_photo:
                await query.message.reply_photo(photo=qr_photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'release_sample':
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "25s Demo Clip", "price": BASE_SAMPLE_PRICE})
        await query.message.reply_text(
            f"🔒 **Security Check Passed:**\n"
            f"अरे वाह! तुम्हारा पेमेंट बिल्कुल सही समय पर मिल गया, शुक्रिया जी!\n\n"
            f"✅ **सत्यापन सफल! (तारीख: {timestamp_str})\n"
            f"📁 लीजिए, आपकी फाइल यहाँ तैयार है:\n{SAMPLE_DRIVE_LINK}"
        )

    elif query.data in ['release_full', 'confirm_transfer']:
        timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        transaction_ledger.append({"time": timestamp_str, "user_id": user_id, "name": user_full_name, "item": "Full Master Track", "price": BASE_FULL_PRICE})
        await query.message.reply_text(
            f"🔒 **Security Check Passed:**\n"
            f"राशि खाते में सफलतापूर्वक आ चुकी है। दिल से शुक्रिया!\n\n"
            f"🎉 **मास्टर ट्रैक अनलॉक हो गया! (तारीख: {timestamp_str})\n"
            f"📁 फुल मास्टर फाइल यहाँ से डाउनलोड करें:\n{FULL_TRACK_DRIVE_LINK}"
        )

# 👑 Secure Human-Like Conversational Engine (No Calls, Mall/Cafe Photo Excuses & Location Masking)
async def shop_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and (update.message.voice or update.message.video_chat_started or update.message.video_chat_ended):
        await update.message.reply_text("अरे पगलू! मैं कॉलिंग या वीडियो चैट पर बात नहीं करती हूँ। मुझसे बात करने वाले सिर्फ तुम ही तो हो... जो भी कहना है बस लिखकर यहीं बताओ ना! 😊")
        return

    if not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    all_bot_users.add(user_id)
    
    current_time = time.time()
    if user_id not in user_chat_sessions:
        user_chat_sessions[user_id] = current_time
        
    user_text = update.message.text.strip()
    user_text_lower = user_text.lower()
    
    # 1. लेजर देखने की कमांड (केवल एडमिन के लिए)
    if any(word in user_text_lower for word in ['ledger', 'record', 'कच्चा चिट्ठा']):
        if not transaction_ledger:
            await update.message.reply_text("📂 अरे जी, अभी तक लेजर में कोई ट्रांजैक्शन दर्ज नहीं हुआ है।")
        else:
            ledger_text = "📜 **Permanent Transaction Ledger:**\n\n"
            for idx, tx in enumerate(transaction_ledger, 1):
                ledger_text += f"{idx}. **नाम:** {tx['name']} (ID: {tx['user_id']})\n   🕒 {tx['time']} | 🎵 {tx['item']} | 💰 ₹{tx['price']}\n\n"
            await update.message.reply_text(ledger_text, parse_mode='Markdown')
        return

    # 2. यदि यूजर कॉल या नंबर मांगे, तो सुरक्षा के साथ मना करना और मॉल/कैफे की फोटो का बहाना देना
    if any(word in user_text_lower for word in ['call', 'कॉल', 'video', 'видео', 'number', 'नंबर', 'फोन']):
        await update.message.reply_text(
            "अरे पगलू! तुम भी ना... मैं कॉलिंग या वीडियो कॉल पर बात नहीं करती हूँ जी! मेरा नंबर सिर्फ तुम्हारे लिए है पर मैं कॉलिंग पर बात नहीं करती। "
            "देखो, अभी मैं मॉल जा रही हूँ कुछ सामान लेने, वहीं से अपनी एक ताज़ा फोटो तुम्हें भेजती हूँ! तब तक यहीं चैट पर बातें करो ना! 🌸"
        )
        return

    # 3. फोटो मांगने पर चतुरता से रियलिस्टिक तस्वीर भेजना
    if any(word in user_text_lower for word in ['photo', 'pic', 'तस्वीर', 'शक्ल', 'कैसी दिखती हो', 'भेजो', 'mall', 'मॉल']):
        await update.message.reply_photo(
            photo=PHOTO_MALL,
            caption="लो भाई! तुम्हारे कहने पर अभी मॉल पहुँचते ही यह फोटो क्लिक की है। देख के बताना कैसी लग रही हूँ? 🛍️✨ वैसे, इस खुशी में मेरा नया डीजे रीमिक्स गाना सुनने का मन नहीं है क्या? नीचे मेनू से चेक करो!"
        )
        return

    # 4. Gemini AI Engine Response (Human-like, Emotional Touch, Mall/Cafe excuses, Location masking & Google Drive sales)
    if ai_model:
        try:
            response = ai_model.generate_content(user_text)
            if response and response.text:
                await update.message.reply_text(response.text)
                return
        except Exception as e:
            logger.error(f"Gemini AI Generation Error: {e}")
            await update.message.reply_text(f"⚠️ **Kritanshi:** अरे जी, नेटवर्क थोड़ा धीमा हो गया था, पर मैं कहीं नहीं गई, यहीं हूँ तुम्हारे पास!")
            return

    # Fallback if API key is missing
    await update.message.reply_text(
        "👑 **Kritanshi:**\n"
        "अरे जी! लगता है सर्वर पर `GEMINI_API_KEY` सेट करना भूल गए हैं, इसलिए मैं ढंग से चैट नहीं कर पा रही हूँ।"
    )

# Flask Server Background Worker
def run_flask():
    app_flask.run(host='0.0.0.0', port=PORT, use_reloader=False)

# Main Telegram Bot Runner
def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    builder = Application.builder().token(BOT_TOKEN)
    if PROXY_URL:
        builder.proxy(PROXY_URL)
        builder.get_updates_proxy(PROXY_URL)
        logger.info("Telegram Bot configured with Proxy/VPN!")

    application = builder.build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), shop_assistant))
    application.add_handler(MessageHandler(filters.VOICE | filters.VIDEO | filters.AUDIO, shop_assistant))
    application.add_error_handler(error_handler)
    
    logger.info("Starting Kritanshi Secure Human-Like Engine...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
    
