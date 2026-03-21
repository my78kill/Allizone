import random
from collections import defaultdict
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

games = {}
leader_queue = defaultdict(list)
ranking = defaultdict(lambda: defaultdict(int))


def load_words():
    try:
        with open("words.txt", "r", encoding="utf-8") as f:
            return [w.strip().lower() for w in f.readlines() if w.strip()]
    except:
        return ["apple", "car", "dog"]


words = load_words()


# ---------------- KEYBOARDS ----------------

def game_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👁 See word", callback_data="see"),
        InlineKeyboardButton("🔄 Change word", callback_data="change")
    )
    markup.row(
        InlineKeyboardButton("🎮 I want to be a leader", callback_data="join"),
        InlineKeyboardButton("❌ Drop Lead", callback_data="drop")
    )
    return markup


def join_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎮 I want to be a leader", callback_data="join")
    )
    return markup


# ---------------- MAIN ----------------

def register_shark_game(bot):

    # START GAME
    @bot.message_handler(commands=['game'])
    def start_game(message):

        chat = message.chat.id

        if chat in games:
            bot.send_message(chat, "⚠️ Game already running!")
            return

        user = message.from_user
        word = random.choice(words)

        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

        msg = bot.send_message(
            chat,
            f"🦈 Shark Game Started!\n\n🎤 {mention} is the leader!",
            parse_mode="HTML",
            reply_markup=game_keyboard()
        )

        games[chat] = {
            "leader": user.id,
            "leader_name": user.first_name,
            "word": word,
            "msg": msg.message_id,
            "drop_pending": False
        }

    # ---------------- BUTTONS ----------------
    @bot.callback_query_handler(func=lambda call: call.data in ["see", "change", "join", "drop", "take_lead"])
    def buttons(call):

        chat = call.message.chat.id
        user = call.from_user
        data = call.data

        if chat not in games:
            bot.answer_callback_query(call.id)
            return

        game = games[chat]

        # ---------------- JOIN QUEUE ----------------
        if data == "join":

            if user.id not in leader_queue[chat]:
                leader_queue[chat].append(user.id)

            bot.answer_callback_query(call.id, "Added to leader queue!")
            bot.send_message(chat, f"🎮 {user.first_name} joined leader queue")
            return

        # ---------------- TAKE LEAD AFTER DROP ----------------
        if data == "take_lead":

            if not game.get("drop_pending"):
                bot.answer_callback_query(call.id, "No lead available!", show_alert=True)
                return

            game["leader"] = user.id
            game["leader_name"] = user.first_name
            game["word"] = random.choice(words)
            game["drop_pending"] = False

            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

            msg = bot.send_message(
                chat,
                f"🦈 Shark game\n{mention} is explaining the word!",
                parse_mode="HTML",
                reply_markup=game_keyboard()
            )

            game["msg"] = msg.message_id

            bot.answer_callback_query(call.id)
            return

        # only leader controls below
        if user.id != game["leader"]:
            bot.answer_callback_query(call.id, "Only leader can do this!", show_alert=True)
            return

        # ---------------- SEE WORD ----------------
        if data == "see":
            bot.answer_callback_query(call.id, f"Word: {game['word']}", show_alert=True)

        # ---------------- CHANGE WORD ----------------
        elif data == "change":
            game["word"] = random.choice(words)
            bot.answer_callback_query(call.id, f"New Word: {game['word']}", show_alert=True)

        # ---------------- DROP LEAD (NEW FLOW) ----------------
        elif data == "drop":

            old_name = game["leader_name"]

            game["leader"] = None
            game["drop_pending"] = True

            try:
                bot.delete_message(chat, game["msg"])
            except:
                pass

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🎮 I want to be a leader", callback_data="take_lead")
            )

            bot.send_message(
                chat,
                f"❌ {old_name} refused to lead\n\n👉 Someone can take leadership!",
                reply_markup=markup
            )

        bot.answer_callback_query(call.id)

    # ---------------- GUESS ----------------
    @bot.message_handler(func=lambda m: m.text and not m.text.startswith("/") and not m.text.startswith("#"))
    def guess(message):

        chat = message.chat.id

        if chat not in games:
            return

        game = games[chat]
        user = message.from_user
        text = message.text.lower().strip()

        if user.id == game["leader"]:
            return

        if text == game["word"]:

            ranking[chat][user.first_name] += 1

            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

            bot.send_message(
                chat,
                f"🎉 {mention} guessed correctly!\n👑 Now you are leader!",
                parse_mode="HTML"
            )

            try:
                bot.delete_message(chat, game["msg"])
            except:
                pass

            game["leader"] = user.id
            game["leader_name"] = user.first_name
            game["word"] = random.choice(words)
            game["drop_pending"] = False

            msg = bot.send_message(
                chat,
                f"🦈 Shark Game\n\n🎤 {mention} is now leader!",
                parse_mode="HTML",
                reply_markup=game_keyboard()
            )

            game["msg"] = msg.message_id

    # ---------------- RANKING ----------------
    @bot.message_handler(commands=['ranking'])
    def rank(message):

        chat = message.chat.id

        if chat not in ranking:
            bot.send_message(chat, "No ranking yet")
            return

        top = sorted(ranking[chat].items(), key=lambda x: x[1], reverse=True)

        text = "🏆 Shark Game Ranking\n\n"

        for i, (name, score) in enumerate(top[:10], 1):
            text += f"{i}. {name} — {score}\n"

        bot.send_message(chat, text)

    # ---------------- STOP ----------------
    @bot.message_handler(commands=['stop'])
    def stop(message):

        chat = message.chat.id

        if chat in games:
            del games[chat]

        bot.send_message(chat, "🛑 Shark Game stopped")
