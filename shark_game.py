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


# ---------------- KEYBOARD ----------------
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
            "msg": msg.message_id
        }

    # ---------------- BUTTONS ----------------
    @bot.callback_query_handler(func=lambda call: call.data in ["see", "change", "join", "drop"])
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

            bot.send_message(
                chat,
                f"🎮 {user.first_name} added to leader queue"
            )
            return

        # only leader controls
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

        # ---------------- DROP LEAD (NEW SYSTEM) ----------------
        elif data == "drop":

            old_leader = game["leader_name"]

            try:
                bot.delete_message(chat, game["msg"])
            except:
                pass

            # REMOVE CURRENT LEADER
            game["leader"] = None

            # NEXT LEADER FROM QUEUE
            if leader_queue[chat]:

                new = leader_queue[chat].pop(0)
                member = bot.get_chat_member(chat, new)

                game["leader"] = new
                game["leader_name"] = member.user.first_name
                game["word"] = random.choice(words)

                mention = f"<a href='tg://user?id={new}'>{member.user.first_name}</a>"

                msg = bot.send_message(
                    chat,
                    f"🦈 {old_leader} refused to lead ❌\n\n🎤 {mention} is now the leader!",
                    parse_mode="HTML",
                    reply_markup=game_keyboard()
                )

                game["msg"] = msg.message_id

            else:

                bot.send_message(
                    chat,
                    f"🦈 {old_leader} refused to lead ❌\n\n⚠️ No leader in queue!"
                )

                # SHOW JOIN BUTTON
                bot.send_message(
                    chat,
                    "👉 No leader available. Join queue to become leader!",
                    reply_markup=join_keyboard()
                )

                del games[chat]

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

            new_word = random.choice(words)

            msg = bot.send_message(
                chat,
                f"🦈 New Leader Game\n\n🎤 {mention} is now leader!",
                parse_mode="HTML",
                reply_markup=game_keyboard()
            )

            games[chat] = {
                "leader": user.id,
                "leader_name": user.first_name,
                "word": new_word,
                "msg": msg.message_id
            }

    # ---------------- RANK ----------------
    @bot.message_handler(commands=['ranking'])
    def rank(message):

        chat = message.chat.id

        if chat not in ranking:
            bot.send_message(chat, "No ranking yet")
            return

        top = sorted(ranking[chat].items(), key=lambda x: x[1], reverse=True)

        text = "🏆 Ranking\n\n"

        for i, (name, score) in enumerate(top[:10], 1):
            text += f"{i}. {name} — {score}\n"

        bot.send_message(chat, text)

    # ---------------- STOP ----------------
    @bot.message_handler(commands=['stop'])
    def stop(message):

        chat = message.chat.id

        if chat in games:
            del games[chat]

        bot.send_message(chat, "🛑 Game stopped")
