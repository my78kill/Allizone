import random
import threading
import time
from collections import defaultdict

game_data = {}
scores = defaultdict(dict)

ROUND_TIME = 120
TOTAL_ROUNDS = 10


def load_questions():
    q = []
    try:
        with open("questions.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    question, answer = line.split("|")
                    q.append((question.strip(), answer.strip().lower()))
    except:
        pass

    if not q:
        q = [("Capital of France?", "paris")]  # fallback

    return q


questions = load_questions()


def register_game_handlers(bot):

    # START
    @bot.message_handler(func=lambda m: m.text and m.text.lower() == "#start")
    def start_game(message):

        if message.chat.type == "private":
            return

        chat_id = message.chat.id

        if chat_id in game_data:
            bot.send_message(chat_id, "⚠️ Game already running!")
            return

        game_data[chat_id] = {
            "round": 0,
            "asked": [],
            "answer": None,
            "msg_id": None
        }

        bot.send_message(chat_id, "🎮 Game Started!")
        next_round(bot, chat_id)

    # NEXT ROUND
    def next_round(bot, chat_id):

        if chat_id not in game_data:
            return

        data = game_data[chat_id]

        if data["round"] >= TOTAL_ROUNDS:
            end_game(bot, chat_id)
            return

        q = random.choice(questions)

        while q in data["asked"]:
            q = random.choice(questions)

        data["asked"].append(q)

        question, answer = q

        data["answer"] = answer
        data["round"] += 1

        msg = bot.send_message(
            chat_id,
            f"🧠 Round {data['round']}/{TOTAL_ROUNDS}\n\n{question}\n\n⏳ 120 sec"
        )

        data["msg_id"] = msg.message_id

        threading.Thread(
            target=round_timer,
            args=(bot, chat_id),
            daemon=True
        ).start()

    # TIMER
    def round_timer(bot, chat_id):

        time.sleep(ROUND_TIME)

        if chat_id not in game_data:
            return

        data = game_data[chat_id]

        if data["answer"] is None:
            return

        try:
            bot.delete_message(chat_id, data["msg_id"])
        except:
            pass

        data["answer"] = None
        next_round(bot, chat_id)

    # ANSWER (🔥 FIXED)
    @bot.message_handler(func=lambda m: m.text and not m.text.startswith("#") and not m.text.startswith("/"))
    def check_answer(message):

        chat_id = message.chat.id

        if chat_id not in game_data:
            return

        data = game_data[chat_id]

        if data["answer"] is None:
            return

        user_answer = message.text.lower().strip()

        if user_answer == data["answer"]:

            user_id = message.from_user.id
            name = message.from_user.first_name

            if user_id not in scores[chat_id]:
                scores[chat_id][user_id] = {"name": name, "points": 0}

            scores[chat_id][user_id]["points"] += 10

            bot.send_message(chat_id, f"✅ {name} answered correctly!\n+10 points 🎉")

            try:
                bot.delete_message(chat_id, data["msg_id"])
            except:
                pass

            data["answer"] = None
            next_round(bot, chat_id)

    # RANK
    @bot.message_handler(func=lambda m: m.text and m.text.lower() == "#rank")
    def rank(message):

        chat_id = message.chat.id

        if chat_id not in scores or not scores[chat_id]:
            bot.send_message(chat_id, "No scores yet.")
            return

        sorted_users = sorted(
            scores[chat_id].values(),
            key=lambda x: x["points"],
            reverse=True
        )

        text = "🏆 Leaderboard\n\n"

        for i, user in enumerate(sorted_users[:10], 1):
            text += f"{i}. {user['name']} — {user['points']}\n"

        bot.send_message(chat_id, text)

    # END
    @bot.message_handler(func=lambda m: m.text and m.text.lower() == "#end")
    def end_cmd(message):
        end_game(bot, message.chat.id)

    def end_game(bot, chat_id):

        if chat_id not in game_data:
            return

        bot.send_message(chat_id, "🎮 Game Ended!")
        del game_data[chat_id]
