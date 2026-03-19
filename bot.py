import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
import requests
from config import BOT_TOKEN, DELETE_TIME, EDIT_DELETE_TIME, API_USER, API_SECRET
from db import cursor, conn

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ------------------ DB FUNCTIONS ------------------

def load_packs():
    cursor.execute("SELECT name FROM packs")
    return [row[0] for row in cursor.fetchall()]

def add_pack_db(pack_name):
    try:
        cursor.execute("INSERT INTO packs (name) VALUES (?)", (pack_name,))
        conn.commit()
    except:
        pass

def remove_pack_db(pack_name):
    cursor.execute("DELETE FROM packs WHERE name=?", (pack_name,))
    conn.commit()

# ------------------ AUTO DELETE ------------------

def auto_delete(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

# ------------------ ADMIN CHECK ------------------

def is_admin(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ["administrator", "creator"]
    except:
        return False

# ------------------ START ------------------

@bot.message_handler(commands=['start'])
def start(msg):
    if msg.chat.type == "private":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ Add me to Group", url=f"https://t.me/{bot.get_me().username}?startgroup=true"),
            InlineKeyboardButton("📖 Help", callback_data="help")
        )

        text = """👋 Welcome!

I am a moderation bot 🤖

✨ Features:
• NSFW detection 🚫
• Sticker pack blocker 📦
• Edited message tracking ⏳
"""

        m = bot.send_message(msg.chat.id, text, reply_markup=markup)
        threading.Thread(target=auto_delete, args=(msg.chat.id, m.message_id, DELETE_TIME)).start()

# ------------------ HELP ------------------

@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_cb(call):
    text = """📖 Commands:

/addpack - Ban sticker pack (reply to sticker)
/removepack - Unban pack
"""

    bot.answer_callback_query(call.id)
    m = bot.send_message(call.message.chat.id, text)
    threading.Thread(target=auto_delete, args=(m.chat.id, m.message_id, DELETE_TIME)).start()

# ------------------ ABUSE FILTER ------------------

with open("abuse.txt", "r", encoding="utf-8") as f:
    ABUSE_WORDS = [line.strip().lower() for line in f.readlines()]

@bot.message_handler(func=lambda m: m.text is not None and not m.text.startswith('/'))
def abuse_filter(message):
    text = message.text.lower()

    for word in ABUSE_WORDS:
        if word in text:
            bot.delete_message(message.chat.id, message.message_id)

            warn = bot.send_message(
                message.chat.id,
                f"⚠️ <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>, abuse not allowed!"
            )

            threading.Thread(target=auto_delete, args=(warn.chat.id, warn.message_id, DELETE_TIME)).start()
            return

# ------------------ NSFW API ------------------

def check_nsfw(file_url):
    url = "https://api.sightengine.com/1.0/check.json"
    params = {
        'models': 'nudity-2.1',
        'api_user': API_USER,
        'api_secret': API_SECRET,
        'url': file_url
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()

        nudity = data.get("nudity", {})
        if nudity.get("sexual_activity", 0) > 0.5 or nudity.get("sexual_display", 0) > 0.5:
            return True
    except:
        pass

    return False

# ------------------ STICKER HANDLER ------------------

@bot.message_handler(content_types=['sticker'])
def sticker_handler(message):
    try:
        sticker = message.sticker
        user = message.from_user
        pack_name = sticker.set_name

        BLOCKED_PACKS = load_packs()

        # 🚫 Blocked pack
        if pack_name in BLOCKED_PACKS:
            bot.delete_message(message.chat.id, message.message_id)

            warn = bot.send_message(
                message.chat.id,
                f"🚫 <a href='tg://user?id={user.id}'>{user.first_name}</a>, this sticker pack is banned!"
            )

            threading.Thread(target=auto_delete, args=(warn.chat.id, warn.message_id, DELETE_TIME)).start()
            return

        # 🧠 Static sticker NSFW check
        if not sticker.is_animated and not sticker.is_video:
            file_info = bot.get_file(sticker.file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

            if check_nsfw(file_url):
                bot.delete_message(message.chat.id, message.message_id)

    except Exception as e:
        print(e)

# ------------------ PHOTO NSFW ------------------

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        if check_nsfw(file_url):
            bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

# ------------------ ADD PACK ------------------

@bot.message_handler(commands=['addpack'])
def add_pack(message):
    try:
        if not is_admin(message.chat.id, message.from_user.id):
            bot.reply_to(message, "❌ You are not admin")
            return

        if message.reply_to_message and message.reply_to_message.sticker:
            pack = message.reply_to_message.sticker.set_name

            if not pack:
                bot.reply_to(message, "❌ Cannot detect pack name")
                return

            add_pack_db(pack)

            bot.reply_to(message, f"✅ Added pack: {pack}")

        else:
            bot.reply_to(message, "❌ Reply to a sticker")

    except Exception as e:
        print(e)

# ------------------ REMOVE PACK ------------------

@bot.message_handler(commands=['removepack'])
def remove_pack(message):
    try:
        if not is_admin(message.chat.id, message.from_user.id):
            bot.reply_to(message, "❌ You are not admin")
            return

        if message.reply_to_message and message.reply_to_message.sticker:
            pack = message.reply_to_message.sticker.set_name

            if not pack:
                bot.reply_to(message, "❌ Cannot detect pack name")
                return

            remove_pack_db(pack)

            bot.reply_to(message, f"✅ Removed pack: {pack}")

        else:
            bot.reply_to(message, "❌ Reply to a sticker")

    except Exception as e:
        print(e)

# ------------------ EDITED MESSAGE ------------------

@bot.edited_message_handler(func=lambda m: True)
def edited_msg(message):
    user = message.from_user

    warn = bot.send_message(
        message.chat.id,
        f"⚠️ <a href='tg://user?id={user.id}'>{user.first_name}</a>, your edited message will be deleted in 30 min."
    )

    threading.Thread(target=auto_delete, args=(message.chat.id, message.message_id, EDIT_DELETE_TIME)).start()
    threading.Thread(target=auto_delete, args=(warn.chat.id, warn.message_id, DELETE_TIME)).start()

# ------------------ RUN ------------------

def run_bot():
    bot.infinity_polling(skip_pending=True)
