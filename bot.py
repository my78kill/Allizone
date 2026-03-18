import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, DELETE_TIME, EDIT_DELETE_TIME, API_USER, API_SECRET
import time
import threading
import requests

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Load abuse words
with open("abuse.txt", "r", encoding="utf-8") as f:
    ABUSE_WORDS = [line.strip().lower() for line in f.readlines()]

# Auto delete function
def auto_delete(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

# ------------------ START COMMAND ------------------
@bot.message_handler(commands=['start'])
def start(msg):
    if msg.chat.type == "private":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ Add me to Group", url=f"https://t.me/{bot.get_me().username}?startgroup=true"),
            InlineKeyboardButton("📖 Help", callback_data="help")
        )

        text = """
👋 Welcome!

I am a smart moderation bot 🤖

✨ Features:
• NSFW image/sticker detection 🚫
• Abuse word filter ⚠️
• Edited message tracking ⏳
• Auto clean bot messages 🧹

Add me to your group and make chat clean 🚀
"""
        m = bot.send_message(msg.chat.id, text, reply_markup=markup)

        threading.Thread(target=auto_delete, args=(msg.chat.id, m.message_id, DELETE_TIME)).start()

# ------------------ HELP BUTTON ------------------
@bot.callback_query_handler(func=lambda call: call.data == "help")
def help_cb(call):
    text = """
📖 Commands:
/start - Start bot
/help - Show help

⚙️ Auto Features:
• NSFW detection (API)
• Abuse filter
• Edited message delete after 30 min
"""
    bot.answer_callback_query(call.id)
    m = bot.send_message(call.message.chat.id, text)

    threading.Thread(target=auto_delete, args=(m.chat.id, m.message_id, DELETE_TIME)).start()

# ------------------ ABUSE FILTER ------------------
@bot.message_handler(func=lambda message: message.text is not None)
def filter_abuse(message):
    text = message.text.lower()

    for word in ABUSE_WORDS:
        if word in text:
            try:
                bot.delete_message(message.chat.id, message.message_id)

                warn = bot.send_message(
                    message.chat.id,
                    f"⚠️ <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>, abuse is not allowed!"
                )

                threading.Thread(target=auto_delete, args=(warn.chat.id, warn.message_id, DELETE_TIME)).start()
            except:
                pass
            return

# ------------------ NSFW CHECK FUNCTION ------------------
def check_nsfw(file_url):
    url = "https://api.sightengine.com/1.0/check.json"
    params = {
        'models': 'nudity-2.1',
        'api_user': API_USER,
        'api_secret': API_SECRET,
        'url': file_url
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()

        nudity = data.get("nudity", {})
        if (
            nudity.get("sexual_activity", 0) > 0.5 or
            nudity.get("sexual_display", 0) > 0.5 or
            nudity.get("erotica", 0) > 0.5
        ):
            return True
    except:
        pass

    return False

# ------------------ NSFW HANDLER ------------------
@bot.message_handler(content_types=['photo', 'sticker'])
def nsfw_handler(message):
    try:
        file_id = None

        if message.content_type == 'sticker':
            file_id = message.sticker.file_id
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id

        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

        if check_nsfw(file_url):
            user = message.from_user

            # Delete NSFW content
            bot.delete_message(message.chat.id, message.message_id)

            # Alert
            warn = bot.send_message(
                message.chat.id,
                f"🚫 <a href='tg://user?id={user.id}'>{user.first_name}</a>, NSFW content is not allowed!"
            )

            threading.Thread(target=auto_delete, args=(warn.chat.id, warn.message_id, DELETE_TIME)).start()

    except Exception as e:
        print(e)

# ------------------ EDITED MESSAGE ------------------
@bot.edited_message_handler(func=lambda message: True)
def edited_msg(message):
    user = message.from_user

    warn = bot.send_message(
        message.chat.id,
        f"⚠️ <a href='tg://user?id={user.id}'>{user.first_name}</a>, your edited message will be deleted in 30 minutes."
    )

    # delete edited msg after 30 min
    threading.Thread(
        target=auto_delete,
        args=(message.chat.id, message.message_id, EDIT_DELETE_TIME)
    ).start()

    # delete warning after 5 min
    threading.Thread(
        target=auto_delete,
        args=(warn.chat.id, warn.message_id, DELETE_TIME)
    ).start()

# ------------------ RUN BOT ------------------
def run_bot():
    bot.infinity_polling()