import os
from dotenv import load_dotenv

load_dotenv()

# BOT TOKEN
BOT_TOKEN = "8678708886:AAH6rKZf5JUxRhlva3vi5YfwTqSzQG7YKSk"

# 🌐 NSFW API
API_URL = "https://nsfw-81ex.onrender.com"
API_KEY = "sk_92KjsH@8sKx_91!dkL"

# ⏱️ Auto delete timings (seconds)
DELETE_TIME = int(os.getenv("DELETE_TIME", 10))        # warning message delete
EDIT_DELETE_TIME = int(os.getenv("EDIT_DELETE_TIME", 1800))  # 30 min
