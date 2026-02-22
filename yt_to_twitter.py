#!/usr/bin/env python3
import sys
import os

# Ensure the current directory is in sys.path so we can import src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot import Bot

if __name__ == "__main__":
    try:
        bot = Bot()
        bot.run()
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)
