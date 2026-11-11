#!/usr/bin/env python3
"""
DEV GOD BOT — Railway Edition (FULLY FIXED)
PACE 0.01 · 𒐫 title fill · Owner-only /start · 85 gap lines
"""

# ═══════════════════════════════════════════
# AUTO PIP INSTALL
# ═══════════════════════════════════════════
import subprocess, sys

def _ensure_dependencies():
    try:
        import aiogram  # noqa
        return
    except ImportError:
        pass
    print("📦 Installing aiogram==3.15.0 ...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "aiogram==3.15.0", "--quiet", "--no-warn-script-location"
        ])
        print("✅ aiogram installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ pip install failed: {e}")
        sys.exit(1)

_ensure_dependencies()

# ═══════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════
import asyncio, os, re, json, time, random, signal, logging, threading
from datetime import datetime
from typing import Dict, List
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatType
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    TelegramRetryAfter, TelegramNetworkError,
    TelegramBadRequest, TelegramForbiddenError,
)

# ═══════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

START_TIME = time.time()
SHUTDOWN_FLAG = False

# ═══════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = (
            f'{{"ok":true,"bots":{len(BOT_POOL)},'
            f'"nc":{len(NC_TASKS)},"spam":{len(SPAM_TASKS)},'
            f'"clock":{len(CLOCK_TASKS)},"reply":{len(REPLY_TASKS)},'
            f'"uptime":{int(time.time()-START_TIME)}}}'
        )
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(payload.encode())

    def log_message(self, *args):
        return

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    try:
        HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()
    except Exception as e:
        logger.warning(f"Health check failed: {e}")

# ═══════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════
PRIMARY_OWNER = 8319293263
ADMIN_IDS = {8319293263, 7461426678}
ADMIN_FILE = "admins.json"
PACE = 0.01

BOT_TOKENS = [
    "9051518442:AAEEaqDOjLIBD10U96r8b5P1-RBoaL-t7hQ",
    "8877796256:AAEdxMsBwBKIpezepvQgA_FabCKpwfOjPz4",
    "8790500982:AAGAl4T3URnvWgGewSn4j4hilGEiwwGG26M",
    "8905270291:AAHvjT5aWUW-PTBHuv8k-DUtvdH7ffDsDcs",
    "8980868545:AAGyNyLW96NBhHqsomFIi9Fg8KpRKbadZ3A",
    "8545475609:AAFjlxrmXm3r0RPR4DH9u1yUHBEg_hFNoYg",
    "8615435529:AAE2-1BZNiG7Aq-6pWewpEH2yecJiXaAyh4",
    "8985748303:AAFyOa0Ram-hw4HCwncw6Xwqmg_RZfPYRnA",
    "8911264155:AAHg0xNTboltvdNkMgxsjDIK-JQF4lFZNqA",
    "8927277234:AAGy723Ul5O_NKxXx17dGLj1kqhQG1MpR1M",
]
BOT_TOKENS = [t.strip() for t in BOT_TOKENS if t and ":" in t]

if not BOT_TOKENS:
    logger.error("❌ No valid tokens!")
    raise SystemExit(1)

# ═══════════════════════════════════════════
# ADMIN PERSISTENCE
# ═══════════════════════════════════════════
def _load_admins():
    global ADMIN_IDS
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, "r") as f:
                data = json.load(f)
                loaded = set(int(x) for x in data.get("admins", []))
                loaded.add(PRIMARY_OWNER)
                ADMIN_IDS = loaded
                logger.info(f"📂 Admins loaded: {sorted(ADMIN_IDS)}")
    except Exception as e:
        logger.warning(f"Admin load failed: {e}")

def _save_admins():
    try:
        with open(ADMIN_FILE, "w") as f:
            json.dump({"admins": sorted(ADMIN_IDS)}, f)
    except Exception as e:
        logger.warning(f"Admin save failed: {e}")

# ═══════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════
BOT_POOL: List[Bot] = []
BOT_USERNAMES: Dict[int, str] = {}
BOT_RESTART_COUNT: Dict[int, int] = {}

NC_TASKS:      Dict[int, List[asyncio.Task]] = {}
ENC_TASKS:     Dict[int, List[asyncio.Task]] = {}
SPAM_TASKS:    Dict[int, asyncio.Task] = {}
CLOCK_TASKS:   Dict[int, asyncio.Task] = {}
REPLY_TASKS:   Dict[int, asyncio.Task] = {}
REPLY_TARGETS: Dict[int, str] = {}
PENDING_REPLIES: Dict[int, List[int]] = {}

SPAM_INFO:     Dict[int, dict] = {}
CLOCK_INFO:    Dict[int, dict] = {}

LOCKS:         Dict[int, asyncio.Lock] = {}

def get_lock(chat_id):
    if chat_id not in LOCKS:
        LOCKS[chat_id] = asyncio.Lock()
    return LOCKS[chat_id]

def is_owner(uid): return uid in ADMIN_IDS

# ═══════════════════════════════════════════
# FANCY FONT
# ═══════════════════════════════════════════
_FANCY = {
    'A':'𝐀','B':'𝐁','C':'𝐂','D':'𝐃','E':'𝐄','F':'𝐅','G':'𝐆','H':'𝐇',
    'I':'𝐈','J':'𝐉','K':'𝐊','L':'𝐋','M':'𝐌','N':'𝐍','O':'𝐎','P':'𝐏',
    'Q':'𝐐','R':'𝐑','S':'𝐒','T':'𝐓','U':'𝐔','V':'𝐕','W':'𝐖','X':'𝐗',
    'Y':'𝐘','Z':'𝐙',
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ',
    'j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ',
    's':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ',
}
def fancy(t): return "".join(_FANCY.get(c, c) for c in str(t))

# ═══════════════════════════════════════════
# SPAM CATEGORIES
# ═══════════════════════════════════════════
SPAM_CATEGORIES = [
    ("Hearts",   ["❤️","🧡","💛","💚","💙","💜","🤎","🖤","🤍","🩷","🩵","🩶"]),
    ("Colors",   ["🔴","🟠","🟡","🟢","🔵","🟣","🟤","⚫","⚪"]),
    ("Box",      ["🟥","🟧","🟨","🟩","🟦","🟪","🟫","⬛","⬜"]),
    ("Fire",     ["🔥","💥","✨","🌟","⭐","💫","☄️","🌠","🎇","🎆","⚡","🌩️","🌪️","❄️","🌊","💧"]),
    ("Skull",    ["💀","☠️","👻","👽","👾","🤖","👹","👺","🧟","🧛"]),
    ("Evil",     ["😈","👿","😡","😠","🤬","🤯","😤","😾","💢","🗯️","💨","🖕","👊","✊"]),
    ("Sad",      ["😭","😢","😥","😓","😞","😔","😟","🙁","☹️","😩","😫","🥺","😿","💔"]),
    ("Happy",    ["😂","🤣","😆","😅","😁","😄","😃","😀","🙂","😊","😇","🥰","😍","🤩","😘"]),
    ("Cool",     ["😎","🤓","🧐","🤠","🥳","🥸","🫡","🤫","🤔","😏","😒","🙄","😬","😑","😐"]),
    ("Pastel",   ["🩵","🩷","🩶","🪼","🪩","🪷","🫟","🌹","🥀","🌸","💐","🌷","🌺","🌻","🌼"]),
    ("Nature",   ["🌈","☀️","🌤️","⛅","🌥️","☁️","🌧️","⛈️","🌨️","🍃","🍂","🍁","🍄","🌵","🌴","🌳","🌱","🍀"]),
    ("Animals",  ["🦋","🐛","🐜","🐝","🪲","🐞","🦗","🕷️","🦂","🐢","🐍","🦎","🐊","🐅","🐆","🦓","🦍","🐘","🦒","🦘","🐎","🦌","🐕","🐈","🐓","🦃","🦚","🦜"]),
    ("Sea",      ["🐳","🐋","🐬","🦭","🐟","🐠","🐡","🦈","🐙","🐚","🪸","🦀","🦞","🦐","🦑","🐌"]),
    ("Mythical", ["🐉","🐲","🦕","🦖","🦄","🧚","🧜","🧞"]),
    ("Fruits",   ["🍏","🍎","🍐","🍊","🍋","🍌","🍉","🍇","🍓","🫐","🍈","🍒","🍑","🥭","🍍","🥝"]),
    ("Food",     ["🍔","🍟","🍕","🌭","🥪","🥙","🌮","🌯","🥗","🍝","🍜","🍲","🍛","🍣","🍱","🍤"]),
    ("Sweets",   ["🍰","🎂","🧁","🍮","🍭","🍬","🍫","🍿","🍩","🍪","🌰","🥜","🍯","☕","🍵","🧋"]),
    ("Games",    ["🎮","🕹️","🎲","♟️","🎯","🎳","🎰","🧩","⚽","🏀","🏈","⚾","🎾","🏐","🎱","🎣"]),
    ("Art",      ["🎨","🖌️","🖍️","✏️","📝","🎭","🎬","🎤","🎧","🎼","🎹","🥁","🎷","🎺","🎸","🎻"]),
    ("Objects",  ["💎","⚙️","⛓️","⚔️","🛡️","🔮","🎀","🧿","📿","🕯️","🔦","💡","🔭","🔬","📡","🧭","🔑"]),
    ("Weapons",  ["🗡️","🔪","🪓","🔫","💣","🧨","🔨","⚒️","🛠️","⛏️","🪚"]),
    ("Girly",    ["👑","💄","💅","🧸","🪆","🎁","🎈","🎉","🎊"]),
    ("Gothic",   ["🦇","🌑","🌚","⚰️","🪦","⚱️"]),
]
SPAM_TOTAL_ROWS = len(SPAM_CATEGORIES)

CLOCK_ROW = [
    "🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚","🕛",
    "🕜","🕝","🕞","🕟","🕠","🕡","🕢","🕣","🕤","🕥","🕦","🕧",
]

# ═══════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════
SPAM_BODY        = fancy("#KI #MAA #BHEN #KO #KUTTIYA #BANA #KAR #CHODUGA ¿?࿐")
CLOCK_BODY_FANCY = fancy("#Tɪᴍᴇ #Dɪᴋʜᴀᴛᴇ #Dɪᴋʜᴀᴛᴇ #Tᴇʀɪ #Mᴀ #Cʜᴏᴅᴜ #Mᴀᴅᴀʀᴄʜxᴅ")

CLOCK_GAP_LINES = 85
SPAM_GAP_LINES  = 85

def build_spam_message(emoji: str, name: str, variant: int = 1) -> str:
    if variant == 2:
        now = datetime.now().strftime("%I:%M:%S %p")
        block = f"<{emoji}> #{name} {CLOCK_BODY_FANCY}"
        return f"🕐 {now}\n{block}" + ("\n" * CLOCK_GAP_LINES) + block
    head = f"^{emoji}^  #{name} {SPAM_BODY}"
    tail = f"#{name} {SPAM_BODY}  ^{emoji}^"
    return head + ("\n" * SPAM_GAP_LINES) + tail

def category_at(n: int):
    return SPAM_CATEGORIES[(max(1, n) - 1) % SPAM_TOTAL_ROWS]

# ═══════════════════════════════════════════
# NC TITLE BUILDER
# ═══════════════════════════════════════════
FILL_CHAR = "𒐫"
FILL_COST = 2
TITLE_MAX = 255

def utf16_len(s: str) -> int:
    return sum(2 if ord(c) > 0xFFFF else 1 for c in s)

def build_nc_title(text: str) -> str:
    while utf16_len(text) > TITLE_MAX - FILL_COST:
        text = text[:-1]
    remaining = TITLE_MAX - utf16_len(text)
    fill_count = remaining // FILL_COST
    result = text + (FILL_CHAR * fill_count)
    while utf16_len(result) > TITLE_MAX:
        result = result[:-1]
    return result

# ═══════════════════════════════════════════
# NC PRESETS
# ═══════════════════════════════════════════
NAME_CHANGE_MESSAGES = [
    "{target} TERI BEHEN KI GAAND ME SUAR KA LUND",
    "{target} TERI BEHEN KO 100 KUTTO NE CHODA",
    "{target} TERI BEHEN KI GAAND MAR DIYA",
    "{target} TERI BEHEN KO RANDI BANA DIYA",
    "{target} TERI BEHEN KI GAAND ME 100 LUND",
    "{target} TERI BEHEN KI GAAND ME BAT",
    "{target} TERI BEHEN KI CHUT ME AAG",
    "{target} TERI BEHEN KI GAAND ME PATHAR",
    "{target} TERI BEHEN KO GANG BANG KARWA DIYA",
    "{target} TERI BEHEN KI CHUT ME SABKA LUND",
    "{target} TERI BUA KI CHUT ME HATHI KA LUND",
    "{target} TERI MASI KI GAAND MAR DIYA",
    "{target} TERI NANI KI CHUT ME AAG",
    "{target} TERI DADI KO KUTTA CHOD RAHA",
    "{target} TERI MAA KO BHAINS CHOD GAYA",
    "{target} TERE GHAR KI SAB RANDI",
    "{target} TERE PARIWAR KI SAB RANDI",
    "{target} TERI 7 PUSHT RANDI",
    "{target} TERI 7 PUSHT BHOSDIKE",
    "{target} TERI BEHEN KI GAAND ME KUTTE KA LUND",
    "{target} TERI BEHEN KI GAAND ME HATHI KA LUND",
    "{target} TERI BEHEN KO KUTTA CHODA",
    "{target} TERI BEHEN KO SUAR CHODA",
    "{target} TERI BEHEN KO BANDAR CHODA",
    "{target} TERI BEHEN KO SABNE CHODA",
    "{target} TERI BEHEN KO PURI BASTI NE CHODA",
    "{target} TERI MAA KI GAAND",
    "{target} TERI MAA KI GAAND ME LUND",
    "{target} TERI MAA KI GAAND MAR DIYA",
    "{target} TERI MAA KI GAAND ME BAT",
    "{target} TERI MAA KI GAAND ME KELA",
    "{target} TERI MAA KI GAAND ME KHIRA",
    "{target} TERI MAA KI GAAND ME HATHI KA LUND",
    "{target} TERI MAA KI GAAND ME SUAR KA LUND",
    "{target} TERI MAA KI GAAND ME SABKA LUND",
    "{target} TERI MAA KI GAAND ME PURI BASTI KA LUND",
    "{target} TERI MAA KO KUTTA CHODA",
    "{target} TERI MAA KO SUAR CHODA",
    "{target} TERI MAA KO BANDAR CHODA",
    "{target} TERI MAA KO BHAINS CHODA",
    "{target} TERI MAA KO HATHI CHODA",
    "{target} TERI MAA KO GADHA CHODA",
    "{target} TERI MAA KO BHOOT CHODA",
    "{target} TERI MAA KO SABNE CHODA",
    "{target} TERI MAA KO PURI BASTI NE CHODA",
    "{target} TERI MAA RANDI",
    "{target} TERI GAAND ME LUND GUS GAYA",
    "{target} TERI GAAND ME KELA GUS GAYA",
    "{target} TERI GAAND MAR DIYA",
    "{target} TERI GAAND ME BAT",
    "{target} TERI GAAND ME 100 LUND",
    "{target} TERI GAAND ME SABKA LUND",
    "{target} TERI GAAND ME HATHI KA LUND",
    "{target} TERI GAAND ME SUAR KA LUND",
    "{target} TERI GAAND ME KUTTE KA LUND",
    "{target} TERI GAAND ME BHOOT KA LUND",
    "{target} TERI GAAND ME BANDAR KA LUND",
    "{target} TERI GAAND ME AAG",
    "{target} TERI GAAND ME PURI BASTI KA LUND",
    "{target} TERI CHUT ME KEEDA",
    "{target} TERI CHUT ME AAG",
    "{target} TERI CHUT ME BAT",
    "{target} TERI CHUT ME 100 LUND",
    "{target} TERI CHUT ME PURI BASTI KA LUND",
    "{target} TU RANDI KA BACHCHA",
    "{target} TU KUTTA KA BACHCHA",
    "{target} TU SUAR KA BACHCHA",
    "{target} TU HARAMI KA BACHCHA",
    "{target} TU NAJAYAZ KA BACHCHA",
    "{target} TU BHOOT KA BACHCHA",
    "{target} TU BANDAR KA BACHCHA",
    "{target} TU BHAINS KA BACHCHA",
    "{target} TU GADHA KA BACHCHA",
    "{target} TU MUTTI KA BACHCHA",
    "{target} RANDI KAHAN CHALI",
    "{target} RANDI KE BACHHE",
    "{target} RANDI KI AULAAD",
    "{target} RANDI KI NANHI",
    "{target} RANDI KA BHAI",
    "{target} LUND CHOOS",
    "{target} LUND CHOOSNE WALA",
    "{target} LUND CHOOSNE WALI",
    "{target} LUND KA BHOOKHA",
    "{target} LUND KI PYAASI",
    "{target} LUND KA KEEDA",
    "{target} TERA LUND CHOTA",
    "{target} TERA LUND TUTA HUA",
    "{target} TERA LUND KAAT DIYA",
    "{target} TERA LUND ME KEEDA",
    "{target} TERA LUND ME AAG",
    "{target} GANDU KAHAN HAI",
    "{target} GANDU KE BACHHE",
    "{target} GANDU KI AULAAD",
    "{target} GANDU NUMBER 1",
    "{target} BHOSDIKE KAHAN HAI",
    "{target} BHOSDIKE KI AULAAD",
    "{target} BHOSDIKE KA BHAI",
    "{target} MADARCHOD KAHAN HAI",
    "{target} MADARCHOD KI AULAAD",
    "{target} CHUTIYA KAHAN HAI",
    "{target} CHUTIYE KI AULAAD",
    "{target} CHUTIYE KA BHAI",
    "{target} TERA BAAP BHOSDIKA",
    "{target} TERA BHAI BHOSDIKA",
    "{target} TERA CHACHA BHOSDIKA",
    "{target} TERA MAMA BHOSDIKA",
    "{target} TERA TAU BHOSDIKA",
    "{target} TERA DADA BHOSDIKA",
    "{target} TERA NANA BHOSDIKA",
    "{target} TERA BETA BHOSDIKA",
    "{target} TERA POTTA BHOSDIKA",
    "{target} TERA KHANDAAN RANDI",
    "{target} TERA KHANDAAN BHOSDIKA",
    "{target} TERA KHANDAAN MADARCHOD",
    "{target} TERA KHANDAAN CHUTIYA",
    "{target} TERA KHANDAAN GANDU",
    "{target} TERI AULAAD RANDI",
    "{target} TERI AULAAD KUTTI",
    "{target} TERI AULAAD SUAR",
    "{target} TERI AULAAD BHOSDIKE",
    "{target} TERI AULAAD MADARCHOD",
    "{target} TERI 7 PUSHT MADARCHOD",
    "{target} TERI 7 PUSHT KUTTI",
    "{target} TERI 7 PUSHT SUAR",
    "{target} TERI SHAKAL BHOOT JAISI",
    "{target} TERI SHAKAL SUAR JAISI",
    "{target} TERI SHAKAL KUTTE JAISI",
    "{target} TERI SHAKAL BANDAR JAISI",
    "{target} TERI SHAKAL GADHE JAISI",
    "{target} TU LANGDA KA BACHCHA",
    "{target} TU ANDHA KA BACHCHA",
    "{target} TU BAHRA KA BACHCHA",
    "{target} TU GUNGA KA BACHCHA",
    "{target} TU KUBDA KA BACHCHA",
    "{target} TU PAGAL KA BACHCHA",
    "{target} TU MENTAL KA BACHCHA",
    "{target} TU SCHIZOPHRENIC",
    "{target} TU DEPRESSED KA KEEDA",
    "{target} TU SUICIDAL KA BACHCHA",
    "{target} TU PSYCHO KA BACHCHA",
    "{target} TU SOCIOPATH",
    "{target} TU PSYCHOPATH",
    "{target} TU MANIAC",
    "{target} TU LUNATIC",
    "{target} TERI MAA KO AIDS HAI",
    "{target} TERI BEHEN KO GONORRHEA HAI",
    "{target} TERI MAA KO SYPHILIS HAI",
    "{target} TERE KHANDAAN ME HERPES",
    "{target} TERI MAA KI GAAND ME CANCER",
    "{target} TERI BEHEN KI GAAND ME TUMOR",
    "{target} TU TB KA KEEDA",
    "{target} TU POLIO KA BACHCHA",
    "{target} TU COVID KA AULAAD",
    "{target} TU PLAGUE KA KEEDA",
    "{target} TERI MAA KI GAAND ME BLACK HOLE",
    "{target} TERI MAA KI GAAND ME GALAXY",
    "{target} TERI MAA KI GAAND ME UNIVERSE",
    "{target} TERI MAA KI GAAND ME MULTIVERSE",
    "{target} TERI MAA KI GAAND ME TIME MACHINE",
    "{target} TERI MAA KI GAAND ME ALIEN KA LUND",
    "{target} TERI MAA KI GAAND ME GOD KA LUND",
    "{target} TERI MAA KI GAAND ME DEVIL KA LUND",
    "{target} TERI MAA KI GAAND ME SABKA LUND",
    "{target} TERI MAA KI GAAND ME PURI DUNIYA BASI HAI",
    "{target} TU 404 NOT FOUND",
    "{target} TU BLUE SCREEN OF DEATH",
    "{target} TU VIRUS KA BACHCHA",
    "{target} TU TROJAN HORSE",
    "{target} TU RANSOMWARE KA BACHCHA",
    "{target} TU PHISHING KA KEEDA",
    "{target} TU SPAM KA AULAAD",
    "{target} TU MALWARE KA BACHCHA",
    "{target} TU DDOS ATTACK",
    "{target} TU BOTNET KA KEEDA",
]
# ═══════════════════════════════════════════
# EMOJI ROTATE LIST
# ═══════════════════════════════════════════
EMOJI_LIST = [
    "🔥","⚡","✨","⭐","💫","🌟","☀️","🌙","💥","💢","🎯","💎","👑","🎨","🎭","🎵",
    "🎶","🎉","🎊","🎈","🎁","🔮","♨️","⚜️","🍀","🌸","🌹","🌊","🦋","❄️","💧","🌈",
    "🍁","🍂","🪐","🌠","🌌","🔱","⚔️","🛡️","❤️","🩷","🧡","💛","💚","💙","🩵","💜",
]

# ═══════════════════════════════════════════
# REPLY MESSAGES
# ═══════════════════════════════════════════
REPLY_MESSAGES = [
    "{target} TERI BEHEN KI GAAND ME SUAR KA LUND",
    "{target} TERI BEHEN KO 100 KUTTO NE CHODA",
    "{target} TERI BEHEN KI GAAND MAR DIYA",
    "{target} TERI BEHEN KO RANDI BANA DIYA",
    "{target} TERI BUA KI CHUT ME HATHI KA LUND",
    "{target} TERI MASI KI GAAND MAR DIYA",
    "{target} TERI DADI KO KUTTA CHOD RAHA",
    "{target} TERE GHAR KI SAB RANDI",
    "{target} TERI 7 PUSHT RANDI",
    "{target} TERI BEHEN KO KUTTA CHODA",
    "{target} TERI BEHEN KO SUAR CHODA",
    "{target} TERI BEHEN KO SABNE CHODA",
    "{target} TERI MAA KI GAAND ME LUND",
    "{target} TERI MAA KI GAAND MAR DIYA",
    "{target} TERI MAA KI GAAND ME BAT",
    "{target} TERI MAA KI GAAND ME HATHI KA LUND",
    "{target} TERI MAA KI GAAND ME SABKA LUND",
    "{target} TERI MAA KO KUTTA CHODA",
    "{target} TERI MAA KO SUAR CHODA",
    "{target} TERI MAA KO SABNE CHODA",
    "{target} TERI MAA RANDI",
    "{target} TERI GAAND ME LUND GUS GAYA",
    "{target} TERI GAAND MAR DIYA",
    "{target} TERI GAAND ME 100 LUND",
    "{target} TERI GAAND ME AAG",
    "{target} TERI CHUT ME KEEDA",
    "{target} TERI CHUT ME AAG",
    "{target} TU RANDI KA BACHCHA",
    "{target} TU KUTTA KA BACHCHA",
    "{target} TU SUAR KA BACHCHA",
    "{target} TU HARAMI KA BACHCHA",
    "{target} TU NAJAYAZ KA BACHCHA",
    "{target} TU BHOOT KA BACHCHA",
    "{target} TU BANDAR KA BACHCHA",
    "{target} RANDI KAHAN CHALI",
    "{target} RANDI KE BACHHE",
    "{target} RANDI KI AULAAD",
    "{target} LUND CHOOS",
    "{target} LUND CHOOSNE WALA",
    "{target} TERA LUND CHOTA",
    "{target} GANDU KAHAN HAI",
    "{target} GANDU KI AULAAD",
    "{target} BHOSDIKE KAHAN HAI",
    "{target} BHOSDIKE KI AULAAD",
    "{target} MADARCHOD KAHAN HAI",
    "{target} MADARCHOD KI AULAAD",
    "{target} CHUTIYA KAHAN HAI",
    "{target} CHUTIYE KI AULAAD",
    "{target} TERA BAAP BHOSDIKA",
    "{target} TERA BHAI BHOSDIKA",
    "{target} TERA DADA BHOSDIKA",
    "{target} TERA KHANDAAN RANDI",
    "{target} TERA KHANDAAN BHOSDIKA",
    "{target} TERI AULAAD RANDI",
    "{target} TERI 7 PUSHT MADARCHOD",
    "{target} TERI SHAKAL BHOOT JAISI",
    "{target} TERI SHAKAL SUAR JAISI",
    "{target} TU LANGDA KA BACHCHA",
    "{target} TU PAGAL KA BACHCHA",
    "{target} TU SCHIZOPHRENIC",
    "{target} TERI MAA KO AIDS HAI",
    "{target} TERI BEHEN KO GONORRHEA HAI",
    "{target} TU TB KA KEEDA",
]

# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════
def fmt_uptime():
    d = int(time.time() - START_TIME)
    h, r = divmod(d, 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m}m {s}s"

async def _safe_send(bot, chat_id, text, retries=3):
    if len(text) > 4000:
        text = text[:4000]
    for attempt in range(retries):
        try:
            await bot.send_message(
                chat_id, text, parse_mode=None,
                disable_web_page_preview=True,
            )
            return True
        except TelegramRetryAfter as ra:
            await asyncio.sleep(ra.retry_after + 0.5)
        except TelegramNetworkError:
            await asyncio.sleep(1)
        except (TelegramForbiddenError, TelegramBadRequest):
            return False
        except Exception:
            await asyncio.sleep(0.5)
    return False

# ═══════════════════════════════════════════
# WORKERS
# ═══════════════════════════════════════════
async def nc_loop(chat_id, base_name, thread_id):
    idx = 0
    n = len(NAME_CHANGE_MESSAGES)
    logger.info(f"NC#{thread_id} cid={chat_id}")
    try:
        while not SHUTDOWN_FLAG:
            template = NAME_CHANGE_MESSAGES[idx % n]
            gaali = template.format(target=base_name)
            title = build_nc_title(gaali)
            success = False
            for bot in BOT_POOL:
                try:
                    await bot.set_chat_title(chat_id=chat_id, title=title)
                    success = True
                    break
                except TelegramRetryAfter:
                    continue
                except (TelegramBadRequest, TelegramForbiddenError):
                    continue
                except Exception:
                    continue
            idx += 1
            await asyncio.sleep(PACE if success else 0.5)
    except asyncio.CancelledError:
        logger.info(f"NC#{thread_id} cid={chat_id} stopped")

async def emoji_loop(chat_id, text, thread_id):
    idx = 0
    n = len(EMOJI_LIST)
    try:
        while not SHUTDOWN_FLAG:
            e = EMOJI_LIST[idx % n]
            title = f"{e} {text} {e}"[:255]
            for bot in BOT_POOL:
                try:
                    await bot.set_chat_title(chat_id=chat_id, title=title)
                    break
                except TelegramRetryAfter:
                    continue
                except Exception:
                    continue
            idx += 1
            await asyncio.sleep(PACE)
    except asyncio.CancelledError:
        pass

async def category_spam_worker(chat_id, cat_name, emojis, name):
    idx = 0
    n = len(emojis)
    try:
        while not SHUTDOWN_FLAG:
            e = emojis[idx % n]
            SPAM_INFO[chat_id] = {"cat": cat_name, "idx": idx % n, "total": n, "emoji": e}
            idx += 1
            text = build_spam_message(e, name, variant=1)
            await asyncio.gather(
                *[_safe_send(bot, chat_id, text) for bot in BOT_POOL],
                return_exceptions=True,
            )
            await asyncio.sleep(PACE)
    except asyncio.CancelledError:
        pass

async def clock_spam_worker(chat_id, name):
    idx = 0
    n = len(CLOCK_ROW)
    try:
        while not SHUTDOWN_FLAG:
            e = CLOCK_ROW[idx % n]
            CLOCK_INFO[chat_id] = {"cat": "Clocks", "idx": idx % n, "total": n, "emoji": e}
            idx += 1
            text = build_spam_message(e, name, variant=2)
            await asyncio.gather(
                *[_safe_send(bot, chat_id, text) for bot in BOT_POOL],
                return_exceptions=True,
            )
            await asyncio.sleep(PACE)
    except asyncio.CancelledError:
        pass

async def reply_loop(chat_id, target_name):
    try:
        while not SHUTDOWN_FLAG:
            pending = PENDING_REPLIES.get(chat_id, [])
            if pending:
                async with get_lock(chat_id):
                    msgs = PENDING_REPLIES.get(chat_id, []).copy()
                    PENDING_REPLIES[chat_id] = []
                for msg_id in msgs:
                    try:
                        reply = random.choice(REPLY_MESSAGES).format(target=target_name)
                        if BOT_POOL:
                            await BOT_POOL[0].send_message(
                                chat_id=chat_id, text=reply, reply_to_message_id=msg_id
                            )
                        await asyncio.sleep(PACE)
                    except Exception:
                        pass
            else:
                await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        pass
                
# ═══════════════════════════════════════════
# STOP HELPERS
# ═══════════════════════════════════════════
def stop_nc(chat_id):
    for t in NC_TASKS.pop(chat_id, []):
        t.cancel()

def stop_enc(chat_id):
    for t in ENC_TASKS.pop(chat_id, []):
        t.cancel()

def stop_spam(chat_id):
    t = SPAM_TASKS.pop(chat_id, None)
    if t: t.cancel()
    SPAM_INFO.pop(chat_id, None)

def stop_clock(chat_id):
    t = CLOCK_TASKS.pop(chat_id, None)
    if t: t.cancel()
    CLOCK_INFO.pop(chat_id, None)

def stop_reply(chat_id):
    t = REPLY_TASKS.pop(chat_id, None)
    if t: t.cancel()
    REPLY_TARGETS.pop(chat_id, None)
    PENDING_REPLIES.pop(chat_id, None)

def stop_chat_all(chat_id):
    stop_nc(chat_id)
    stop_enc(chat_id)
    stop_spam(chat_id)
    stop_clock(chat_id)
    stop_reply(chat_id)

def stop_global():
    all_cids = set(NC_TASKS) | set(ENC_TASKS) | set(SPAM_TASKS) | set(CLOCK_TASKS) | set(REPLY_TASKS)
    for cid in all_cids:
        stop_chat_all(cid)
    return len(all_cids)

# ═══════════════════════════════════════════
# BOT INSTANCE
# ═══════════════════════════════════════════
class BotInstance:
    def __init__(self):
        self._spam_re = re.compile(r"^/spam(\d+)(?:\s+(.+))?$", re.IGNORECASE)

    async def check_owner(self, message):
        uid = message.from_user.id if message.from_user else None
        if not uid or not is_owner(uid):
            logger.info(f"🚫 /{message.text.split()[0] if message.text else '?'} blocked: uid={uid}")
            try:
                await message.answer("⛔ Owner only")
            except Exception as e:
                logger.warning(f"Owner reject send failed: {e}")
            return False
        return True

    # ────────── /start — OWNER ONLY · NO HTML ──────────
    async def start(self, message: Message):
        if not await self.check_owner(message):
            return

        text = (
            "𓆩 𝐃𝐄𝐕 𝐁𝐎𝐓 𓆪\n\n"
            "🏷️ 𝐍𝐂\n"
            "/nc1 [target] — Preset NC loop\n"
            "/enc [text] — Emoji rotate\n"
            "/stopnc — Stop NC\n"
            "/stopenc — Stop ENC\n\n"
            "💣 𝐒𝐏𝐀𝐌\n"
            "/spam[N] [name] — Category N spam\n"
            "/clockspam [name] — Clock template\n"
            "/rows — List categories\n"
            "/stopspam — Stop spam\n"
            "/stopclock — Stop clock\n\n"
            "🎯 𝐎𝐓𝐇𝐄𝐑\n"
            "/target [name] — NC + spam combo\n"
            "/reply [target] — Reply loop\n"
            "/stopreply — Stop reply\n\n"
            "🛑 𝐒𝐓𝐎𝐏\n"
            "/stop — ALL loops (this chat)\n"
            "/stopall — ALL loops (global)\n\n"
            "👥 𝐀𝐃𝐌𝐈𝐍\n"
            "/addadmin [id] — Add admin\n"
            "/rmadmin [id] — Remove admin\n"
            "/admins — List admins\n\n"
            "📊 𝐈𝐍𝐅𝐎\n"
            "/ping — Latency\n"
            "/status — Bots + uptime\n\n"
            "🔒 Owner only commands"
        )

        try:
            await message.answer(text, parse_mode=None)
            logger.info(f"✅ /start sent to uid={message.from_user.id}")
        except Exception as e:
            logger.error(f"❌ /start FAILED for uid={message.from_user.id}: {e}")
            try:
                await message.answer("⚠️ Menu error — check logs")
            except Exception:
                pass

    # ────────── NC ──────────
    async def nc_command(self, message: Message, command: CommandObject):
        if not await self.check_owner(message): return
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.answer("Groups only!", parse_mode=None)
        if not command.args:
            return await message.answer("Usage: /nc1 [target]", parse_mode=None)
        chat_id = message.chat.id
        stop_nc(chat_id)
        NC_TASKS[chat_id] = [asyncio.create_task(nc_loop(chat_id, command.args, 1))]
        await message.answer(
            f"⚡ 𝐃𝐄𝐕 𝐁𝐎𝐓 · NC started\n"
            f"Target: {command.args}\n"
            f"Pace: {PACE}s · Bots: {len(BOT_POOL)}\n"
            f"Fill: {FILL_CHAR} (255 max)\n"
            f"Stop: /stopnc",
            parse_mode=None,
        )

    async def enc_command(self, message: Message, command: CommandObject):
        if not await self.check_owner(message): return
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.answer("Groups only!", parse_mode=None)
        if not command.args:
            return await message.answer("Usage: /enc [text]", parse_mode=None)
        chat_id = message.chat.id
        stop_enc(chat_id)
        ENC_TASKS[chat_id] = [asyncio.create_task(emoji_loop(chat_id, command.args, 1))]
        await message.answer("✨ ENC started · Stop: /stopenc", parse_mode=None)

    async def spam_n_command(self, message: Message):
        if not await self.check_owner(message): return
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.answer("Groups only!", parse_mode=None)
        match = self._spam_re.match((message.text or "").strip())
        if not match:
            return await message.answer(
                f"Usage: /spam[N] [name]\nN = 1-{SPAM_TOTAL_ROWS}\nSee: /rows",
                parse_mode=None,
            )
        n = int(match.group(1))
        name = (match.group(2) or "").strip()
        if not 1 <= n <= SPAM_TOTAL_ROWS:
            return await message.answer(f"❌ N must be 1-{SPAM_TOTAL_ROWS}", parse_mode=None)
        if not name:
            return await message.answer(f"Usage: /spam{n} [name]", parse_mode=None)
        cat_name, emojis = category_at(n)
        chat_id = message.chat.id
        stop_spam(chat_id)
        SPAM_TASKS[chat_id] = asyncio.create_task(
            category_spam_worker(chat_id, cat_name, emojis, name[:50])
        )
        await message.answer(
            f"💣 SPAM LIVE\n"
            f"Category: {n} · {cat_name}\n"
            f"Name: {name[:50]}\n"
            f"Gap: {SPAM_GAP_LINES} lines\n"
            f"Stop: /stopspam",
            parse_mode=None,
        )

    async def clockspam_command(self, message: Message, command: CommandObject):
        if not await self.check_owner(message): return
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.answer("Groups only!", parse_mode=None)
        if not command.args:
            return await message.answer("Usage: /clockspam [name]", parse_mode=None)
        chat_id = message.chat.id
        stop_clock(chat_id)
        CLOCK_TASKS[chat_id] = asyncio.create_task(clock_spam_worker(chat_id, command.args[:50]))
        await message.answer("🕐 CLOCK SPAM LIVE · Stop: /stopclock", parse_mode=None)

    async def rows_command(self, message: Message, command: CommandObject):
        if not await self.check_owner(message): return
        if command.args and command.args.strip().isdigit():
            n = int(command.args.strip())
            if not 1 <= n <= SPAM_TOTAL_ROWS:
                return await message.answer(f"❌ N must be 1-{SPAM_TOTAL_ROWS}", parse_mode=None)
            cat_name, emojis = category_at(n)
            lines = [f"Row {n} · {cat_name} ({len(emojis)})\n"]
            chunk = []
            for e in emojis:
                chunk.append(e)
                if len(chunk) == 10:
                    lines.append(" ".join(chunk))
                    chunk = []
            if chunk: lines.append(" ".join(chunk))
            lines.append(f"\nUse: /spam{n} [name]")
            return await message.answer("\n".join(lines), parse_mode=None)
        lines = [f"📋 CATEGORIES (1-{SPAM_TOTAL_ROWS})\n"]
        for i, (name, emojis) in enumerate(SPAM_CATEGORIES, 1):
            lines.append(f"  {i:>2}. {name} ({len(emojis)})")
        await message.answer("\n".join(lines), parse_mode=None)

    async def target_command(self, message: Message, command: CommandObject):
        if not await self.check_owner(message): return
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await message.answer("Groups only!", parse_mode=None)
        if not command.args:
            return await message.answer("Usage: /target [name]", parse_mode=None)
        chat_id = message.chat.id
        name = command.args[:50]
        stop_nc(chat_id); stop_spam(chat_id)
        NC_TASKS[chat_id] = [asyncio.create_task(nc_loop(chat_id, name, 1))]
        cat_name, emojis = category_at(1)
        SPAM_TASKS[chat_id] = asyncio.create_task(category_spam_worker(chat_id, cat_name, emojis, name))
        await message.answer("🎯 TARGET MODE · Stop: /stop", parse_mode=None)

    async def reply_command(self, message: Message, command: CommandObject):
        if not await self.check_owner(message): return
        if not command.args:
            return await message.answer("Usage: /reply [target]", parse_mode=None)
        chat_id = message.chat.id
        stop_reply(chat_id)
        REPLY_TARGETS[chat_id] = command.args
        PENDING_REPLIES[chat_id] = []
        REPLY_TASKS[chat_id] = asyncio.create_task(reply_loop(chat_id, command.args))
        await message.answer("💬 REPLY started · Stop: /stopreply", parse_mode=None)

    async def stopnc_cmd(self, m: Message):
        if not await self.check_owner(m): return
        was = m.chat.id in NC_TASKS
        stop_nc(m.chat.id)
        await m.answer("🛑 NC stopped" if was else "ℹ️ No NC running", parse_mode=None)

    async def stopenc_cmd(self, m: Message):
        if not await self.check_owner(m): return
        was = m.chat.id in ENC_TASKS
        stop_enc(m.chat.id)
        await m.answer("🛑 ENC stopped" if was else "ℹ️ No ENC running", parse_mode=None)

    async def stopspam_cmd(self, m: Message):
        if not await self.check_owner(m): return
        was = m.chat.id in SPAM_TASKS
        stop_spam(m.chat.id)
        await m.answer("🛑 SPAM stopped" if was else "ℹ️ No spam running", parse_mode=None)

    async def stopclock_cmd(self, m: Message):
        if not await self.check_owner(m): return
        was = m.chat.id in CLOCK_TASKS
        stop_clock(m.chat.id)
        await m.answer("🛑 CLOCK stopped" if was else "ℹ️ No clock running", parse_mode=None)

    async def stopreply_cmd(self, m: Message):
        if not await self.check_owner(m): return
        was = m.chat.id in REPLY_TASKS
        stop_reply(m.chat.id)
        await m.answer("🛑 REPLY stopped" if was else "ℹ️ No reply running", parse_mode=None)

    async def stop_cmd(self, m: Message):
        if not await self.check_owner(m): return
        cid = m.chat.id
        counts = {
            "nc": cid in NC_TASKS, "enc": cid in ENC_TASKS,
            "spam": cid in SPAM_TASKS, "clock": cid in CLOCK_TASKS,
            "reply": cid in REPLY_TASKS,
        }
        stop_chat_all(cid)
        stopped = [k.upper() for k, v in counts.items() if v]
        await m.answer(
            f"🛑 Stopped: {', '.join(stopped)}" if stopped else "ℹ️ Nothing running",
            parse_mode=None,
        )

    async def stopall_cmd(self, m: Message):
        if not await self.check_owner(m): return
        n_chats = stop_global()
        await m.answer(f"🛑 𝐆𝐋𝐎𝐁𝐀𝐋 𝐒𝐓𝐎𝐏 · {n_chats} chats cleared", parse_mode=None)

    async def ping_cmd(self, m: Message):
        if not await self.check_owner(m): return
        t0 = time.time()
        msg = await m.answer("🏓 pinging...", parse_mode=None)
        latency = (time.time() - t0) * 1000
        quality = "🟢 EXCELLENT" if latency < 200 else "🟡 GOOD" if latency < 500 else "🔴 SLOW"
        await msg.edit_text(
            f"🏓 𝐏𝐎𝐍𝐆\nLatency: {latency:.0f} ms\nQuality: {quality}\nBots: {len(BOT_POOL)}",
            parse_mode=None,
        )

    async def status_cmd(self, m: Message):
        if not await self.check_owner(m): return
        bot_list = "\n".join(
            f"  #{i+1} @{BOT_USERNAMES.get(b.id, 'unknown')}"
            for i, b in enumerate(BOT_POOL)
        ) if BOT_POOL else "  none"
        total_chats = len(set(NC_TASKS) | set(ENC_TASKS) | set(SPAM_TASKS) | set(CLOCK_TASKS) | set(REPLY_TASKS))
        await m.answer(
            f"📊 𝐒𝐓𝐀𝐓𝐔𝐒\n"
            f"Uptime: {fmt_uptime()}\n"
            f"Pace: {PACE}s\n"
            f"Gap: {SPAM_GAP_LINES} lines\n"
            f"Owners: {', '.join(str(x) for x in sorted(ADMIN_IDS))}\n\n"
            f"🤖 𝐁𝐎𝐓𝐒 ({len(BOT_POOL)})\n{bot_list}\n\n"
            f"🔥 𝐀𝐂𝐓𝐈𝐕𝐄\n"
            f"NC: {len(NC_TASKS)} · ENC: {len(ENC_TASKS)}\n"
            f"SPAM: {len(SPAM_TASKS)} · CLOCK: {len(CLOCK_TASKS)}\n"
            f"REPLY: {len(REPLY_TASKS)} · Total: {total_chats}",
            parse_mode=None,
        )

    async def collector(self, m: Message):
        if not m.text: return
        cid = m.chat.id
        if cid in REPLY_TARGETS:
            async with get_lock(cid):
                PENDING_REPLIES.setdefault(cid, []).append(m.message_id)

    # ────────── ADMIN MANAGEMENT ──────────
    async def addadmin_cmd(self, m: Message, command: CommandObject):
        if not m.from_user or not is_owner(m.from_user.id):
            return await m.answer("⛔ Owner only", parse_mode=None)

        target_id = None
        target_name = None
        if m.reply_to_message and m.reply_to_message.from_user:
            target_id = m.reply_to_message.from_user.id
            target_name = m.reply_to_message.from_user.first_name or str(target_id)
        elif command.args:
            arg = command.args.strip().split()[0].lstrip("@")
            if arg.isdigit():
                target_id = int(arg)
                target_name = arg
            else:
                return await m.answer("❌ Reply to user or give numeric ID", parse_mode=None)
        else:
            return await m.answer("Usage:\n/addadmin [id]\nOR reply + /addadmin", parse_mode=None)

        if target_id in ADMIN_IDS:
            return await m.answer(f"ℹ️ Already admin: {target_id}", parse_mode=None)

        ADMIN_IDS.add(target_id)
        _save_admins()
        logger.info(f"➕ Admin added: {target_id} by {m.from_user.id}")
        await m.answer(
            f"✅ 𝐀𝐃𝐌𝐈𝐍 𝐀𝐃𝐃𝐄𝐃\n"
            f"Name: {target_name}\n"
            f"ID: {target_id}\n"
            f"Total: {len(ADMIN_IDS)}",
            parse_mode=None,
        )

    async def rmadmin_cmd(self, m: Message, command: CommandObject):
        if not m.from_user or not is_owner(m.from_user.id):
            return await m.answer("⛔ Owner only", parse_mode=None)

        target_id = None
        target_name = None
        if m.reply_to_message and m.reply_to_message.from_user:
            target_id = m.reply_to_message.from_user.id
            target_name = m.reply_to_message.from_user.first_name or str(target_id)
        elif command.args:
            arg = command.args.strip().split()[0].lstrip("@")
            if arg.isdigit():
                target_id = int(arg)
                target_name = arg
            else:
                return await m.answer("❌ Reply to user or give numeric ID", parse_mode=None)
        else:
            return await m.answer("Usage:\n/rmadmin [id]\nOR reply + /rmadmin", parse_mode=None)

        if target_id == PRIMARY_OWNER:
            return await m.answer(f"🚫 Primary owner {PRIMARY_OWNER} protected", parse_mode=None)

        if target_id not in ADMIN_IDS:
            return await m.answer(f"ℹ️ Not admin: {target_id}", parse_mode=None)

        ADMIN_IDS.discard(target_id)
        _save_admins()
        logger.info(f"➖ Admin removed: {target_id} by {m.from_user.id}")
        await m.answer(
            f"🗑️ 𝐀𝐃𝐌𝐈𝐍 𝐑𝐄𝐌𝐎𝐕𝐄𝐃\n"
            f"Name: {target_name}\n"
            f"ID: {target_id}\n"
            f"Remaining: {len(ADMIN_IDS)}",
            parse_mode=None,
        )

    async def admins_cmd(self, m: Message):
        if not m.from_user or not is_owner(m.from_user.id):
            return await m.answer("⛔ Owner only", parse_mode=None)
        lines = ["👑 𝐀𝐃𝐌𝐈𝐍 𝐋𝐈𝐒𝐓\n━━━━━━━━━━━━━━"]
        for uid in sorted(ADMIN_IDS):
            tag = "👑 PRIMARY" if uid == PRIMARY_OWNER else "⭐ ADMIN"
            lines.append(f"  {tag}  {uid}")
        lines.append(f"\nTotal: {len(ADMIN_IDS)}")
        await m.answer("\n".join(lines), parse_mode=None)

# ═══════════════════════════════════════════
# DISPATCHER
# ═══════════════════════════════════════════
def create_dispatcher() -> Dispatcher:
    inst = BotInstance()
    r = Router()

    r.message.register(inst.start, Command("start", "help"))
    r.message.register(inst.ping_cmd, Command("ping"))
    r.message.register(inst.status_cmd, Command("status"))
    r.message.register(inst.nc_command, Command("nc", "nc1"))
    r.message.register(inst.enc_command, Command("enc"))
    r.message.register(inst.clockspam_command, Command("clockspam"))
    r.message.register(inst.rows_command, Command("rows"))
    r.message.register(inst.target_command, Command("target"))
    r.message.register(inst.reply_command, Command("reply"))
    r.message.register(inst.stopnc_cmd, Command("stopnc"))
    r.message.register(inst.stopenc_cmd, Command("stopenc"))
    r.message.register(inst.stopspam_cmd, Command("stopspam"))
    r.message.register(inst.stopclock_cmd, Command("stopclock"))
    r.message.register(inst.stopreply_cmd, Command("stopreply"))
    r.message.register(inst.stop_cmd, Command("stop"))
    r.message.register(inst.stopall_cmd, Command("stopall"))
    r.message.register(inst.addadmin_cmd, Command("addadmin"))
    r.message.register(inst.rmadmin_cmd, Command("rmadmin", "deladmin"))
    r.message.register(inst.admins_cmd, Command("admins", "adminlist"))
    r.message.register(inst.spam_n_command, F.text.regexp(r"^/spam\d+"))
    r.message.register(inst.collector, F.text)

    dp = Dispatcher()
    dp.include_router(r)
    return dp

# ═══════════════════════════════════════════
# BOT RUNNER — 🔥 NO HTML PARSE MODE
# ═══════════════════════════════════════════
async def run_bot(token: str, idx: int):
    # ✅ No DefaultBotProperties → no global HTML parse mode
    bot = Bot(token=token)
    dp = create_dispatcher()
    me = await bot.get_me()
    BOT_USERNAMES[bot.id] = me.username
    if bot not in BOT_POOL:
        BOT_POOL.append(bot)
    logger.info(f"✅ #{idx} @{me.username} (id:{bot.id})")
    await dp.start_polling(bot, drop_pending_updates=True)

async def supervised_bot(token: str, idx: int):
    attempt = 0
    while not SHUTDOWN_FLAG:
        attempt += 1
        BOT_RESTART_COUNT[idx] = BOT_RESTART_COUNT.get(idx, 0) + 1
        try:
            logger.info(f"🔁 Bot #{idx} starting (attempt {attempt})")
            await run_bot(token, idx)
        except asyncio.CancelledError:
            logger.info(f"🛑 Bot #{idx} cancelled")
            raise
        except Exception as e:
            logger.error(f"💥 Bot #{idx} crash: {e}")
        if SHUTDOWN_FLAG:
            break
        delay = min(5 * (2 ** (attempt - 1)), 60)
        logger.info(f"⏳ Bot #{idx} restarting in {delay}s")
        await asyncio.sleep(delay)

async def main():
    _load_admins()
    logger.info(f"🚀 DEV BOT · {len(BOT_TOKENS)} tokens · Owners {sorted(ADMIN_IDS)} · Pace {PACE}s · Fill {FILL_CHAR} · Gap {SPAM_GAP_LINES}")
    tasks = [asyncio.create_task(supervised_bot(t, i + 1)) for i, t in enumerate(BOT_TOKENS)]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

def _signal_handler(sig, frame):
    global SHUTDOWN_FLAG
    SHUTDOWN_FLAG = True
    logger.info(f"📴 Signal {sig} — shutting down")
    stop_global()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    threading.Thread(target=run_health_check, daemon=True).start()
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Shutdown complete")
