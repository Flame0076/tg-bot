import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import csv
import re
import os
from flask import Flask
import threading

# --- YAHAN APNI DETAILS FILL KAREIN ---
TOKEN = "8901757330:AAEuCvPa3HkzOVc1AmhAOSrLs1qxVIOZ2RU"
OWNER_ID = 6022261644  # Apna User ID yahan daalein
# --------------------------------------

bot = telebot.TeleBot(TOKEN)
allowed_users = {OWNER_ID}
user_data = {}

# Dummy Web Server (Render ko awake rakhne ke liye)
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot is Running 24/7!"

def is_auth(message):
    return message.from_user.id in allowed_users

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_command(message):
    text = (
        "Welcome To Text TO CSV BOT\n"
        "Follow The Commands Below To Start\n"
        "/start - To Start The Bot\n"
        "/Txt_To_CSV - Convert TXT File TO CSV\n"
        "/CSV_To_TXT - Convert CSV File To TXT\n"
        "/reset - Reset Command For Stopping Ongoing Procces\n\n"
        "Created By @Flame9906"
    )
    bot.send_message(message.chat.id, text)

# --- RESET COMMAND ---
@bot.message_handler(commands=['reset'])
def reset_command(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.chat.id in user_data:
        del user_data[message.chat.id]
    bot.send_message(message.chat.id, "Process stopped immediately. Use commands to start again.")

# --- OWNER ACCESS SYSTEM ---
@bot.message_handler(commands=['add_user'])
def add_user(message):
    if message.from_user.id == OWNER_ID:
        try:
            new_user = int(message.text.split()[1])
            allowed_users.add(new_user)
            bot.reply_to(message, f"Access Granted to User ID: {new_user}")
        except:
            bot.reply_to(message, "Send command like this: /add_user 123456789")

# --- TXT TO CSV FLOW ---
@bot.message_handler(commands=['Txt_To_CSV'])
def txt_to_csv_start(message):
    if not is_auth(message):
        bot.reply_to(message, "You do not have access to this bot.")
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "Send Your Txt Format File")
    bot.register_next_step_handler(msg, process_txt_file)

def process_txt_file(message):
    if message.text == '/reset': return reset_command(message)
    if not message.document:
        msg = bot.send_message(message.chat.id, "Please send a valid TXT file.")
        bot.register_next_step_handler(msg, process_txt_file)
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        
        numbers = [re.sub(r'[^\d+]', '', line.strip()) for line in content.split('\n') if re.sub(r'[^\d+]', '', line.strip())]
        
        if not numbers:
            bot.send_message(message.chat.id, "No numbers found in the file.")
            return
            
        user_data[message.chat.id] = {'numbers': numbers}
        msg = bot.send_message(message.chat.id, f"{len(numbers)} Contact Found In Your File.\n\nSend Me Name For Your Contacts Example Flame 1")
        bot.register_next_step_handler(msg, process_contact_name)
    except Exception as e:
        bot.send_message(message.chat.id, "Error processing file.")

def process_contact_name(message):
    if message.text == '/reset': return reset_command(message)
    raw_name = message.text.strip()
    
    match = re.match(r'^(.*?)(?:\s+(\d+))?$', raw_name)
    if match:
        prefix = match.group(1).strip()
        start_index = int(match.group(2)) if match.group(2) else 1
    else:
        prefix = raw_name
        start_index = 1
        
    user_data[message.chat.id].update({'prefix': prefix, 'index': start_index})
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Yes", callback_data="tags_yes"), 
        InlineKeyboardButton("No", callback_data="tags_no")
    )
    bot.send_message(message.chat.id, "Do You Want To Add Tags ?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['tags_yes', 'tags_no'])
def tags_callback(call):
    chat_id = call.message.chat.id
    if call.data == 'tags_yes':
        msg = bot.send_message(chat_id, "Send Me Your Tag Name Example Flame")
        bot.register_next_step_handler(msg, process_tag_name)
    else:
        generate_csv(chat_id, tag="")

def process_tag_name(message):
    if message.text == '/reset': return reset_command(message)
    generate_csv(message.chat.id, tag=message.text.strip())

def generate_csv(chat_id, tag=""):
    data = user_data.get(chat_id)
    if not data: return
        
    numbers = data['numbers']
    prefix = data['prefix']
    start_idx = data['index']
    
    filename = f"{chat_id}_contacts.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Phone Number', 'Tags'])
        for i, num in enumerate(numbers):
            contact_name = f"{prefix} {start_idx + i}"
            writer.writerow([contact_name, num, tag])
            
    with open(filename, 'rb') as f:
        bot.send_document(chat_id, f, caption="Your CSV File Is Ready")
        
    os.remove(filename)
    del user_data[chat_id]

# --- CSV TO TXT FLOW ---
@bot.message_handler(commands=['CSV_To_TXT'])
def csv_to_txt_start(message):
    if not is_auth(message):
        bot.reply_to(message, "You do not have access to this bot.")
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(message.chat.id, "Send Me Your CSV File")
    bot.register_next_step_handler(msg, process_csv_file)

def process_csv_file(message):
    if message.text == '/reset': return reset_command(message)
    if not message.document:
        msg = bot.send_message(message.chat.id, "Please send a valid CSV file.")
        bot.register_next_step_handler(msg, process_csv_file)
        return
        
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        
        reader = csv.reader(content.splitlines())
        next(reader, None) # Skip header
        
        numbers = []
        for row in reader:
            if len(row) > 1: 
                num = re.sub(r'[^\d+]', '', row[1])
                if num:
                    numbers.append(num)
                    
        if not numbers:
            bot.send_message(message.chat.id, "No numbers found in the CSV.")
            return
            
        filename = f"{message.chat.id}_numbers.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(numbers))
            
        with open(filename, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="Your TXT File Is Ready")
            
        os.remove(filename)
        
    except Exception as e:
        bot.send_message(message.chat.id, "Error processing CSV.")

def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    # Telegram Bot ko alag se run karega
    threading.Thread(target=run_bot).start()
    # Web server ko start karega
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
