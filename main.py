from flask import Flask
import threading
from bot import run_bot

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def start_bot():
    run_bot()

threading.Thread(target=start_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)