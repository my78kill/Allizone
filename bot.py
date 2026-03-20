import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
import requests
import os
from config import BOT_TOKEN, DELETE_TIME, EDIT_DELETE_TIME
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
• Edited message auto-delete ⏳
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

# ------------------ NSFW CHECK ------------------

def check_nsfw_file(file_path):
    try:
        with open(file_path, "rb") as f:
            res = requests.post(
                API_URL,
                headers={"x-api-key": API_KEY},
                files={"file": f},
                timeout=20
            )
        return res.json().get("nsfw", False)
    except Exception as e:
        print("API Error:", e)
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

        # 📥 Download sticker
        file_info = bot.get_file(sticker.file_id)
        file_path = file_info.file_path
        downloaded = bot.download_file(file_path)

        ext = file_path.split('.')[-1]
        path = f"sticker.{ext}"

        with open(path, "wb") as f:
            f.write(downloaded)

        # 🔥 NSFW CHECK
        if check_nsfw_file(path):
            bot.delete_message(message.chat.id, message.message_id)

        os.remove(path)

    except Exception as e:
        print("Sticker Error:", e)

# ------------------ PHOTO HANDLER ------------------

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path

        downloaded = bot.download_file(file_path)

        path = "photo.jpg"
        with open(path, "wb") as f:
            f.write(downloaded)

        if check_nsfw_file(path):
            bot.delete_message(message.chat.id, message.message_id)

        os.remove(path)

    except Exception as e:
        print("Photo Error:", e)

# ------------------ EDIT HANDLER (FIXED) ------------------

@bot.edited_message_handler(func=lambda m: True)
def edited_msg(message):
    try:
        # ❌ Ignore reactions / empty edits
        if not message.text and not message.caption:
            return

        user = message.from_user

        warn = bot.send_message(
            message.chat.id,
            f"⚠️ <a href='tg://user?id={user.id}'>{user.first_name}</a>, your edited message will be deleted in 30 min."
        )

        # ⏳ delete edited message after 30 min
        threading.Thread(
            target=auto_delete,
            args=(message.chat.id, message.message_id, EDIT_DELETE_TIME)
        ).start()

        # ⏳ delete warning message
        threading.Thread(
            target=auto_delete,
            args=(warn.chat.id, warn.message_id, DELETE_TIME)
        ).start()

    except Exception as e:
        print("Edit Error:", e)

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

# ------------------ RUN ------------------

def run_bot():
    print("Bot running with NSFW API 🚀")
    bot.infinity_polling(skip_pending=True)
