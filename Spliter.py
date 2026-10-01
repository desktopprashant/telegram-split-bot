import io
import os
import re
import time
import html
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# 24/7 Web Server (Render/Cloud free hosting keep-alive ke liye)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Telegram Bot is running 24/7 online!")

    def log_message(self, format, *args):
        pass  # Logs console me clean rakhne ke liye

def start_keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Background me web server start karna
threading.Thread(target=start_keep_alive, daemon=True).start()

# Bot Token aur Initialization
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8924379773:AAE4v0CjMestz2FFCbo1Uqx0xJrHsHWpxAo")
bot = telebot.TeleBot(BOT_TOKEN)

# User session storage (In-memory)
# Format: {chat_id: {"mode": "extract", "password": "Ramu0001", "awaiting": None}}
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            "mode": "extract",       # Default mode: 'extract' ya 'password'
            "password": "Ramu0001",  # Default password
            "awaiting": None         # 'new_password' jab user se password input chahiye
        }
    return user_sessions[chat_id]

# Main Reply Keyboard Markup
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_extract = types.KeyboardButton("✂️ Extract Numbers (Mono)")
    btn_pass = types.KeyboardButton("🔐 Number:Password + TXT")
    btn_set_pass = types.KeyboardButton("🔑 Set Password")
    btn_help = types.KeyboardButton("ℹ️ Help / Guide")
    markup.add(btn_extract, btn_pass)
    markup.add(btn_set_pass, btn_help)
    return markup

# Function to extract phone numbers from mixed text
def extract_phone_numbers(text):
    extracted = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # 1. Indian numbers 10-digits (starting with 6-9), optionally with +91 or 91
        m1 = re.findall(r'(?:(?:\+|0{0,2})91[\s-]?)?([6-9]\d{9})(?!\d)', line)
        if m1:
            extracted.extend(m1)
            continue
            
        # 2. Any 10-digit number sequence
        m2 = re.findall(r'\b\d{10}\b', line)
        if m2:
            extracted.extend(m2)
            continue

        # 3. Any 8 to 12 digits chunk (e.g. 894833840amanp)
        m3 = re.findall(r'\d{8,12}', line)
        if m3:
            extracted.extend(m3)
            continue
            
    return extracted

# 1. /start command handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    session = get_session(message.chat.id)
    curr_pass = session["password"]
    curr_mode = "✂️ Extract Numbers" if session["mode"] == "extract" else "🔐 Number:Password + TXT"
    
    welcome_text = (
        "👋 <b>Welcome to Phone Splitter & Password Tool Bot!</b>\n\n"
        "Ye bot 2 main kaam karta hai:\n"
        "1️⃣ <b>✂️ Extract Numbers (Mono):</b> Kisi bhi text me se phone numbers alag karke tap-to-copy mono format me dega.\n"
        "2️⃣ <b>🔐 Number:Password + TXT:</b> Sabhi numbers ke aage custom password lagakar (e.g. <code>9899882946:Ramu0001</code>) 📄 <b>.txt file</b> create karega.\n\n"
        f"⚙️ <b>Current Status:</b>\n"
        f"• Active Mode: <b>{curr_mode}</b>\n"
        f"• Current Password: <code>{html.escape(curr_pass)}</code>\n\n"
        "Niche diye gaye buttons se apna mode chunein ya text bhejein:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())

# 2. /help command handler
@bot.message_handler(commands=['help'])
def send_help(message):
    session = get_session(message.chat.id)
    help_text = (
        "📖 <b>Bot Guide & Commands:</b>\n\n"
        "🔹 <b>Button 1: ✂️ Extract Numbers (Mono)</b>\n"
        "Koi bhi text bhejiye (e.g. <code>8053483439 amanku pen</code>).\n"
        "Bot usme se number extract karke <code>8053483439</code> (tap to copy) format me send karega.\n\n"
        "🔹 <b>Button 2: 🔐 Number:Password + TXT</b>\n"
        "Jab aap numbers bhejenge, bot unhe is format me banayega:\n"
        "<pre>9899882946:{pwd}\n9899882947:{pwd}</pre>\n"
        "aur uski ready <b>.txt file</b> bhej dega.\n\n"
        "🔹 <b>Button 3: 🔑 Set Password</b>\n"
        "Apna password badalne ke liye button dabayein ya <code>/setpassword MyPass123</code> type karein.\n\n"
        "🔹 <b>Commands:</b>\n"
        "/extract - Extract mode me switch karein\n"
        "/password - Password + TXT mode me switch karein\n"
        "/setpassword &lt;pass&gt; - Direct password change karein\n"
        "/cancel - Current operation cancel karein"
    ).format(pwd=html.escape(session["password"]))
    bot.send_message(message.chat.id, help_text, parse_mode='HTML', reply_markup=get_main_keyboard())

# 3. Mode switch: Extract Numbers
@bot.message_handler(func=lambda msg: msg.text == "✂️ Extract Numbers (Mono)" or msg.text == "/extract")
def set_extract_mode(message):
    session = get_session(message.chat.id)
    session["mode"] = "extract"
    session["awaiting"] = None
    bot.send_message(
        message.chat.id,
        "✅ <b>Extract Numbers Mode Active!</b>\n\n"
        "Ab aap koi bhi text ya list bhejiye (jaise <code>8053483439 amanku pen</code>).\n"
        "Bot usme se sirf numbers alag karke <b>Tap-to-Copy (Mono)</b> format me bhejega.",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

# 4. Mode switch: Number:Password + TXT
@bot.message_handler(func=lambda msg: msg.text == "🔐 Number:Password + TXT" or msg.text == "/password")
def set_password_mode(message):
    session = get_session(message.chat.id)
    session["mode"] = "password"
    session["awaiting"] = None
    bot.send_message(
        message.chat.id,
        f"✅ <b>Number:Password + TXT Mode Active!</b>\n\n"
        f"🔑 <b>Current Password:</b> <code>{html.escape(session['password'])}</code>\n\n"
        f"Ab aap apne numbers/text send karein. Bot unhe:\n"
        f"<pre>9899882946:{html.escape(session['password'])}\n9899882947:{html.escape(session['password'])}</pre>\n"
        f"format me convert karke <b>.txt file</b> bhej dega.\n\n"
        f"<i>(Password badalne ke liye '🔑 Set Password' button dabayein)</i>",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

# 5. Set Password button or /setpassword command
@bot.message_handler(func=lambda msg: msg.text == "🔑 Set Password")
def request_new_password(message):
    session = get_session(message.chat.id)
    session["awaiting"] = "new_password"
    bot.send_message(
        message.chat.id,
        f"✏️ <b>Apna naya password bhejiye:</b>\n"
        f"(Example: <code>Ramu0001</code> ya <code>9540182226Aa@</code>)\n\n"
        f"Current Password: <code>{html.escape(session['password'])}</code>\n\n"
        f"<i>Cancel karne ke liye /cancel type karein.</i>",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['setpassword'])
def cmd_set_password(message):
    session = get_session(message.chat.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        new_pass = parts[1].strip()
        session["password"] = new_pass
        session["awaiting"] = None
        bot.send_message(
            message.chat.id,
            f"✅ <b>Password update ho gaya!</b>\n\n🔑 <b>Naya Password:</b> <code>{html.escape(new_pass)}</code>",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    else:
        session["awaiting"] = "new_password"
        bot.send_message(
            message.chat.id,
            "✏️ Kripya apna naya password likh kar send karein:",
            parse_mode='HTML'
        )

# 6. Cancel command
@bot.message_handler(commands=['cancel'])
def cancel_action(message):
    session = get_session(message.chat.id)
    session["awaiting"] = None
    bot.send_message(
        message.chat.id,
        "❌ Action cancel kar diya gaya hai.",
        reply_markup=get_main_keyboard()
    )

# 7. Help button handler
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Help / Guide")
def help_button_handler(message):
    send_help(message)

# 8. Document Handler (Agar user .txt file upload kare)
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not message.document.file_name.lower().endswith('.txt'):
        bot.reply_to(message, "⚠️ Kripya sirf .txt file send karein.")
        return
        
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_text = downloaded_file.decode('utf-8', errors='ignore')
        process_text_input(message, file_text)
    except Exception as e:
        bot.reply_to(message, f"❌ File read karne me error: {str(e)}")

# 9. Normal Text Message Handler
@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    session = get_session(message.chat.id)
    user_text = message.text.strip()
    
    # Agar user password enter kar raha hai
    if session.get("awaiting") == "new_password":
        session["password"] = user_text
        session["awaiting"] = None
        bot.send_message(
            message.chat.id,
            f"✅ <b>Password successfully set ho gaya!</b>\n\n"
            f"🔑 <b>Naya Password:</b> <code>{html.escape(user_text)}</code>\n\n"
            f"Ab aap numbers send kar sakte hain.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        return
        
    process_text_input(message, user_text)

# Core processing function
def process_text_input(message, input_text):
    session = get_session(message.chat.id)
    numbers = extract_phone_numbers(input_text)
    
    if not numbers:
        bot.reply_to(
            message,
            "⚠️ <b>Koi valid number nahi mila!</b>\n\n"
            "Kripya aisa text bhejein jisme phone number ho (e.g. <code>8053483439 amanku pen</code>).",
            parse_mode='HTML'
        )
        return
        
    total = len(numbers)
    
    # MODE 1: Extract Numbers (Mono tap to copy)
    if session["mode"] == "extract":
        bot.send_message(
            message.chat.id,
            f"✂️ <b>Extracted {total} Number{'s' if total > 1 else ''}:</b>\n<i>(Tap on number to copy)</i>",
            parse_mode='HTML'
        )
        for num in numbers:
            # Monospaced code block for single tap copy on Telegram
            bot.send_message(message.chat.id, f"<code>{html.escape(num)}</code>", parse_mode='HTML')
            time.sleep(0.3)  # Anti-flood delay
            
        print(f"Chat {message.chat.id}: Processed {total} numbers in Extract Mode.")

    # MODE 2: Number:Password + TXT Generation
    elif session["mode"] == "password":
        curr_pass = session["password"]
        formatted_lines = [f"{num}:{curr_pass}" for num in numbers]
        full_content = "\n".join(formatted_lines)
        
        # Preview send karna
        preview_limit = 15
        preview_text = "\n".join(formatted_lines[:preview_limit])
        extra_note = f"\n<i>...aur {total - preview_limit} numbers niche file me hain.</i>" if total > preview_limit else ""
        
        preview_msg = (
            f"🔐 <b>Formatted {total} Number{'s' if total > 1 else ''}:</b>\n\n"
            f"<pre>{html.escape(preview_text)}</pre>"
            f"{extra_note}"
        )
        bot.send_message(message.chat.id, preview_msg, parse_mode='HTML')
        
        # TXT file generate karke send karna
        txt_stream = io.BytesIO(full_content.encode('utf-8'))
        txt_stream.name = f"numbers_{curr_pass}_{total}.txt"
        
        bot.send_document(
            message.chat.id,
            txt_stream,
            caption=(
                f"📄 <b>TXT File Ready!</b>\n\n"
                f"📊 <b>Total Numbers:</b> <code>{total}</code>\n"
                f"🔑 <b>Password:</b> <code>{html.escape(curr_pass)}</code>"
            ),
            parse_mode='HTML'
        )
        print(f"Chat {message.chat.id}: Generated TXT file for {total} numbers with password '{curr_pass}'.")

print("Bot active hai... Numbers Extractor & Password TXT Generator ready.")

# Bot Polling
bot.infinity_polling()
