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
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            "mode": "extract",       # 'extract', 'password', 'combine'
            "password": "Ramu0001",  # Default password
            "awaiting": None,        # 'new_password'
            "combine_buffer": [],    # List of all extracted numbers across files
            "combine_files": []      # List of uploaded file names
        }
    return user_sessions[chat_id]

# Main Reply Keyboard
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_extract = types.KeyboardButton("✂️ Extract Numbers (Mono)")
    btn_pass = types.KeyboardButton("🔐 Number:Password + TXT")
    btn_combine = types.KeyboardButton("📂 Combine TXT Files")
    btn_set_pass = types.KeyboardButton("🔑 Set Password")
    btn_help = types.KeyboardButton("ℹ️ Help / Guide")
    markup.add(btn_extract, btn_pass)
    markup.add(btn_combine, btn_set_pass)
    markup.add(btn_help)
    return markup

# Combine Mode Keyboard
def get_combine_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_merge = types.KeyboardButton("✅ Merge & Download TXT")
    btn_cancel = types.KeyboardButton("❌ Cancel / Main Menu")
    markup.add(btn_merge, btn_cancel)
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

# Function to remove duplicates while preserving order
def deduplicate_numbers(numbers):
    seen = set()
    unique = []
    duplicates = []
    for num in numbers:
        if num in seen:
            duplicates.append(num)
        else:
            seen.add(num)
            unique.append(num)
    return unique, duplicates

# 1. /start command handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    session = get_session(message.chat.id)
    curr_pass = session["password"]
    
    welcome_text = (
        "👋 <b>Welcome to Phone Splitter & Combiner Bot!</b>\n\n"
        "✨ <b>Main Features:</b>\n"
        "1️⃣ <b>✂️ Extract Numbers (Mono):</b> Faltu text hata kar sirf unique phone numbers nikalta hai (Tap to Copy).\n"
        "2️⃣ <b>🔐 Number:Password + TXT:</b> Sabhi unique numbers ke sath password jodh kar 📄 <b>.txt file</b> banata hai.\n"
        "3️⃣ <b>📂 Combine TXT Files:</b> Multiple .txt files ko ek sath jod kar single combined file banata hai (Duplicates auto-removed!).\n"
        "4️⃣ <b>🛡️ Auto-Duplicate Filter:</b> Koi bhi duplicate number repeat nahi hoga!\n\n"
        f"⚙️ <b>Current Status:</b>\n"
        f"• Active Mode: <b>{session['mode'].upper()}</b>\n"
        f"• Current Password: <code>{html.escape(curr_pass)}</code>\n\n"
        "Niche diye gaye buttons se shuru karein:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())

# 2. /help command handler
@bot.message_handler(commands=['help'])
def send_help(message):
    session = get_session(message.chat.id)
    help_text = (
        "📖 <b>Bot Guide & Options:</b>\n\n"
        "🔹 <b>✂️ Extract Numbers (Mono)</b>\n"
        "Text bhejiye, bot usme se duplicate hata kar sirf unique numbers alag message me tap-to-copy dega.\n\n"
        "🔹 <b>🔐 Number:Password + TXT</b>\n"
        "Numbers bhejiye, bot format karega: <code>number:{pwd}</code> aur uski <b>.txt file</b> send karega.\n\n"
        "🔹 <b>📂 Combine TXT Files</b>\n"
        "Is option se aap multiple .txt files bhej sakte hain. Bot sabhi files ke numbers jod kar ek master file bana dega.\n\n"
        "🔹 <b>🔑 Set Password</b>\n"
        "Apna password badalne ke liye button dabayein ya <code>/setpassword MyPass123</code> type karein.\n\n"
        "🔹 <b>Commands:</b>\n"
        "/extract - Extract mode\n"
        "/password - Password + TXT mode\n"
        "/combine - Combine multiple files mode\n"
        "/setpassword &lt;pass&gt; - Direct password change\n"
        "/cancel - Current operation cancel"
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
        "Bot sirf <b>Unique Numbers (Duplicates removed)</b> tap-to-copy mono format me bhejega.",
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
        f"Ab aap apne numbers/text send karein. Bot duplicate numbers filter karke:\n"
        f"<pre>9899882946:{html.escape(session['password'])}\n9899882947:{html.escape(session['password'])}</pre>\n"
        f"format me convert karega aur <b>.txt file</b> bhej dega.",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

# 5. Mode switch: Combine Multiple Files
@bot.message_handler(func=lambda msg: msg.text == "📂 Combine TXT Files" or msg.text == "/combine")
def set_combine_mode(message):
    session = get_session(message.chat.id)
    session["mode"] = "combine"
    session["awaiting"] = None
    session["combine_buffer"] = []
    session["combine_files"] = []
    
    bot.send_message(
        message.chat.id,
        "📂 <b>Combine Multiple TXT Files Mode Active!</b>\n\n"
        "1. Aap ek-ek karke ya ek sath kitni bhi <b>.txt files</b> send kijiye.\n"
        "2. Har file ke numbers isme add hote jayenge.\n"
        "3. Jab saari files bhej lein, to niche <b>'✅ Merge & Download TXT'</b> button dabayein.\n\n"
        "<i>(Bot saare duplicate numbers automatically remove kar dega!)</i>",
        parse_mode='HTML',
        reply_markup=get_combine_keyboard()
    )

# 6. Merge & Download Trigger
@bot.message_handler(func=lambda msg: msg.text == "✅ Merge & Download TXT")
def trigger_merge(message):
    session = get_session(message.chat.id)
    all_numbers = session.get("combine_buffer", [])
    files = session.get("combine_files", [])
    
    if not all_numbers:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Koi .txt file receive nahi hui!</b>\n\nKripya pehle ek ya zyada .txt files send karein.",
            parse_mode='HTML',
            reply_markup=get_combine_keyboard()
        )
        return
        
    unique_nums, dups = deduplicate_numbers(all_numbers)
    total_raw = len(all_numbers)
    total_unique = len(unique_nums)
    total_dups = len(dups)
    
    # Inline buttons for format selection
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📄 Plain Unique Numbers (.txt)", callback_data="merge_plain")
    btn2 = types.InlineKeyboardButton(f"🔐 With Password ({session['password']})", callback_data="merge_combo")
    markup.add(btn1)
    markup.add(btn2)
    
    summary_text = (
        f"📊 <b>Files Merge Summary:</b>\n\n"
        f"📁 <b>Total Files:</b> {len(files)}\n"
        f"🔢 <b>Total Numbers:</b> {total_raw}\n"
        f"✅ <b>Unique Numbers:</b> {total_unique}\n"
        f"🗑️ <b>Duplicates Removed:</b> {total_dups}\n\n"
        f"<b>Combined File kis format me chahiye? Niche click karein:</b>"
    )
    bot.send_message(message.chat.id, summary_text, parse_mode='HTML', reply_markup=markup)

# 7. Inline Callback for Combine File Formats
@bot.callback_query_handler(func=lambda call: call.data in ["merge_plain", "merge_combo"])
def handle_merge_callback(call):
    session = get_session(call.message.chat.id)
    all_numbers = session.get("combine_buffer", [])
    unique_nums, dups = deduplicate_numbers(all_numbers)
    
    if not unique_nums:
        bot.answer_callback_query(call.id, "No numbers to export!")
        return

    bot.answer_callback_query(call.id, "Generating File...")
    
    if call.data == "merge_plain":
        file_content = "\n".join(unique_nums)
        file_name = f"combined_unique_{len(unique_nums)}.txt"
        caption = (
            f"📄 <b>Combined Plain Numbers File!</b>\n\n"
            f"✅ Unique Numbers: <code>{len(unique_nums)}</code>\n"
            f"🗑️ Duplicates Filtered: <code>{len(dups)}</code>"
        )
    else:
        curr_pass = session["password"]
        formatted_lines = [f"{num}:{curr_pass}" for num in unique_nums]
        file_content = "\n".join(formatted_lines)
        file_name = f"combined_{curr_pass}_{len(unique_nums)}.txt"
        caption = (
            f"🔐 <b>Combined Password File!</b>\n\n"
            f"✅ Unique Numbers: <code>{len(unique_nums)}</code>\n"
            f"🔑 Password: <code>{html.escape(curr_pass)}</code>\n"
            f"🗑️ Duplicates Filtered: <code>{len(dups)}</code>"
        )
        
    txt_stream = io.BytesIO(file_content.encode('utf-8'))
    txt_stream.name = file_name
    
    bot.send_document(
        call.message.chat.id,
        txt_stream,
        caption=caption,
        parse_mode='HTML'
    )
    
    # Reset combine buffer after successful merge
    session["combine_buffer"] = []
    session["combine_files"] = []
    session["mode"] = "extract"
    bot.send_message(
        call.message.chat.id,
        "✅ <b>Files successfully merge ho gayi hain!</b>\nExtract mode active hai.",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

# 8. Set Password button or /setpassword command
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

# 9. Cancel command / Menu reset
@bot.message_handler(func=lambda msg: msg.text in ["❌ Cancel / Main Menu", "/cancel"])
def cancel_action(message):
    session = get_session(message.chat.id)
    session["awaiting"] = None
    session["mode"] = "extract"
    session["combine_buffer"] = []
    session["combine_files"] = []
    bot.send_message(
        message.chat.id,
        "🏠 <b>Main Menu:</b> Mode reset to Extract Numbers.",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

# 10. Help button handler
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Help / Guide")
def help_button_handler(message):
    send_help(message)

# 11. Document Handler (Agar user .txt file upload kare)
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not message.document.file_name.lower().endswith('.txt'):
        bot.reply_to(message, "⚠️ Kripya sirf .txt file send karein.")
        return
        
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_text = downloaded_file.decode('utf-8', errors='ignore')
        
        session = get_session(message.chat.id)
        
        # Agar Combine Mode me file aayi hai
        if session.get("mode") == "combine":
            file_nums = extract_phone_numbers(file_text)
            if not file_nums:
                bot.reply_to(message, f"⚠️ <code>{html.escape(message.document.file_name)}</code> me koi phone number nahi mila.", parse_mode='HTML')
                return
                
            session["combine_buffer"].extend(file_nums)
            session["combine_files"].append(message.document.file_name)
            
            bot.reply_to(
                message,
                f"📥 <b>File #{len(session['combine_files'])} Added:</b> <code>{html.escape(message.document.file_name)}</code>\n"
                f"• Is file me numbers: <b>{len(file_nums)}</b>\n"
                f"• Ab tak total numbers: <b>{len(session['combine_buffer'])}</b>\n\n"
                f"<i>Aur .txt files bhejiye ya niche '✅ Merge & Download TXT' button dabayein!</i>",
                parse_mode='HTML',
                reply_markup=get_combine_keyboard()
            )
            return

        # Normal single file processing
        process_text_input(message, file_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ File read karne me error: {str(e)}")

# 12. Normal Text Message Handler
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

# Core processing function (with auto-deduplication)
def process_text_input(message, input_text):
    session = get_session(message.chat.id)
    raw_numbers = extract_phone_numbers(input_text)
    
    if not raw_numbers:
        bot.reply_to(
            message,
            "⚠️ <b>Koi valid number nahi mila!</b>\n\n"
            "Kripya aisa text bhejein jisme phone number ho (e.g. <code>8053483439 amanku pen</code>).",
            parse_mode='HTML'
        )
        return
        
    # Deduplication
    unique_numbers, duplicates = deduplicate_numbers(raw_numbers)
    total_raw = len(raw_numbers)
    total_unique = len(unique_numbers)
    total_dups = len(duplicates)
    
    dup_info = f" <i>(🗑️ {total_dups} duplicate{'s' if total_dups > 1 else ''} removed)</i>" if total_dups > 0 else ""

    # MODE 1: Extract Numbers (Mono tap to copy)
    if session["mode"] == "extract":
        bot.send_message(
            message.chat.id,
            f"✂️ <b>Extracted {total_unique} Unique Number{'s' if total_unique > 1 else ''}:</b>{dup_info}\n<i>(Tap on number to copy)</i>",
            parse_mode='HTML'
        )
        
        # Agar numbers 15 ya kam hain, to direct mono messages bhejo
        if total_unique <= 15:
            for num in unique_numbers:
                bot.send_message(message.chat.id, f"<code>{html.escape(num)}</code>", parse_mode='HTML')
                time.sleep(0.3)
        else:
            # Agar bohot saare numbers hain, to pehle 10 preview bhejo aur sath me .txt file
            preview = "\n".join([f"<code>{html.escape(n)}</code>" for n in unique_numbers[:10]])
            bot.send_message(
                message.chat.id,
                f"<b>Preview (First 10):</b>\n{preview}\n\n<i>Baki sabhi {total_unique} numbers ki file niche hai:</i>",
                parse_mode='HTML'
            )
            txt_stream = io.BytesIO("\n".join(unique_numbers).encode('utf-8'))
            txt_stream.name = f"unique_numbers_{total_unique}.txt"
            bot.send_document(
                message.chat.id,
                txt_stream,
                caption=f"📄 <b>Total Unique Numbers:</b> <code>{total_unique}</code>{dup_info}",
                parse_mode='HTML'
            )
            
        print(f"Chat {message.chat.id}: Processed {total_unique} unique numbers ({total_dups} duplicates removed).")

    # MODE 2: Number:Password + TXT Generation
    elif session["mode"] == "password":
        curr_pass = session["password"]
        formatted_lines = [f"{num}:{curr_pass}" for num in unique_numbers]
        full_content = "\n".join(formatted_lines)
        
        # Preview send karna
        preview_limit = 15
        preview_text = "\n".join(formatted_lines[:preview_limit])
        extra_note = f"\n<i>...aur {total_unique - preview_limit} numbers niche file me hain.</i>" if total_unique > preview_limit else ""
        
        preview_msg = (
            f"🔐 <b>Formatted {total_unique} Unique Number{'s' if total_unique > 1 else ''}:</b>{dup_info}\n\n"
            f"<pre>{html.escape(preview_text)}</pre>"
            f"{extra_note}"
        )
        bot.send_message(message.chat.id, preview_msg, parse_mode='HTML')
        
        # TXT file generate karke send karna
        txt_stream = io.BytesIO(full_content.encode('utf-8'))
        txt_stream.name = f"numbers_{curr_pass}_{total_unique}.txt"
        
        bot.send_document(
            message.chat.id,
            txt_stream,
            caption=(
                f"📄 <b>Unique Combo TXT File Ready!</b>\n\n"
                f"📊 <b>Total Unique:</b> <code>{total_unique}</code>\n"
                f"🗑️ <b>Duplicates Filtered:</b> <code>{total_dups}</code>\n"
                f"🔑 <b>Password:</b> <code>{html.escape(curr_pass)}</code>"
            ),
            parse_mode='HTML'
        )
        print(f"Chat {message.chat.id}: Generated TXT file for {total_unique} unique numbers ({total_dups} dups removed).")

print("Bot active hai... Numbers Extractor, Duplicate Remover & File Combiner ready.")

# Bot Polling
bot.infinity_polling()
