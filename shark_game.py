import random
from collections import defaultdict
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

games = {}
leader_queue = defaultdict(list)
ranking = defaultdict(lambda: defaultdict(int))


def load_words():
    try:
        with open("words.txt") as f:
            return [w.strip().lower() for w in f.readlines()]
    except:
        return ["apple", "car", "dog"]


words = load_words()


def game_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👁 See word", callback_data="see"),
        InlineKeyboardButton("🔄 Change word", callback_data="change")
    )
    markup.row(
        InlineKeyboardButton("🎮 I want to be a leader", callback_data="join"),
        InlineKeyboardButton("❌ Drop lead", callback_data="drop")
    )
    return markup


def register_shark_game(bot):

    # START
    @bot.message_handler(commands=['game'])
    def start_game(message):
        chat = message.chat.id

        if chat in games:
            bot.send_message(chat, "Game already running!")
            return

        user = message.from_user
        word = random.choice(words)

        msg = bot.send_message(
            chat,
            f"🦈 Shark Game\n\n🎤 {user.first_name} is explaining the word!",
            reply_markup=game_keyboard()
        )

        games[chat] = {
            "leader": user.id,
            "leader_name": user.first_name,
            "word": word,
            "msg": msg.message_id
        }

    # GUESS (FINAL FIX)
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/") and not m.text.startswith("#"))
def guess(message):

        chat = call.message.chat.id
        user = call.from_user
        data = call.data

        # JOIN
        if data == "join":
            if user.id not in leader_queue[chat]:
                leader_queue[chat].append(user.id)
                bot.send_message(chat, f"{user.first_name} joined queue")
            return

        if chat not in games:
            return

        game = games[chat]

        if user.id != game["leader"]:
            bot.answer_callback_query(call.id, "Only leader", show_alert=True)
            return

        if data == "see":
            bot.answer_callback_query(call.id, f"Word: {game['word']}", show_alert=True)

        elif data == "change":
            game["word"] = random.choice(words)
            bot.answer_callback_query(call.id, f"New word: {game['word']}", show_alert=True)

        elif data == "drop":

            if leader_queue[chat]:
                new = leader_queue[chat].pop(0)
                member = bot.get_chat_member(chat, new)

                new_word = random.choice(words)

                mention = f"<a href='tg://user?id={new}'>{member.user.first_name}</a>"

                msg = bot.send_message(
                    chat,
                    f"🦈 Shark Game\n\n🎤 {mention} is now explaining!",
                    parse_mode="HTML",
                    reply_markup=game_keyboard()
                )

                games[chat] = {
                    "leader": new,
                    "leader_name": member.user.first_name,
                    "word": new_word,
                    "msg": msg.message_id
                }

            else:
                bot.send_message(chat, "No leader left")
                del games[chat]

    # GUESS (🔥 FIXED)
    @bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
    def guess(message):

        chat = message.chat.id

        if chat not in games:
            return

        game = games[chat]
        user = message.from_user
        text = message.text.lower().strip()

        # Leader cheating
        if user.id == game["leader"]:
            return

        # ✅ CORRECT ANSWER
        if text == game["word"]:

            ranking[chat][user.first_name] += 1

            mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

            bot.send_message(
                chat,
                f"🎉 {mention} guessed correctly!\n\n👑 Now you are the leader!",
                parse_mode="HTML"
            )

            # delete old msg
            try:
                bot.delete_message(chat, game["msg"])
            except:
                pass

            # NEW LEADER SET
            new_word = random.choice(words)

            msg = bot.send_message(
                chat,
                f"🦈 Shark Game\n\n🎤 {mention} is now explaining!",
                parse_mode="HTML",
                reply_markup=game_keyboard()
            )

            games[chat] = {
                "leader": user.id,
                "leader_name": user.first_name,
                "word": new_word,
                "msg": msg.message_id
            }

    # RANK
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

    # STOP
    @bot.message_handler(commands=['stop'])
    def stop(message):

        chat = message.chat.id

        if chat in games:
            del games[chat]

        bot.send_message(chat, "Game stopped")
