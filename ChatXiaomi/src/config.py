import os
import time
import warnings
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

warnings.filterwarnings("ignore")

# Get the project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "data" / ".env")

console = Console()


class Config:
    KIMI_EMAIL = os.getenv("KIMI_EMAIL")
    KIMI_PASSWORD = os.getenv("KIMI_PASSWORD")
    BROWSER_PATH = os.getenv("BROWSER_PATH")

    HEADLESS = False
    AUTH_WAIT_TIME = 10

    COOKIES_FILE = str(PROJECT_ROOT / "data" / "kimi_cookies.json")
    TOKEN_FILE = str(PROJECT_ROOT / "data" / "auth_token.txt")
    BROWSER_PROFILE_DIR = str(PROJECT_ROOT / "data" / "browser_profile")
    LAST_LOGIN_FILE = str(PROJECT_ROOT / "data" / "last_login.txt")

    SESSION_TIMEOUT = 3600

    BASE_URL = "https://aistudio.xiaomimimo.com"
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://aistudio.xiaomimimo.com",
        "Referer": "https://aistudio.xiaomimimo.com/",
        "Priority": "u=1, i",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    @staticmethod
    def print_status(message, style="white"):
        console.print(f"[{style}][Xiaomi][/{style}] {message}")

    @staticmethod
    def needs_reauth():
        try:
            with open(Config.LAST_LOGIN_FILE, "r") as f:
                last_login = float(f.read().strip())
            return (time.time() - last_login) > Config.SESSION_TIMEOUT
        except:
            return True

    @staticmethod
    def update_login_time():
        with open(Config.LAST_LOGIN_FILE, "w") as f:
            f.write(str(time.time()))
