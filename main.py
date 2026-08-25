import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Flask server to keep Render service alive 24/7
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Mix Maker Ultra Bot is Live & Running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# Mix Maker Ultra Configuration (100% Ad-Free)
SAMPLE_CLIP_PRICE = 50   # 25-Sec Audio Preview Clip
FULL_TRACK_PRICE = 250   # Full Master Track (320kbps)

# Static Google Drive Links (Replace with your automated drive links)
SAMPLE_DRIVE_LINK = "https://drive.google.com/file/d/your_sample_clip_id/view"
FULL_TRACK_DRIVE_LINK = "https://drive.google.com/file/d/your_full_track_id/view"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    
    welcome_text = (
        f"प्रणाम {user_name} जी!\n\n"
        f"🎧 **MIX MAKER ULTRA AI BOT** 🎧\n"
        f"--------------------------------------------------\n"
        f"⚡ **Fast, Clean & 100% Ad-Free Audio Processing**\n\n"
        f"💰 **रेट लिस्ट (Direct Auto-Delivery):**\n"
        f"• 25-सेकंड टेस्ट क्लिप: ₹{SAMPLE_CLIP_PRICE}\n"
        f"• फुल 320kbps मास्टर रीमिक्स: ₹{FULL_TRACK_PRICE}\n\n"
        f"👇 नीचे दिए गए बटन से अपना विकल्प चुनें:"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"💳 ₹{SAMPLE_CLIP_PRICE} (Buy 25s Demo Clip)", callback_data='buy_sample')],
        [InlineKeyboardButton(f"🚀 ₹{FULL_TRACK_PRICE} (Buy Full Master Track)", callback_data='buy_full')],
        [InlineKeyboardButton("🔍 Live Demo Rules & Security Info", callback_data='info')]
    ]
    
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # अपना असली UPI ID यहाँ डालें
    upi_id = "yourbrand@upi" 
    
    if query.data == 'buy_sample':
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi://pay?pa={upi_id}%26pn=MixMaker%26am={SAMPLE_CLIP_PRICE}%26cu=INR"
        
        caption = (
            f"💳 **25-Second Clip Payment (₹{SAMPLE_CLIP_PRICE})**\n\n"
            f"1. ऊपर दिए गए QR कोड को स्कैन करके ₹{SAMPLE_CLIP_PRICE} का भुगतान करें।\n"
            f"2. भुगतान पूरा होते ही **'Confirm Payment'** बटन दबाएं।\n"
            f"3. तुरंत आपकी Google Drive फाइल अनलॉक हो जाएगी।"
        )
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_sample')]]
        
        await query.message.reply_photo(photo=qr_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'buy_full':
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=upi://pay?pa={upi_id}%26pn=MixMaker%26am={FULL_TRACK_PRICE}%26cu=INR"
        
        caption = (
            f"🚀 **Full Master Track Payment (₹{FULL_TRACK_PRICE})**\n\n"
            f"1. QR कोड स्कैन करके ₹{FULL_TRACK_PRICE} पे करें।\n"
            f"2. पे करने के बाद **'Confirm Payment'** बटन पर क्लिक करें।\n"
            f"3. 320kbps मास्टर फाइल का Google Drive डाउनलोड लिंक तुरंत मिल जाएगा।"
        )
        keyboard = [[InlineKeyboardButton("✅ Confirm Payment & Release File", callback_data='release_full')]]
        
        await query.message.reply_photo(photo=qr_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'release_sample':
        await query.message.reply_text(
            f"✅ **भुगतान सत्यापित हो गया है!**\n\n"
            f"📁 आपकी 25s टेस्ट फाइल यहाँ से डाउनलोड करें:\n{SAMPLE_DRIVE_LINK}"
        )

    elif query.data == 'release_full':
        await query.message.reply_text(
            f"🎉 **भुगतान सफलतापूर्वक पूरा हुआ!**\n\n"
            f"📁 आपकी 320kbps फुल मास्टर फाइल यहाँ से डाउनलोड करें:\n{FULL_TRACK_DRIVE_LINK}"
        )

    elif query.data == 'info':
        await query.message.reply_text(
            "🔒 **ODGU Security & Privacy Protocol**\n\n"
            "• यह सिस्टम 100% सुरक्षित और प्राइवेसी-फर्स्ट सिद्धांतों पर काम करता है।\n"
            "• बिना अधिकृत अनुमति या लीगल वेरीफिकेशन के कोई भी डेटा शेयर नहीं किया जाता।\n"
            "• अधिक जानकारी के लिए चैनल प्रशासक (Admin) से संपर्क करें।"
        )

def main():
    # अपना असली Telegram Bot Token यहाँ डालें (या Render के Environment Variable में सेट करें)
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Start Flask server in background thread for Render hosting stability
    t = Thread(target=run_flask)
    t.start()

    print("Mix Maker Ultra Bot (Ad-Free Engine) Running...")
    app.run_polling()

if __name__ == '__main__':
    main()
       
