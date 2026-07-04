from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
from PIL import Image, ImageOps
from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
import base64
import json
import os
import time
import re
import unicodedata
import requests
import smtplib
from io import BytesIO
from uuid import uuid4
from difflib import SequenceMatcher
from email.message import EmailMessage
from html import escape
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
from functools import wraps
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from datetime import datetime, timedelta
from urllib.parse import urlparse

try:
    import stripe
except ImportError:
    stripe = None

from database import db
from models import (
    User,
    Product,
    ProductSubmission,
    ScanHistory,
    Favorite,
    CartItem,
    PriceObservation,
    SearchEvent,
    Subscription,
    FamilyProfile,
    UsageEvent,
)


OPEN_FOOD_FACTS_ALTERNATIVES_CACHE = {}
OPEN_FOOD_FACTS_PRODUCT_CACHE = {}
OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL = 10 * 60
OPEN_FOOD_FACTS_PRODUCT_CACHE_TTL = 60 * 60
PRODUCT_SEARCH_RESULT_CACHE = {}
PRODUCT_SEARCH_RESULT_CACHE_TTL = int(os.environ.get("PRODUCT_SEARCH_RESULT_CACHE_TTL", "900"))
OPEN_PRICES_CACHE = {}
OPEN_PRICES_CACHE_TTL = 30 * 60
AI_STATUS_CACHE = {"created_at": 0, "data": None}
AI_STATUS_CACHE_TTL = 30
LEADERBOARD_CACHE = {}
LEADERBOARD_CACHE_TTL = int(os.environ.get("LEADERBOARD_CACHE_TTL", "60"))
APPROX_RON_EXCHANGE_RATES = {
    "RON": 1.0,
    "EUR": 5.0,
    "USD": 4.6,
    "GBP": 5.85,
    "CHF": 5.35,
    "BGN": 2.56,
    "HUF": 0.0127,
    "PLN": 1.17,
    "CZK": 0.2,
    "TRY": 0.14,
    "KZT": 0.0084,
    "INR": 0.053,
    "MDL": 0.26,
}
RATE_LIMIT_BUCKETS = defaultdict(deque)
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
PRODUCTION_MODE = APP_ENV in {"production", "prod"}
DEFAULT_AUTH_SECRET = "local-development-change-this-secret"
GLOBAL_RATE_LIMIT = int(os.environ.get("GLOBAL_RATE_LIMIT", "300"))
GLOBAL_RATE_LIMIT_WINDOW = int(os.environ.get("GLOBAL_RATE_LIMIT_WINDOW", "60"))
AUTH_RATE_LIMIT = int(os.environ.get("AUTH_RATE_LIMIT", "5"))
AUTH_RATE_LIMIT_WINDOW = int(os.environ.get("AUTH_RATE_LIMIT_WINDOW", str(15 * 60)))
MAX_JSON_BODY_BYTES = int(os.environ.get("MAX_JSON_BODY_BYTES", str(200 * 1024)))

OFF_FALLBACK_BARCODES_BY_CATEGORY = {
    "en:iced-coffees": [
        "9002490100070",
        "000009042414",
        "0007084701247",
        "0007084789994",
        "0007084702834",
        "5060517883560",
    ],
    "en:dairy-desserts": [
        "5997536140131",
        "3033490906290",
        "3033491432729",
        "4002971243802",
        "3760122966055",
        "42244035",
        "4025500277468",
        "42400455",
    ],
    "en:dairies": [
        "42400455",
        "4025500277468",
        "4002971243802",
    ],
    "en:sweet-snacks": [
        "3017624010701",
    ],
    "en:beverages": [
        "5449000000996",
        "9002490100070",
    ],
    "en:energy-drinks": [
        "9002490100070",
        "000009042414",
        "0007084701247",
        "0007084789994",
        "0007084702834",
        "5060517883560",
    ],
    "en:condiments": [
        "8715700110622",
    ],
    "en:instant-noodles": [
        "8801073110502",
        "8801073141384",
        "8801073210776",
        "8801073211391",
        "8801043014830",
        "8801052062228",
    ],
    "en:fruit-yogurts": [
        "5941352001855",
        "5941352001886",
        "5941352001848",
        "5941238013309",
    ],
    "en:ice-creams": [
        "4056489122095",
        "4056489122101",
        "20636267",
    ],
    "en:pizzas": [
        "4001724819806",
        "5941194001888",
    ],
    "en:ready-meals": [
        "5941194002328",
    ],
}


def load_local_environment():
    env_path = os.path.join(os.path.dirname(__file__), ".env")

    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_local_environment()


def read_secret_env(name, default=""):
    value = os.environ.get(name, default).strip().strip("\"'")
    prefixed_name = f"{name}="

    if value.startswith(prefixed_name):
        value = value[len(prefixed_name):].strip().strip("\"'")

    return value

app = Flask(__name__)


def normalize_origin_value(origin):
    raw_origin = str(origin or "").strip().rstrip("/")

    if not raw_origin:
        return ""

    parsed = urlparse(raw_origin)

    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def origin_variants(origin):
    normalized_origin = normalize_origin_value(origin)

    if not normalized_origin:
        return []

    parsed = urlparse(normalized_origin)
    host = parsed.hostname or ""

    if host in {"localhost", "127.0.0.1"} or not host:
        return [normalized_origin]

    if host.startswith("www."):
        alternate_host = host[4:]
    elif host.count(".") == 1:
        alternate_host = f"www.{host}"
    else:
        return [normalized_origin]

    if parsed.port:
        alternate_netloc = f"{alternate_host}:{parsed.port}"
    else:
        alternate_netloc = alternate_host

    return [
        normalized_origin,
        f"{parsed.scheme}://{alternate_netloc}".rstrip("/"),
    ]


def get_frontend_origins():
    configured_origins = []

    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(","):
        configured_origins.extend(origin_variants(origin))

    configured_origins.extend(origin_variants(os.environ.get("FRONTEND_PUBLIC_URL", "")))
    origins = [origin for origin in configured_origins if origin]

    return list(dict.fromkeys(origins))


frontend_origins = get_frontend_origins()
CORS(app, resources={r"/*": {"origins": frontend_origins}})

database_url = os.environ.get("DATABASE_URL", "").strip()

if PRODUCTION_MODE and not database_url:
    raise RuntimeError(
        "DATABASE_URL is required in production. "
        "Refusing to use ephemeral SQLite storage."
    )

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///cealeg.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = (
    {
        "pool_pre_ping": True,
        "pool_recycle": 240,
        "connect_args": {"sslmode": "require"},
    }
    if database_url.startswith("postgresql+psycopg://")
    else {}
)
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("MAX_UPLOAD_MB", "8")
) * 1024 * 1024
Image.MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", "24000000"))

db.init_app(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SUBMISSIONS_FOLDER = os.path.join(UPLOAD_FOLDER, "submissions")
os.makedirs(SUBMISSIONS_FOLDER, exist_ok=True)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_PRODUCT_IMAGES_BUCKET = os.environ.get(
    "SUPABASE_PRODUCT_IMAGES_BUCKET", "product-images"
)
app.config["AUTH_SECRET"] = os.environ.get(
    "AUTH_SECRET", DEFAULT_AUTH_SECRET
)
SUPABASE_SUBMISSIONS_BUCKET = os.environ.get(
    "SUPABASE_SUBMISSIONS_BUCKET", "product-submissions"
)
ALLOW_DEV_TUNNEL_ORIGINS = os.environ.get(
    "ALLOW_DEV_TUNNEL_ORIGINS", "true"
).lower() == "true"

AUTH_COOKIE_NAME = "cealeg_session"
AUTH_MAX_AGE = 60 * 60 * 24 * 30
FREE_MONTHLY_SCAN_LIMIT = int(
    os.environ.get(
        "FREE_MONTHLY_SCAN_LIMIT",
        os.environ.get("FREE_WEEKLY_SCAN_LIMIT", "5"),
    )
)
FREE_WEEKLY_SCAN_LIMIT = FREE_MONTHLY_SCAN_LIMIT
INVITE_BONUS_DAYS = int(os.environ.get("INVITE_BONUS_DAYS", "2"))
SUBMISSION_APPROVAL_BONUS_CREDITS = int(
    os.environ.get("SUBMISSION_APPROVAL_BONUS_CREDITS", "1")
)
PASSWORD_MIN_LENGTH = int(os.environ.get("PASSWORD_MIN_LENGTH", "8"))
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "manual").strip().lower()
FRONTEND_PUBLIC_URL = (
    os.environ.get("FRONTEND_PUBLIC_URL", "").strip().rstrip("/")
    or (frontend_origins[0].rstrip("/") if frontend_origins else "http://localhost:3000")
)
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "smtp").strip().lower()
BREVO_API_KEY = read_secret_env("BREVO_API_KEY")
RESEND_API_KEY = read_secret_env("RESEND_API_KEY")
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "").strip()
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USERNAME = os.environ.get("EMAIL_SMTP_USERNAME", "").strip()
EMAIL_SMTP_PASSWORD = read_secret_env("EMAIL_SMTP_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Ce aleg?").strip()
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "contact@cealeg.shop").strip().lower()
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PASSWORD_RESET_MAX_AGE = int(os.environ.get("PASSWORD_RESET_MAX_AGE", "3600"))
EMAIL_VERIFICATION_MAX_AGE = int(
    os.environ.get("EMAIL_VERIFICATION_MAX_AGE", str(48 * 60 * 60))
)
ACCOUNT_DELETE_MAX_AGE = int(os.environ.get("ACCOUNT_DELETE_MAX_AGE", str(24 * 60 * 60)))
LAST_EMAIL_PROVIDER_ERROR = ""

PLAN_CATALOG = {
    "free": {
        "id": "free",
        "name": "Free",
        "monthlyPrice": 0,
        "yearlyPrice": 0,
        "monthlyScanLimit": FREE_MONTHLY_SCAN_LIMIT,
        "weeklyScanLimit": FREE_WEEKLY_SCAN_LIMIT,
        "features": [
            "5 scanari pe luna",
            "2 alternative pentru fiecare produs",
            "scanare cod de bare si cautare manuala",
            "verdict rapid",
            "istoric de baza",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "monthlyPrice": 19.99,
        "yearlyPrice": 149,
        "monthlyScanLimit": None,
        "weeklyScanLimit": None,
        "features": [
            "scanari nelimitate",
            "3 alternative initiale plus afiseaza mai multe",
            "cautare dupa preferintele tale",
            "istoric complet",
            "cos si favorite salvate",
            "asistent vizual AI in curand",
        ],
    },
    "family": {
        "id": "family",
        "name": "Family",
        "monthlyPrice": 29.99,
        "yearlyPrice": 249,
        "monthlyScanLimit": None,
        "weeklyScanLimit": None,
        "features": [
            "scanari nelimitate",
            "3 alternative initiale plus afiseaza mai multe",
            "cautare dupa preferintele tale",
            "istoric complet",
            "cos si favorite salvate",
            "profiluri pentru familie",
            "preferinte separate pe profil",
            "cos separat pentru fiecare profil",
            "asistent vizual AI in curand",
        ],
    },
}

STRIPE_PRICE_ENV_BY_PLAN = {
    "pro": {
        "monthly": "STRIPE_PRO_PRICE_ID",
        "yearly": "STRIPE_PRO_YEARLY_PRICE_ID",
    },
    "family": {
        "monthly": "STRIPE_FAMILY_PRICE_ID",
        "yearly": "STRIPE_FAMILY_YEARLY_PRICE_ID",
    },
}
PLAN_RANK = {"free": 0, "pro": 1, "family": 2}

MISSION_SERIES = [
    {
        "seriesId": "scan",
        "metric": "scanCount",
        "icon": "scan",
        "titleTemplate": "Scanează {target} produs(e)",
        "description": "Scanează produse noi și construiește un istoric util.",
        "targets": [3],
        "coins": 10,
        "daily": True,
    },
    {
        "seriesId": "cart",
        "metric": "cartCount",
        "icon": "cart",
        "titleTemplate": "Pune {target} produs(e) în coș",
        "description": "Construiește liste utile pentru cumpărăturile următoare.",
        "targets": [2],
        "coins": 10,
        "daily": True,
    },
    {
        "seriesId": "favorite",
        "metric": "favoritesCount",
        "icon": "favorite",
        "titleTemplate": "Salvează {target} favorite",
        "description": "Păstrează produsele și alternativele la care vrei să revii.",
        "targets": [1],
        "coins": 10,
        "daily": True,
    },
    {
        "seriesId": "catalog",
        "metric": "approvedSubmissions",
        "icon": "catalog",
        "titleTemplate": "Adaugă {target} produs(e) aprobate",
        "description": "Produsele aprobate ajută catalogul și îți cresc recompensa.",
        "targets": [1],
        "coins": 10,
        "daily": True,
    },
    {
        "seriesId": "invite",
        "metric": "confirmedInvites",
        "icon": "invite",
        "titleTemplate": "Invită prieteni",
        "description": "Primești automat 100 CeCoins pentru fiecare prieten care confirmă emailul cu codul tău.",
        "targets": [1],
        "coins": 100,
        "daily": False,
    },
]

CECOIN_SHOP_ITEMS = [
    {
        "id": "bonus_scan_1",
        "title": "1 scanare bonus",
        "description": "Adaugă o scanare extra peste limita lunară.",
        "cost": 80,
        "bonusScans": 1,
    },
    {
        "id": "bonus_scan_5",
        "title": "5 scanări bonus",
        "description": "Pachet bun pentru o tură de cumpărături mai lungă.",
        "cost": 350,
        "bonusScans": 5,
    },
    {
        "id": "unlimited_day_1",
        "title": "1 zi de scanări nelimitate",
        "description": "Activează acces nelimitat pentru toate scanările din următoarele 24 de ore.",
        "cost": 400,
        "bonusDays": 1,
    },
    {
        "id": "unlimited_month_1",
        "title": "1 lună de scanări nelimitate",
        "description": "Activează scanări nelimitate pentru 30 de zile.",
        "cost": 1050,
        "bonusDays": 30,
    },
]

CECOIN_PACKS = [
    {
        "id": "bronze",
        "title": "Bronze CeCoins",
        "coins": 500,
        "priceText": "9,99 lei",
        "priceEnv": "STRIPE_CECOINS_BRONZE_PRICE_ID",
        "legacyPriceEnv": "STRIPE_CECOINS_STARTER_PRICE_ID",
        "image": "/brand/Bronze.png",
        "icon": "/brand/Bronze_icon.png",
    },
    {
        "id": "gold",
        "title": "Gold CeCoins",
        "coins": 1200,
        "priceText": "19,99 lei",
        "priceEnv": "STRIPE_CECOINS_GOLD_PRICE_ID",
        "legacyPriceEnv": "STRIPE_CECOINS_BOOST_PRICE_ID",
        "image": "/brand/Gold.png",
        "icon": "/brand/Gold_icon.png",
    },
    {
        "id": "diamond",
        "title": "Diamond CeCoins",
        "coins": 3000,
        "priceText": "39,99 lei",
        "priceEnv": "STRIPE_CECOINS_DIAMOND_PRICE_ID",
        "legacyPriceEnv": "STRIPE_CECOINS_POWER_PRICE_ID",
        "image": "/brand/Diamond.png",
        "icon": "/brand/Diamond_icon.png",
    },
]


def build_mission_catalog():
    missions = []

    for series in MISSION_SERIES:
        for index, target in enumerate(series["targets"], start=1):
            missions.append({
                "id": f"{series['seriesId']}_{target}",
                "seriesId": series["seriesId"],
                "tier": index,
                "title": series["titleTemplate"].format(target=target),
                "description": series["description"],
                "metric": series["metric"],
                "target": target,
                "icon": series["icon"],
                "coins": int(series.get("coins", 10) or 0),
                "bonusScans": int(series.get("bonusScans", 0) or 0),
                "bonusDays": int(series.get("bonusDays", 0) or 0),
                "daily": bool(series.get("daily", False)),
            })

    return missions


MISSION_CATALOG = build_mission_catalog()


def get_auth_serializer():
    return URLSafeTimedSerializer(app.config["AUTH_SECRET"], salt="cealeg-auth")


def get_password_reset_serializer():
    return URLSafeTimedSerializer(
        app.config["AUTH_SECRET"],
        salt="cealeg-password-reset",
    )


def get_email_verification_serializer():
    return URLSafeTimedSerializer(
        app.config["AUTH_SECRET"],
        salt="cealeg-email-verification",
    )


def get_account_deletion_serializer():
    return URLSafeTimedSerializer(
        app.config["AUTH_SECRET"],
        salt="cealeg-account-deletion",
    )


def is_email_configured():
    if EMAIL_PROVIDER == "brevo":
        return bool(BREVO_API_KEY and EMAIL_FROM)

    if EMAIL_PROVIDER == "resend":
        return bool(RESEND_API_KEY and EMAIL_FROM)

    return bool(EMAIL_SMTP_HOST and EMAIL_FROM)


def set_email_provider_error(message=""):
    global LAST_EMAIL_PROVIDER_ERROR
    LAST_EMAIL_PROVIDER_ERROR = str(message or "").strip()[:600]


def is_valid_email_address(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email or "").strip()))


def get_email_reply_to():
    if is_valid_email_address(CONTACT_EMAIL):
        return CONTACT_EMAIL

    return ""


def validate_password_strength(password):
    password = password or ""
    suggestions = []
    score = 0

    if len(password) >= PASSWORD_MIN_LENGTH:
        score += 1
    else:
        suggestions.append(f"Foloseste minimum {PASSWORD_MIN_LENGTH} caractere.")

    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        score += 1
    else:
        suggestions.append("Combina litere mici si litere mari.")

    if re.search(r"\d", password):
        score += 1
    else:
        suggestions.append("Adauga cel putin o cifra.")

    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    else:
        suggestions.append("Adauga un simbol, de exemplu !, ?, # sau @.")

    if len(password) >= 12:
        score += 1

    if len(password) < PASSWORD_MIN_LENGTH:
        label = "slaba"
    elif score >= 5:
        label = "puternica"
    elif score >= 3:
        label = "medie"
    else:
        label = "slaba"

    return {
        "label": label,
        "score": score,
        "isValid": len(password) >= PASSWORD_MIN_LENGTH,
        "suggestions": suggestions,
    }


def get_email_html_body(text_body, html_body=None):
    if html_body:
        return html_body

    escaped_lines = [
        line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for line in text_body.splitlines()
    ]
    return "<br>".join(escaped_lines)


def send_brevo_email(to_email, subject, text_body, html_body=None):
    reply_to = get_email_reply_to()
    payload = {
        "sender": {
            "name": EMAIL_FROM_NAME,
            "email": EMAIL_FROM,
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": text_body,
        "htmlContent": get_email_html_body(text_body, html_body),
    }

    if reply_to:
        payload["replyTo"] = {
            "name": EMAIL_FROM_NAME,
            "email": reply_to,
        }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
            timeout=10,
        )

        if 200 <= response.status_code < 300:
            set_email_provider_error("")
            return True

        set_email_provider_error(f"Brevo HTTP {response.status_code}: {response.text[:300]}")
        app.logger.warning(
            "Brevo email failed with status %s: %s",
            response.status_code,
            response.text[:300],
        )
        return False
    except Exception as error:
        set_email_provider_error(f"Brevo exception: {error}")
        app.logger.warning("Brevo email failed: %s", error)
        return False


def send_resend_email(to_email, subject, text_body, html_body=None):
    reply_to = get_email_reply_to()
    payload = {
        "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": get_email_html_body(text_body, html_body),
    }

    if reply_to:
        payload["reply_to"] = reply_to

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "authorization": f"Bearer {RESEND_API_KEY}",
                "content-type": "application/json",
            },
            json=payload,
            timeout=10,
        )

        if 200 <= response.status_code < 300:
            set_email_provider_error("")
            return True

        set_email_provider_error(f"Resend HTTP {response.status_code}: {response.text[:300]}")
        app.logger.warning(
            "Resend email failed with status %s: %s",
            response.status_code,
            response.text[:300],
        )
        return False
    except Exception as error:
        set_email_provider_error(f"Resend exception: {error}")
        app.logger.warning("Resend email failed: %s", error)
        return False


def send_smtp_email(to_email, subject, text_body, html_body=None):
    reply_to = get_email_reply_to()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    message["To"] = to_email
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if EMAIL_USE_SSL:
            smtp_client = smtplib.SMTP_SSL(
                EMAIL_SMTP_HOST,
                EMAIL_SMTP_PORT,
                timeout=10,
            )
        else:
            smtp_client = smtplib.SMTP(
                EMAIL_SMTP_HOST,
                EMAIL_SMTP_PORT,
                timeout=10,
            )

        with smtp_client as server:
            if EMAIL_USE_TLS and not EMAIL_USE_SSL:
                server.starttls()

            if EMAIL_SMTP_USERNAME:
                server.login(EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD)

            server.send_message(message)

        set_email_provider_error("")
        return True
    except Exception as error:
        set_email_provider_error(f"SMTP exception: {error}")
        app.logger.warning("SMTP email failed: %s", error)
        return False


def send_transactional_email(to_email, subject, text_body, html_body=None):
    if not is_email_configured():
        set_email_provider_error(
            f"Provider={EMAIL_PROVIDER}, EMAIL_FROM set={bool(EMAIL_FROM)}, provider key/host configured={bool(BREVO_API_KEY or RESEND_API_KEY or EMAIL_SMTP_HOST)}"
        )
        app.logger.info(
            "Email not sent because provider is not configured. To=%s Subject=%s Provider=%s",
            to_email,
            subject,
            EMAIL_PROVIDER,
        )
        return False

    if EMAIL_PROVIDER == "brevo":
        return send_brevo_email(to_email, subject, text_body, html_body)

    if EMAIL_PROVIDER == "resend":
        return send_resend_email(to_email, subject, text_body, html_body)

    return send_smtp_email(to_email, subject, text_body, html_body)


def brand_logo_url():
    return f"{FRONTEND_PUBLIC_URL}/brand/ce-aleg-logo.png"


def render_brand_email(preheader, title, intro, button_label=None, button_url=None, details=None, tone="standard"):
    safe_preheader = escape(preheader or "")
    safe_title = escape(title or "")
    safe_intro = escape(intro or "")
    safe_button_label = escape(button_label or "")
    safe_button_url = escape(button_url or "")
    safe_logo_url = escape(brand_logo_url())
    detail_items = "".join(
        f"""
        <tr>
          <td style="padding:10px 0;border-top:1px solid rgba(148,163,184,0.18);">
            <span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:#22d3ee;margin-right:10px;"></span>
            <span style="color:#cbd5e1;font-size:14px;line-height:22px;">{escape(str(item))}</span>
          </td>
        </tr>
        """
        for item in (details or [])
    )
    button_html = (
        f"""
        <tr>
          <td align="center" style="padding:24px 0 8px;text-align:center;">
            <a href="{safe_button_url}" style="display:inline-block;background:#ffffff;color:#020617;text-decoration:none;font-weight:800;font-size:15px;padding:14px 22px;border-radius:12px;">
              {safe_button_label}
            </a>
          </td>
        </tr>
        """
        if button_label and button_url
        else ""
    )
    accent_color = "#facc15" if tone == "danger" else "#22d3ee"

    return f"""
    <!doctype html>
    <html>
      <body style="margin:0;padding:0;background:#020617;font-family:Inter,Arial,sans-serif;color:#f8fafc;">
        <div style="display:none;max-height:0;overflow:hidden;color:transparent;opacity:0;">{safe_preheader}</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#020617;padding:28px 14px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;overflow:hidden;border-radius:26px;border:1px solid rgba(148,163,184,0.22);background:linear-gradient(145deg,#07111f,#0b1220 54%,#111827);box-shadow:0 30px 90px rgba(0,0,0,0.45);">
                <tr>
                  <td style="padding:28px 28px 8px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:middle;">
                          <img src="{safe_logo_url}" width="54" height="54" alt="Ce aleg?" style="display:inline-block;border-radius:14px;vertical-align:middle;margin-right:12px;">
                          <span style="display:inline-block;vertical-align:middle;">
                            <span style="display:block;color:#ffffff;font-size:18px;font-weight:900;line-height:22px;">Ce aleg?</span>
                            <span style="display:block;color:#a5f3fc;font-size:12px;font-weight:700;">cumpărături mai inteligente</span>
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:22px 28px 6px;">
                    <div style="display:inline-block;border:1px solid {accent_color};background:rgba(34,211,238,0.08);color:#cffafe;border-radius:999px;padding:7px 12px;font-size:12px;font-weight:800;letter-spacing:.02em;">
                      {safe_preheader}
                    </div>
                    <h1 style="margin:18px 0 12px;color:#ffffff;font-size:34px;line-height:40px;font-weight:900;letter-spacing:-0.02em;">
                      {safe_title}
                    </h1>
                    <p style="margin:0;color:#cbd5e1;font-size:16px;line-height:26px;">
                      {safe_intro}
                    </p>
                  </td>
                </tr>
                {button_html}
                <tr>
                  <td style="padding:4px 28px 24px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;">
                      {detail_items}
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:18px 28px 26px;border-top:1px solid rgba(148,163,184,0.16);color:#94a3b8;font-size:12px;line-height:20px;">
                    Dacă nu ai cerut acest email, îl poți ignora. Pentru siguranță, nu trimitem niciodată parola ta prin email.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def send_welcome_email(user):
    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    text_body = (
        f"Salut, {user.name}!\n\n"
        "Contul tău Ce aleg? este pregătit.\n"
        "Poți scana produse, salva coșul și primi alternative mai bune.\n\n"
        f"Intră aici: {dashboard_url}\n"
    )
    html_body = render_brand_email(
        "Cont activ",
        f"Salut, {user.name}.",
        "Contul tău este pregătit. Poți scana produse, salva coșul și compara alternative potrivite pentru tine.",
        "Deschide dashboardul",
        dashboard_url,
        [
            "Scanează produse direct cu telefonul.",
            "Păstrează istoricul, favoritele și coșul de cumpărături.",
            "Compară rapid alternative mai potrivite.",
        ],
    )
    return send_transactional_email(
        user.email,
        "Bine ai venit în Ce aleg?",
        text_body,
        html_body,
    )


def create_email_verification_token(user):
    payload = {
        "action": "verify_email",
        "user_id": user.id,
        "email": user.email,
        "password_hash": user.password_hash,
    }
    return get_email_verification_serializer().dumps(payload)


def verify_email_verification_token(token):
    try:
        payload = get_email_verification_serializer().loads(
            token,
            max_age=EMAIL_VERIFICATION_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return None

    if payload.get("action") != "verify_email":
        return None

    user = db.session.get(User, payload.get("user_id"))

    if not user:
        return None

    if user.email != payload.get("email") or user.password_hash != payload.get("password_hash"):
        return None

    return user


def send_email_verification_email(user):
    token = create_email_verification_token(user)
    verification_url = f"{FRONTEND_PUBLIC_URL}/verify-email?token={token}"
    text_body = (
        f"Salut, {user.name}!\n\n"
        "Confirmă adresa de email pentru contul Ce aleg?.\n"
        f"Confirmă aici: {verification_url}\n\n"
        "Linkul expiră în 48 de ore.\n"
    )
    html_body = render_brand_email(
        "Confirmă emailul",
        "Verifică adresa de email.",
        "Apasă pe buton pentru a activa contul și pentru a păstra aplicația curată de conturi false.",
        "Confirmă emailul",
        verification_url,
        [
            "Confirmarea durează câteva secunde.",
            "După confirmare poți intra în cont și scana produse.",
            "Linkul expiră în 48 de ore.",
        ],
    )
    sent = send_transactional_email(
        user.email,
        "Confirmă emailul pentru Ce aleg?",
        text_body,
        html_body,
    )
    return sent, verification_url


def create_password_reset_token(user):
    payload = {
        "user_id": user.id,
        "password_hash": user.password_hash,
    }
    return get_password_reset_serializer().dumps(payload)


def verify_password_reset_token(token):
    try:
        payload = get_password_reset_serializer().loads(
            token,
            max_age=PASSWORD_RESET_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, payload.get("user_id"))

    if not user or user.password_hash != payload.get("password_hash"):
        return None

    return user


def send_password_reset_email(user):
    token = create_password_reset_token(user)
    reset_url = f"{FRONTEND_PUBLIC_URL}/reset-password?token={token}"
    text_body = (
        f"Salut, {user.name}!\n\n"
        "Ai cerut resetarea parolei pentru contul Ce aleg?.\n"
        f"Schimbă parola aici: {reset_url}\n\n"
        "Linkul expiră în 60 de minute. Dacă nu ai cerut resetarea, ignoră acest email.\n"
    )
    html_body = render_brand_email(
        "Securitate cont",
        "Schimbă parola în siguranță.",
        "Am primit o cerere de resetare pentru contul tău. Folosește linkul de mai jos dacă tu ai cerut schimbarea parolei.",
        "Schimbă parola",
        reset_url,
        [
            "Linkul expiră în 60 de minute.",
            "Dacă nu ai cerut resetarea, ignoră acest email.",
            "Parola ta veche nu este trimisă și nu poate fi văzută.",
        ],
    )
    sent = send_transactional_email(
        user.email,
        "Resetare parolă Ce aleg?",
        text_body,
        html_body,
    )
    return sent, reset_url


def create_account_deletion_token(user):
    payload = {
        "action": "delete_account",
        "user_id": user.id,
        "email": user.email,
        "password_hash": user.password_hash,
    }
    return get_account_deletion_serializer().dumps(payload)


def verify_account_deletion_token(token):
    try:
        payload = get_account_deletion_serializer().loads(
            token,
            max_age=ACCOUNT_DELETE_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return None

    if payload.get("action") != "delete_account":
        return None

    user = db.session.get(User, payload.get("user_id"))

    if not user:
        return None

    if user.email != payload.get("email") or user.password_hash != payload.get("password_hash"):
        return None

    return user


def send_account_deletion_email(user):
    token = create_account_deletion_token(user)
    deletion_url = f"{FRONTEND_PUBLIC_URL}/delete-account?token={token}"
    text_body = (
        f"Salut, {user.name}!\n\n"
        "Ai cerut ștergerea contului Ce aleg?.\n"
        "Dacă tu ai făcut cererea, confirmă ștergerea aici:\n"
        f"{deletion_url}\n\n"
        "Linkul expiră în 24 de ore. Dacă nu ai cerut ștergerea, ignoră acest email "
        "și contul tău rămâne activ.\n"
    )
    html_body = render_brand_email(
        "Confirmare necesară",
        "Confirmă ștergerea contului.",
        "Ștergerea contului elimină istoricul, coșul, favoritele și contribuțiile tale după confirmare.",
        "Șterge contul meu",
        deletion_url,
        [
            "Linkul expiră în 24 de ore.",
            "Dacă nu ai cerut ștergerea, ignoră acest email.",
            "Contul rămâne activ până confirmi din email.",
        ],
        tone="danger",
    )
    sent = send_transactional_email(
        user.email,
        "Confirmare ștergere cont Ce aleg?",
        text_body,
        html_body,
    )
    return sent, deletion_url


def delete_local_submission_file(image_path):
    prefix = "/uploads/submissions/"

    if not image_path or not image_path.startswith(prefix):
        return

    filename = image_path.removeprefix(prefix)
    absolute_path = os.path.abspath(os.path.join(SUBMISSIONS_FOLDER, filename))
    submissions_root = os.path.abspath(SUBMISSIONS_FOLDER)

    if not absolute_path.startswith(submissions_root + os.sep):
        app.logger.warning("Refused to delete unexpected upload path: %s", image_path)
        return

    try:
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
    except OSError as error:
        app.logger.warning("Could not delete local submission image %s: %s", image_path, error)


def delete_supabase_submission_file(image_path):
    prefix = "/uploads/supabase-submissions/"

    if not image_path or not image_path.startswith(prefix) or not supabase_storage_enabled():
        return

    object_path = image_path.removeprefix(prefix)

    try:
        response = requests.delete(
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_SUBMISSIONS_BUCKET}/{object_path}",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=10,
        )

        if response.status_code not in {200, 204, 404}:
            app.logger.warning(
                "Could not delete Supabase submission image %s: %s",
                image_path,
                response.text[:200],
            )
    except Exception as error:
        app.logger.warning("Could not delete Supabase submission image %s: %s", image_path, error)


def delete_submission_file(image_path):
    delete_local_submission_file(image_path)
    delete_supabase_submission_file(image_path)


def cancel_subscription_before_account_deletion(user):
    subscription = Subscription.query.filter_by(user_id=user.id).first()

    if not subscription or subscription.provider != "stripe" or not subscription.provider_subscription_id:
        return True, None

    if subscription.status not in {"active", "trialing", "past_due", "incomplete"}:
        return True, None

    if not configure_stripe():
        return False, "Abonamentul Stripe nu a putut fi anulat momentan. Încearcă din nou sau contactează suportul."

    try:
        cancel_method = getattr(stripe.Subscription, "cancel", None)

        if callable(cancel_method):
            cancel_method(subscription.provider_subscription_id)
        else:
            stripe.Subscription.delete(subscription.provider_subscription_id)

        subscription.status = "canceled"
        subscription.updated_at = datetime.utcnow()
        return True, None
    except Exception as error:
        app.logger.warning("Stripe subscription cancel before account deletion failed: %s", error)
        return False, "Abonamentul nu a putut fi anulat momentan. Contul nu a fost sters ca sa nu ramai taxat."


def delete_account_data(user):
    user_id = user.id

    for submission in ProductSubmission.query.filter_by(user_id=user_id).all():
        delete_submission_file(submission.front_image)
        delete_submission_file(submission.nutrition_image)

    CartItem.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Favorite.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    ScanHistory.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    PriceObservation.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    ProductSubmission.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    SearchEvent.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Subscription.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    FamilyProfile.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    UsageEvent.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()


def normalize_invite_code(code):
    return re.sub(r"[^A-Z0-9]", "", str(code or "").upper())[:24]


def generate_invite_code():
    return f"CEA{uuid4().hex[:8].upper()}"


def ensure_user_invite_code(user):
    if getattr(user, "invite_code", None):
        return user.invite_code

    for _attempt in range(12):
        user.invite_code = generate_invite_code()

        try:
            db.session.commit()
            return user.invite_code
        except IntegrityError:
            db.session.rollback()
            user = db.session.get(User, user.id)

    app.logger.warning("Could not generate invite code for user %s", user.id)
    return None


def find_inviter_by_code(code):
    normalized_code = normalize_invite_code(code)

    if not normalized_code:
        return None

    return User.query.filter(func.upper(User.invite_code) == normalized_code).first()


def bonus_unlimited_is_active(user, now=None):
    now = now or datetime.utcnow()
    return bool(user.bonus_unlimited_until and user.bonus_unlimited_until > now)


def extend_bonus_unlimited(user, days=INVITE_BONUS_DAYS, source="invite", metadata=None):
    if not user or days <= 0:
        return

    now = datetime.utcnow()
    current_end = user.bonus_unlimited_until if bonus_unlimited_is_active(user, now) else now
    user.bonus_unlimited_until = current_end + timedelta(days=days)
    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="bonus_unlimited",
            source=source,
            metadata_json=json.dumps(metadata or {}),
        )
    )


def add_bonus_scan_credits(user, credits=SUBMISSION_APPROVAL_BONUS_CREDITS, source="submission", metadata=None):
    if not user or credits <= 0:
        return

    user.bonus_scan_credits = max(0, int(user.bonus_scan_credits or 0)) + credits
    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="bonus_scan_credit",
            source=source,
            metadata_json=json.dumps(metadata or {}),
        )
    )


def apply_referral_bonus_after_verification(user):
    if not user or not user.referred_by_user_id:
        return False

    already_rewarded = UsageEvent.query.filter(
        UsageEvent.user_id == user.id,
        UsageEvent.event_type == "bonus_unlimited",
        UsageEvent.source == "referral_new_user",
    ).first()

    if already_rewarded:
        return False

    inviter = db.session.get(User, user.referred_by_user_id)

    if not inviter or inviter.id == user.id:
        return False

    extend_bonus_unlimited(
        user,
        INVITE_BONUS_DAYS,
        "referral_new_user",
        {"inviterUserId": inviter.id},
    )
    extend_bonus_unlimited(
        inviter,
        INVITE_BONUS_DAYS,
        "referral_inviter",
        {"invitedUserId": user.id},
    )
    db.session.add(
        UsageEvent(
            user_id=inviter.id,
            event_type="referral_cecoin_bonus",
            source="referral_inviter",
            metadata_json=json.dumps({
                "coins": 100,
                "invitedUserId": user.id,
                "awardedAt": datetime.utcnow().isoformat() + "Z",
            }),
        )
    )
    db.session.commit()
    clear_leaderboard_cache()
    return True


def user_to_dict(user):
    invite_code = ensure_user_invite_code(user)
    subscription = get_or_create_subscription(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "isAdmin": bool(user.is_admin),
        "emailVerified": bool(getattr(user, "email_verified", True)),
        "plan": subscription.plan,
        "subscriptionStatus": subscription.status,
        "inviteCode": invite_code,
        "bonusScanCredits": max(0, int(user.bonus_scan_credits or 0)),
        "bonusUnlimitedUntil": (
            user.bonus_unlimited_until.isoformat() + "Z"
            if user.bonus_unlimited_until
            else None
        ),
    }


def subscription_to_billing_dict(subscription):
    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "provider": subscription.provider,
        "hasCustomer": bool(subscription.provider_customer_id),
        "currentPeriodEnd": (
            subscription.current_period_end.isoformat() + "Z"
            if subscription.current_period_end
            else None
        ),
    }


def is_subscription_period_active(subscription):
    if not subscription:
        return False

    if subscription.plan not in {"pro", "family"}:
        return False

    if subscription.status not in {"active", "trialing", "past_due"}:
        return False

    if subscription.current_period_end and subscription.current_period_end <= datetime.utcnow():
        return False

    return True


def set_auth_cookie(response, user):
    token = get_auth_serializer().dumps({"user_id": user.id})
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=AUTH_MAX_AGE,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        samesite="Lax",
        path="/",
    )
    return response


def get_current_user():
    token = request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        return None

    try:
        payload = get_auth_serializer().loads(token, max_age=AUTH_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

    return db.session.get(User, payload.get("user_id"))


def require_auth(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        user = get_current_user()

        if not user:
            return jsonify({"error": "Autentificare necesară."}), 401

        g.current_user = user
        return handler(*args, **kwargs)

    return wrapped


def require_admin(handler):
    @wraps(handler)
    @require_auth
    def wrapped(*args, **kwargs):
        if not g.current_user.is_admin:
            return jsonify({"error": "Acces rezervat administratorului."}), 403

        return handler(*args, **kwargs)

    return wrapped


def require_same_user(user_id):
    return g.current_user.is_admin or int(user_id) == g.current_user.id


def rate_limit(scope, limit, window_seconds):
    key = f"{scope}:{request.remote_addr or 'unknown'}"
    now = time.time()
    bucket = RATE_LIMIT_BUCKETS[key]

    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        return False

    bucket.append(now)
    return True


def validate_request_payload():
    if request.method not in {"POST", "PATCH", "PUT"}:
        return None

    content_length = request.content_length or 0

    if request.is_json:
        if content_length > MAX_JSON_BODY_BYTES:
            return jsonify({"error": "Cererea este prea mare."}), 413

        if content_length == 0:
            return None

        try:
            request.get_json(silent=False)
        except BadRequest:
            return jsonify({"error": "JSON invalid sau malformat."}), 400

    return None


def is_trusted_browser_origin(origin):
    if not origin:
        return True

    parsed = urlparse(origin)
    origin_host = parsed.hostname or ""
    normalized_origin = normalize_origin_value(origin)

    if normalized_origin in frontend_origins:
        return True

    if ALLOW_DEV_TUNNEL_ORIGINS and origin_host.endswith(".loca.lt"):
        return True

    return False


def request_origin_is_trusted():
    origin = request.headers.get("Origin")

    if origin:
        return is_trusted_browser_origin(origin)

    referer = request.headers.get("Referer")

    if referer:
        parsed = urlparse(referer)
        return is_trusted_browser_origin(
            f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        )

    return True


def request_fetch_metadata_is_trusted():
    fetch_site = request.headers.get("Sec-Fetch-Site", "").strip().lower()
    fetch_mode = request.headers.get("Sec-Fetch-Mode", "").strip().lower()

    if fetch_mode == "no-cors":
        return False

    if fetch_site == "cross-site" and not (
        request.headers.get("Origin") or request.headers.get("Referer")
    ):
        return False

    return True


def get_request_id():
    supplied_request_id = request.headers.get("X-Request-ID", "").strip()

    if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id):
        return supplied_request_id

    return uuid4().hex


def env_flag(name, default=False):
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def origin_looks_local(origin):
    try:
        hostname = urlparse(origin).hostname or ""
    except ValueError:
        return True

    return hostname in {"localhost", "127.0.0.1", "0.0.0.0"} or hostname.startswith("192.168.")


def get_publication_readiness():
    blockers = []
    warnings = []

    auth_secret = app.config["AUTH_SECRET"]
    cookie_secure = env_flag("COOKIE_SECURE", False)
    flask_debug = env_flag("FLASK_DEBUG", False)
    payment_provider = PAYMENT_PROVIDER

    if not database_url:
        blockers.append("DATABASE_URL lipseste. Configureaza Supabase/Postgres pentru mediul de productie.")

    if not auth_secret or auth_secret == DEFAULT_AUTH_SECRET or len(auth_secret) < 32:
        blockers.append("AUTH_SECRET trebuie sa fie unic, lung si secret.")

    if PRODUCTION_MODE and not cookie_secure:
        blockers.append("COOKIE_SECURE trebuie sa fie true in productie.")

    if PRODUCTION_MODE and ALLOW_DEV_TUNNEL_ORIGINS:
        blockers.append("ALLOW_DEV_TUNNEL_ORIGINS trebuie sa fie false in productie.")

    if PRODUCTION_MODE and flask_debug:
        blockers.append("FLASK_DEBUG trebuie sa fie false in productie.")

    if PRODUCTION_MODE and any(origin_looks_local(origin) for origin in frontend_origins):
        blockers.append("FRONTEND_ORIGINS nu trebuie sa contina localhost/IP local in productie.")

    if payment_provider == "stripe":
        stripe_secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
        missing_stripe_settings = [
            key
            for key in [
                "STRIPE_SECRET_KEY",
                "STRIPE_WEBHOOK_SECRET",
                "STRIPE_PRO_PRICE_ID",
                "STRIPE_FAMILY_PRICE_ID",
                "FRONTEND_PUBLIC_URL",
            ]
            if not os.environ.get(key, "").strip()
        ]

        if missing_stripe_settings:
            message = (
                "Stripe este selectat, dar lipsesc setari: "
                + ", ".join(missing_stripe_settings)
                + "."
            )
            if PRODUCTION_MODE:
                blockers.append(message)
            else:
                warnings.append(message)

        missing_yearly_prices = [
            key
            for key in [
                "STRIPE_PRO_YEARLY_PRICE_ID",
                "STRIPE_FAMILY_YEARLY_PRICE_ID",
            ]
            if not os.environ.get(key, "").strip()
        ]

        if missing_yearly_prices:
            warnings.append(
                "Planurile anuale Stripe nu sunt active inca. Lipsesc: "
                + ", ".join(missing_yearly_prices)
                + "."
            )

        missing_cecoin_prices = [
            pack["priceEnv"]
            for pack in CECOIN_PACKS
            if not get_cecoin_pack_price_id(pack)
        ]

        if missing_cecoin_prices:
            warnings.append(
                "Pachetele CeCoins nu pot fi cumparate inca. Lipsesc: "
                + ", ".join(missing_cecoin_prices)
                + "."
            )

        if PRODUCTION_MODE and stripe_secret_key.startswith("sk_test_"):
            blockers.append(
                "Stripe este in modul test. Configureaza STRIPE_SECRET_KEY live si price id-uri live."
            )

        if PRODUCTION_MODE and "cealeg.shop" not in FRONTEND_PUBLIC_URL:
            warnings.append(
                "FRONTEND_PUBLIC_URL nu pare să fie domeniul public cealeg.shop. Verifică linkurile din emailuri și Stripe."
            )
    elif payment_provider in {"", "manual", "mock", "none"}:
        warnings.append("Platile reale nu sunt conectate. Pro/Family se pot activa doar manual din admin.")

    if not env_flag("ENABLE_OPENAI_VISION", False):
        warnings.append("Identificarea vizuala avansata este oprita. Produsul ramane functional prin cod de bare, citirea etichetelor si Open Food Facts.")

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        warnings.append("Storage Supabase nu este complet configurat; imaginile contribuite pot rămâne locale.")

    if not is_email_configured():
        warnings.append(
            "Emailurile tranzacționale nu sunt configurate; welcome/reset vor merge doar în mod local de test."
        )
    elif PRODUCTION_MODE and EMAIL_PROVIDER == "brevo" and str(os.environ.get("EMAIL_FROM", "")).lower().endswith("@gmail.com"):
        warnings.append(
            "Brevo este configurat; recomandam un sender pe domeniul cealeg.shop cu SPF/DKIM."
        )

    return {
        "ready": not blockers,
        "environment": APP_ENV,
        "database": "postgres" if database_url else "sqlite",
        "cookieSecure": cookie_secure,
        "devTunnelOriginsAllowed": ALLOW_DEV_TUNNEL_ORIGINS,
        "paymentProvider": payment_provider or "manual",
        "emailProvider": EMAIL_PROVIDER,
        "emailConfigured": is_email_configured(),
        "freeMode": True,
        "cloudVisionRequired": False,
        "blockers": blockers,
        "warnings": warnings,
    }


def get_week_start(reference=None):
    reference = reference or datetime.utcnow()
    start = reference - timedelta(days=reference.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_day_start(reference=None):
    reference = reference or datetime.utcnow()
    return reference.replace(hour=0, minute=0, second=0, microsecond=0)


def get_next_day_start(reference=None):
    return get_day_start(reference) + timedelta(days=1)


def get_month_start(reference=None):
    reference = reference or datetime.utcnow()
    return reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_next_month_start(reference=None):
    month_start = get_month_start(reference)

    if month_start.month == 12:
        return month_start.replace(year=month_start.year + 1, month=1)

    return month_start.replace(month=month_start.month + 1)


def get_or_create_subscription(user):
    subscription = Subscription.query.filter_by(user_id=user.id).first()

    if subscription:
        return subscription

    subscription = Subscription(user_id=user.id, plan="free", status="active")
    db.session.add(subscription)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        subscription = Subscription.query.filter_by(user_id=user.id).first()

    return subscription


def normalize_billing_interval(interval):
    normalized = str(interval or "monthly").strip().lower()
    if normalized in {"yearly", "annual", "year", "an"}:
        return "yearly"
    return "monthly"


def get_stripe_price_env_name(plan, interval="monthly"):
    plan_prices = STRIPE_PRICE_ENV_BY_PLAN.get(plan) or {}
    return plan_prices.get(normalize_billing_interval(interval), "")


def get_stripe_price_id(plan, interval="monthly"):
    env_name = get_stripe_price_env_name(plan, interval)
    return os.environ.get(env_name, "").strip() if env_name else ""


def get_plan_for_stripe_price(price_id):
    if not price_id:
        return None

    for plan, interval_envs in STRIPE_PRICE_ENV_BY_PLAN.items():
        for env_name in interval_envs.values():
            if os.environ.get(env_name, "").strip() == price_id:
                return plan

    return None


def configure_stripe():
    secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()

    if stripe is None or not secret_key:
        return False

    stripe.api_key = secret_key
    return True


def stripe_customer_is_usable(customer_id):
    customer_id = str(customer_id or "").strip()

    if not customer_id or not configure_stripe():
        return False

    try:
        customer = stripe.Customer.retrieve(customer_id)
    except Exception as error:
        app.logger.warning("Stripe customer %s could not be verified: %s", customer_id, error)
        return False

    return not bool(customer.get("deleted"))


def clear_stale_stripe_customer(subscription):
    if not subscription or not subscription.provider_customer_id:
        return

    app.logger.warning(
        "Clearing stale Stripe customer %s for subscription %s.",
        subscription.provider_customer_id,
        subscription.id,
    )
    subscription.provider_customer_id = None
    subscription.updated_at = datetime.utcnow()
    db.session.commit()


def stripe_error_mentions_missing_customer(error):
    text = str(error or "").lower()
    return "no such customer" in text or (
        "customer" in text and "does not exist" in text
    )


def apply_stripe_customer_to_checkout(checkout_params, subscription, user, allow_customer_update=False):
    customer_id = (
        subscription.provider_customer_id
        if subscription and subscription.provider == "stripe"
        else ""
    )

    if customer_id and stripe_customer_is_usable(customer_id):
        checkout_params["customer"] = customer_id

        if allow_customer_update:
            checkout_params["customer_update"] = {
                "address": "auto",
                "name": "auto",
            }

        return customer_id

    if customer_id:
        clear_stale_stripe_customer(subscription)

    checkout_params["customer_email"] = user.email
    return None


def create_checkout_session_with_stale_customer_retry(checkout_params, subscription, user):
    try:
        return stripe.checkout.Session.create(**checkout_params)
    except Exception as error:
        if (
            subscription
            and subscription.provider_customer_id
            and checkout_params.get("customer") == subscription.provider_customer_id
            and stripe_error_mentions_missing_customer(error)
        ):
            app.logger.warning(
                "Retrying Stripe checkout without stale customer %s.",
                subscription.provider_customer_id,
            )
            db.session.rollback()
            clear_stale_stripe_customer(subscription)
            retry_params = dict(checkout_params)
            retry_params.pop("customer", None)
            retry_params.pop("customer_update", None)
            retry_params["customer_email"] = user.email
            return stripe.checkout.Session.create(**retry_params)

        raise


def datetime_from_unix(timestamp):
    if not timestamp:
        return None

    try:
        return datetime.utcfromtimestamp(int(timestamp))
    except (TypeError, ValueError, OSError):
        return None


def stripe_subscription_status_to_local(status):
    if status in {"active", "trialing"}:
        return "active"

    if status in {"canceled", "incomplete_expired", "unpaid"}:
        return "canceled"

    return "inactive"


def update_local_subscription_from_stripe(
    user,
    plan,
    status,
    customer_id=None,
    subscription_id=None,
    current_period_start=None,
    current_period_end=None,
):
    subscription = get_or_create_subscription(user)
    subscription.plan = plan
    subscription.status = status
    subscription.provider = "stripe"
    subscription.provider_customer_id = customer_id or subscription.provider_customer_id
    subscription.provider_subscription_id = (
        subscription_id or subscription.provider_subscription_id
    )
    subscription.current_period_start = current_period_start
    subscription.current_period_end = current_period_end
    subscription.updated_at = datetime.utcnow()
    db.session.commit()
    return subscription


def get_subscription_line_price_id(stripe_subscription):
    items = (stripe_subscription.get("items") or {}).get("data") or []

    if not items:
        return None

    return ((items[0].get("price") or {}).get("id") or "").strip()


def get_subscription_line_item_id(stripe_subscription):
    items = (stripe_subscription.get("items") or {}).get("data") or []

    if not items:
        return None

    return (items[0].get("id") or "").strip()


def sync_stripe_subscription_by_id(subscription_id):
    if not subscription_id or not configure_stripe():
        return None

    try:
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
    except Exception as error:
        app.logger.warning("Stripe subscription retrieve failed: %s", error)
        return None

    return sync_stripe_subscription(stripe_subscription)


def get_invoice_subscription_id(stripe_invoice):
    subscription_id = stripe_invoice.get("subscription")

    if subscription_id:
        return subscription_id

    parent = stripe_invoice.get("parent") or {}
    subscription_details = parent.get("subscription_details") or {}
    return subscription_details.get("subscription")


def get_subscription_sync_rank(stripe_subscription):
    price_id = get_subscription_line_price_id(stripe_subscription)
    plan = get_plan_for_stripe_price(price_id)
    status = stripe_subscription_status_to_local(stripe_subscription.get("status"))

    if plan not in {"pro", "family"} or status != "active":
        return None

    return (
        PLAN_RANK.get(plan, 0),
        int(stripe_subscription.get("current_period_end") or 0),
        int(stripe_subscription.get("created") or 0),
    )


def sync_best_stripe_subscription_for_user(user):
    subscription = get_or_create_subscription(user)

    if (
        subscription.provider != "stripe"
        or not subscription.provider_customer_id
        or not configure_stripe()
    ):
        return subscription

    try:
        stripe_subscriptions = stripe.Subscription.list(
            customer=subscription.provider_customer_id,
            status="all",
            limit=20,
        )
    except Exception as error:
        app.logger.warning("Stripe customer subscription sync failed: %s", error)
        return subscription

    candidates = []

    for stripe_subscription in stripe_subscriptions.get("data") or []:
        rank = get_subscription_sync_rank(stripe_subscription)

        if rank:
            candidates.append((rank, stripe_subscription))

    if not candidates:
        return subscription

    _rank, best_subscription = max(candidates, key=lambda candidate: candidate[0])
    return sync_stripe_subscription(best_subscription) or subscription


def find_user_for_stripe_subscription(stripe_subscription):
    metadata = stripe_subscription.get("metadata") or {}
    user_id = metadata.get("user_id")

    if user_id:
        try:
            user = db.session.get(User, int(user_id))
            if user:
                return user
        except (TypeError, ValueError):
            pass

    subscription_id = stripe_subscription.get("id")
    customer_id = stripe_subscription.get("customer")
    local_subscription = None

    if subscription_id:
        local_subscription = Subscription.query.filter_by(
            provider_subscription_id=subscription_id
        ).first()

    if not local_subscription and customer_id:
        local_subscription = Subscription.query.filter_by(
            provider_customer_id=customer_id
        ).first()

    return local_subscription.user if local_subscription else None


def sync_stripe_subscription(stripe_subscription, deleted=False):
    user = find_user_for_stripe_subscription(stripe_subscription)

    if not user:
        app.logger.warning(
            "Stripe subscription event ignored: no local user for subscription %s",
            stripe_subscription.get("id"),
        )
        return None

    local_subscription = get_or_create_subscription(user)
    incoming_subscription_id = stripe_subscription.get("id")
    is_current_subscription = (
        not local_subscription.provider_subscription_id
        or incoming_subscription_id == local_subscription.provider_subscription_id
    )

    if deleted:
        if not is_current_subscription:
            app.logger.info(
                "Stripe subscription deletion ignored for inactive local subscription %s",
                incoming_subscription_id,
            )
            return None

        return update_local_subscription_from_stripe(
            user=user,
            plan="free",
            status="active",
            customer_id=stripe_subscription.get("customer"),
            subscription_id=stripe_subscription.get("id"),
            current_period_start=None,
            current_period_end=None,
        )

    metadata = stripe_subscription.get("metadata") or {}
    price_id = get_subscription_line_price_id(stripe_subscription)
    plan = get_plan_for_stripe_price(price_id) or metadata.get("plan")

    if plan not in {"pro", "family"}:
        app.logger.warning(
            "Stripe subscription event ignored: unknown price %s for subscription %s",
            price_id,
            stripe_subscription.get("id"),
        )
        return None

    if (
        not is_current_subscription
        and local_subscription.status == "active"
        and PLAN_RANK.get(plan, 0) < PLAN_RANK.get(local_subscription.plan, 0)
    ):
        app.logger.info(
            "Stripe subscription event ignored: older lower plan %s cannot replace current %s",
            plan,
            local_subscription.plan,
        )
        return None

    return update_local_subscription_from_stripe(
        user=user,
        plan=plan,
        status=stripe_subscription_status_to_local(stripe_subscription.get("status")),
        customer_id=stripe_subscription.get("customer"),
        subscription_id=stripe_subscription.get("id"),
        current_period_start=datetime_from_unix(
            stripe_subscription.get("current_period_start")
        ),
        current_period_end=datetime_from_unix(
            stripe_subscription.get("current_period_end")
        ),
    )


def get_cecoin_pack(pack_id):
    normalized_id = str(pack_id or "").strip().lower()
    normalized_id = {
        "starter": "bronze",
        "boost": "gold",
        "power": "diamond",
    }.get(normalized_id, normalized_id)
    return next((pack for pack in CECOIN_PACKS if pack["id"] == normalized_id), None)


def get_cecoin_pack_price_id(pack):
    for env_name in [pack.get("priceEnv"), pack.get("legacyPriceEnv")]:
        price_id = os.environ.get(str(env_name or ""), "").strip()
        if price_id:
            return price_id

    return ""


def validate_cecoin_price_for_checkout(price_id):
    if not configure_stripe():
        return "Stripe nu este configurat complet."

    try:
        price = stripe.Price.retrieve(price_id)
    except Exception as error:
        app.logger.warning("Stripe CeCoins price validation failed: %s", error)
        return "Prețul Stripe pentru acest pachet nu a putut fi verificat."

    if not price.get("active", True):
        return "Prețul Stripe pentru acest pachet este inactiv."

    if price.get("recurring"):
        return (
            "Pachetele CeCoins trebuie să folosească un preț Stripe one-time, "
            "nu un preț de abonament. Creează un price one-time pentru acest pachet "
            "și actualizează variabila din Render."
        )

    return ""


def handle_stripe_cecoin_checkout_completed(session):
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    pack_id = metadata.get("pack_id")
    payment_status = session.get("payment_status")
    session_id = session.get("id")
    pack = get_cecoin_pack(pack_id)

    if not pack or not user_id:
        app.logger.warning("Stripe CeCoins checkout ignored: missing metadata.")
        return None

    if payment_status not in {"paid", "no_payment_required"}:
        app.logger.warning(
            "Stripe CeCoins checkout ignored: payment status %s.",
            payment_status,
        )
        return None

    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        user = None

    if not user:
        app.logger.warning("Stripe CeCoins checkout ignored: user %s not found.", user_id)
        return None

    existing_events = UsageEvent.query.filter_by(
        user_id=user.id,
        event_type="cecoin_purchase",
        source=pack["id"],
    ).all()

    if any(parse_usage_metadata(event).get("sessionId") == session_id for event in existing_events):
        return None

    customer_id = str(session.get("customer") or "").strip()

    if customer_id:
        subscription = get_or_create_subscription(user)

        if (
            subscription.provider != "stripe"
            or subscription.provider_customer_id != customer_id
        ):
            subscription.provider = "stripe"
            subscription.provider_customer_id = customer_id
            subscription.updated_at = datetime.utcnow()

    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="cecoin_purchase",
            source=pack["id"],
            metadata_json=json.dumps({
                "coins": int(pack["coins"]),
                "packId": pack["id"],
                "sessionId": session_id,
                "paymentStatus": payment_status,
                "priceEnv": pack["priceEnv"],
            }),
        )
    )
    db.session.commit()
    clear_leaderboard_cache()
    return user


def handle_stripe_checkout_completed(session):
    metadata = session.get("metadata") or {}

    if metadata.get("type") == "cecoins":
        return handle_stripe_cecoin_checkout_completed(session)

    plan = metadata.get("plan")
    user_id = metadata.get("user_id")
    subscription_id = session.get("subscription")
    payment_status = session.get("payment_status")

    if plan not in {"pro", "family"} or not user_id:
        app.logger.warning("Stripe checkout ignored: missing metadata.")
        return None

    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        user = None

    if not user:
        app.logger.warning("Stripe checkout ignored: user %s not found.", user_id)
        return None

    if subscription_id and configure_stripe():
        synced_subscription = sync_stripe_subscription_by_id(subscription_id)
        if synced_subscription:
            return synced_subscription

    fallback_status = "active" if payment_status in {"paid", "no_payment_required"} else "incomplete"

    return update_local_subscription_from_stripe(
        user=user,
        plan=plan,
        status=fallback_status,
        customer_id=session.get("customer"),
        subscription_id=subscription_id,
    )


def is_paid_subscription(subscription):
    return (
        subscription
        and subscription.status == "active"
        and subscription.plan in {"pro", "family"}
    )


def is_family_subscription(subscription):
    return subscription and subscription.status == "active" and subscription.plan == "family"


def family_profile_to_dict(profile):
    return {
        "id": profile.id,
        "name": profile.name,
        "color": profile.color,
        "avatar": profile.avatar,
        "isPrimary": bool(profile.is_primary),
        "createdAt": profile.created_at.isoformat() + "Z" if profile.created_at else None,
    }


def get_or_create_primary_family_profile(user):
    profile = FamilyProfile.query.filter_by(user_id=user.id, is_primary=True).first()

    if profile:
        return profile

    existing_profile = FamilyProfile.query.filter_by(user_id=user.id).order_by(
        FamilyProfile.created_at.asc()
    ).first()

    if existing_profile:
        existing_profile.is_primary = True
        db.session.commit()
        return existing_profile

    profile = FamilyProfile(
        user_id=user.id,
        name=user.name or "Profil principal",
        color="teal",
        avatar="user",
        is_primary=True,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def sanitize_family_profile_name(name):
    name = re.sub(r"\s+", " ", str(name or "")).strip()

    if len(name) < 2:
        return None

    return name[:80]


def parse_profile_id(value):
    if value in {None, "", "null", "undefined"}:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_requested_family_profile_id(data=None):
    payload = data or {}
    return parse_profile_id(
        request.args.get("profile_id")
        or request.args.get("family_profile_id")
        or payload.get("profile_id")
        or payload.get("family_profile_id")
    )


def resolve_cart_profile(user, requested_profile_id=None):
    subscription = get_or_create_subscription(user)

    if not is_family_subscription(subscription):
        return None

    primary_profile = get_or_create_primary_family_profile(user)
    assign_unprofiled_cart_items_to_profile(user, primary_profile)

    if requested_profile_id:
        profile = FamilyProfile.query.filter_by(
            id=requested_profile_id,
            user_id=user.id,
        ).first()
        if profile:
            return profile

    return primary_profile


def assign_unprofiled_cart_items_to_profile(user, profile):
    if not profile:
        return

    updated = CartItem.query.filter(
        CartItem.user_id == user.id,
        CartItem.family_profile_id.is_(None),
    ).update(
        {"family_profile_id": profile.id},
        synchronize_session=False,
    )

    if updated:
        db.session.commit()


def cart_query_for_profile(user, profile=None):
    query = CartItem.query.filter_by(user_id=user.id)

    if not profile:
        return query.filter(CartItem.family_profile_id.is_(None))

    return query.filter(CartItem.family_profile_id == profile.id)


def get_monthly_scan_count(user_id):
    month_start = get_month_start()
    return UsageEvent.query.filter(
        UsageEvent.user_id == user_id,
        UsageEvent.event_type == "scan",
        UsageEvent.created_at >= month_start,
    ).count()


def get_weekly_scan_count(user_id):
    return get_monthly_scan_count(user_id)


def get_usage_summary(user):
    subscription = get_or_create_subscription(user)
    has_paid_plan = is_paid_subscription(subscription)
    has_bonus_unlimited = bonus_unlimited_is_active(user)
    limit = None if has_paid_plan or has_bonus_unlimited else FREE_MONTHLY_SCAN_LIMIT
    used = get_monthly_scan_count(user.id)
    reset_at = get_next_month_start()
    bonus_credits = max(0, int(user.bonus_scan_credits or 0))
    remaining = None if limit is None else max(limit - used, 0)

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "monthlyScanLimit": limit,
        "monthlyScansUsed": used,
        "monthlyScansRemaining": remaining,
        "weeklyScanLimit": limit,
        "weeklyScansUsed": used,
        "weeklyScansRemaining": remaining,
        "freeScanLimit": limit,
        "freeScansUsed": used,
        "freeScansRemaining": remaining,
        "scanLimitPeriod": "month",
        "bonusScanCredits": bonus_credits,
        "bonusUnlimitedUntil": (
            user.bonus_unlimited_until.isoformat() + "Z"
            if user.bonus_unlimited_until
            else None
        ),
        "bonusUnlimitedActive": has_bonus_unlimited,
        "unlimitedSource": "plan" if has_paid_plan else ("invite" if has_bonus_unlimited else None),
        "resetsAt": reset_at.isoformat() + "Z",
        "isUnlimited": limit is None,
    }


def get_scan_limit_error():
    return {
        "code": "scan_limit_reached",
        "message": "Ai folosit scanările gratuite din această lună. Poți trece la Pro sau folosi scanări bonus.",
    }


def check_scan_usage_allowed(user):
    if user.is_admin:
        return {"allowed": True, "usage": get_usage_summary(user)}

    subscription = get_or_create_subscription(user)

    if is_paid_subscription(subscription):
        return {"allowed": True, "usage": get_usage_summary(user)}

    if bonus_unlimited_is_active(user):
        return {"allowed": True, "usage": get_usage_summary(user)}

    used = get_monthly_scan_count(user.id)

    if used >= FREE_MONTHLY_SCAN_LIMIT:
        if max(0, int(user.bonus_scan_credits or 0)) > 0:
            return {"allowed": True, "usage": get_usage_summary(user)}

        return {
            "allowed": False,
            "usage": get_usage_summary(user),
            "error": get_scan_limit_error(),
        }

    return {"allowed": True, "usage": get_usage_summary(user)}


def consume_scan_usage(user, source, metadata=None):
    scan_gate = check_scan_usage_allowed(user)

    if not scan_gate["allowed"] or user.is_admin:
        return scan_gate

    usage_metadata = metadata or {}
    subscription = get_or_create_subscription(user)
    should_use_bonus_credit = (
        not is_paid_subscription(subscription)
        and not bonus_unlimited_is_active(user)
        and get_monthly_scan_count(user.id) >= FREE_MONTHLY_SCAN_LIMIT
        and max(0, int(user.bonus_scan_credits or 0)) > 0
    )

    if should_use_bonus_credit:
        user.bonus_scan_credits = max(0, int(user.bonus_scan_credits or 0) - 1)
        usage_metadata = {**usage_metadata, "usedBonusScanCredit": True}

    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="scan",
            source=source,
            metadata_json=json.dumps(usage_metadata),
        )
    )
    db.session.commit()
    return {"allowed": True, "usage": get_usage_summary(user)}


def reserve_scan_usage(user, source, metadata=None):
    return consume_scan_usage(user, source, metadata)


def respond_scan_limit(scan_gate):
    return jsonify({
        "error": scan_gate["error"]["message"],
        "code": scan_gate["error"]["code"],
        "usage": scan_gate["usage"],
        "plans": PLAN_CATALOG,
    }), 402


def parse_usage_metadata(event):
    if not event or not event.metadata_json:
        return {}

    try:
        data = json.loads(event.metadata_json)
    except (TypeError, ValueError):
        return {}

    return data if isinstance(data, dict) else {}


def get_user_gamification_metrics(user_id, since=None):
    scan_query = UsageEvent.query.filter_by(
        user_id=user_id,
        event_type="scan",
    )
    history_query = ScanHistory.query.filter_by(user_id=user_id)
    favorites_query = Favorite.query.filter_by(user_id=user_id)
    cart_query = db.session.query(func.coalesce(func.sum(CartItem.quantity), 0)).filter(
        CartItem.user_id == user_id
    )
    cart_event_query = UsageEvent.query.filter_by(
        user_id=user_id,
        event_type="cart_add",
    )
    submissions_query = ProductSubmission.query.filter_by(
        user_id=user_id,
        status="approved",
    )
    invites_query = UsageEvent.query.filter_by(
        user_id=user_id,
        event_type="bonus_unlimited",
        source="referral_inviter",
    )

    if since:
        scan_query = scan_query.filter(UsageEvent.created_at >= since)
        history_query = history_query.filter(ScanHistory.scanned_at >= since)
        favorites_query = favorites_query.filter(Favorite.created_at >= since)
        cart_query = cart_query.filter(CartItem.created_at >= since)
        cart_event_query = cart_event_query.filter(UsageEvent.created_at >= since)
        submissions_query = submissions_query.filter(ProductSubmission.created_at >= since)
        invites_query = invites_query.filter(UsageEvent.created_at >= since)

    scan_count = scan_query.count()
    history_count = history_query.count()
    favorites_count = favorites_query.count()
    cart_count = cart_query.scalar() or 0
    cart_event_count = cart_event_query.count()
    approved_submissions = submissions_query.count()
    confirmed_invites = invites_query.count()

    return {
        "scanCount": max(scan_count, history_count),
        "historyCount": history_count,
        "favoritesCount": favorites_count,
        "cartCount": max(int(cart_count or 0), cart_event_count),
        "approvedSubmissions": approved_submissions,
        "confirmedInvites": confirmed_invites,
    }


def get_mission_claim_events(user_id, series_id=None, since=None):
    query = UsageEvent.query.filter_by(
        user_id=user_id,
        event_type="mission_claim",
    )

    if since:
        query = query.filter(UsageEvent.created_at >= since)

    events = query.order_by(UsageEvent.created_at.asc()).all()

    if series_id:
        prefix = f"{series_id}_"
        events = [event for event in events if str(event.source or "").startswith(prefix)]

    return events


def get_claimed_mission_events(user_id):
    events = get_mission_claim_events(user_id)
    return {event.source: event for event in events if event.source}


def get_claimed_mission_ids(user_id, series_id=None):
    return {
        event.source
        for event in get_mission_claim_events(user_id, series_id=series_id)
        if event.source
    }


def mission_target_from_source(source):
    try:
        return int(str(source or "").rsplit("_", 1)[1])
    except (IndexError, TypeError, ValueError):
        return 0


def calculate_claimed_mission_coins(user_id):
    total = 0

    for event in get_mission_claim_events(user_id):
        reward = parse_usage_metadata(event).get("reward") or {}
        total += int(reward.get("coins") or 0)

    return total


def calculate_claimed_invite_mission_coins(user_id):
    total = 0

    for event in get_mission_claim_events(user_id, series_id="invite"):
        reward = parse_usage_metadata(event).get("reward") or {}
        total += int(reward.get("coins") or 0)

    return total


def calculate_event_coin_total(user_id, event_type):
    total = 0
    events = UsageEvent.query.filter_by(
        user_id=user_id,
        event_type=event_type,
    ).all()

    for event in events:
        data = parse_usage_metadata(event)
        total += int(data.get("coins") or data.get("cost") or 0)

    return total


def calculate_referral_cecoin_bonus(user_id, metrics=None):
    metrics = metrics or get_user_gamification_metrics(user_id)
    expected_total = int(metrics.get("confirmedInvites", 0) or 0) * 100
    claimed_invite_total = calculate_claimed_invite_mission_coins(user_id)
    recorded_total = calculate_event_coin_total(user_id, "referral_cecoin_bonus")
    return max(recorded_total, max(0, expected_total - claimed_invite_total))


def calculate_activity_score(metrics):
    return (
        int(metrics["scanCount"]) * 3
        + int(metrics["favoritesCount"]) * 5
        + min(int(metrics["cartCount"]) * 2, 50)
        + int(metrics["approvedSubmissions"]) * 60
        + int(metrics["confirmedInvites"]) * 100
    )


def calculate_user_coins(user_id, metrics=None):
    earned = (
        calculate_claimed_mission_coins(user_id)
        + calculate_event_coin_total(user_id, "cecoin_purchase")
        + calculate_referral_cecoin_bonus(user_id, metrics)
    )
    spent = calculate_event_coin_total(user_id, "cecoin_spend")
    return max(0, earned - spent)


def clear_leaderboard_cache():
    LEADERBOARD_CACHE.clear()


def empty_leaderboard(current_user_id=None, metrics=None, coins=0):
    metrics = metrics or {}
    return {
        "top": [],
        "currentUser": {
            "userId": current_user_id,
            "rank": None,
            "name": "Tu",
            "coins": coins,
            "score": calculate_activity_score({
                "scanCount": metrics.get("scanCount", 0),
                "favoritesCount": metrics.get("favoritesCount", 0),
                "cartCount": metrics.get("cartCount", 0),
                "approvedSubmissions": metrics.get("approvedSubmissions", 0),
                "confirmedInvites": metrics.get("confirmedInvites", 0),
            }),
            "scanCount": metrics.get("scanCount", 0),
            "approvedSubmissions": metrics.get("approvedSubmissions", 0),
            "isCurrentUser": True,
        },
    }


def build_mission_title(series_id, target):
    target = int(target or 0)

    if series_id == "scan":
        return f"Scanează {target} produs" if target == 1 else f"Scanează {target} produse"

    if series_id == "cart":
        return f"Pune {target} produs în coș" if target == 1 else f"Pune {target} produse în coș"

    if series_id == "favorite":
        return "Salvează 1 produs favorit" if target == 1 else f"Salvează {target} produse favorite"

    if series_id == "catalog":
        return "Adaugă 1 produs aprobat" if target == 1 else f"Adaugă {target} produse aprobate"

    if series_id == "invite":
        return "Invită prieteni"

    return f"Misiune {target}"


def build_mission_statuses(user_id, metrics=None):
    all_time_metrics = metrics or get_user_gamification_metrics(user_id)
    day_start = get_day_start()
    next_day_start = get_next_day_start()
    daily_metrics = get_user_gamification_metrics(user_id, since=day_start)
    missions = []

    for series in MISSION_SERIES:
        series_id = series["seriesId"]
        is_daily = bool(series.get("daily", False))
        series_missions = [
            mission for mission in MISSION_CATALOG
            if mission["seriesId"] == series_id
        ]
        claimed_ids = get_claimed_mission_ids(user_id, series_id=series_id)
        claimed_today = False

        if is_daily:
            claimed_today = bool(get_mission_claim_events(
                user_id,
                series_id=series_id,
                since=day_start,
            ))

        if series_id == "invite":
            confirmed_invites = int(all_time_metrics.get(series["metric"], 0) or 0)
            display_target = max(1, confirmed_invites)
            display_current = confirmed_invites
            progress = 100 if confirmed_invites > 0 else 0
            reward = {
                "coins": series.get("coins", 100),
                "bonusScans": 0,
                "bonusDays": 0,
            }

            missions.append({
                "id": series_missions[0]["id"],
                "seriesId": series_id,
                "tier": 1,
                "icon": series.get("icon"),
                "title": build_mission_title(series_id, display_target),
                "description": series["description"],
                "current": display_current,
                "target": display_target,
                "progress": progress,
                "completed": False,
                "claimed": False,
                "claimedToday": False,
                "claimable": False,
                "automatic": True,
                "daily": False,
                "availableAt": None,
                "reward": reward,
            })
            continue

        mission = next(
            (
                item for item in series_missions
                if item["id"] not in claimed_ids
            ),
            series_missions[-1],
        )
        previous_target = max(
            [
                mission_target_from_source(claimed_id)
                for claimed_id in claimed_ids
                if claimed_id != mission["id"]
            ]
            or [0]
        )

        if is_daily:
            raw_current = 0 if claimed_today else int(daily_metrics.get(mission["metric"], 0) or 0)
            display_target = int(mission["target"])
            display_current = min(raw_current, display_target)
        else:
            cumulative_current = int(all_time_metrics.get(mission["metric"], 0) or 0)
            display_target = max(1, int(mission["target"]) - previous_target)
            raw_current = max(0, cumulative_current - previous_target)
            display_current = min(raw_current, display_target)

        completed = raw_current >= display_target and not (is_daily and claimed_today)
        reward = {
            "coins": mission.get("coins", 0),
            "bonusScans": mission.get("bonusScans", 0),
            "bonusDays": mission.get("bonusDays", 0),
        }
        title = build_mission_title(series_id, display_target)

        missions.append({
            "id": mission["id"],
            "seriesId": mission["seriesId"],
            "tier": mission["tier"],
            "icon": mission.get("icon"),
            "title": title,
            "description": mission["description"],
            "current": display_current,
            "target": display_target,
            "progress": min(100, round((display_current / display_target) * 100)) if display_target else 100,
            "completed": completed,
            "claimed": False,
            "claimedToday": claimed_today,
            "claimable": completed,
            "daily": is_daily,
            "availableAt": (
                next_day_start.isoformat() + "Z"
                if claimed_today
                else None
            ),
            "reward": reward,
        })

    return missions


def count_completed_catalog_missions(user_id, metrics=None):
    return sum(
        1
        for mission in build_mission_statuses(user_id, metrics)
        if mission.get("completed") or mission.get("claimedToday")
    )


def build_user_leaderboard(current_user_id=None, limit=10, since=None):
    safe_limit = max(1, min(limit, 25))
    since_key = since.isoformat() if since else "all_time"
    cache_key = (safe_limit, since_key)
    cached = LEADERBOARD_CACHE.get(cache_key)

    if cached and time.time() - cached["created_at"] < LEADERBOARD_CACHE_TTL:
        rows = [dict(row) for row in cached["rows"]]
    else:
        users = User.query.order_by(User.created_at.asc()).all()
        rows = []

        for user in users:
            metrics = get_user_gamification_metrics(user.id, since=since)
            score = calculate_activity_score(metrics)
            coins = calculate_user_coins(user.id) if since is None else score

            rows.append({
                "userId": user.id,
                "name": (user.name or "Utilizator").split()[0],
                "coins": coins,
                "score": score,
                "scanCount": metrics["scanCount"],
                "approvedSubmissions": metrics["approvedSubmissions"],
            })

        rows.sort(
            key=lambda item: (
                item["coins"],
                item["scanCount"],
                item["approvedSubmissions"],
            ),
            reverse=True,
        )

        for index, row in enumerate(rows, start=1):
            row["rank"] = index

        LEADERBOARD_CACHE[cache_key] = {
            "created_at": time.time(),
            "rows": [dict(row) for row in rows],
        }

    for row in rows:
        row["isCurrentUser"] = row["userId"] == current_user_id

    top_rows = rows[:safe_limit]
    current_row = next((row for row in rows if row["isCurrentUser"]), None)

    return {
        "top": top_rows,
        "currentUser": current_row,
    }


def get_public_cecoin_packs():
    return [
        {
            "id": pack["id"],
            "title": pack["title"],
            "coins": pack["coins"],
            "priceText": pack["priceText"],
            "image": pack.get("image"),
            "icon": pack.get("icon"),
            "configured": bool(get_cecoin_pack_price_id(pack)),
        }
        for pack in CECOIN_PACKS
    ]


def get_gamification_summary_for_user(user, include_leaderboard=False):
    metrics = get_user_gamification_metrics(user.id)
    missions = build_mission_statuses(user.id, metrics)
    completed_count = sum(
        1
        for mission in missions
        if mission.get("completed") or mission.get("claimedToday")
    )
    claimed_count = sum(
        1
        for mission in missions
        if mission.get("claimedToday") or mission.get("claimed")
    )
    coins = calculate_user_coins(user.id, metrics)

    if include_leaderboard:
        try:
            week_start = get_week_start()
            all_time_leaderboard = build_user_leaderboard(user.id)
            weekly_leaderboard = build_user_leaderboard(user.id, since=week_start)
        except Exception:
            app.logger.exception("Gamification leaderboard failed")
            all_time_leaderboard = empty_leaderboard(user.id, metrics, coins)
            weekly_leaderboard = empty_leaderboard(user.id, metrics, coins)
    else:
        all_time_leaderboard = empty_leaderboard(user.id, metrics, coins)
        weekly_leaderboard = empty_leaderboard(user.id, metrics, coins)

    daily_claimed_coins = sum(
        int((mission.get("reward") or {}).get("coins") or 0)
        for mission in missions
        if mission.get("daily") and mission.get("claimedToday")
    )

    return {
        "coins": coins,
        "level": (
            "Expert la raft"
            if coins >= 500
            else "Cumpărător avansat"
            if coins >= 250
            else "În creștere"
            if coins >= 100
            else "Start bun"
        ),
        "metrics": metrics,
        "missions": missions,
        "completedMissions": completed_count,
        "claimedMissions": claimed_count,
        "totalMissions": len(missions),
        "dailyClaimedCoins": daily_claimed_coins,
        "dailyCoinLimit": 40,
        "missionsResetAt": get_next_day_start().isoformat() + "Z",
        "leaderboard": {
            "allTime": all_time_leaderboard,
            "weekly": weekly_leaderboard,
            "top": all_time_leaderboard["top"],
            "currentUser": all_time_leaderboard["currentUser"],
        },
        "shopItems": CECOIN_SHOP_ITEMS,
        "coinPacks": get_public_cecoin_packs(),
        "nextRewards": [
            {
                "title": "Pro",
                "description": "Scanări nelimitate și căutare după preferințe.",
                "href": "/pricing",
            },
            {
                "title": "Family",
                "description": "Profiluri separate pentru fiecare persoană din casă.",
                "href": "/pricing",
            },
            {
                "title": "Contribuie produse",
                "description": "Produsele aprobate îți aduc scanări bonus.",
                "href": "/submit-product",
            },
        ],
    }


ADMIN_ENDPOINTS = {
    "init_db",
    "get_users",
    "seed_products",
    "cleanup_duplicate_products",
    "ai_review_product_submission",
    "approve_product_submission",
    "get_admin_overview",
    "get_admin_submissions",
    "get_admin_search_misses",
    "delete_admin_product",
    "admin_update_user_plan",
    "get_readiness",
    "send_admin_email_test",
}

AUTH_ENDPOINTS = {
    "analyze_product",
    "ai_extract_product_info",
    "add_to_cart",
    "update_cart_item",
    "delete_cart_item",
    "clear_cart",
    "add_to_favorites",
    "delete_favorite_item",
    "clear_favorites",
    "add_scan_history",
    "delete_scan_history_item",
    "clear_scan_history",
    "get_user_submissions",
    "add_product_submission",
    "delete_product_submission",
    "get_submission_image",
    "get_supabase_submission_image",
    "report_local_price",
    "import_barcode_product",
    "identify_product_frame",
    "lookup_barcode",
    "translate_text",
    "logout",
    "get_open_food_facts_alternatives",
    "get_billing_status",
    "get_dashboard_summary",
    "get_gamification_summary",
    "claim_gamification_mission",
    "redeem_cecoin_reward",
    "start_cecoin_checkout",
    "sync_cecoin_checkout_session",
    "start_checkout",
    "start_billing_portal",
    "get_family_profiles",
    "create_family_profile",
    "update_family_profile",
    "delete_family_profile",
    "request_account_deletion",
}

USER_PATH_ENDPOINTS = {
    "get_cart",
    "clear_cart",
    "get_favorites",
    "clear_favorites",
    "get_scan_history",
    "clear_scan_history",
    "get_user_submissions",
}

USER_BODY_ENDPOINTS = {
    "add_to_cart",
    "add_to_favorites",
    "add_scan_history",
    "report_local_price",
}

ITEM_OWNER_MODELS = {
    "update_cart_item": (CartItem, "item_id"),
    "delete_cart_item": (CartItem, "item_id"),
    "delete_favorite_item": (Favorite, "favorite_id"),
    "delete_scan_history_item": (ScanHistory, "history_id"),
    "delete_product_submission": (ProductSubmission, "submission_id"),
}


@app.before_request
def enforce_access_controls():
    g.request_id = get_request_id()
    endpoint = request.endpoint

    if not endpoint or endpoint == "static":
        return None

    if endpoint == "health":
        return None

    if not rate_limit("global", GLOBAL_RATE_LIMIT, GLOBAL_RATE_LIMIT_WINDOW):
        return jsonify({"error": "Prea multe cereri. Reîncearcă în câteva secunde."}), 429

    payload_error = validate_request_payload()

    if payload_error:
        return payload_error

    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        if not request_origin_is_trusted() or not request_fetch_metadata_is_trusted():
            return jsonify({"error": "Cererea a fost blocata din motive de securitate."}), 403

    if endpoint in {
        "login",
        "register",
        "verify_email",
        "resend_email_verification",
        "forgot_password",
        "reset_password",
        "request_account_deletion",
        "confirm_account_deletion",
    } and not rate_limit(endpoint, AUTH_RATE_LIMIT, AUTH_RATE_LIMIT_WINDOW):
        return jsonify({"error": "Prea multe încercări. Așteaptă puțin."}), 429

    if endpoint in {"identify_product_frame", "lookup_barcode"} and not rate_limit(
        endpoint, 45, 60
    ):
        return jsonify({"error": "Prea multe cereri. Reîncearcă în câteva secunde."}), 429

    if endpoint == "translate_text" and not rate_limit(endpoint, 120, 60):
        return jsonify({"error": "Prea multe traduceri. Reîncearcă în câteva secunde."}), 429

    if endpoint in {"ai_extract_product_info", "get_open_food_facts_alternatives"} and not rate_limit(
        endpoint, 30, 60
    ):
        return jsonify({"error": "Prea multe cereri. Reîncearcă în câteva secunde."}), 429

    needs_auth = (
        endpoint in AUTH_ENDPOINTS
        or endpoint in ADMIN_ENDPOINTS
        or endpoint in USER_PATH_ENDPOINTS
    )

    if not needs_auth:
        return None

    user = get_current_user()

    if not user:
        return jsonify({"error": "Autentificare necesară."}), 401

    g.current_user = user

    if endpoint in ADMIN_ENDPOINTS and not user.is_admin:
        return jsonify({"error": "Acces rezervat administratorului."}), 403

    if endpoint in USER_PATH_ENDPOINTS:
        user_id = request.view_args.get("user_id")

        if user_id is not None and not require_same_user(user_id):
            return jsonify({"error": "Nu poți accesa datele altui cont."}), 403

    if endpoint in ITEM_OWNER_MODELS and not user.is_admin:
        model, argument_name = ITEM_OWNER_MODELS[endpoint]
        item = db.session.get(model, request.view_args.get(argument_name))

        if item and item.user_id != user.id:
            return jsonify({"error": "Nu poți modifica datele altui cont."}), 403

    if endpoint in USER_BODY_ENDPOINTS and not user.is_admin:
        data = request.get_json(silent=True) or {}

        if data.get("user_id") and not require_same_user(data["user_id"]):
            return jsonify({"error": "Nu poți modifica datele altui cont."}), 403

    if endpoint == "add_product_submission" and not user.is_admin:
        user_id = request.form.get("user_id")

        if user_id and not require_same_user(user_id):
            return jsonify({"error": "Nu poți trimite produse pentru alt cont."}), 403

    return None


@app.after_request
def add_security_headers(response):
    endpoint = request.endpoint
    is_sensitive_response = (
        endpoint in AUTH_ENDPOINTS
        or endpoint in ADMIN_ENDPOINTS
        or endpoint in USER_PATH_ENDPOINTS
        or endpoint
        in {
            "login",
            "register",
            "verify_email",
            "resend_email_verification",
            "forgot_password",
            "reset_password",
            "get_authenticated_user",
            "confirm_account_deletion",
        }
    )

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    )
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault(
        "X-Request-ID",
        getattr(g, "request_id", uuid4().hex),
    )

    if is_sensitive_response:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"

    if PRODUCTION_MODE:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    return response


@app.errorhandler(413)
def handle_request_too_large(_error):
    return jsonify({
        "error": "Fisierul sau cererea depaseste limita acceptata.",
        "requestId": getattr(g, "request_id", uuid4().hex),
    }), 413


@app.errorhandler(405)
def handle_method_not_allowed(_error):
    return jsonify({
        "error": "Metoda HTTP nu este acceptata pentru aceasta ruta.",
        "requestId": getattr(g, "request_id", uuid4().hex),
    }), 405


@app.errorhandler(500)
def handle_internal_server_error(error):
    request_id = getattr(g, "request_id", uuid4().hex)
    app.logger.error(
        "Unhandled server error. request_id=%s endpoint=%s",
        request_id,
        request.endpoint,
        exc_info=error,
    )
    return jsonify({
        "error": "A apărut o eroare internă. Reîncearcă în câteva momente.",
        "requestId": request_id,
    }), 500


PRODUCTS_DB_SEED = [
    {
        "name": "Iaurt grecesc 2% grăsime",
        "store": "Kaufland",
        "category": "Lactate",
        "score": 8.6,
        "tag": "Best value",
        "image": "/products/iaurt-grecesc.jpg",
        "price": 3.49,
        "price_text": "aprox. 3.49 lei",
        "calories": 73,
        "protein": 7.5,
        "sugar": 3.8,
        "fat": 2,
        "vegan": False,
        "lactose_free": False,
        "natural": True,
        "reason": "Mai ieftin per 100g, ingrediente simple și proteină decentă pentru preț.",
    },
    {
        "name": "Skyr natural",
        "store": "Kaufland",
        "category": "Lactate",
        "score": 8.9,
        "tag": "Mai multă proteină",
        "image": "/products/skyr.jpg",
        "price": 4.99,
        "price_text": "aprox. 4.99 lei",
        "calories": 65,
        "protein": 11,
        "sugar": 4,
        "fat": 0.2,
        "vegan": False,
        "lactose_free": False,
        "natural": True,
        "reason": "Proteină mai mare, zahăr redus și sațietate bună. Potrivit pentru sală sau dietă.",
    },
    {
        "name": "Iaurt simplu fără zahăr",
        "store": "Kaufland",
        "category": "Lactate",
        "score": 8.2,
        "tag": "Mai sănătos",
        "image": "/products/iaurt-simplu.jpg",
        "price": 2.99,
        "price_text": "aprox. 2.99 lei",
        "calories": 61,
        "protein": 4.2,
        "sugar": 3.5,
        "fat": 3,
        "vegan": False,
        "lactose_free": False,
        "natural": True,
        "reason": "Mai puțin zahăr și mai puțini aditivi. O alegere mai curată pentru consum zilnic.",
    },
    {
        "name": "Băutură vegetală ovăz",
        "store": "Lidl",
        "category": "Lactate",
        "score": 7.9,
        "tag": "De post",
        "image": "/products/lapte-ovaz.jpg",
        "price": 5.49,
        "price_text": "aprox. 5.49 lei",
        "calories": 46,
        "protein": 1.1,
        "sugar": 3.2,
        "fat": 1.5,
        "vegan": True,
        "lactose_free": True,
        "natural": True,
        "reason": "Variantă de post, fără lactoză, potrivită pentru cafea sau cereale.",
    },
    {
        "name": "Iaurt proteic Lidl",
        "store": "Lidl",
        "category": "Lactate",
        "score": 8.4,
        "tag": "Mai multă proteină",
        "image": "/products/iaurt-proteic-lidl.jpg",
        "price": 4.49,
        "price_text": "aprox. 4.49 lei",
        "calories": 72,
        "protein": 10,
        "sugar": 4.5,
        "fat": 0.5,
        "vegan": False,
        "lactose_free": False,
        "natural": False,
        "reason": "Proteină bună pentru preț și potrivit ca gustare după sală.",
    },
    {
        "name": "Iaurt natural Lidl",
        "store": "Lidl",
        "category": "Lactate",
        "score": 7.8,
        "tag": "Mai ieftin",
        "image": "/products/iaurt-natural-lidl.jpg",
        "price": 2.39,
        "price_text": "aprox. 2.39 lei",
        "calories": 62,
        "protein": 4,
        "sugar": 3.8,
        "fat": 3.2,
        "vegan": False,
        "lactose_free": False,
        "natural": True,
        "reason": "Preț bun și ingrediente simple. Nu are proteină foarte mare, dar e ok pentru consum zilnic.",
    },
    {
        "name": "Baton proteic ciocolată",
        "store": "Carrefour",
        "category": "Snacks",
        "score": 7.5,
        "tag": "Proteină",
        "image": "/products/baton-proteic.jpg",
        "price": 6.99,
        "price_text": "aprox. 6.99 lei",
        "calories": 210,
        "protein": 20,
        "sugar": 2,
        "fat": 7,
        "vegan": False,
        "lactose_free": False,
        "natural": False,
        "reason": "Proteină mare și zahăr redus, dar prețul este ridicat pentru o gustare.",
    },
    {
        "name": "Baton ovăz și fructe",
        "store": "Carrefour",
        "category": "Snacks",
        "score": 7.1,
        "tag": "Mai natural",
        "image": "/products/baton-ovaz.jpg",
        "price": 3.99,
        "price_text": "aprox. 3.99 lei",
        "calories": 180,
        "protein": 4,
        "sugar": 8,
        "fat": 5,
        "vegan": True,
        "lactose_free": True,
        "natural": True,
        "reason": "Ingrediente mai simple și preț decent, dar proteină mai mică.",
    },
]


# =========================
# Helpers
# =========================

DEFAULT_LIMITED_PRODUCT_REASON = (
    "Informațiile nutriționale sunt limitate. Verifică zahărul, caloriile și "
    "ingredientele de pe etichetă, apoi compară produsul cu variante similare."
)


def clean_product_reason(reason):
    text_value = str(reason or "").strip()
    normalized = normalize_search_text(text_value)

    if not text_value:
        return DEFAULT_LIMITED_PRODUCT_REASON

    outdated_phrases = [
        "adaugat de comunitate",
        "adaugat automat",
        "produs adaugat",
        "verificat automat",
        "poate fi comparat",
    ]

    if any(phrase in normalized for phrase in outdated_phrases):
        return DEFAULT_LIMITED_PRODUCT_REASON

    return text_value


def cart_item_to_dict(item):
    return {
        "id": item.id,
        "user_id": item.user_id,
        "familyProfileId": item.family_profile_id,
        "name": item.product_name,
        "store": item.store,
        "score": item.score,
        "price": item.price,
        "image": item.image,
        "reason": clean_product_reason(item.reason),
        "quantity": item.quantity,
        "bought": item.bought,
        "created_at": item.created_at.isoformat(),
    }


def favorite_item_to_dict(item):
    return {
        "id": item.id,
        "user_id": item.user_id,
        "name": item.product_name,
        "store": item.store,
        "category": item.category,
        "score": item.score,
        "price": item.price,
        "image": item.image,
        "reason": clean_product_reason(item.reason),
        "created_at": item.created_at.isoformat(),
    }


def scan_history_item_to_dict(item):
    return {
        "id": item.id,
        "user_id": item.user_id,
        "name": item.product_name,
        "store": item.store,
        "category": item.category,
        "score": item.score,
        "price": item.price,
        "image": item.image,
        "verdict": clean_product_reason(item.verdict),
        "shortAdvice": clean_product_reason(item.short_advice),
        "scanned_at": item.scanned_at.isoformat(),
    }


def product_to_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "store": product.store,
        "category": product.category,
        "score": product.score,
        "tag": product.tag,
        "image": product.image,
        "price": product.price,
        "priceText": product.price_text,
        "calories": product.calories,
        "protein": product.protein,
        "sugar": product.sugar,
        "fat": product.fat,
        "vegan": product.vegan,
        "lactoseFree": product.lactose_free,
        "natural": product.natural,
        "reason": clean_product_reason(product.reason),
        "ingredients": product.ingredients,
        "barcode": product.barcode,
    }


def product_submission_to_dict(item):
    return {
        "id": item.id,
        "user_id": item.user_id,
        "product_name": item.product_name,
        "brand": item.brand,
        "store": item.store,
        "category": item.category,
        "quantity": item.quantity,
        "barcode": item.barcode,
        "price": item.price,
        "front_image": item.front_image,
        "nutrition_image": item.nutrition_image,
        "calories": item.calories,
        "protein": item.protein,
        "sugar": item.sugar,
        "fat": item.fat,
        "ingredients": item.ingredients,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
    }


def get_store_name_from_id(store_id):
    stores = {
        "lidl": "Lidl",
        "kaufland": "Kaufland",
        "carrefour": "Carrefour",
        "mega": "Mega Image",
        "profi": "Profi",
        "penny": "Penny",
        "local": "Market local",
        "any": "Fără magazin ales",
    }

    return stores.get(store_id, "Fără magazin ales")


def record_search_event(search_text, store=None, result_count=0, source="search", user_id=None):
    normalized_text = str(search_text or "").strip()

    if not normalized_text:
        return

    db.session.add(SearchEvent(
        user_id=user_id if user_id and db.session.get(User, user_id) else None,
        search_text=normalized_text[:250],
        store=str(store or "").strip()[:100] or None,
        result_count=max(0, int(result_count or 0)),
        source=str(source or "search").strip()[:40],
    ))


def infer_alternative_criteria_from_request(request_text):
    text_value = normalize_search_text(request_text)
    criteria = []

    if not text_value:
        return criteria

    if any(token in text_value for token in ["ieftin", "pret mic", "mai ieftin", "sub "]):
        criteria.append("cheap")

    if any(token in text_value for token in ["proteina", "protein", "proteic"]):
        criteria.append("protein")

    if any(token in text_value for token in ["zahar", "zero sugar", "fara zahar", "no sugar"]):
        criteria.append("low_sugar")

    if any(token in text_value for token in ["calorii", "slabit", "dieta", "low calorie"]):
        criteria.append("low_calorie")

    if any(token in text_value for token in ["cafeina", "cofeina", "caffeine", "taurina", "energiz", "energie"]):
        criteria.append("caffeine")

    if any(token in text_value for token in ["vegan", "post", "vegetal"]):
        criteria.append("vegan")

    if any(token in text_value for token in ["lactoza", "lactose"]):
        criteria.append("lactose_free")

    if any(token in text_value for token in ["curat", "natural", "ingrediente simple", "fara aditivi"]):
        criteria.append("natural")

    return list(dict.fromkeys(criteria))


def get_cached_product_search_results(cache_key):
    cache_item = PRODUCT_SEARCH_RESULT_CACHE.get(cache_key)

    if not cache_item:
        return None

    if time.time() - cache_item["created_at"] > PRODUCT_SEARCH_RESULT_CACHE_TTL:
        PRODUCT_SEARCH_RESULT_CACHE.pop(cache_key, None)
        return None

    return [dict(item) for item in cache_item["results"]]


def set_cached_product_search_results(cache_key, results):
    PRODUCT_SEARCH_RESULT_CACHE[cache_key] = {
        "created_at": time.time(),
        "results": [dict(item) for item in results],
    }


def product_to_analysis_result(product, uploaded_filename):
    return {
        "id": product.id,
        "name": product.name,
        "store": product.store,
        "score": product.score,
        "category": product.category,
        "price": product.price_text,
        "calories": product.calories,
        "protein": product.protein,
        "sugar": product.sugar,
        "fat": product.fat,
        "image": product.image,
        "verdict": product.reason or "Produs analizat pe baza informațiilor disponibile.",
        "shortAdvice": product.reason or "Produsul poate fi comparat cu alternative din aceeași categorie.",
        "uploadedFile": uploaded_filename,
    }


def product_data_to_analysis_result(product_data, uploaded_filename, store_name=None):
    display_store = (
        store_name
        if store_name and store_name != "Fără magazin ales"
        else product_data.get("store", "Open Food Facts")
    )

    return {
        "id": product_data.get("id"),
        "barcode": product_data.get("barcode"),
        "name": product_data.get("name"),
        "brand": product_data.get("brand"),
        "store": display_store,
        "source": product_data.get("source", "openfoodfacts"),
        "score": product_data.get("score"),
        "category": product_data.get("category"),
        "price": product_data.get("priceText") or product_data.get("price"),
        "calories": product_data.get("calories"),
        "protein": product_data.get("protein"),
        "sugar": product_data.get("sugar"),
        "fat": product_data.get("fat"),
        "image": (
            product_data.get("image")
            or f"/uploads/scans/{uploaded_filename}"
        ),
        "verdict": product_data.get("reason") or DEFAULT_LIMITED_PRODUCT_REASON,
        "shortAdvice": product_data.get("reason") or DEFAULT_LIMITED_PRODUCT_REASON,
        "ingredients": product_data.get("ingredients"),
        "limitedData": bool(product_data.get("limitedData")),
        "uploadedFile": uploaded_filename,
    }


def infer_category_from_query(search_text):
    product_type = detect_product_type(search_text)

    category_map = {
        "water": "Apă",
        "juice": "Sucuri",
        "soft_drink": "Băuturi răcoritoare",
        "coffee_drink": "Băuturi cu cafea",
        "ice_cream": "Înghețată",
        "spread": "Creme tartinabile",
        "fruit_yogurt": "Iaurturi cu fructe",
        "yogurt": "Lactate",
        "cheese": "Lactate și brânzeturi",
        "energy_drink": "Băuturi energizante",
        "instant_noodles": "Tăiței instant",
        "chips": "Snacks sărate",
        "cereal": "Cereale",
        "protein": "Proteine și fitness",
        "sauce": "Sosuri și condimente",
        "bread": "Panificație",
        "pizza": "Pizza",
        "ready_meal": "Mese gata preparate",
        "meat": "Carne",
        "fish": "Pește și fructe de mare",
    }

    return category_map.get(product_type, "Categorie neconfirmată")


def build_limited_analysis_result(product_name, uploaded_filename, store_name):
    return {
        "id": None,
        "barcode": None,
        "name": product_name.strip(),
        "brand": detect_query_brand(product_name),
        "store": store_name,
        "source": "user_identified",
        "score": None,
        "category": infer_category_from_query(product_name),
        "price": None,
        "calories": None,
        "protein": None,
        "sugar": None,
        "fat": None,
        "image": f"/uploads/scans/{uploaded_filename}",
        "verdict": (
            "Produs identificat după numele introdus și textul vizibil de pe ambalaj. "
            "Datele nutriționale nu sunt disponibile încă; fotografiază eticheta "
            "nutrițională sau scanează codul de bare pentru o analiză completă."
        ),
        "shortAdvice": (
            "Identitatea produsului este posibilă, dar valorile nutriționale trebuie "
            "confirmate de pe etichetă sau prin codul de bare."
        ),
        "ingredients": None,
        "limitedData": True,
        "uploadedFile": uploaded_filename,
    }


def parse_optional_float(value):
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_barcode(barcode, required=False):
    barcode = str(barcode or "").strip()

    if not barcode:
        return "Codul de bare lipsește." if required else None

    if not re.fullmatch(r"\d{8,14}", barcode):
        return "Codul de bare trebuie să conțină între 8 și 14 cifre."

    if len(barcode) in {8, 12, 13, 14} and not has_valid_gs1_checksum(barcode):
        return "Codul de bare pare citit greșit. Verifică cifrele sau scanează din nou."

    return None


def has_valid_gs1_checksum(barcode):
    digits = [int(digit) for digit in barcode]
    check_digit = digits.pop()
    weighted_sum = 0

    for position, digit in enumerate(reversed(digits)):
        weighted_sum += digit * (3 if position % 2 == 0 else 1)

    return (10 - weighted_sum % 10) % 10 == check_digit


def get_barcode_lookup_candidates(barcode):
    barcode = str(barcode or "").strip()
    candidates = [barcode] if barcode else []

    if len(barcode) == 13 and barcode.startswith("0"):
        upc_candidate = barcode[1:]

        if has_valid_gs1_checksum(upc_candidate):
            candidates.append(upc_candidate)

    if len(barcode) == 12:
        ean_candidate = f"0{barcode}"

        if has_valid_gs1_checksum(ean_candidate):
            candidates.append(ean_candidate)

    return list(dict.fromkeys(candidates))


def validate_text_length(value, label, max_length, min_length=0):
    value = str(value or "").strip()

    if value and len(value) < min_length:
        return f"{label} trebuie să conțină cel puțin {min_length} caractere."

    if len(value) > max_length:
        return f"{label} poate conține maximum {max_length} caractere."

    return None


def validate_nutrition_values(calories, protein, sugar, fat):
    limits = {
        "Caloriile": (calories, 1000),
        "Proteina": (protein, 100),
        "Zahărul": (sugar, 100),
        "Grăsimile": (fat, 100),
    }

    for label, (value, maximum) in limits.items():
        if value is None:
            continue

        if value < 0 or value > maximum:
            return f"{label} trebuie să fie între 0 și {maximum} per 100 g/ml."

    return None


def parse_form_float(form, field_name, label):
    raw_value = form.get(field_name)

    if raw_value is None or raw_value == "":
        return None, None

    value = parse_optional_float(raw_value)

    if value is None:
        return None, f"{label} trebuie să fie un număr valid."

    return value, None

def normalize_search_text(text):
    if not text:
        return ""

    text = text.lower().strip()

    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    replacements = {
        "-": " ",
        "_": " ",
        ".": " ",
        ",": " ",
        "/": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    words = text.split()
    return " ".join(words)


def expand_query_with_synonyms(text):
    normalized = normalize_search_text(text)
    words = normalized.split()

    synonyms = {
        "0": "zero sugar fara zahar",
        "zero": "0 fara zahar sugar",
        "alb": "white",
        "alba": "white",
        "fara": "zero",
        "zahăr": "sugar",
        "zahar": "sugar",
        "redbull": "red bull",
        "red": "redbull",
        "bull": "redbull",
        "energizant": "energy",
        "energizanta": "energy",
        "energie": "energy",
        "doza": "can",
        "bautura": "drink",
        "băutură": "drink",
        "proteic": "protein",
        "proteina": "protein",
        "inghetata": "ice cream gelato",
        "gelatelli": "gelatelli",
        "alune": "hazelnut",
        "aluna": "hazelnut",
        "vanilie": "vanilla",
        "ciocolata": "chocolate",
    }

    expanded_words = []

    for word in words:
        expanded_words.append(word)

        if word in synonyms:
            expanded_words.append(synonyms[word])

    return " ".join(expanded_words)


SEARCH_STOPWORDS = {
    "a",
    "al",
    "ale",
    "cu",
    "de",
    "din",
    "fara",
    "la",
    "pe",
    "si",
    "sau",
    "the",
    "with",
    "without",
}


def get_product_field(product, field, default=""):
    if isinstance(product, dict):
        return product.get(field, default)

    return getattr(product, field, default)


def get_important_query_words(search_text):
    normalized = normalize_search_text(search_text)
    raw_words = normalized.split()
    words = []

    for word in raw_words:
        if word in SEARCH_STOPWORDS:
            continue

        if len(word) >= 3 or word in {"0"}:
            words.append(word)

        if word == "redbull":
            words.extend(["red", "bull"])

        if word == "0":
            words.append("zero")

        if word == "zero":
            words.append("0")

        if word == "inghetata":
            words.extend(["ice", "cream", "gelato"])

        if word in {"alune", "aluna"}:
            words.append("hazelnut")

    if "red bull" in normalized:
        words.extend(["red", "bull", "redbull"])

    if "fara zahar" in normalized or "no sugar" in normalized:
        words.extend(["zero", "sugar", "zahar"])

    return words


def query_has_product_overlap(query_words, product_text):
    product_words = set(product_text.split())

    for word in query_words:
        if word in product_words:
            return True

        if len(word) >= 4 and any(word in product_word or product_word in word for product_word in product_words):
            return True

    return False


def detect_query_brand(search_text):
    text = normalize_search_text(search_text)
    words = set(text.split())

    if "gelatelli" in words:
        return "gelatelli"

    if "zuzu" in words:
        return "zuzu"

    if "samyang" in words:
        return "samyang"

    if "redbull" in text or "red bull" in text or {"red", "bull"}.issubset(words):
        return "redbull"

    brand_aliases = {
        "monster": {"monster"},
        "hell": {"hell"},
        "burn": {"burn"},
        "rockstar": {"rockstar"},
        "pepsi": {"pepsi"},
        "coca-cola": {"coca", "cola", "coca-cola", "cocacola"},
        "mountain dew": {"mountain", "dew", "mountaindew"},
        "buldak": {"buldak"},
    }

    for brand, aliases in brand_aliases.items():
        if any(alias in words or alias in text for alias in aliases):
            return brand

    return None


def detect_product_type(search_text):
    text = normalize_search_text(search_text)

    yogurt_tokens = {"iaurt", "yogurt", "yoghurt", "skyr", "zuzu"}
    fruit_tokens = {
        "fruct",
        "fructe",
        "capsuni",
        "strawberry",
        "piersici",
        "peach",
        "visine",
        "cherry",
        "afine",
        "blueberry",
        "zmeura",
        "raspberry",
        "padure",
        "berries",
    }

    if any(token in text for token in yogurt_tokens) and any(
        token in text for token in fruit_tokens
    ):
        return "fruit_yogurt"

    product_types = [
        (
            "water",
            {
                "apa",
                "water",
                "mineral",
                "minerala",
                "spring water",
            },
        ),
        (
            "juice",
            {
                "suc",
                "juice",
                "nectar",
                "fresh",
            },
        ),
        (
            "soft_drink",
            {
                "cola",
                "pepsi",
                "coca cola",
                "cocacola",
                "soda",
                "soft drink",
                "bautura racoritoare",
            },
        ),
        (
            "coffee_drink",
            {
                "coffee",
                "cafea",
                "cappuccino",
                "capuccino",
                "latte",
                "mocha",
                "espresso",
                "iced coffee",
                "ice coffee",
                "cold brew",
                "frappe",
            },
        ),
        (
            "ice_cream",
            {
                "inghetata",
                "gelato",
                "ice cream",
                "icecream",
                "sorbet",
            },
        ),
        (
            "spread",
            {
                "crema tartinabila",
                "spread",
                "nutella",
            },
        ),
        (
            "yogurt",
            {
                "iaurt",
                "yogurt",
                "yoghurt",
                "skyr",
            },
        ),
        (
            "instant_noodles",
            {
                "buldak",
                "samyang",
                "ramen",
                "noodle",
                "noodles",
                "taitei",
                "cup noodles",
                "instant noodles",
            },
        ),
        (
            "cheese",
            {
                "branza",
                "cheese",
                "cascaval",
                "mozzarella",
            },
        ),
        (
            "energy_drink",
            {
                "energizant",
                "energy drink",
                "red bull",
                "redbull",
                "monster",
                "hell",
            },
        ),
        (
            "chips",
            {
                "chips",
                "snack",
                "crackers",
                "pufule",
                "popcorn",
            },
        ),
        (
            "cereal",
            {
                "cereale",
                "cereal",
                "muesli",
                "granola",
                "oatmeal",
            },
        ),
        (
            "protein",
            {
                "protein",
                "proteic",
                "proteina",
                "whey",
                "fitness",
            },
        ),
        (
            "sauce",
            {
                "sos",
                "sauce",
                "ketchup",
                "mustar",
                "mayonnaise",
                "maioneza",
                "salsa",
            },
        ),
        (
            "bread",
            {
                "paine",
                "bread",
                "chifla",
                "bagheta",
                "toast",
            },
        ),
        (
            "pizza",
            {
                "pizza",
            },
        ),
        (
            "ready_meal",
            {
                "ready meal",
                "meal",
                "sandwich",
                "salata",
                "supa",
                "soup",
                "frozen meal",
            },
        ),
        (
            "meat",
            {
                "carne",
                "meat",
                "salam",
                "sausage",
                "carnati",
                "ham",
                "prosciutto",
            },
        ),
        (
            "fish",
            {
                "peste",
                "fish",
                "ton",
                "tuna",
                "somon",
                "salmon",
                "seafood",
            },
        ),
    ]

    for product_type, tokens in product_types:
        if any(token in text for token in tokens):
            return product_type

    return None


def product_matches_query_type(product_text, product_type):
    if not product_type:
        return True

    type_tokens = {
        "water": {"apa", "water", "mineral", "minerala", "spring water"},
        "juice": {"suc", "juice", "nectar"},
        "soft_drink": {"cola", "pepsi", "coca cola", "cocacola", "soda", "soft drink"},
        "coffee_drink": {"coffee", "cafea", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee"},
        "ice_cream": {"inghetata", "gelato", "ice cream", "icecream", "sorbet"},
        "spread": {"crema tartinabila", "spread", "nutella"},
        "fruit_yogurt": {"iaurt", "yogurt", "yoghurt", "skyr", "zuzu", "fruct", "fructe"},
        "yogurt": {"iaurt", "yogurt", "yoghurt", "skyr", "zuzu"},
        "instant_noodles": {
            "buldak",
            "samyang",
            "ramen",
            "noodle",
            "noodles",
            "taitei",
            "cup noodles",
            "instant noodles",
        },
        "cheese": {"branza", "cheese", "cascaval", "mozzarella"},
        "energy_drink": {
            "energizant",
            "energy drink",
            "red bull",
            "redbull",
            "monster",
            "hell",
            "taurina",
            "taurine",
        },
        "chips": {"chips", "snack", "crackers", "pufule", "popcorn"},
        "cereal": {"cereale", "cereal", "muesli", "granola", "oatmeal"},
        "protein": {"protein", "proteic", "proteina", "whey", "fitness"},
        "sauce": {"sos", "sauce", "ketchup", "mustar", "mayonnaise", "maioneza", "salsa"},
        "bread": {"paine", "bread", "chifla", "bagheta", "toast"},
        "pizza": {"pizza"},
        "ready_meal": {"ready meal", "meal", "sandwich", "salata", "supa", "soup", "frozen meal"},
        "meat": {"carne", "meat", "salam", "sausage", "carnati", "ham"},
        "fish": {"peste", "fish", "ton", "tuna", "somon", "salmon", "seafood"},
    }

    return any(token in product_text for token in type_tokens.get(product_type, set()))


def product_matches_query_brand(product_text, brand):
    if not brand:
        return True

    if brand == "redbull":
        return "redbull" in product_text or "red bull" in product_text

    if brand == "coca-cola":
        return (
            "coca cola" in product_text
            or "coca-cola" in product_text
            or "cocacola" in product_text
        )

    if brand == "mountain dew":
        return "mountain dew" in product_text or "mountaindew" in product_text

    return brand in product_text


def query_requests_zero_sugar(search_text):
    text = normalize_search_text(search_text)
    words = set(text.split())

    return (
        "0" in words
        or "zero" in words
        or "fara zahar" in text
        or "no sugar" in text
        or "sugarfree" in text
        or "sugar free" in text
    )


def product_matches_zero_sugar_request(product, product_text):
    sugar = get_product_field(product, "sugar", None)

    try:
        if sugar is not None and float(sugar) <= 0.5:
            return True
    except (TypeError, ValueError):
        pass

    return any(
        token in product_text
        for token in [
            "zero",
            "0 zahar",
            "0 sugar",
            "fara zahar",
            "no sugar",
            "sugarfree",
            "sugar free",
        ]
    )


def get_strong_variant_groups(search_text):
    text = normalize_search_text(search_text)
    words = set(text.split())
    groups = []

    variant_map = [
        ({"cappuccino", "capuccino"}, {"cappuccino", "capuccino"}),
        ({"latte"}, {"latte"}),
        ({"mocha"}, {"mocha"}),
        ({"espresso"}, {"espresso"}),
        ({"frappe"}, {"frappe"}),
        ({"vanilie", "vanilla"}, {"vanilie", "vanilla"}),
        ({"capsuni", "strawberry"}, {"capsuni", "strawberry"}),
        ({"ciocolata", "chocolate"}, {"ciocolata", "chocolate"}),
        (
            {"alune", "aluna", "hazelnut"},
            {"alune", "aluna", "hazelnut", "haselnuss", "nocciola"},
        ),
        ({"alb", "white"}, {"alb", "white"}),
    ]

    for triggers, matches in variant_map:
        if words.intersection(triggers):
            groups.append(matches)

    return groups


def product_match_score(product, search_text):
    query = expand_query_with_synonyms(search_text)

    identity_text = " ".join([
        get_product_field(product, "name") or "",
        get_product_field(product, "brand") or "",
        get_product_field(product, "store") or "",
        get_product_field(product, "category") or "",
        get_product_field(product, "tag") or "",
    ])

    product_text = normalize_search_text(identity_text)

    if not query or not product_text:
        return 0

    query_brand = detect_query_brand(search_text)
    query_type = detect_product_type(search_text)

    if query_brand and not product_matches_query_brand(product_text, query_brand):
        return 0

    if query_type and not product_matches_query_type(product_text, query_type):
        return 0

    if query_requests_zero_sugar(search_text) and not product_matches_zero_sugar_request(product, product_text):
        return 0

    for variant_group in get_strong_variant_groups(search_text):
        if not any(variant in product_text for variant in variant_group):
            return 0

    query_words = query.split()
    product_words = product_text.split()
    important_words = get_important_query_words(search_text)
    matched_important_words = {
        word
        for word in important_words
        if query_has_product_overlap([word], product_text)
    }

    score = 0

    # potrivire directă pe frază
    if query in product_text:
        score += 80

    # potrivire pe fiecare cuvânt
    for word in query_words:
        if word in product_words:
            score += 20
        elif any(word in product_word for product_word in product_words):
            score += 10

    # similaritate generală între textul căutat și numele produsului
    name_similarity = SequenceMatcher(
        None,
        query,
        normalize_search_text(get_product_field(product, "name"))
    ).ratio()

    score += int(name_similarity * 40)

    if important_words:
        required_matches = 1

        if len(set(important_words)) >= 3:
            required_matches = 2

        if len(matched_important_words) < required_matches:
            if name_similarity < 0.72:
                return 0
            score = min(score, 32)

    return score


def product_label_match_score(product, label_text):
    query = expand_query_with_synonyms(label_text)
    product_name = normalize_search_text(get_product_field(product, "name"))

    if not query or not product_name:
        return 0

    query_words = {
        word for word in query.split()
        if len(word) >= 3 and not word.isdigit()
    }
    product_words = set(product_name.split())
    shared_words = query_words.intersection(product_words)
    score = len(shared_words) * 24

    if product_name in query:
        score += 80

    if len(shared_words) >= 2:
        score += 20

    return score


def find_best_product_match(search_text, store_name=None):
    expanded_query = expand_query_with_synonyms(search_text)
    query_words = [
        word for word in normalize_search_text(expanded_query).split()
        if len(word) >= 3 and not word.isdigit()
    ]
    query_words = list(dict.fromkeys(query_words))[:8]
    products_query = Product.query

    if query_words:
        filters = []

        for word in query_words:
            pattern = f"%{word}%"
            filters.extend([
                Product.name.ilike(pattern),
                Product.category.ilike(pattern),
                Product.store.ilike(pattern),
                Product.ingredients.ilike(pattern),
            ])

        products_query = products_query.filter(or_(*filters))

    if store_name and store_name != "Fără magazin ales":
        store_candidates = products_query.filter(Product.store == store_name)
        all_products = store_candidates.limit(700).all()

        if len(all_products) < 80:
            fallback_products = products_query.limit(700).all()
            seen_ids = {product.id for product in all_products}
            all_products.extend(
                product for product in fallback_products if product.id not in seen_ids
            )
    else:
        all_products = products_query.limit(900).all()

    scored_products = []

    for product in all_products:
        score = product_match_score(product, search_text)

        if store_name and store_name != "Fără magazin ales":
            if product.store == store_name:
                score += 15

        scored_products.append((score, product))

    scored_products.sort(key=lambda item: item[0], reverse=True)

    if not scored_products:
        return None, 0

    best_score, best_product = scored_products[0]

    if best_score < 35:
        return None, best_score

    return best_product, best_score


def extract_openai_output_text(response_data):
    output_text = response_data.get("output_text")

    if output_text:
        return output_text

    for output_item in response_data.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "output_text":
                return content_item.get("text", "")

    return ""


def parse_json_object(text_value):
    text_value = (text_value or "").strip()

    if text_value.startswith("```"):
        text_value = re.sub(r"^```(?:json)?\s*", "", text_value)
        text_value = re.sub(r"\s*```$", "", text_value)

    return json.loads(text_value)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_image_file(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def supabase_storage_enabled():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def upload_to_supabase_storage(image_bytes, bucket, object_path):
    response = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}",
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Content-Type": "image/jpeg",
            "x-upsert": "false",
        },
        data=image_bytes,
        timeout=20,
    )
    response.raise_for_status()


def get_supabase_public_url(bucket, object_path):
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{object_path}"


def download_supabase_private_object(bucket, object_path):
    response = requests.get(
        f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}",
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "image/jpeg")


def publish_submission_image(image_path):
    prefix = "/uploads/supabase-submissions/"

    if not image_path or not image_path.startswith(prefix):
        return image_path

    object_path = image_path.removeprefix(prefix)
    image_bytes, _ = download_supabase_private_object(
        SUPABASE_SUBMISSIONS_BUCKET,
        object_path,
    )
    public_path = f"products/{uuid4().hex}.jpg"
    upload_to_supabase_storage(
        image_bytes,
        SUPABASE_PRODUCT_IMAGES_BUCKET,
        public_path,
    )
    return get_supabase_public_url(SUPABASE_PRODUCT_IMAGES_BUCKET, public_path)


def user_can_access_submission_image(image_path):
    user = getattr(g, "current_user", None)

    if not user:
        return False

    if user.is_admin:
        return True

    return ProductSubmission.query.filter(
        ProductSubmission.user_id == user.id,
        (
            (ProductSubmission.front_image == image_path)
            | (ProductSubmission.nutrition_image == image_path)
        ),
    ).first() is not None


def save_uploaded_file(file, folder):
    if not file:
        return None

    if not allowed_image_file(file.filename):
        raise ValueError("Format imagine invalid. Sunt acceptate: JPG, JPEG, PNG, WEBP.")

    safe_name = secure_filename(file.filename)
    name_without_extension = os.path.splitext(safe_name)[0]

    filename = f"{uuid4().hex}_{name_without_extension[:60]}.jpg"
    try:
        image = ImageOps.exif_transpose(Image.open(file.stream))

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        image.thumbnail((1800, 1800))
        image_buffer = BytesIO()
        image.save(image_buffer, "JPEG", quality=88, optimize=True)
        image_bytes = image_buffer.getvalue()

    except Exception:
        raise ValueError(
            "Imaginea nu a putut fi procesată. Încearcă alt fișier JPG, PNG sau WEBP."
        )

    if supabase_storage_enabled():
        object_path = f"submissions/{uuid4().hex}_{filename}"
        upload_to_supabase_storage(
            image_bytes,
            SUPABASE_SUBMISSIONS_BUCKET,
            object_path,
        )
        return f"/uploads/supabase-submissions/{object_path}"

    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as image_file:
        image_file.write(image_bytes)

    return f"/uploads/submissions/{filename}"


def review_product_submission_with_ai(submission):
    confidence = 100
    problems = []
    warnings = []

    name = (submission.product_name or "").strip().lower()
    category = (submission.category or "").strip().lower()
    quantity = (submission.quantity or "").strip().lower()
    ingredients = (submission.ingredients or "").strip().lower()

    if len(name) < 3:
        confidence -= 35
        problems.append("Numele produsului este prea scurt sau lipsește.")

    if not submission.store:
        confidence -= 25
        problems.append("Magazinul lipsește.")

    if not category:
        confidence -= 10
        warnings.append("Categoria produsului nu este completată.")

    if not quantity:
        confidence -= 10
        warnings.append("Cantitatea/gramajul nu este completată.")

    if not submission.front_image:
        confidence -= 15
        warnings.append("Lipsește poza cu fața produsului.")

    if not submission.nutrition_image:
        confidence -= 10
        warnings.append("Lipsește poza cu eticheta nutrițională.")

    nutrition_values = [
        submission.calories,
        submission.protein,
        submission.sugar,
        submission.fat,
    ]

    if all(value is None for value in nutrition_values):
        confidence -= 30
        problems.append("Nu există valori nutriționale completate.")

    if submission.calories is None:
        confidence -= 8
        warnings.append("Caloriile lipsesc.")

    if submission.sugar is None:
        confidence -= 6
        warnings.append("Zahărul lipsește.")

    if submission.protein is None:
        confidence -= 5
        warnings.append("Proteina lipsește.")

    if submission.fat is None:
        confidence -= 5
        warnings.append("Grăsimile lipsesc.")

    if submission.calories is not None and submission.calories < 0:
        confidence -= 30
        problems.append("Caloriile nu pot fi negative.")

    if submission.sugar is not None and submission.sugar < 0:
        confidence -= 30
        problems.append("Zahărul nu poate fi negativ.")

    if submission.protein is not None and submission.protein < 0:
        confidence -= 30
        problems.append("Proteina nu poate fi negativă.")

    if submission.fat is not None and submission.fat < 0:
        confidence -= 30
        problems.append("Grăsimile nu pot fi negative.")

    if "monster" in name or "energiz" in category:
        if "cafein" not in ingredients and "cofein" not in ingredients:
            warnings.append(
                "Produsul pare energizant, dar nu este menționată cafeina în observații."
            )
            confidence -= 8

        if submission.protein is not None and submission.protein > 5:
            warnings.append(
                "Pentru o băutură energizantă, proteina pare neobișnuit de mare."
            )
            confidence -= 10

        if submission.fat is not None and submission.fat > 5:
            warnings.append(
                "Pentru o băutură energizantă, grăsimile par neobișnuit de mari."
            )
            confidence -= 10

    if submission.sugar == 0:
        if (
            "fara zahar" not in ingredients
            and "fără zahăr" not in ingredients
            and "indulcitor" not in ingredients
            and "îndulcitor" not in ingredients
        ):
            warnings.append(
                "Zahărul este 0, dar nu apare o mențiune despre fără zahăr sau îndulcitori."
            )
            confidence -= 8

    confidence = max(0, min(confidence, 100))

    if confidence >= 80 and len(problems) == 0:
        status = "ai_approved"
        message = "Produsul pare corect și complet."
    elif confidence >= 55:
        status = "needs_review"
        message = "Produsul pare posibil corect, dar are câteva informații lipsă sau neclare."
    else:
        status = "rejected"
        message = "Produsul pare incomplet sau incorect."

    return {
        "status": status,
        "confidence": confidence,
        "message": message,
        "problems": problems,
        "warnings": warnings,
    }

def safe_float(value, default=0):
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_product_score(category, calories, protein, sugar, fat, ingredients):
    category_text = (category or "").lower()
    ingredients_text = (ingredients or "").lower()

    calories = parse_optional_float(calories)
    protein = parse_optional_float(protein)
    sugar = parse_optional_float(sugar)
    fat = parse_optional_float(fat)

    score = 7.0

    # Calorii
    if calories is not None:
        if calories <= 50:
            score += 0.8
        elif calories <= 100:
            score += 0.5
        elif calories <= 200:
            score += 0.1
        elif calories > 350:
            score -= 0.8

    # Zahăr
    if sugar is not None:
        if sugar == 0:
            score += 0.9
        elif sugar <= 5:
            score += 0.6
        elif sugar <= 10:
            score += 0.2
        elif sugar <= 20:
            score -= 0.5
        else:
            score -= 1.2

    # Proteină
    if protein is not None:
        if protein >= 15:
            score += 0.9
        elif protein >= 10:
            score += 0.7
        elif protein >= 5:
            score += 0.3

    # Grăsimi
    if fat is not None:
        if fat <= 1:
            score += 0.3
        elif fat <= 5:
            score += 0.1
        elif fat > 15:
            score -= 0.7

    # Reguli pe categorii
    if "energiz" in category_text or "energy" in category_text or "monster" in ingredients_text:
        # Energizantele nu trebuie punctate doar pentru zahăr 0.
        score -= 0.5

        if sugar == 0:
            score += 0.4

        if "cafein" in ingredients_text or "cofein" in ingredients_text:
            score -= 0.2

    if "lactate" in category_text or "iaurt" in category_text or "skyr" in ingredients_text:
        if protein is not None and protein >= 8:
            score += 0.5

        if sugar is not None and sugar <= 5:
            score += 0.3

    if "snacks" in category_text or "dulciuri" in category_text:
        if sugar is not None and sugar > 15:
            score -= 0.8

        if protein is not None and protein >= 10:
            score += 0.4

    if "fructe" in category_text or "legume" in category_text:
        score += 0.7

    # Ingrediente / observații
    if "fara zahar" in ingredients_text or "fără zahăr" in ingredients_text:
        score += 0.3

    if "indulcitor" in ingredients_text or "îndulcitor" in ingredients_text:
        score -= 0.1

    if "aditivi" in ingredients_text:
        score -= 0.3

    if "natural" in ingredients_text or "ingrediente simple" in ingredients_text:
        score += 0.4

    # Limitare scor între 1 și 9.8
    score = max(1.0, min(score, 9.8))

    return round(score, 1)


def generate_product_tag(category, calories, protein, sugar, fat, ingredients):
    category_text = (category or "").lower()
    ingredients_text = (ingredients or "").lower()

    calories = parse_optional_float(calories)
    protein = parse_optional_float(protein)
    sugar = parse_optional_float(sugar)
    fat = parse_optional_float(fat)

    if sugar is not None and sugar == 0:
        return "Fără zahăr"

    if protein is not None and protein >= 10:
        return "Mai multă proteină"

    if calories is not None and calories <= 70:
        return "Puține calorii"

    if sugar is not None and sugar <= 5:
        return "Zahăr redus"

    if "energiz" in category_text:
        return "Energizant"

    if "natural" in ingredients_text or "ingrediente simple" in ingredients_text:
        return "Ingrediente curate"

    if fat is not None and fat <= 1:
        return "Grăsimi reduse"

    return "Date limitate"


def generate_product_reason(category, calories, protein, sugar, fat, ingredients):
    category_text = (category or "").lower()
    ingredients_text = (ingredients or "").strip()

    calories = parse_optional_float(calories)
    protein = parse_optional_float(protein)
    sugar = parse_optional_float(sugar)
    fat = parse_optional_float(fat)

    reasons = []

    if sugar is not None and sugar == 0:
        reasons.append("are zahăr 0")
    elif sugar is not None and sugar <= 5:
        reasons.append("are zahăr redus")
    elif sugar is not None and sugar > 15:
        reasons.append("are un conținut ridicat de zahăr")

    if protein is not None and protein >= 10:
        reasons.append("are un aport bun de proteină")
    elif protein is not None and protein >= 5:
        reasons.append("are proteină moderată")

    if calories is not None and calories <= 70:
        reasons.append("are puține calorii")
    elif calories is not None and calories > 250:
        reasons.append("are densitate calorică mai mare")

    if fat is not None and fat <= 1:
        reasons.append("are grăsimi reduse")
    elif fat is not None and fat > 15:
        reasons.append("are grăsimi ridicate")

    if "energiz" in category_text:
        if "cafein" in ingredients_text.lower() or "cofein" in ingredients_text.lower():
            reasons.append("conține cafeină, deci trebuie consumat cu moderație")
        else:
            reasons.append("fiind băutură energizantă, trebuie consumat cu moderație")

    if not reasons:
        return (
            "Produsul are informații nutriționale limitate. Verifică zahărul, "
            "caloriile și ingredientele de pe etichetă, apoi compară-l cu produse "
            "din aceeași categorie."
        )

    sentence = "Produsul " + ", ".join(reasons) + "."

    if ingredients_text:
        sentence += f" Observații: {ingredients_text}"

    return sentence

def normalize_product_name_for_duplicate(text):
    if not text:
        return ""

    text = normalize_search_text(text)
    replacements = {
        "filetto": "file",
        "filet": "file",
        "muschiulet": "muschi",
        "mușchi": "muschi",
        "sunca": "ham",
        "șuncă": "ham",
        "jambon": "ham",
        "prosciutto": "ham",
        "carne porc": "porc",
        "pork": "porc",
        "chicken": "pui",
        "turkey": "curcan",
        "yoghurt": "yogurt",
        "yaourt": "yogurt",
        "fromage": "branza",
        "cheese": "branza",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    generic_words = {
        "aliment",
        "alimento",
        "aliments",
        "articol",
        "energy",
        "energizant",
        "energizanta",
        "bautura",
        "băutură",
        "boisson",
        "drink",
        "doza",
        "can",
        "conserva",
        "ambalaj",
        "pack",
        "package",
        "produs",
        "product",
        "produit",
        "producto",
        "cu",
        "de",
        "din",
        "si",
        "și",
        "la",
        "le",
        "les",
        "el",
        "the",
        "with",
        "and",
        "fara",
        "fără",
        "zero",
        "original",
        "clasic",
        "classic",
        "natural",
        "naturale",
        "naturelle",
        "felii",
        "feliat",
        "sliced",
        "bucati",
        "bucăți",
        "piece",
        "pieces",
        "gram",
        "grams",
        "g",
        "kg",
        "ml",
        "l",
    }

    words = text.split()
    important_words = [word for word in words if word not in generic_words]

    return " ".join(important_words)


def numbers_are_close(a, b, tolerance=0.01):
    if a is None or b is None:
        return True

    try:
        return abs(float(a) - float(b)) <= tolerance
    except (ValueError, TypeError):
        return True


def is_duplicate_product(existing_product, submission):
    if existing_product.store != submission.store:
        return False

    existing_name = normalize_product_name_for_duplicate(existing_product.name)
    submission_name = normalize_product_name_for_duplicate(submission.product_name)

    if not existing_name or not submission_name:
        return False

    name_similarity = SequenceMatcher(
        None,
        existing_name,
        submission_name
    ).ratio()

    same_category = normalize_search_text(existing_product.category) == normalize_search_text(
        submission.category
    )

    same_nutrition = (
        numbers_are_close(existing_product.calories, submission.calories)
        and numbers_are_close(existing_product.protein, submission.protein)
        and numbers_are_close(existing_product.sugar, submission.sugar)
        and numbers_are_close(existing_product.fat, submission.fat)
    )

    # Caz clar: după normalizare numele devine identic
    if existing_name == submission_name and same_category:
        return True

    # Caz fuzzy: nume foarte asemănător + aceeași categorie + aceleași valori nutriționale
    if name_similarity >= 0.78 and same_category and same_nutrition:
        return True

    return False


def find_duplicate_product_for_submission(submission):
    products = Product.query.filter_by(store=submission.store).all()

    for product in products:
        if is_duplicate_product(product, submission):
            return product

    return None

def add_column_if_missing(table_name, column_name, column_definition):
    columns = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    existing_columns = [column[1] for column in columns]

    if column_name not in existing_columns:
        db.session.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        )
        db.session.commit()


def ensure_database_columns():
    if db.engine.dialect.name != "sqlite":
        statements = [
            (
                "users is_admin",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE",
            ),
            (
                "users email_verified",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE",
            ),
            (
                "users email_verified_at",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP NULL",
            ),
            (
                "users invite_code",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS invite_code VARCHAR(30)",
            ),
            (
                "users referred_by_user_id",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS referred_by_user_id INTEGER REFERENCES users(id)",
            ),
            (
                "users bonus_unlimited_until",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS bonus_unlimited_until TIMESTAMP NULL",
            ),
            (
                "users bonus_scan_credits",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS bonus_scan_credits INTEGER NOT NULL DEFAULT 0",
            ),
            (
                "cart family_profile_id",
                "ALTER TABLE cart_items "
                "ADD COLUMN IF NOT EXISTS family_profile_id INTEGER REFERENCES family_profiles(id)",
            ),
        ]

        for label, statement in statements:
            execute_schema_statement(statement, label)

        return

    add_column_if_missing("users", "is_admin", "BOOLEAN NOT NULL DEFAULT 0")
    add_column_if_missing("users", "email_verified", "BOOLEAN NOT NULL DEFAULT 1")
    add_column_if_missing("users", "email_verified_at", "DATETIME")
    add_column_if_missing("users", "invite_code", "VARCHAR(30)")
    add_column_if_missing("users", "referred_by_user_id", "INTEGER")
    add_column_if_missing("users", "bonus_unlimited_until", "DATETIME")
    add_column_if_missing("users", "bonus_scan_credits", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("products", "barcode", "VARCHAR(80)")
    add_column_if_missing("products", "ingredients", "TEXT")
    add_column_if_missing("product_submissions", "barcode", "VARCHAR(80)")
    add_column_if_missing("cart_items", "family_profile_id", "INTEGER")


def execute_schema_statement(statement, label):
    try:
        db.session.execute(text(statement))
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        app.logger.warning("Database schema update skipped for %s: %s", label, error)


def ensure_database_indexes():
    common_indexes = [
        (
            "products barcode",
            "CREATE INDEX IF NOT EXISTS ix_products_barcode ON products (barcode)",
        ),
        (
            "products category",
            "CREATE INDEX IF NOT EXISTS ix_products_category ON products (category)",
        ),
        (
            "products store",
            "CREATE INDEX IF NOT EXISTS ix_products_store ON products (store)",
        ),
        (
            "products score",
            "CREATE INDEX IF NOT EXISTS ix_products_score ON products (score)",
        ),
        (
            "scan history user date",
            "CREATE INDEX IF NOT EXISTS ix_scan_history_user_scanned_at "
            "ON scan_history (user_id, scanned_at)",
        ),
        (
            "favorites user",
            "CREATE INDEX IF NOT EXISTS ix_favorites_user_id ON favorites (user_id)",
        ),
        (
            "cart user",
            "CREATE INDEX IF NOT EXISTS ix_cart_items_user_id ON cart_items (user_id)",
        ),
        (
            "cart user profile",
            "CREATE INDEX IF NOT EXISTS ix_cart_items_user_profile "
            "ON cart_items (user_id, family_profile_id)",
        ),
        (
            "cart user profile product store",
            "CREATE INDEX IF NOT EXISTS ix_cart_items_user_profile_product_store "
            "ON cart_items (user_id, family_profile_id, product_name, store)",
        ),
        (
            "price observations barcode",
            "CREATE INDEX IF NOT EXISTS ix_price_observations_barcode "
            "ON price_observations (product_barcode)",
        ),
        (
            "search events result date",
            "CREATE INDEX IF NOT EXISTS ix_search_events_result_created "
            "ON search_events (result_count, created_at)",
        ),
        (
            "search events query",
            "CREATE INDEX IF NOT EXISTS ix_search_events_query "
            "ON search_events (query)",
        ),
        (
            "search events user date",
            "CREATE INDEX IF NOT EXISTS ix_search_events_user_created "
            "ON search_events (user_id, created_at)",
        ),
        (
            "users invite code",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_invite_code "
            "ON users (invite_code)",
        ),
    ]

    for label, statement in common_indexes:
        execute_schema_statement(statement, label)

    if db.engine.dialect.name == "postgresql":
        execute_schema_statement(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            "postgres trigram extension",
        )
        execute_schema_statement(
            "CREATE INDEX IF NOT EXISTS ix_products_name_trgm "
            "ON products USING gin (name gin_trgm_ops)",
            "products name trigram",
        )


def ensure_configured_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()

    if not admin_email:
        return

    user = User.query.filter_by(email=admin_email).first()

    if user and not user.is_admin:
        user.is_admin = True
        db.session.commit()


def ensure_invite_codes_for_existing_users():
    users_without_codes = User.query.filter(
        or_(User.invite_code.is_(None), User.invite_code == "")
    ).limit(200).all()

    for user in users_without_codes:
        ensure_user_invite_code(user)

# =========================
# Main routes
# =========================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Backend Ce Aleg funcționează.",
        "database": "Supabase Postgres" if database_url else "SQLite local",
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "service": "ce-aleg-api",
    })


@app.route("/readiness", methods=["GET"])
def get_readiness():
    return jsonify(get_publication_readiness())


@app.route("/admin/email-test", methods=["POST"])
def send_admin_email_test():
    data = request.get_json(silent=True) or {}
    to_email = (
        data.get("to")
        or CONTACT_EMAIL
        or os.environ.get("ADMIN_EMAIL")
        or g.current_user.email
    ).strip().lower()

    if not is_valid_email_address(to_email):
        return jsonify({"error": "Adresa de email nu este valida."}), 400

    if not is_email_configured():
        return jsonify({
            "sent": False,
            "error": "Emailul nu este configurat. Completează EMAIL_PROVIDER, EMAIL_FROM și cheia providerului ales.",
            "provider": EMAIL_PROVIDER,
            "from": EMAIL_FROM,
            "to": to_email,
        }), 400

    sent = send_transactional_email(
        to_email,
        "Test email Ce aleg?",
        (
            "Salut!\n\n"
            "Emailurile tranzacționale Ce aleg? funcționează.\n"
            f"Expeditor: {EMAIL_FROM_NAME} <{EMAIL_FROM}>\n"
            f"Reply-to: {get_email_reply_to() or EMAIL_FROM}\n"
            f"Destinatar test: {to_email}\n\n"
            "Resetarea parolei, confirmarea emailului și mesajele de cont pot fi trimise din cloud.\n"
        ),
        render_brand_email(
            "Test email",
            "Emailurile Ce aleg? funcționează.",
            (
                "Acesta este un test trimis din panoul de administrare. "
                "Dacă îl vezi în inbox, Brevo, domeniul și forwardingul sunt configurate corect."
            ),
            "Deschide site-ul",
            FRONTEND_PUBLIC_URL,
            [
                f"Expeditor: {EMAIL_FROM_NAME} <{EMAIL_FROM}>",
                f"Reply-to: {get_email_reply_to() or EMAIL_FROM}",
                f"Destinatar test: {to_email}",
            ],
        ),
    )

    if not sent:
        provider_error = LAST_EMAIL_PROVIDER_ERROR or "Providerul nu a returnat detalii."
        return jsonify({
            "sent": False,
            "error": f"Emailul de test nu a putut fi trimis. {provider_error}",
            "provider": EMAIL_PROVIDER,
            "from": EMAIL_FROM,
            "to": to_email,
        }), 502

    return jsonify({
        "sent": True,
        "message": f"Email de test trimis către {to_email}. Verifică inboxul și Spam.",
        "from": EMAIL_FROM,
        "to": to_email,
    })


@app.route("/ai/status", methods=["GET"])
def get_ai_status():
    now = time.time()

    if (
        AI_STATUS_CACHE["data"]
        and now - AI_STATUS_CACHE["created_at"] < AI_STATUS_CACHE_TTL
    ):
        return jsonify(AI_STATUS_CACHE["data"])

    libretranslate_url = os.environ.get("LIBRETRANSLATE_URL", "").strip().rstrip("/")
    libretranslate_available = False

    if libretranslate_url:
        try:
            response = requests.get(f"{libretranslate_url}/languages", timeout=2)
            libretranslate_available = response.status_code == 200
        except requests.RequestException:
            libretranslate_available = False

    openai_vision_enabled = (
        os.environ.get("ENABLE_OPENAI_VISION", "false").lower() == "true"
        and bool(os.environ.get("OPENAI_API_KEY", "").strip())
    )

    status_data = {
        "localOcr": {
            "enabled": True,
            "label": "OCR local pentru coduri și etichete",
        },
        "localTranslation": {
            "enabled": libretranslate_available,
            "label": "Traducere locală LibreTranslate",
        },
        "cloudVision": {
            "enabled": openai_vision_enabled,
            "label": "Identificare vizuala cloud optionala",
            "required": False,
        },
        "openFoodFacts": {
            "enabled": True,
            "label": "Catalog Open Food Facts",
        },
        "freeMode": {
            "enabled": True,
            "label": "Mod gratuit: cod de bare, OCR local, catalog public si recomandari calculate",
        },
    }
    AI_STATUS_CACHE["created_at"] = now
    AI_STATUS_CACHE["data"] = status_data
    return jsonify(status_data)


@app.route("/init-db", methods=["GET"])
def init_db():
    db.create_all()
    ensure_database_columns()
    ensure_database_indexes()
    ensure_invite_codes_for_existing_users()

    return jsonify({
        "message": "Baza de date a fost creată cu succes."
    })


# =========================
# Auth
# =========================

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    age_confirmed = bool(data.get("ageConfirmed"))
    accepted_terms = bool(data.get("acceptedTerms"))
    invite_code = normalize_invite_code(
        data.get("inviteCode") or data.get("invite_code") or ""
    )

    if not name or not email or not password:
        return jsonify({"error": "Numele, emailul și parola sunt obligatorii."}), 400

    if not age_confirmed:
        return jsonify({
            "error": "Pentru cont trebuie sa confirmi ca ai cel putin 16 ani sau acordul parintelui/tutorelui."
        }), 400

    if not accepted_terms:
        return jsonify({
            "error": "Trebuie să accepți Termenii și Politica de confidențialitate."
        }), 400

    password_strength = validate_password_strength(password)

    if not password_strength["isValid"]:
        return jsonify({
            "error": f"Parola trebuie să aibă minimum {PASSWORD_MIN_LENGTH} caractere.",
            "passwordStrength": password_strength,
        }), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({"error": "Exista deja un cont cu acest email."}), 409

    inviter = None

    if invite_code:
        inviter = find_inviter_by_code(invite_code)

        if not inviter:
            return jsonify({"error": "Codul de invitație nu este valid."}), 400

    new_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        email_verified=False,
        email_verified_at=None,
        referred_by_user_id=inviter.id if inviter else None,
    )

    db.session.add(new_user)
    db.session.commit()
    ensure_user_invite_code(new_user)
    verification_sent, verification_url = send_email_verification_email(new_user)
    email_status = {
        "verificationSent": verification_sent,
        "configured": is_email_configured(),
        "provider": EMAIL_PROVIDER,
    }

    if not verification_sent:
        app.logger.warning("Verification email was not sent for user %s", new_user.id)

    if not verification_sent and not PRODUCTION_MODE:
        email_status["devVerificationLink"] = verification_url

    response = jsonify({
        "message": "Cont creat. Verifică emailul ca să activezi contul.",
        "user": user_to_dict(new_user),
        "emailStatus": email_status,
    })
    return response, 201


@app.route("/auth/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"error": "Linkul de confirmare lipseste."}), 400

    user = verify_email_verification_token(token)

    if not user:
        return jsonify({"error": "Linkul de confirmare este invalid sau a expirat."}), 400

    was_already_verified = bool(user.email_verified)
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.session.commit()

    referralRewardApplied = False

    if not was_already_verified:
        referralRewardApplied = apply_referral_bonus_after_verification(user)

    welcome_sent = True if was_already_verified else send_welcome_email(user)
    response = jsonify({
        "message": "Email confirmat. Contul este activ.",
        "user": user_to_dict(user),
        "emailStatus": {
            "welcomeSent": welcome_sent,
            "referralRewardApplied": referralRewardApplied,
            "configured": is_email_configured(),
            "provider": EMAIL_PROVIDER,
        },
    })
    return set_auth_cookie(response, user)


@app.route("/auth/resend-verification", methods=["POST"])
def resend_email_verification():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Emailul este obligatoriu."}), 400

    user = User.query.filter_by(email=email).first()
    dev_verification_link = None

    if user and not user.email_verified:
        sent, verification_url = send_email_verification_email(user)
        if not sent and not PRODUCTION_MODE:
            dev_verification_link = verification_url

    response = {
        "message": "Dacă există un cont neconfirmat cu acest email, trimitem un nou link de confirmare.",
    }

    if dev_verification_link:
        response["devVerificationLink"] = dev_verification_link

    return jsonify(response)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Emailul și parola sunt obligatorii."}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Email sau parolă greșită."}), 401

    if not user.email_verified:
        return jsonify({
            "error": "Confirma emailul inainte sa intri in cont.",
            "code": "email_not_verified",
        }), 403

    return jsonify({
        "message": "Autentificare reusita.",
        "user": user_to_dict(user),
    })


@app.route("/auth/password-strength", methods=["POST"])
def get_password_strength():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    return jsonify(validate_password_strength(password))


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Emailul este obligatoriu."}), 400

    user = User.query.filter_by(email=email).first()
    dev_reset_link = None

    if user:
        sent, reset_url = send_password_reset_email(user)
        if not sent and not PRODUCTION_MODE:
            dev_reset_link = reset_url

    response = {
        "message": "Dacă există un cont cu acest email, vei primi un link pentru resetarea parolei.",
    }

    if dev_reset_link:
        response["devResetLink"] = dev_reset_link

    return jsonify(response)


@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    password = data.get("password", "")

    if not token or not password:
        return jsonify({"error": "Tokenul și parola nouă sunt obligatorii."}), 400

    user = verify_password_reset_token(token)

    if not user:
        return jsonify({"error": "Linkul de resetare este invalid sau a expirat."}), 400

    password_strength = validate_password_strength(password)

    if not password_strength["isValid"]:
        return jsonify({
            "error": f"Parola trebuie să aibă minimum {PASSWORD_MIN_LENGTH} caractere.",
            "passwordStrength": password_strength,
        }), 400

    user.password_hash = generate_password_hash(password)
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
    db.session.commit()

    response = jsonify({
        "message": "Parola a fost schimbată. Te-am autentificat automat.",
        "user": user_to_dict(user),
    })
    return set_auth_cookie(response, user)


@app.route("/account/delete/request", methods=["POST"])
def request_account_deletion():
    user = g.current_user
    sent, deletion_url = send_account_deletion_email(user)

    if not sent and PRODUCTION_MODE:
        return jsonify({
            "error": "Emailul de confirmare nu a putut fi trimis momentan. Încearcă din nou mai târziu.",
            "emailConfigured": is_email_configured(),
        }), 502

    response = {
        "message": "Ți-am trimis un email cu linkul de confirmare pentru ștergerea contului.",
        "sent": sent,
        "email": user.email,
        "emailConfigured": is_email_configured(),
    }

    if not sent and not PRODUCTION_MODE:
        response["devDeletionLink"] = deletion_url
        response["message"] = (
            "Emailul nu a putut fi trimis în mediul local. Folosește linkul de test pentru confirmare."
        )

    return jsonify(response)


@app.route("/account/delete/confirm", methods=["POST"])
def confirm_account_deletion():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"error": "Linkul de confirmare lipseste."}), 400

    user = verify_account_deletion_token(token)

    if not user:
        return jsonify({"error": "Linkul de ștergere este invalid sau a expirat."}), 400

    canceled, cancel_error = cancel_subscription_before_account_deletion(user)

    if not canceled:
        return jsonify({"error": cancel_error}), 502

    try:
        delete_account_data(user)
    except Exception as error:
        db.session.rollback()
        app.logger.exception("Account deletion failed: %s", error)
        return jsonify({
            "error": "Contul nu a putut fi șters momentan. Încearcă din nou mai târziu.",
        }), 500

    response = jsonify({
        "message": "Contul tău și datele personale asociate au fost șterse.",
    })
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@app.route("/auth/me", methods=["GET"])
def get_authenticated_user():
    user = get_current_user()

    if not user:
        return jsonify({"error": "Autentificare necesara."}), 401

    return jsonify({"user": user_to_dict(user)})


@app.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Deconectare reusita."})
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@app.after_request
def persist_login_session(response):
    if request.endpoint == "login" and response.status_code < 300:
        data = response.get_json(silent=True) or {}
        user_id = (data.get("user") or {}).get("id")
        user = db.session.get(User, user_id) if user_id else None

        if user:
            set_auth_cookie(response, user)

    return response

@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()

    return jsonify([
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": bool(user.is_admin),
            "email_verified": bool(user.email_verified),
            "plan": get_or_create_subscription(user).plan,
            "subscription_status": get_or_create_subscription(user).status,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ])


@app.route("/billing/status", methods=["GET"])
def get_billing_status():
    user = g.current_user
    if request.args.get("sync") == "stripe":
        subscription = sync_best_stripe_subscription_for_user(user)
    else:
        subscription = get_or_create_subscription(user)

    return jsonify({
        "user": user_to_dict(user),
        "usage": get_usage_summary(user),
        "subscription": subscription_to_billing_dict(subscription),
        "plans": PLAN_CATALOG,
    })


@app.route("/dashboard/summary", methods=["GET"])
def get_dashboard_summary():
    user = g.current_user
    requested_profile_id = get_requested_family_profile_id()
    profile = resolve_cart_profile(user, requested_profile_id)
    cart_count = cart_query_for_profile(user, profile).with_entities(
        func.coalesce(func.sum(CartItem.quantity), 0)
    ).scalar() or 0
    history_count = ScanHistory.query.filter_by(user_id=user.id).count()
    favorites_count = Favorite.query.filter_by(user_id=user.id).count()
    last_history_item = ScanHistory.query.filter_by(user_id=user.id).order_by(
        ScanHistory.scanned_at.desc()
    ).first()
    subscription = get_or_create_subscription(user)

    return jsonify({
        "counts": {
            "cart": int(cart_count or 0),
            "history": int(history_count or 0),
            "favorites": int(favorites_count or 0),
        },
        "lastScannedProduct": last_history_item.product_name if last_history_item else "-",
        "billing": {
            "user": user_to_dict(user),
            "usage": get_usage_summary(user),
            "subscription": subscription_to_billing_dict(subscription),
            "plans": PLAN_CATALOG,
        },
    })


@app.route("/family/profiles", methods=["GET"])
def get_family_profiles():
    user = g.current_user
    subscription = get_or_create_subscription(user)
    get_or_create_primary_family_profile(user)
    profiles = FamilyProfile.query.filter_by(user_id=user.id).order_by(
        FamilyProfile.is_primary.desc(),
        FamilyProfile.created_at.asc(),
    ).all()

    return jsonify({
        "plan": subscription.plan,
        "enabled": is_family_subscription(subscription),
        "maxProfiles": 5,
        "profiles": [family_profile_to_dict(profile) for profile in profiles],
    })


@app.route("/family/profiles", methods=["POST"])
def create_family_profile():
    user = g.current_user
    subscription = get_or_create_subscription(user)

    if not is_family_subscription(subscription):
        return jsonify({
            "error": "Profilurile pentru familie sunt disponibile in planul Family.",
            "code": "family_plan_required",
        }), 402

    profile_count = FamilyProfile.query.filter_by(user_id=user.id).count()

    if profile_count >= 5:
        return jsonify({"error": "Planul Family permite pana la 5 profiluri."}), 400

    data = request.get_json(silent=True) or {}
    name = sanitize_family_profile_name(data.get("name"))

    if not name:
        return jsonify({"error": "Scrie un nume de profil de cel putin 2 caractere."}), 400

    color = str(data.get("color") or "teal").strip().lower()[:30]
    avatar = str(data.get("avatar") or "user").strip().lower()[:20]
    profile = FamilyProfile(
        user_id=user.id,
        name=name,
        color=color,
        avatar=avatar,
        is_primary=False,
    )
    db.session.add(profile)
    db.session.commit()

    return jsonify({"profile": family_profile_to_dict(profile)}), 201


@app.route("/family/profiles/<int:profile_id>", methods=["PATCH"])
def update_family_profile(profile_id):
    user = g.current_user
    subscription = get_or_create_subscription(user)

    if not is_family_subscription(subscription):
        return jsonify({
            "error": "Profilurile pentru familie sunt disponibile in planul Family.",
            "code": "family_plan_required",
        }), 402

    profile = FamilyProfile.query.filter_by(id=profile_id, user_id=user.id).first()

    if not profile:
        return jsonify({"error": "Profilul nu a fost gasit."}), 404

    data = request.get_json(silent=True) or {}
    name = sanitize_family_profile_name(data.get("name"))

    if name:
        profile.name = name

    if data.get("color"):
        profile.color = str(data.get("color")).strip().lower()[:30]

    if data.get("avatar"):
        profile.avatar = str(data.get("avatar")).strip().lower()[:20]

    db.session.commit()
    return jsonify({"profile": family_profile_to_dict(profile)})


@app.route("/family/profiles/<int:profile_id>", methods=["DELETE"])
def delete_family_profile(profile_id):
    user = g.current_user
    subscription = get_or_create_subscription(user)

    if not is_family_subscription(subscription):
        return jsonify({
            "error": "Profilurile pentru familie sunt disponibile in planul Family.",
            "code": "family_plan_required",
        }), 402

    profile = FamilyProfile.query.filter_by(id=profile_id, user_id=user.id).first()

    if not profile:
        return jsonify({"error": "Profilul nu a fost gasit."}), 404

    if profile.is_primary:
        return jsonify({"error": "Profilul principal nu poate fi sters."}), 400

    CartItem.query.filter_by(
        user_id=user.id,
        family_profile_id=profile.id,
    ).delete(synchronize_session=False)
    db.session.delete(profile)
    db.session.commit()
    return jsonify({"deleted": True})


@app.route("/billing/checkout", methods=["POST"])
def start_checkout():
    data = request.get_json(silent=True) or {}
    plan = str(data.get("plan") or "pro").strip().lower()
    billing_interval = normalize_billing_interval(
        data.get("billingInterval") or data.get("interval")
    )

    if plan not in {"pro", "family"}:
        return jsonify({"error": "Plan invalid."}), 400

    if PAYMENT_PROVIDER == "stripe":
        price_id = get_stripe_price_id(plan, billing_interval)
        price_env_name = get_stripe_price_env_name(plan, billing_interval)

        if not configure_stripe() or not price_id:
            return jsonify({
                "error": "Plata online nu este configurata complet.",
                "code": "stripe_not_configured",
                "required": [
                    "STRIPE_SECRET_KEY",
                    price_env_name,
                    "STRIPE_WEBHOOK_SECRET",
                    "FRONTEND_PUBLIC_URL",
                ],
            }), 503

        user = g.current_user
        subscription = get_or_create_subscription(user)

        if is_subscription_period_active(subscription):
            current_plan_name = PLAN_CATALOG.get(subscription.plan, {}).get(
                "name",
                subscription.plan.title(),
            )
            period_end = (
                subscription.current_period_end.isoformat() + "Z"
                if subscription.current_period_end
                else None
            )
            return jsonify({
                "error": (
                    f"Ai deja planul {current_plan_name} activ. "
                    "Poți alege alt plan după finalul perioadei curente sau poți administra abonamentul din portal."
                ),
                "code": "active_subscription_exists",
                "currentPlan": subscription.plan,
                "currentPeriodEnd": period_end,
            }), 409

        metadata = {
            "user_id": str(user.id),
            "plan": plan,
            "billing_interval": billing_interval,
            "price_id": price_id,
            "price_env": price_env_name,
            "app": "ce-aleg",
        }

        automatic_tax_enabled = env_flag("STRIPE_AUTOMATIC_TAX", False)
        checkout_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{FRONTEND_PUBLIC_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{FRONTEND_PUBLIC_URL}/billing/cancel",
            "client_reference_id": str(user.id),
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
            "allow_promotion_codes": True,
            "locale": "auto",
            "billing_address_collection": "auto",
            "automatic_tax": {"enabled": automatic_tax_enabled},
            "tax_id_collection": {
                "enabled": env_flag("STRIPE_TAX_ID_COLLECTION", False),
            },
        }

        apply_stripe_customer_to_checkout(
            checkout_params,
            subscription,
            user,
            allow_customer_update=True,
        )

        try:
            checkout_session = create_checkout_session_with_stale_customer_retry(
                checkout_params,
                subscription,
                user,
            )
        except Exception as error:
            app.logger.warning("Stripe checkout session failed: %s", error)
            return jsonify({
                "error": "Plata nu a putut fi pornita momentan.",
                "code": "stripe_checkout_failed",
            }), 502

        return jsonify({
            "mode": "stripe",
            "plan": plan,
            "billingInterval": billing_interval,
            "checkoutUrl": checkout_session.url,
            "sessionId": checkout_session.id,
        })

    return jsonify({
        "mode": "manual",
        "plan": plan,
        "billingInterval": billing_interval,
        "message": "Am notat alegerea ta. Verifică datele de plată sau activează planul din administrare.",
        "nextStep": "prepare_plan_activation",
    })


@app.route("/billing/portal", methods=["POST"])
def start_billing_portal():
    user = g.current_user
    subscription = get_or_create_subscription(user)

    if PAYMENT_PROVIDER != "stripe":
        return jsonify({
            "error": "Administrarea online a abonamentului nu este activa inca.",
            "code": "billing_portal_unavailable",
        }), 503

    if not configure_stripe():
        return jsonify({
            "error": "Stripe nu este configurat complet.",
            "code": "stripe_not_configured",
        }), 503

    if subscription.provider != "stripe" or not subscription.provider_customer_id:
        return jsonify({
            "error": "Nu exista inca un abonament Stripe pentru contul tau.",
            "code": "stripe_customer_missing",
        }), 404

    if not stripe_customer_is_usable(subscription.provider_customer_id):
        clear_stale_stripe_customer(subscription)
        return jsonify({
            "error": "Customer-ul Stripe salvat pentru cont nu mai există. Pornește o plată nouă ca să fie creat automat unul valid.",
            "code": "stripe_customer_stale",
        }), 409

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.provider_customer_id,
            return_url=f"{FRONTEND_PUBLIC_URL}/pricing",
        )
    except Exception as error:
        app.logger.warning("Stripe billing portal failed: %s", error)
        return jsonify({
            "error": "Portalul de abonament nu poate fi deschis momentan.",
            "code": "stripe_portal_failed",
        }), 502

    return jsonify({"portalUrl": portal_session.url})


@app.route("/billing/stripe/webhook", methods=["POST"])
def stripe_webhook():
    if stripe is None:
        return jsonify({"error": "Stripe SDK nu este instalat."}), 503

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()

    if not webhook_secret:
        return jsonify({"error": "Stripe webhook nu este configurat."}), 503

    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
    except ValueError:
        return jsonify({"error": "Payload Stripe invalid."}), 400
    except Exception:
        return jsonify({"error": "Semnatura Stripe invalida."}), 400

    event_type = event.get("type")
    event_object = (event.get("data") or {}).get("object") or {}

    try:
        if event_type == "checkout.session.completed":
            handle_stripe_checkout_completed(event_object)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.paused",
            "customer.subscription.resumed",
        }:
            sync_stripe_subscription_by_id(event_object.get("id"))
        elif event_type == "customer.subscription.deleted":
            sync_stripe_subscription(event_object, deleted=True)
        elif event_type in {
            "invoice.paid",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "invoice.payment_action_required",
        }:
            sync_stripe_subscription_by_id(get_invoice_subscription_id(event_object))
    except Exception:
        db.session.rollback()
        app.logger.exception(
            "Stripe webhook handler failed for event %s",
            event_type,
        )
        return jsonify({
            "code": "stripe_webhook_handler_failed",
            "error": "Evenimentul Stripe nu a putut fi procesat momentan.",
        }), 500

    return jsonify({"received": True})


# =========================
# Gamification
# =========================

@app.route("/gamification/coin-packs", methods=["GET"])
def get_cecoin_packs():
    return jsonify({"coinPacks": get_public_cecoin_packs()})


@app.route("/gamification/summary", methods=["GET"])
def get_gamification_summary():
    try:
        include_leaderboard = request.args.get("leaderboard") == "1"
        return jsonify(get_gamification_summary_for_user(
            g.current_user,
            include_leaderboard=include_leaderboard,
        ))
    except Exception:
        app.logger.exception("Gamification summary failed")
        return jsonify({
            "code": "gamification_summary_failed",
            "error": "Misiunile nu s-au putut încărca momentan.",
        }), 500


@app.route("/gamification/claim", methods=["POST"])
def claim_gamification_mission():
    data = request.get_json(silent=True) or {}
    mission_id = str(data.get("missionId") or "").strip()
    missions = build_mission_statuses(g.current_user.id)
    mission = next((item for item in missions if item["id"] == mission_id), None)

    if not mission:
        return jsonify({
            "error": "Misiunea s-a actualizat. Reîncarcă pagina și încearcă din nou.",
            "summary": get_gamification_summary_for_user(g.current_user),
        }), 400

    if mission.get("claimedToday"):
        return jsonify({
            "error": "Ai revendicat deja recompensa acestei misiuni azi. Revino mâine pentru următorul nivel.",
            "summary": get_gamification_summary_for_user(g.current_user),
        }), 409

    if not mission.get("claimable"):
        return jsonify({
            "error": "Misiunea nu este finalizată încă.",
            "summary": get_gamification_summary_for_user(g.current_user),
        }), 400

    reward = mission.get("reward") or {}

    if reward.get("bonusScans"):
        add_bonus_scan_credits(
            g.current_user,
            int(reward.get("bonusScans") or 0),
            "mission_reward",
            {"missionId": mission_id},
        )

    if reward.get("bonusDays"):
        extend_bonus_unlimited(
            g.current_user,
            int(reward.get("bonusDays") or 0),
            "mission_reward",
            {"missionId": mission_id},
        )

    db.session.add(
        UsageEvent(
            user_id=g.current_user.id,
            event_type="mission_claim",
            source=mission_id,
            metadata_json=json.dumps({
                "reward": reward,
                "seriesId": mission.get("seriesId"),
                "daily": bool(mission.get("daily")),
                "current": mission.get("current"),
                "target": mission.get("target"),
                "claimedAt": datetime.utcnow().isoformat() + "Z",
                "dayStart": (
                    get_day_start().isoformat() + "Z"
                    if mission.get("daily")
                    else None
                ),
            }),
        )
    )
    db.session.commit()
    clear_leaderboard_cache()

    return jsonify({
        "message": "Recompensă revendicată.",
        "reward": reward,
        "summary": get_gamification_summary_for_user(g.current_user),
    })


@app.route("/gamification/redeem", methods=["POST"])
def redeem_cecoin_reward():
    data = request.get_json(silent=True) or {}
    item_id = str(data.get("itemId") or "").strip()
    item = next((entry for entry in CECOIN_SHOP_ITEMS if entry["id"] == item_id), None)

    if not item:
        return jsonify({"error": "Recompensă invalidă."}), 400

    current_coins = calculate_user_coins(g.current_user.id)
    cost = int(item.get("cost") or 0)

    if current_coins < cost:
        return jsonify({
            "error": "Nu ai suficiente CeCoins pentru această recompensă.",
            "coins": current_coins,
            "required": cost,
            "summary": get_gamification_summary_for_user(g.current_user),
        }), 402

    if item.get("bonusScans"):
        add_bonus_scan_credits(
            g.current_user,
            int(item["bonusScans"]),
            "cecoin_shop",
            {"itemId": item_id},
        )

    if item.get("bonusDays"):
        extend_bonus_unlimited(
            g.current_user,
            int(item["bonusDays"]),
            "cecoin_shop",
            {"itemId": item_id},
        )

    db.session.add(
        UsageEvent(
            user_id=g.current_user.id,
            event_type="cecoin_spend",
            source=item_id,
            metadata_json=json.dumps({
                "cost": cost,
                "item": {
                    "id": item["id"],
                    "title": item["title"],
                    "bonusScans": item.get("bonusScans", 0),
                    "bonusDays": item.get("bonusDays", 0),
                },
            }),
        )
    )
    db.session.commit()
    clear_leaderboard_cache()

    return jsonify({
        "message": "Recompensa a fost activată.",
        "item": item,
        "summary": get_gamification_summary_for_user(g.current_user),
    })


@app.route("/gamification/coin-checkout", methods=["POST"])
def start_cecoin_checkout():
    data = request.get_json(silent=True) or {}
    pack = get_cecoin_pack(data.get("packId"))

    if not pack:
        return jsonify({"error": "Pachet CeCoins invalid."}), 400

    price_id = get_cecoin_pack_price_id(pack)

    if not configure_stripe() or not price_id:
        return jsonify({
            "error": "Pachetele CeCoins nu sunt configurate complet.",
            "code": "cecoins_checkout_not_configured",
            "required": ["STRIPE_SECRET_KEY", pack["priceEnv"], "STRIPE_WEBHOOK_SECRET"],
        }), 503

    price_error = validate_cecoin_price_for_checkout(price_id)

    if price_error:
        return jsonify({
            "error": price_error,
            "code": "cecoins_price_invalid",
            "required": [pack["priceEnv"]],
        }), 400

    user = g.current_user
    subscription = get_or_create_subscription(user)
    metadata = {
        "type": "cecoins",
        "user_id": str(user.id),
        "pack_id": pack["id"],
        "coins": str(pack["coins"]),
        "price_env": pack["priceEnv"],
        "app": "ce-aleg",
    }
    checkout_params = {
        "mode": "payment",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{FRONTEND_PUBLIC_URL}/dashboard?cecoins=success&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{FRONTEND_PUBLIC_URL}/dashboard?cecoins=cancelled",
        "client_reference_id": str(user.id),
        "metadata": metadata,
        "allow_promotion_codes": True,
        "locale": "auto",
        "billing_address_collection": "auto",
        "automatic_tax": {"enabled": env_flag("STRIPE_AUTOMATIC_TAX", False)},
    }

    apply_stripe_customer_to_checkout(checkout_params, subscription, user)

    try:
        checkout_session = create_checkout_session_with_stale_customer_retry(
            checkout_params,
            subscription,
            user,
        )
    except Exception as error:
        app.logger.warning("Stripe CeCoins checkout failed: %s", error)
        detail = str(error).strip()
        message = "Cumpărarea de CeCoins nu a putut fi pornită momentan."

        if detail:
            message = f"{message} Detalii Stripe: {detail[:280]}"

        return jsonify({
            "error": message,
            "code": "cecoins_checkout_failed",
        }), 502

    return jsonify({
        "mode": "stripe",
        "pack": pack["id"],
        "checkoutUrl": checkout_session.url,
        "sessionId": checkout_session.id,
    })


@app.route("/gamification/coin-checkout/sync", methods=["POST"])
def sync_cecoin_checkout_session():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("sessionId") or "").strip()

    if not session_id.startswith("cs_"):
        return jsonify({"error": "Sesiunea Stripe este invalidă."}), 400

    if not configure_stripe():
        return jsonify({
            "error": "Stripe nu este configurat complet.",
            "code": "stripe_not_configured",
        }), 503

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception as error:
        app.logger.warning("Stripe CeCoins session sync failed: %s", error)
        return jsonify({
            "error": "Plata nu a putut fi verificată momentan.",
            "code": "stripe_session_sync_failed",
        }), 502

    metadata = checkout_session.get("metadata") or {}

    if metadata.get("type") != "cecoins":
        return jsonify({"error": "Sesiunea Stripe nu aparține unui pachet CeCoins."}), 400

    if str(metadata.get("user_id") or "") != str(g.current_user.id):
        return jsonify({"error": "Sesiunea Stripe aparține altui cont."}), 403

    if checkout_session.get("payment_status") not in {"paid", "no_payment_required"}:
        return jsonify({
            "error": "Plata nu este confirmată încă.",
            "code": "stripe_payment_not_confirmed",
        }), 409

    try:
        handle_stripe_cecoin_checkout_completed(checkout_session)
    except Exception:
        db.session.rollback()
        app.logger.exception("Stripe CeCoins session sync handler failed")
        return jsonify({
            "error": "CeCoins nu au putut fi actualizate momentan.",
            "code": "cecoins_session_sync_failed",
        }), 500

    return jsonify({
        "message": "CeCoins au fost actualizate.",
        "summary": get_gamification_summary_for_user(g.current_user),
    })


# =========================
# Admin
# =========================

@app.route("/admin/overview", methods=["GET"])
def get_admin_overview():
    return jsonify({
        "users": User.query.count(),
        "products": Product.query.count(),
        "pendingSubmissions": ProductSubmission.query.filter(
            ProductSubmission.status != "approved"
        ).count(),
        "searches": SearchEvent.query.count(),
        "missingProducts": SearchEvent.query.filter(SearchEvent.result_count == 0).count(),
        "priceObservations": PriceObservation.query.count(),
        "proUsers": Subscription.query.filter(
            Subscription.plan.in_(["pro", "family"]),
            Subscription.status == "active",
        ).count(),
    })


@app.route("/admin/submissions", methods=["GET"])
def get_admin_submissions():
    submissions = ProductSubmission.query.order_by(
        ProductSubmission.created_at.desc()
    ).all()
    return jsonify([product_submission_to_dict(item) for item in submissions])


@app.route("/admin/search-misses", methods=["GET"])
def get_admin_search_misses():
    days = request.args.get("days", default=30, type=int)
    limit = request.args.get("limit", default=50, type=int)
    safe_days = max(1, min(days or 30, 365))
    safe_limit = max(1, min(limit or 50, 200))
    since = datetime.utcnow() - timedelta(days=safe_days)

    rows = (
        db.session.query(
            SearchEvent.search_text.label("search_text"),
            SearchEvent.store.label("store"),
            SearchEvent.source.label("source"),
            func.count(SearchEvent.id).label("count"),
            func.max(SearchEvent.created_at).label("last_seen"),
        )
        .filter(
            SearchEvent.result_count == 0,
            SearchEvent.created_at >= since,
        )
        .group_by(SearchEvent.search_text, SearchEvent.store, SearchEvent.source)
        .order_by(func.count(SearchEvent.id).desc(), func.max(SearchEvent.created_at).desc())
        .limit(safe_limit)
        .all()
    )

    return jsonify([
        {
            "query": row.search_text,
            "store": row.store or "Fără magazin ales",
            "source": row.source or "search",
            "count": int(row.count or 0),
            "lastSeen": row.last_seen.isoformat() + "Z" if row.last_seen else None,
        }
        for row in rows
    ])


@app.route("/admin/products/<int:product_id>", methods=["DELETE"])
def delete_admin_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"error": "Produsul nu exista."}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Produs șters din catalog."})


@app.route("/admin/users/<int:user_id>/plan", methods=["PATCH"])
def admin_update_user_plan(user_id):
    data = request.get_json(silent=True) or {}
    plan = str(data.get("plan") or "").strip().lower()
    status = str(data.get("status") or "active").strip().lower()

    if plan not in PLAN_CATALOG:
        return jsonify({"error": "Plan invalid."}), 400

    if status not in {"active", "inactive", "canceled"}:
        return jsonify({"error": "Status invalid."}), 400

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu exista."}), 404

    subscription = get_or_create_subscription(user)
    subscription.plan = plan
    subscription.status = status
    subscription.provider = data.get("provider") or "manual_admin"
    subscription.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": "Plan actualizat.",
        "user": user_to_dict(user),
        "usage": get_usage_summary(user),
    })



# =========================
# Products
# =========================

@app.route("/products/seed", methods=["GET"])
def seed_products():
    db.create_all()

    inserted = 0

    for product_data in PRODUCTS_DB_SEED:
        existing_product = Product.query.filter_by(
            name=product_data["name"],
            store=product_data["store"]
        ).first()

        if existing_product:
            continue

        product = Product(
            name=product_data["name"],
            store=product_data["store"],
            category=product_data["category"],
            score=product_data["score"],
            tag=product_data["tag"],
            image=product_data["image"],
            price=product_data["price"],
            price_text=product_data["price_text"],
            calories=product_data["calories"],
            protein=product_data["protein"],
            sugar=product_data["sugar"],
            fat=product_data["fat"],
            vegan=product_data["vegan"],
            lactose_free=product_data["lactose_free"],
            natural=product_data["natural"],
            reason=product_data["reason"],
        )

        db.session.add(product)
        inserted += 1

    db.session.commit()

    return jsonify({
        "message": "Produsele demo au fost inserate în baza de date.",
        "inserted": inserted
    })


@app.route("/products", methods=["GET"])
def get_products():
    store = request.args.get("store")

    query = Product.query

    if store:
        query = query.filter_by(store=store)

    products = query.order_by(Product.score.desc()).all()

    return jsonify([product_to_dict(product) for product in products])


@app.route("/products/search", methods=["GET"])
def search_products():
    query_text = request.args.get("q", "").strip()
    store_id = request.args.get("store", "").strip()
    user_id = request.args.get("user_id", type=int)

    if not query_text:
        return jsonify({"error": "Parametrul q este obligatoriu."}), 400

    store_name = get_store_name_from_id(store_id) if store_id else None

    results = []
    seen_keys = set()
    seen_names = set()
    cache_key = f"product-search:{normalize_search_text(query_text)}:{normalize_search_text(store_name or '')}"
    cached_results = get_cached_product_search_results(cache_key)
    source = "openfoodfacts"

    if cached_results is not None:
        results = cached_results
        source = "openfoodfacts-cache"
    elif len(query_text) >= 3:
        try:
            for off_product in fetch_off_text_search_products(query_text):
                product_data = build_off_search_result(off_product, query_text, store_name)
                score = product_data.get("matchScore") or 0

                if score < 34:
                    continue

                key = normalize_search_text(
                    f"{product_data.get('barcode') or ''} {product_data.get('name') or ''}"
                )
                name_key = normalize_search_text(product_data.get("name") or "")

                if key in seen_keys or name_key in seen_names:
                    continue

                product_data["matchScore"] = score
                results.append(product_data)
                seen_keys.add(key)
                seen_names.add(name_key)
        except requests.RequestException as error:
            app.logger.warning("Open Food Facts suggestions failed: %s", error)
            return jsonify({
                "error": "Catalogul extern nu este disponibil momentan.",
                "code": "external_catalog_unavailable",
                "source": "openfoodfacts",
            }), 502

        results.sort(key=lambda item: item.get("matchScore", 0), reverse=True)
        results = results[:10]
        set_cached_product_search_results(cache_key, results)

    record_search_event(
        query_text,
        store=store_name,
        result_count=len(results),
        source=source,
        user_id=user_id,
    )
    db.session.commit()

    response = jsonify(results)
    response.headers["X-Product-Source"] = source
    return response


@app.route("/products/search-label", methods=["GET"])
def search_products_by_label():
    label_text = request.args.get("q", "").strip()

    if len(label_text) < 5:
        return jsonify([])

    try:
        external_products = fetch_off_text_search_products(label_text)
    except requests.RequestException as error:
        app.logger.warning("Open Food Facts label search failed: %s", error)
        return jsonify({
            "error": "Catalogul extern nu este disponibil momentan.",
            "code": "external_catalog_unavailable",
            "source": "openfoodfacts",
        }), 502

    results = []

    for off_product in external_products:
        product_data = build_off_search_result(off_product, label_text)
        score = product_data.get("matchScore") or 0

        if score >= 34:
            results.append(product_data)

    results.sort(key=lambda item: item.get("matchScore", 0), reverse=True)
    record_search_event(
        label_text,
        result_count=len(results),
        source="label_search",
    )
    db.session.commit()
    return jsonify(results[:5])


@app.route("/alternatives/open-food-facts", methods=["POST"])
def get_open_food_facts_alternatives():
    data = request.get_json(silent=True) or {}
    scanned_product = data.get("product") or {}
    barcode = str(scanned_product.get("barcode") or "").strip()
    criteria = [
        str(item).strip()
        for item in data.get("criteria", [])
        if str(item).strip()
    ]
    criteria = list(dict.fromkeys([
        *criteria,
        *infer_alternative_criteria_from_request(data.get("request") or ""),
    ]))
    category_tag = get_off_alternative_category(scanned_product)
    scanned_family = get_product_recommendation_family(scanned_product)

    off_products = []
    lookup_errors = []
    seen_off_codes = set()
    local_seed_alternatives = [
        *get_local_catalog_alternatives(scanned_product, criteria),
        *get_known_catalog_alternatives(scanned_product, criteria),
    ]
    prefer_local_catalog = len(local_seed_alternatives) >= 10 and scanned_family != "general"

    if not prefer_local_catalog and category_tag:
        try:
            category_products = fetch_off_category_products(category_tag)
            off_products.extend(category_products)
            seen_off_codes.update(
                str(product.get("code") or "").strip()
                for product in category_products
            )
        except requests.RequestException as error:
            lookup_errors.append(str(error))
            app.logger.warning(
                "Open Food Facts category alternatives failed for %s: %s",
                category_tag,
                error,
            )

    if not prefer_local_catalog and "caffeine" in criteria and scanned_family in {"coffee_drink", "energy_drink", "caffeinated_beverage", "cola"}:
        for extra_category_tag in ["en:energy-drinks", "en:iced-coffees"]:
            if extra_category_tag == category_tag:
                continue

            try:
                for product in fetch_off_category_products(extra_category_tag):
                    code = str(product.get("code") or "").strip()

                    if code and code not in seen_off_codes:
                        off_products.append(product)
                        seen_off_codes.add(code)
            except requests.RequestException as error:
                lookup_errors.append(str(error))
                app.logger.warning(
                    "Open Food Facts caffeine alternatives failed for %s: %s",
                    extra_category_tag,
                    error,
                )

    if not prefer_local_catalog and len(off_products) < 8:
        try:
            existing_codes = {
                str(product.get("code") or "").strip()
                for product in off_products
            }
            search_products = fetch_off_search_products(scanned_product, category_tag)
            off_products.extend(
                product
                for product in search_products
                if str(product.get("code") or "").strip() not in existing_codes
            )
        except requests.RequestException as error:
            lookup_errors.append(str(error))
            app.logger.warning(
                "Open Food Facts search alternatives failed: %s",
                error,
            )

    if not prefer_local_catalog and not off_products and category_tag:
        try:
            search_products = fetch_off_search_products(scanned_product, None)
            off_products.extend(search_products)
        except requests.RequestException as error:
            lookup_errors.append(str(error))
            app.logger.warning(
                "Open Food Facts broad alternatives failed: %s",
                error,
            )

    if not prefer_local_catalog and len(off_products) < 6:
        existing_codes = {
            str(product.get("code") or "").strip()
            for product in off_products
        }
        seed_products = fetch_off_seed_products(scanned_product, category_tag)
        off_products.extend(
            product
            for product in seed_products
            if str(product.get("code") or "").strip() not in existing_codes
        )

    alternatives = []

    for off_product in off_products:
        candidate_barcode = str(off_product.get("code") or "").strip()

        if not candidate_barcode or candidate_barcode == barcode:
            continue

        candidate = build_product_from_open_food_facts(
            candidate_barcode,
            off_product,
            translate_ingredients=False,
        )

        if not candidate.get("name") or candidate["name"].startswith("Produs "):
            continue

        if all(
            candidate.get(field) is None
            for field in ("calories", "protein", "sugar", "fat")
        ):
            continue

        if not is_compatible_alternative(scanned_product, candidate):
            continue

        if "caffeine" in criteria and not is_caffeine_relevant_candidate(candidate):
            continue

        alternatives.append(candidate)

    existing_alternative_keys = {
        normalize_search_text(f"{item.get('barcode') or ''} {item.get('name') or ''}")
        for item in alternatives
    }

    for candidate in local_seed_alternatives:
        candidate_key = normalize_search_text(
            f"{candidate.get('barcode') or ''} {candidate.get('name') or ''}"
        )

        if candidate_key in existing_alternative_keys:
            continue

        alternatives.append(candidate)
        existing_alternative_keys.add(candidate_key)

    for alternative in alternatives:
        score_off_alternative(alternatives, alternative, criteria, scanned_product)

    alternatives.sort(
        key=lambda product: product["recommendationScore"],
        reverse=True,
    )
    attach_open_prices(alternatives[:18])

    for alternative in alternatives:
        score_off_alternative(alternatives, alternative, criteria, scanned_product)

    alternatives.sort(
        key=lambda product: product["recommendationScore"],
        reverse=True,
    )
    alternatives = [
        product
        for product in alternatives
        if product.get("recommendationScore", 0) > -20
    ]
    alternatives = dedupe_alternatives_by_identity(alternatives)
    photographed_alternatives = [
        product for product in alternatives if product.get("image")
    ]
    alternatives_without_photos = [
        product for product in alternatives if not product.get("image")
    ]
    products = (photographed_alternatives + alternatives_without_photos)[:6]

    if len(products) < 2:
        current_user = getattr(g, "current_user", None)
        record_search_event(
            scanned_product.get("name") or barcode or category_tag or "alternative_missing",
            store=scanned_product.get("store"),
            result_count=len(products),
            source="alternatives_low",
            user_id=getattr(current_user, "id", None),
        )
        db.session.commit()

    return jsonify({
        "source": "catalog" if prefer_local_catalog else "openfoodfacts",
        "category": category_tag,
        "products": products,
        "message": (
            (
                "Alternative calculate rapid din catalogul intern."
                if prefer_local_catalog
                else "Alternative calculate din catalogul Open Food Facts."
            )
            if alternatives
            else "Nu am gasit suficiente alternative externe pentru produsul scanat."
        ),
    })


@app.route("/analyze", methods=["POST"])
def analyze_product():
    if "image" not in request.files:
        return jsonify({
            "error": "Nu a fost trimisă nicio imagine."
        }), 400

    image = request.files["image"]
    store_id = request.form.get("store", "any")
    product_query = request.form.get("product_query", "").strip()
    label_text = request.form.get("label_text", "").strip()
    selected_barcode = request.form.get("selected_barcode", "").strip()
    demo_product_id = request.form.get("demo_product_id", "")

    if not product_query and label_text:
        product_query = label_text

    safe_original_name = secure_filename(image.filename) or "product.jpg"
    filename = f"scan_{uuid4().hex}_{safe_original_name}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    image.save(filepath)

    selected_product = None
    store_name = get_store_name_from_id(store_id)
    match_score = 0

    if selected_product is None and selected_barcode:
        if re.fullmatch(r"\d{8,14}", selected_barcode):
            try:
                selected_off_product = fetch_off_product_by_barcode(selected_barcode)
            except requests.RequestException as error:
                app.logger.warning("Selected Open Food Facts product failed: %s", error)
                selected_off_product = None

            if selected_off_product:
                selected_product_data = build_product_from_open_food_facts(
                    selected_barcode,
                    selected_off_product,
                    translate_ingredients=False,
                )
                result = product_data_to_analysis_result(
                    selected_product_data,
                    filename,
                    store_name,
                )
                result["searchedText"] = product_query
                result["confirmedSuggestion"] = True
                return jsonify(result)

    if selected_product is None and product_query:
        try:
            off_product_data, off_score = find_best_off_product_match(
                product_query,
                store_name,
            )
        except requests.RequestException as error:
            app.logger.warning("Open Food Facts analysis search failed: %s", error)
            return jsonify({
                "error": "Catalogul extern nu este disponibil momentan.",
                "code": "external_catalog_unavailable",
                "source": "openfoodfacts",
            }), 502

        if off_product_data:
            result = product_data_to_analysis_result(
                off_product_data,
                filename,
                store_name,
            )
            result["searchedText"] = product_query
            result["matchScore"] = off_score
            return jsonify(result)

    if selected_product is None and demo_product_id:
        selected_product = db.session.get(Product, int(demo_product_id))

    if selected_product is None and product_query:
        record_search_event(
            product_query,
            store=store_name,
            result_count=0,
            source="analysis_not_found",
            user_id=getattr(getattr(g, "current_user", None), "id", None),
        )
        db.session.commit()
        return jsonify({
            "product_not_found": True,
            "message": (
                "Nu am găsit o potrivire sigură în catalogul extern. "
                "Nu afișăm un produs aproximativ, deoarece ar putea fi greșit."
            ),
            "code": "external_product_not_found",
            "source": "openfoodfacts",
            "searchedText": product_query,
            "store": store_name,
            "matchScore": match_score,
            "uploadedFile": filename,
        }), 404

    if selected_product is None:
        return jsonify({
            "error": "Scrie numele produsului sau scanează codul de bare.",
            "code": "product_identity_required",
        }), 400

    result = product_to_analysis_result(selected_product, filename)

    if product_query:
        result["searchedText"] = product_query

    return jsonify(result)


# =========================
# Cart
# =========================

@app.route("/cart/<int:user_id>", methods=["GET"])
def get_cart(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    requested_profile_id = get_requested_family_profile_id()
    profile = resolve_cart_profile(user, requested_profile_id)
    items = cart_query_for_profile(user, profile).order_by(
        CartItem.created_at.desc()
    ).all()

    return jsonify([cart_item_to_dict(item) for item in items])


@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    user_id = data.get("user_id")
    product_name = data.get("name")
    store = data.get("store", "Fără magazin ales")

    if not user_id or not product_name:
        return jsonify({"error": "user_id și name sunt obligatorii."}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    requested_profile_id = get_requested_family_profile_id(data)
    profile = resolve_cart_profile(user, requested_profile_id)
    profile_id = profile.id if profile else None

    existing_item = cart_query_for_profile(user, profile).filter_by(
        product_name=product_name,
        store=store,
    ).first()

    if existing_item:
        if profile_id and existing_item.family_profile_id is None:
            existing_item.family_profile_id = profile_id
        existing_item.quantity += 1
        db.session.add(
            UsageEvent(
                user_id=user.id,
                event_type="cart_add",
                source="cart",
                metadata_json=json.dumps({
                    "productName": product_name,
                    "store": store,
                    "quantity": 1,
                    "familyProfileId": profile_id,
                }),
            )
        )
        db.session.commit()

        return jsonify({
            "message": "Cantitatea produsului a fost actualizată.",
            "item": cart_item_to_dict(existing_item)
        })

    new_item = CartItem(
        user_id=user_id,
        family_profile_id=profile_id,
        product_name=product_name,
        store=store,
        score=data.get("score"),
        price=data.get("price"),
        image=data.get("image"),
        reason=data.get("reason"),
        quantity=data.get("quantity", 1),
        bought=False,
    )

    db.session.add(new_item)
    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="cart_add",
            source="cart",
            metadata_json=json.dumps({
                "productName": product_name,
                "store": store,
                "quantity": int(data.get("quantity", 1) or 1),
                "familyProfileId": profile_id,
            }),
        )
    )
    db.session.commit()

    return jsonify({
        "message": "Produs adăugat în coș.",
        "item": cart_item_to_dict(new_item)
    }), 201


@app.route("/cart/item/<int:item_id>", methods=["PATCH"])
def update_cart_item(item_id):
    item = CartItem.query.get(item_id)

    if not item:
        return jsonify({"error": "Produsul din coș nu există."}), 404

    data = request.get_json() or {}

    if "quantity" in data:
        quantity = int(data["quantity"])

        if quantity <= 0:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"message": "Produsul a fost eliminat din coș."})

        item.quantity = quantity

    if "bought" in data:
        item.bought = bool(data["bought"])

    if "store" in data:
        item.store = data["store"]

    db.session.commit()

    return jsonify({
        "message": "Produs actualizat.",
        "item": cart_item_to_dict(item)
    })


@app.route("/cart/item/<int:item_id>", methods=["DELETE"])
def delete_cart_item(item_id):
    item = CartItem.query.get(item_id)

    if not item:
        return jsonify({"error": "Produsul din coș nu există."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Produs șters din coș."})


@app.route("/cart/clear/<int:user_id>", methods=["DELETE"])
def clear_cart(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    requested_profile_id = get_requested_family_profile_id()
    profile = resolve_cart_profile(user, requested_profile_id)
    cart_query_for_profile(user, profile).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({"message": "Coșul a fost golit."})


# =========================
# Favorites
# =========================

@app.route("/favorites/<int:user_id>", methods=["GET"])
def get_favorites(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    items = Favorite.query.filter_by(user_id=user_id).order_by(
        Favorite.created_at.desc()
    ).all()

    return jsonify([favorite_item_to_dict(item) for item in items])


@app.route("/favorites/add", methods=["POST"])
def add_to_favorites():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    user_id = data.get("user_id")
    product_name = data.get("name")
    store = data.get("store", "Fără magazin ales")

    if not user_id or not product_name:
        return jsonify({"error": "user_id și name sunt obligatorii."}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    existing_favorite = Favorite.query.filter_by(
        user_id=user_id,
        product_name=product_name,
        store=store
    ).first()

    if existing_favorite:
        return jsonify({
            "message": "Produsul este deja la favorite.",
            "item": favorite_item_to_dict(existing_favorite)
        })

    new_favorite = Favorite(
        user_id=user_id,
        product_name=product_name,
        store=store,
        category=data.get("category"),
        score=data.get("score"),
        price=data.get("price"),
        image=data.get("image"),
        reason=data.get("reason"),
    )

    db.session.add(new_favorite)
    db.session.commit()

    return jsonify({
        "message": "Produs adăugat la favorite.",
        "item": favorite_item_to_dict(new_favorite)
    }), 201


@app.route("/favorites/item/<int:favorite_id>", methods=["DELETE"])
def delete_favorite_item(favorite_id):
    item = Favorite.query.get(favorite_id)

    if not item:
        return jsonify({"error": "Produsul favorit nu există."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Produs șters din favorite."})


@app.route("/favorites/clear/<int:user_id>", methods=["DELETE"])
def clear_favorites(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    Favorite.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return jsonify({"message": "Favoritele au fost șterse."})


# =========================
# History
# =========================

@app.route("/history/<int:user_id>", methods=["GET"])
def get_scan_history(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    items = ScanHistory.query.filter_by(user_id=user_id).order_by(
        ScanHistory.scanned_at.desc()
    ).all()

    return jsonify([scan_history_item_to_dict(item) for item in items])


@app.route("/history/add", methods=["POST"])
def add_scan_history():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    user_id = data.get("user_id")
    product_name = data.get("name")
    store = data.get("store", "Fără magazin ales")

    if not user_id or not product_name:
        return jsonify({"error": "user_id și name sunt obligatorii."}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    new_history_item = ScanHistory(
        user_id=user_id,
        product_name=product_name,
        store=store,
        category=data.get("category"),
        score=data.get("score"),
        price=data.get("price"),
        image=data.get("image"),
        verdict=data.get("verdict"),
        short_advice=data.get("shortAdvice"),
    )

    db.session.add(new_history_item)
    db.session.commit()

    return jsonify({
        "message": "Scanare salvată în istoric.",
        "item": scan_history_item_to_dict(new_history_item)
    }), 201


@app.route("/history/item/<int:history_id>", methods=["DELETE"])
def delete_scan_history_item(history_id):
    item = ScanHistory.query.get(history_id)

    if not item:
        return jsonify({"error": "Scanarea nu există."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Scanare ștearsă din istoric."})


@app.route("/history/clear/<int:user_id>", methods=["DELETE"])
def clear_scan_history(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    ScanHistory.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return jsonify({"message": "Istoricul scanărilor a fost șters."})


# =========================
# Product submissions
# =========================

@app.route("/uploads/submissions/<path:filename>", methods=["GET"])
def get_submission_image(filename):
    image_path = f"/uploads/submissions/{filename}"

    if not user_can_access_submission_image(image_path):
        return jsonify({"error": "Nu poți accesa această imagine."}), 403

    return send_from_directory(SUBMISSIONS_FOLDER, filename)


@app.route("/uploads/scans/<path:filename>", methods=["GET"])
@require_auth
def get_scan_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/uploads/supabase-submissions/<path:object_path>", methods=["GET"])
def get_supabase_submission_image(object_path):
    image_path = f"/uploads/supabase-submissions/{object_path}"

    if not user_can_access_submission_image(image_path):
        return jsonify({"error": "Nu poți accesa această imagine."}), 403

    if not supabase_storage_enabled():
        return jsonify({"error": "Storage indisponibil."}), 503

    try:
        image_bytes, content_type = download_supabase_private_object(
            SUPABASE_SUBMISSIONS_BUCKET,
            object_path,
        )
    except requests.RequestException:
        return jsonify({"error": "Imaginea nu a putut fi încărcată."}), 502

    return app.response_class(image_bytes, mimetype=content_type)


@app.route("/submissions/<int:user_id>", methods=["GET"])
def get_user_submissions(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    submissions = ProductSubmission.query.filter_by(user_id=user_id).order_by(
        ProductSubmission.created_at.desc()
    ).all()

    return jsonify([product_submission_to_dict(item) for item in submissions])


@app.route("/submissions/add", methods=["POST"])
def add_product_submission():
    user_id = request.form.get("user_id")
    product_name = request.form.get("product_name", "").strip()
    store = request.form.get("store", "").strip()
    category = request.form.get("category", "").strip()
    quantity = request.form.get("quantity", "").strip()
    barcode = request.form.get("barcode", "").strip()
    brand = request.form.get("brand", "").strip()
    price = request.form.get("price", "").strip()
    ingredients = request.form.get("ingredients", "").strip()

    if not user_id or not product_name or not store:
        return jsonify({
            "error": "user_id, product_name și store sunt obligatorii."
        }), 400

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "user_id trebuie să fie un număr valid."}), 400

    validation_errors = [
        validate_text_length(product_name, "Numele produsului", 150, 2),
        validate_text_length(store, "Magazinul", 100, 2),
        validate_text_length(category, "Categoria", 100),
        validate_text_length(quantity, "Cantitatea", 100),
        validate_text_length(brand, "Brandul", 100),
        validate_text_length(price, "Prețul", 100),
        validate_text_length(ingredients, "Ingredientele", 5000),
        validate_barcode(barcode),
    ]

    calories, calories_error = parse_form_float(request.form, "calories", "Caloriile")
    protein, protein_error = parse_form_float(request.form, "protein", "Proteina")
    sugar, sugar_error = parse_form_float(request.form, "sugar", "Zahărul")
    fat, fat_error = parse_form_float(request.form, "fat", "Grăsimile")

    validation_errors.extend([
        calories_error,
        protein_error,
        sugar_error,
        fat_error,
        validate_nutrition_values(calories, protein, sugar, fat),
    ])

    validation_errors = [error for error in validation_errors if error]

    if validation_errors:
        return jsonify({
            "error": validation_errors[0],
            "errors": validation_errors,
        }), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    front_image_file = request.files.get("front_image")
    nutrition_image_file = request.files.get("nutrition_image")

    try:
        front_image_path = save_uploaded_file(front_image_file, SUBMISSIONS_FOLDER)
        nutrition_image_path = save_uploaded_file(nutrition_image_file, SUBMISSIONS_FOLDER)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    new_submission = ProductSubmission(
    user_id=user_id,
    product_name=product_name,
    brand=brand,
    store=store,
    category=category,
    quantity=quantity,
    barcode=barcode,
    price=price,
    front_image=front_image_path,
    nutrition_image=nutrition_image_path,
    calories=calories,
    protein=protein,
    sugar=sugar,
    fat=fat,
    ingredients=ingredients,
    status="pending",
)
    db.session.add(new_submission)
    db.session.commit()

    return jsonify({
        "message": "Produsul a fost trimis ca propunere.",
        "item": product_submission_to_dict(new_submission)
    }), 201


@app.route("/submissions/item/<int:submission_id>", methods=["DELETE"])
def delete_product_submission(submission_id):
    submission = ProductSubmission.query.get(submission_id)

    if not submission:
        return jsonify({"error": "Propunerea nu există."}), 404

    db.session.delete(submission)
    db.session.commit()

    return jsonify({"message": "Propunerea a fost ștearsă."})


@app.route("/submissions/ai-review/<int:submission_id>", methods=["POST"])
def ai_review_product_submission(submission_id):
    submission = ProductSubmission.query.get(submission_id)

    if not submission:
        return jsonify({"error": "Propunerea nu există."}), 404

    review = review_product_submission_with_ai(submission)

    submission.status = review["status"]
    db.session.commit()

    return jsonify({
        "message": review["message"],
        "status": review["status"],
        "confidence": review["confidence"],
        "problems": review["problems"],
        "warnings": review["warnings"],
        "item": product_submission_to_dict(submission),
    })


@app.route("/submissions/approve/<int:submission_id>", methods=["POST"])
def approve_product_submission(submission_id):
    submission = ProductSubmission.query.get(submission_id)

    if not submission:
        return jsonify({"error": "Propunerea nu există."}), 404

    if submission.status != "ai_approved":
        return jsonify({
            "error": "Produsul poate fi publicat doar dacă are status ai_approved."
        }), 400

    existing_product = None

    if submission.barcode:
        existing_product = Product.query.filter_by(barcode=submission.barcode).first()

    if existing_product is None:
        existing_product = find_duplicate_product_for_submission(submission)

    if existing_product:
        submission.status = "approved"
        contributor = db.session.get(User, submission.user_id)
        add_bonus_scan_credits(
            contributor,
            SUBMISSION_APPROVAL_BONUS_CREDITS,
            "submission_approved",
            {"submissionId": submission.id, "productId": existing_product.id},
        )
        db.session.commit()

        return jsonify({
            "message": "Produsul exista deja în baza oficială. Propunerea a fost aprobată, iar utilizatorul a primit o scanare bonus.",
            "product": product_to_dict(existing_product),
            "submission": product_submission_to_dict(submission),
        })

    try:
        published_image = publish_submission_image(submission.front_image)
    except requests.RequestException:
        return jsonify({
            "error": "Imaginea produsului nu a putut fi publicată momentan."
        }), 502

    calculated_score = calculate_product_score(
        submission.category,
        submission.calories,
        submission.protein,
        submission.sugar,
        submission.fat,
        submission.ingredients,
    )

    generated_tag = generate_product_tag(
        submission.category,
        submission.calories,
        submission.protein,
        submission.sugar,
        submission.fat,
        submission.ingredients,
    )

    generated_reason = generate_product_reason(
        submission.category,
        submission.calories,
        submission.protein,
        submission.sugar,
        submission.fat,
        submission.ingredients,
    )

    new_product = Product(
    name=submission.product_name,
    store=submission.store,
    category=submission.category or "Altele",
    barcode=submission.barcode,
    score=calculated_score,
    tag=generated_tag,
    image=published_image,
    price=None,
    price_text=submission.price or "preț necunoscut",
    calories=submission.calories,
    protein=submission.protein,
    sugar=submission.sugar,
    fat=submission.fat,
    vegan=False,
    lactose_free=False,
    natural=False,
    reason=generated_reason,
)

    db.session.add(new_product)
    submission.status = "approved"
    contributor = db.session.get(User, submission.user_id)
    add_bonus_scan_credits(
        contributor,
        SUBMISSION_APPROVAL_BONUS_CREDITS,
        "submission_approved",
        {"submissionId": submission.id},
    )
    db.session.commit()

    return jsonify({
        "message": "Produsul a fost publicat în baza oficială, iar utilizatorul a primit o scanare bonus.",
        "product": product_to_dict(new_product),
        "submission": product_submission_to_dict(submission),
    })

@app.route("/ai/extract-product-info", methods=["POST"])
def ai_extract_product_info():
    front_image = request.files.get("front_image")
    nutrition_image = request.files.get("nutrition_image")
    product_hint = request.form.get("product_hint", "").strip()

    if not front_image and not nutrition_image and not product_hint:
        return jsonify({
            "error": "Trimite cel puțin o poză sau un nume aproximativ al produsului."
        }), 400

    extracted = {
        "productName": "",
        "brand": "",
        "category": "Altele",
        "quantityValue": "",
        "quantityUnit": "g",
        "calories": "",
        "protein": "",
        "sugar": "",
        "fat": "",
        "ingredients": "",
        "confidence": 60,
        "source": "AI demo local",
        "notes": [],
    }

    hint = product_hint.lower()

    front_filename = front_image.filename.lower() if front_image else ""
    nutrition_filename = nutrition_image.filename.lower() if nutrition_image else ""

    combined_text = f"{hint} {front_filename} {nutrition_filename}"

    if "monster" in combined_text:
        extracted["productName"] = "Monster Energy Ultra White"
        extracted["brand"] = "Monster"
        extracted["category"] = "Băuturi energizante"
        extracted["quantityValue"] = "500"
        extracted["quantityUnit"] = "ml"
        extracted["calories"] = "11"
        extracted["protein"] = "0"
        extracted["sugar"] = "0"
        extracted["fat"] = "0"
        extracted["ingredients"] = "Fără zahăr, conține cafeină, cu îndulcitori."
        extracted["confidence"] = 82
        extracted["notes"].append("Produs detectat după indiciul introdus sau numele fișierului.")

    elif "skyr" in combined_text:
        extracted["productName"] = "Skyr natural"
        extracted["brand"] = ""
        extracted["category"] = "Lactate"
        extracted["quantityValue"] = "150"
        extracted["quantityUnit"] = "g"
        extracted["calories"] = "65"
        extracted["protein"] = "11"
        extracted["sugar"] = "4"
        extracted["fat"] = "0.2"
        extracted["ingredients"] = "Produs lactat bogat în proteină."
        extracted["confidence"] = 78
        extracted["notes"].append("Produs detectat după indiciul introdus sau numele fișierului.")

    elif "iaurt" in combined_text or "yogurt" in combined_text:
        extracted["productName"] = "Iaurt natural"
        extracted["brand"] = ""
        extracted["category"] = "Lactate"
        extracted["quantityValue"] = "150"
        extracted["quantityUnit"] = "g"
        extracted["calories"] = "62"
        extracted["protein"] = "4"
        extracted["sugar"] = "3.8"
        extracted["fat"] = "3.2"
        extracted["ingredients"] = "Iaurt simplu, valori completate estimativ pentru demo."
        extracted["confidence"] = 70
        extracted["notes"].append("Categorie detectată după textul introdus.")

    else:
        extracted["productName"] = product_hint
        extracted["brand"] = ""
        extracted["category"] = "Altele"
        extracted["quantityValue"] = ""
        extracted["quantityUnit"] = "g"
        extracted["calories"] = ""
        extracted["protein"] = ""
        extracted["sugar"] = ""
        extracted["fat"] = ""
        extracted["ingredients"] = ""
        extracted["confidence"] = 35
        extracted["notes"].append(
            "Nu am putut identifica sigur produsul. Completează manual câmpurile rămase."
        )

    return jsonify({
        "message": "Date extrase automat în mod demo.",
        "data": extracted,
    })

def find_duplicate_products():
    products = Product.query.order_by(Product.id.asc()).all()

    removed = []
    kept = []

    for product in products:
        already_removed = any(item["removed_id"] == product.id for item in removed)

        if already_removed:
            continue

        duplicate_found = False

        for kept_product in kept:
            same_store = product.store == kept_product.store
            same_category = normalize_search_text(product.category) == normalize_search_text(
                kept_product.category
            )

            product_name = normalize_product_name_for_duplicate(product.name)
            kept_name = normalize_product_name_for_duplicate(kept_product.name)

            name_similarity = SequenceMatcher(None, product_name, kept_name).ratio()

            same_nutrition = (
                numbers_are_close(product.calories, kept_product.calories)
                and numbers_are_close(product.protein, kept_product.protein)
                and numbers_are_close(product.sugar, kept_product.sugar)
                and numbers_are_close(product.fat, kept_product.fat)
            )

            is_duplicate = (
                same_store
                and same_category
                and same_nutrition
                and (
                    product_name == kept_name
                    or name_similarity >= 0.78
                )
            )

            if is_duplicate:
                removed.append({
                    "removed_id": product.id,
                    "removed_name": product.name,
                    "kept_id": kept_product.id,
                    "kept_name": kept_product.name,
                })
                duplicate_found = True
                break

        if not duplicate_found:
            kept.append(product)

    return removed


def find_demo_products():
    return [
        product
        for product in Product.query.order_by(Product.id.asc()).all()
        if (product.barcode or "").startswith("test-")
        or product.name == "Produs OFF Test"
    ]


@app.route("/products/cleanup-duplicates", methods=["POST", "GET"])
def cleanup_duplicate_products():
    duplicates = find_duplicate_products()
    demo_products = find_demo_products()
    demo_product_report = [
        {
            "removed_id": product.id,
            "removed_name": product.name,
            "barcode": product.barcode,
        }
        for product in demo_products
    ]
    should_apply = (
        request.method == "POST"
        and request.args.get("apply", "").lower() == "true"
    )

    if should_apply:
        product_ids = {
            item["removed_id"] for item in duplicates
        } | {
            product.id for product in demo_products
        }

        if product_ids:
            Product.query.filter(Product.id.in_(product_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()

    return jsonify({
        "message": (
            "Curățare duplicate finalizată."
            if should_apply
            else "Previzualizare curățare duplicate."
        ),
        "applied": should_apply,
        "removed_count": len(duplicates) + len(demo_products),
        "duplicates": duplicates,
        "demo_products": demo_product_report,
    })

def get_off_value(nutriments, key):
    value = nutriments.get(key)

    if value is None:
        value = nutriments.get(f"{key}_100g")

    return value


def get_localized_off_text(off_product, field):
    return (
        off_product.get(f"{field}_ro")
        or off_product.get(f"{field}_en")
        or off_product.get(field)
        or ""
    )


@lru_cache(maxsize=256)
def translate_ingredients_to_romanian(ingredients):
    libretranslate_url = os.environ.get("LIBRETRANSLATE_URL", "").strip().rstrip("/")

    if not libretranslate_url or not ingredients:
        return ingredients

    try:
        response = requests.post(
            f"{libretranslate_url}/translate",
            json={
                "q": ingredients[:4000],
                "source": "auto",
                "target": "ro",
                "format": "text",
            },
            timeout=5,
        )

        if response.status_code >= 400:
            app.logger.warning(
                "LibreTranslate ingredient translation failed with status %s: %s",
                response.status_code,
                response.text[:500],
            )
            return ingredients

        translated_text = response.json().get("translatedText", "").strip()
        return translated_text or ingredients
    except (requests.RequestException, ValueError, KeyError) as error:
        app.logger.warning("LibreTranslate ingredient translation failed: %s", error)
        return ingredients


@lru_cache(maxsize=512)
def translate_catalog_text(text_value, target_language):
    libretranslate_url = os.environ.get("LIBRETRANSLATE_URL", "").strip().rstrip("/")
    text_value = (text_value or "").strip()

    if not libretranslate_url or not text_value or target_language not in {"ro", "en"}:
        return text_value

    try:
        response = requests.post(
            f"{libretranslate_url}/translate",
            json={
                "q": text_value[:5000],
                "source": "auto",
                "target": target_language,
                "format": "text",
            },
            timeout=7,
        )
        response.raise_for_status()
        return response.json().get("translatedText", "").strip() or text_value
    except (requests.RequestException, ValueError, KeyError) as error:
        app.logger.warning("Catalog text translation failed: %s", error)
        return text_value


@app.route("/translate", methods=["POST"])
def translate_text():
    data = request.get_json(silent=True) or {}
    text_value = str(data.get("text") or "").strip()
    target_language = str(data.get("target") or "ro").strip().lower()

    if not text_value:
        return jsonify({"translatedText": ""})

    if len(text_value) > 5000:
        return jsonify({"error": "Textul este prea lung."}), 400

    if target_language not in {"ro", "en"}:
        return jsonify({"error": "Limba ceruta nu este acceptata."}), 400

    return jsonify({
        "translatedText": translate_catalog_text(text_value, target_language),
        "target": target_language,
    })


def build_product_from_open_food_facts(barcode, off_product, translate_ingredients=True):
    nutriments = off_product.get("nutriments", {})

    product_name = (
        get_localized_off_text(off_product, "product_name")
        or get_localized_off_text(off_product, "generic_name")
        or f"Produs {barcode}"
    )

    brands = off_product.get("brands", "")
    quantity = off_product.get("quantity", "")
    categories = off_product.get("categories", "")
    categories_tags = off_product.get("categories_tags", [])
    labels_tags = off_product.get("labels_tags", [])
    ingredients_analysis_tags = off_product.get("ingredients_analysis_tags", [])

    calories = get_off_value(nutriments, "energy-kcal")
    protein = get_off_value(nutriments, "proteins")
    sugar = get_off_value(nutriments, "sugars")
    fat = get_off_value(nutriments, "fat")

    ingredients = get_localized_off_text(off_product, "ingredients_text")

    if (
        translate_ingredients
        and ingredients
        and not off_product.get("ingredients_text_ro")
    ):
        ingredients = translate_ingredients_to_romanian(ingredients)

    category = "Altele"
    categories_lower = categories.lower()
    tags_text = normalize_search_text(" ".join(str(tag) for tag in categories_tags))
    product_text = normalize_search_text(
        " ".join([product_name, brands, categories, tags_text, ingredients or ""])
    )

    def has_any(tokens):
        return any(token in product_text for token in tokens)

    if has_any(["buldak", "samyang", "ramen", "instant noodles", "cup noodles", "noodle", "noodles", "taitei", "nongshim", "yakisoba", "udon"]):
        category = "Tăiței instant"
    elif has_any(["ice cream", "icecream", "gelato", "sorbet", "inghetata"]):
        category = "Înghețată"
    elif has_any(["energy drink", "energiz", "red bull", "redbull", "monster", "hell", "burn", "rockstar", "taurina", "taurine"]) or "energy-drinks" in tags_text:
        category = "Băuturi energizante"
    elif has_any(["coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "ice coffee", "iced coffee", "cold brew", "frappe"]):
        category = "Băuturi cu cafea"
    elif has_any(["cola", "pepsi", "coca cola", "coca-cola", "cocacola", "soda", "soft drink", "carbonated drink"]):
        category = "Băuturi răcoritoare"
    elif has_any(["juice", "suc", "nectar", "smoothie"]):
        category = "Sucuri"
    elif has_any(["water", "apa", "mineral", "minerala", "spring water", "eau minerale"]):
        category = "Apă"
    elif (
        "dairy dessert" in categories_lower
        or "dessert" in categories_lower
        or "pudding" in categories_lower
        or "custard" in categories_lower
        or "cream dessert" in categories_lower
        or has_any(["danette", "budinca", "desert lactat", "dairy dessert"])
    ):
        category = "Deserturi lactate"
    elif has_any(["iaurt", "yogurt", "yoghurt", "skyr", "zuzu"]) and has_any(["fruct", "fructe", "capsuni", "strawberry", "piersici", "peach", "visine", "cherry", "afine", "blueberry", "zmeura", "raspberry", "padure", "berries"]):
        category = "Iaurturi cu fructe"
    elif has_any(["cheese", "branza", "branzeturi", "cascaval", "mozzarella", "telemea", "feta"]):
        category = "Lactate și brânzeturi"
    elif "plant-based-milks" in tags_text or has_any(["lapte vegetal", "plant based milk", "oat drink", "almond drink", "soy drink"]):
        category = "Alternative vegetale"
    elif "yogurt" in categories_lower or "dairy" in categories_lower or has_any(["iaurt", "yogurt", "yoghurt", "skyr", "lapte", "milk"]):
        category = "Lactate"
    elif has_any(["protein bar", "protein", "proteic", "proteina", "whey", "sports nutrition"]):
        category = "Proteine și fitness"
    elif has_any(["chips", "crisps", "crackers", "popcorn", "salty snack", "pufule"]):
        category = "Snacks sărate"
    elif "cereal" in categories_lower or has_any(["cereale", "cereal", "muesli", "granola", "oatmeal"]):
        category = "Cereale"
    elif "bread" in categories_lower or "bakery" in categories_lower or has_any(["paine", "bread", "toast", "bagheta", "chifla"]):
        category = "Panificație"
    elif has_any(["pizza"]):
        category = "Pizza"
    elif "frozen" in categories_lower or has_any(["frozen", "congelat", "congelata"]):
        category = "Congelate"
    elif "ready meal" in categories_lower or has_any(["ready meal", "meal", "sandwich", "salata", "supa", "soup"]):
        category = "Mese gata preparate"
    elif has_any(["sauce", "sos", "mustard", "mustar", "ketchup", "mayonnaise", "maioneza", "salsa", "condiment"]):
        category = "Sosuri și condimente"
    elif has_any(["pasta", "paste", "rice", "orez", "beans", "lentils", "linte", "naut", "chickpeas", "fasole"]):
        category = "Paste, orez și leguminoase"
    elif has_any(["canned", "conserva", "conserve", "pickles", "muraturi", "olives", "masline"]):
        category = "Conserve și murături"
    elif has_any(["oil", "ulei", "vinegar", "otet", "spice", "condiment"]):
        category = "Uleiuri și condimente"
    elif "meat" in categories_lower or has_any(["carne", "meat", "salam", "sausage", "carnati", "ham"]):
        category = "Carne"
    elif has_any(["fish", "peste", "tuna", "ton", "somon", "salmon", "seafood"]):
        category = "Pește și fructe de mare"
    elif "fruit" in categories_lower or "vegetable" in categories_lower or has_any(["fruct", "vegetable", "legume", "salata"]):
        category = "Fructe și legume"
    elif has_any(["spread", "crema tartinabila", "hazelnut spread", "peanut butter", "gem", "jam", "miere", "honey"]):
        category = "Creme și gemuri"
    elif has_any(["nuts", "nuci", "alune", "seeds", "seminte", "dried fruits"]):
        category = "Nuci și semințe"
    elif "sweet" in categories_lower or "candy" in categories_lower or "chocolate" in categories_lower or has_any(["ciocolata", "chocolate", "biscuit", "wafer", "napolitana", "dulce", "candy"]):
        category = "Dulciuri"
    elif "beverage" in categories_lower or "drink" in categories_lower:
        category = "Băuturi"

    vegan = "en:vegan" in ingredients_analysis_tags or "en:vegan" in labels_tags
    lactose_free = "en:lactose-free" in labels_tags
    additives_n = off_product.get("additives_n")
    natural = additives_n == 0 if additives_n is not None else False

    has_nutrition_data = any(
        value is not None
        for value in (calories, protein, sugar, fat)
    )

    score = (
        calculate_product_score(
            category,
            calories,
            protein,
            sugar,
            fat,
            ingredients,
        )
        if has_nutrition_data
        else None
    )

    tag = generate_product_tag(
        category,
        calories,
        protein,
        sugar,
        fat,
        ingredients,
    )

    reason = generate_product_reason(
        category,
        calories,
        protein,
        sugar,
        fat,
        ingredients,
    )

    return {
        "id": None,
        "barcode": barcode,
        "name": product_name,
        "brand": brands,
        "store": "Open Food Facts",
        "category": category,
        "quantity": quantity,
        "score": score,
        "tag": tag,
        "image": off_product.get("image_front_url") or off_product.get("image_url"),
        "price": None,
        "priceText": "preț necunoscut",
        "calories": calories,
        "protein": protein,
        "sugar": sugar,
        "fat": fat,
        "vegan": vegan,
        "lactoseFree": lactose_free,
        "natural": natural,
        "nutriScore": off_product.get("nutrition_grades"),
        "offCategories": categories_tags,
        "reason": reason,
        "ingredients": ingredients,
    }


def convert_price_to_ron(value, currency):
    currency_code = str(currency or "RON").strip().upper()
    rate = APPROX_RON_EXCHANGE_RATES.get(currency_code)

    if rate is None:
        return None

    try:
        return round(float(value) * rate, 2)
    except (TypeError, ValueError):
        return None


def format_ron_price(value, approximate=False):
    amount = f"{float(value):.2f}".replace(".", ",")
    prefix = "aprox. " if approximate else ""
    return f"{prefix}{amount} lei"


def format_observed_price(value, currency):
    currency_code = str(currency or "RON").strip().upper()

    if currency_code == "RON":
        return format_ron_price(value)

    converted_value = convert_price_to_ron(value, currency_code)

    if converted_value is not None:
        return format_ron_price(converted_value, approximate=True)

    return "Verifică prețul în magazin"


def get_local_price_summary(barcode):
    if not barcode:
        return None

    observation = (
        PriceObservation.query
        .filter_by(product_barcode=barcode, currency="RON")
        .order_by(PriceObservation.observed_at.desc())
        .first()
    )

    if not observation:
        return None

    return {
        "price": observation.price,
        "priceText": format_observed_price(observation.price, observation.currency),
        "priceSource": "Ce aleg?",
        "priceStore": observation.store,
        "priceCountry": "RO",
        "priceDate": observation.observed_at.date().isoformat(),
        "priceCurrency": observation.currency,
        "priceIsLocal": True,
    }


def get_open_prices_summary(barcode):
    if not barcode:
        return None

    now = time.time()
    cache_item = OPEN_PRICES_CACHE.get(barcode)

    if cache_item and now - cache_item["created_at"] < OPEN_PRICES_CACHE_TTL:
        return cache_item["summary"]

    try:
        response = requests.get(
            "https://prices.openfoodfacts.org/api/v1/prices",
            params={
                "product_code": barcode,
                "size": 12,
                "order_by": "-date",
            },
            headers={
                "User-Agent": "CeAlegApp/1.0 (contact: contact@cealeg.shop)",
                "Accept": "application/json",
            },
            timeout=6,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except (requests.RequestException, ValueError, KeyError) as error:
        app.logger.warning("Open Prices lookup failed for %s: %s", barcode, error)
        items = []

    valid_items = [
        item
        for item in items
        if item.get("price") is not None and item.get("currency")
    ]

    valid_items.sort(
        key=lambda item: (
            item.get("location", {}).get("osm_address_country_code") == "RO",
            item.get("currency") == "RON",
            item.get("date") or "",
        ),
        reverse=True,
    )

    if valid_items:
        selected = valid_items[0]
        location = selected.get("location") or {}
        currency = selected.get("currency")
        converted_price = convert_price_to_ron(selected["price"], currency)
        displayed_price = (
            float(selected["price"])
            if str(currency or "").upper() == "RON"
            else converted_price
        )
        summary = {
            "price": displayed_price,
            "priceText": format_observed_price(selected["price"], currency),
            "priceSource": "Open Prices",
            "priceStore": (
                location.get("osm_name")
                or location.get("osm_brand")
                or "magazin raportat"
            ),
            "priceCountry": location.get("osm_address_country_code"),
            "priceDate": selected.get("date"),
            "priceCurrency": "RON" if displayed_price is not None else currency,
            "priceOriginal": float(selected["price"]),
            "priceOriginalCurrency": currency,
            "priceIsLocal": (
                location.get("osm_address_country_code") == "RO"
                or currency == "RON"
            ),
            "priceIsConverted": str(currency or "").upper() != "RON" and displayed_price is not None,
        }
    else:
        summary = None

    OPEN_PRICES_CACHE[barcode] = {
        "created_at": now,
        "summary": summary,
    }
    return summary


def attach_open_prices(products):
    products_with_barcodes = [
        product for product in products if product.get("barcode")
    ]

    products_needing_open_price = []

    for product in products_with_barcodes:
        summary = get_local_price_summary(product["barcode"])

        if summary:
            product.update(summary)
        else:
            products_needing_open_price.append(product)

    if not products_needing_open_price:
        return

    def fetch_external_price_summary(barcode):
        try:
            return get_open_prices_summary(barcode)
        except requests.RequestException as error:
            app.logger.warning(
                "Open Prices lookup failed for %s: %s",
                barcode,
                error,
            )
            return None

    with ThreadPoolExecutor(max_workers=6) as executor:
        summaries = executor.map(
            fetch_external_price_summary,
            [product["barcode"] for product in products_needing_open_price],
        )

    for product, summary in zip(products_needing_open_price, summaries):
        if summary:
            product.update(summary)


def product_to_dict_with_open_price(product):
    product_data = product_to_dict(product)
    summary = get_local_price_summary(product.barcode) or get_open_prices_summary(
        product.barcode
    )

    if summary and product.price is None:
        product_data.update(summary)

    return product_data


@app.route("/prices/report", methods=["POST"])
def report_local_price():
    data = request.get_json(silent=True) or {}
    barcode = str(data.get("barcode") or "").strip()
    store = str(data.get("store") or "").strip()
    user_id = data.get("user_id")
    price = parse_optional_float(data.get("price"))

    validation_errors = [
        validate_barcode(barcode, required=True),
        "Alege magazinul." if not store else None,
        validate_text_length(store, "Magazinul", 100),
    ]

    if not user_id or not User.query.get(user_id):
        validation_errors.append("Autentifică-te pentru a salva prețul.")

    if price is None or price <= 0 or price > 100000:
        validation_errors.append("Introdu un preț valid.")

    validation_errors = [error for error in validation_errors if error]

    if validation_errors:
        return jsonify({"error": " ".join(validation_errors)}), 400

    observation = PriceObservation(
        user_id=user_id,
        product_barcode=barcode,
        store=store,
        price=price,
        currency="RON",
    )
    db.session.add(observation)
    db.session.commit()

    return jsonify({
        "message": "Prețul a fost salvat. Mulțumim pentru contribuție.",
        "price": get_local_price_summary(barcode),
    }), 201


@app.route("/prices/<barcode>", methods=["GET"])
def get_latest_local_price(barcode):
    barcode_error = validate_barcode(barcode, required=True)

    if barcode_error:
        return jsonify({"error": barcode_error}), 400

    summary = get_local_price_summary(barcode)

    return jsonify({
        "found": bool(summary),
        "price": summary,
    })


def get_product_recommendation_family(product_data):
    off_categories = product_data.get("offCategories") or []

    if isinstance(off_categories, str):
        off_categories = [off_categories]

    text_value = normalize_search_text(
        " ".join([
            str(product_data.get("name") or ""),
            str(product_data.get("brand") or ""),
            str(product_data.get("category") or ""),
            str(product_data.get("store") or ""),
            str(product_data.get("ingredients") or ""),
            str(product_data.get("tag") or ""),
            " ".join(off_categories),
        ])
    )

    water_words = [
        "apa",
        "water",
        "mineral",
        "minerala",
        "minerale",
        "eau",
        "sidi",
        "aquafina",
        "ain atlas",
        "spring",
    ]
    energy_words = [
        "energy",
        "energiz",
        "red bull",
        "redbull",
        "monster",
        "hell",
        "burn",
        "rockstar",
        "taurina",
        "taurine",
    ]
    coffee_words = [
        "coffee",
        "cafea",
        "cafe",
        "cappuccino",
        "capuccino",
        "latte",
        "mocha",
        "espresso",
        "iced coffee",
        "ice coffee",
        "cold brew",
        "frappe",
    ]
    caffeine_words = ["cafeina", "cofeina", "caffeine", "cafein"]
    cola_words = ["cola", "pepsi", "coca cola", "coca-cola"]
    dairy_dessert_words = [
        "danette",
        "budinca",
        "pudding",
        "custard",
        "desert lactat",
        "dairy dessert",
    ]
    ice_cream_words = [
        "inghetata",
        "ice cream",
        "icecream",
        "gelato",
        "sorbet",
        "gelatelli",
    ]
    instant_noodle_words = [
        "buldak",
        "samyang",
        "ramen",
        "noodle",
        "noodles",
        "taitei",
        "taitel",
        "taietei",
        "instant noodles",
        "cup noodles",
        "nongshim",
        "yakisoba",
        "udon",
        "soba",
    ]
    yogurt_words = ["iaurt", "yogurt", "yoghurt", "skyr", "zuzu", "activia", "danone"]
    fruit_words = [
        "fruct",
        "fructe",
        "capsuni",
        "capsuna",
        "strawberry",
        "berries",
        "padure",
        "piersici",
        "peach",
        "visine",
        "cherry",
        "afine",
        "blueberry",
        "zmeura",
        "raspberry",
    ]
    protein_words = ["protein", "proteic", "proteina", "whey", "fitness"]
    salty_snack_words = ["chips", "crisps", "crackers", "popcorn", "pufule", "salty snack"]
    sweet_snack_words = ["ciocolata", "chocolate", "biscuit", "wafer", "napolitana", "candy", "dulce"]
    cereal_words = ["cereale", "cereal", "muesli", "granola", "oatmeal"]
    sauce_words = ["sos", "sauce", "mustar", "ketchup", "maioneza", "mayonnaise", "salsa", "condiment"]
    bread_words = ["paine", "bread", "toast", "bagheta", "chifla", "bakery"]
    meat_words = [
        "carne",
        "meat",
        "salam",
        "sausage",
        "carnati",
        "ham",
        "prosciutto",
        "jambon",
        "sunca",
        "șuncă",
        "muschi",
        "mușchi",
        "file",
        "filet",
        "filetto",
        "porc",
        "pork",
        "pui",
        "chicken",
        "curcan",
        "turkey",
        "pastrama",
        "pastramă",
        "bacon",
    ]
    fish_words = ["peste", "fish", "ton", "tuna", "somon", "salmon", "seafood"]
    spread_words = ["spread", "crema tartinabila", "nutella", "peanut butter", "gem", "jam", "miere", "honey"]
    nuts_words = ["nuts", "nuci", "alune", "seeds", "seminte"]
    ready_meal_words = ["ready meal", "sandwich", "salata", "supa", "soup"]
    frozen_words = ["frozen", "congelat", "congelata"]

    if any(word in text_value for word in instant_noodle_words):
        return "instant_noodles"

    if any(word in text_value for word in ice_cream_words):
        return "ice_cream"

    if any(word in text_value for word in water_words) and not any(
        word in text_value
        for word in energy_words + coffee_words + caffeine_words + cola_words
    ):
        return "water"

    if any(word in text_value for word in coffee_words):
        return "coffee_drink"

    if any(word in text_value for word in energy_words):
        return "energy_drink"

    if any(word in text_value for word in cola_words):
        return "cola"

    if any(word in text_value for word in caffeine_words):
        return "caffeinated_beverage"

    if any(word in text_value for word in dairy_dessert_words):
        return "dairy_dessert"

    if any(word in text_value for word in yogurt_words) and any(
        word in text_value for word in fruit_words
    ):
        return "fruit_yogurt"

    if any(word in text_value for word in ["lactate", "dairy", "iaurt", "yogurt", "yoghurt", "skyr", "lapte", "milk"]):
        return "lactate"

    if any(word in text_value for word in protein_words):
        return "protein"

    if any(word in text_value for word in salty_snack_words):
        return "salty_snack"

    if any(word in text_value for word in cereal_words):
        return "cereal"

    if any(word in text_value for word in sauce_words):
        return "sauce"

    if "pizza" in text_value:
        return "pizza"

    if any(word in text_value for word in frozen_words):
        return "frozen"

    if any(word in text_value for word in ready_meal_words):
        return "ready_meal"

    if any(word in text_value for word in bread_words):
        return "bread"

    if any(word in text_value for word in meat_words):
        return "meat"

    if any(word in text_value for word in fish_words):
        return "fish"

    if any(word in text_value for word in spread_words):
        return "spread"

    if any(word in text_value for word in nuts_words):
        return "nuts"

    if any(word in text_value for word in sweet_snack_words):
        return "sweet_snack"

    if "bauturi" in text_value or "beverage" in text_value or "drink" in text_value:
        return "beverage"

    return "general"


def is_compatible_alternative(scanned_product, candidate):
    scanned_family = get_product_recommendation_family(scanned_product)
    candidate_family = get_product_recommendation_family(candidate)
    scanned_text = product_text_for_recommendation(scanned_product)
    candidate_text = product_text_for_recommendation(candidate)
    beverage_families = {
        "water",
        "cola",
        "beverage",
        "energy_drink",
        "coffee_drink",
        "caffeinated_beverage",
    }
    lactate_families = {"lactate", "fruit_yogurt", "dairy_dessert"}
    strict_food_families = {
        "protein",
        "salty_snack",
        "sweet_snack",
        "cereal",
        "sauce",
        "ice_cream",
        "pizza",
        "frozen",
        "ready_meal",
        "bread",
        "meat",
        "fish",
        "spread",
        "nuts",
    }
    non_food_beverage_blocks = beverage_families | {
        "instant_noodles",
        "lactate",
        "fruit_yogurt",
        "dairy_dessert",
        "protein",
        "salty_snack",
        "sweet_snack",
        "cereal",
        "sauce",
        "ice_cream",
        "pizza",
        "frozen",
        "ready_meal",
        "bread",
        "meat",
        "fish",
        "spread",
        "nuts",
    }
    incompatible_families = {
        "instant_noodles": non_food_beverage_blocks - {"instant_noodles"},
        "energy_drink": non_food_beverage_blocks - {"energy_drink", "coffee_drink", "caffeinated_beverage"},
        "coffee_drink": non_food_beverage_blocks - {"coffee_drink", "energy_drink", "caffeinated_beverage"},
        "caffeinated_beverage": non_food_beverage_blocks - {"coffee_drink", "energy_drink", "caffeinated_beverage"},
        "cola": non_food_beverage_blocks - {"cola", "energy_drink", "caffeinated_beverage"},
        "water": non_food_beverage_blocks - {"water"},
        "fruit_yogurt": non_food_beverage_blocks - {"fruit_yogurt", "lactate"},
        "lactate": non_food_beverage_blocks - {"fruit_yogurt", "lactate", "dairy_dessert"},
        "dairy_dessert": non_food_beverage_blocks - {"dairy_dessert", "lactate", "fruit_yogurt"},
        "meat": non_food_beverage_blocks - {"meat"},
        "fish": non_food_beverage_blocks - {"fish"},
        "ice_cream": non_food_beverage_blocks - {"ice_cream"},
        "sauce": non_food_beverage_blocks - {"sauce"},
        "spread": non_food_beverage_blocks - {"spread", "nuts"},
    }

    if candidate_family in incompatible_families.get(scanned_family, set()):
        return False

    if scanned_family == "general":
        signal_rules = [
            (["buldak", "ramen", "noodle", "taitei", "taitel"], {"instant_noodles"}),
            (["iaurt", "yogurt", "yoghurt", "zuzu", "skyr"], {"fruit_yogurt", "lactate"}),
            (["energiz", "red bull", "redbull", "monster", "hell", "taurina"], {"energy_drink", "caffeinated_beverage"}),
            (["cafea", "coffee", "cappuccino", "latte", "espresso"], {"coffee_drink", "energy_drink", "caffeinated_beverage"}),
            (["muschi", "mușchi", "file", "filet", "sunca", "șuncă", "salam", "prosciutto"], {"meat"}),
        ]

        for tokens, allowed_families in signal_rules:
            if any(token in scanned_text for token in tokens):
                return candidate_family in allowed_families

    if candidate_family == "water" and scanned_family != "water":
        return False

    if scanned_family == "water":
        return candidate_family == "water"

    if scanned_family not in beverage_families and candidate_family in beverage_families:
        return False

    if scanned_family in beverage_families and candidate_family not in beverage_families:
        return False

    if scanned_family == "instant_noodles":
        return candidate_family == "instant_noodles"

    if candidate_family == "instant_noodles":
        return scanned_family == "instant_noodles"

    if scanned_family == "fruit_yogurt":
        if candidate_family not in {"fruit_yogurt", "lactate"}:
            return False
        return any(token in candidate_text for token in ["iaurt", "yogurt", "yoghurt", "skyr", "zuzu", "fruct"])

    if scanned_family == "lactate":
        return candidate_family in lactate_families

    if candidate_family in lactate_families and scanned_family not in lactate_families:
        return False

    if scanned_family in strict_food_families:
        return candidate_family == scanned_family

    if candidate_family in strict_food_families and scanned_family != candidate_family:
        return False

    if scanned_family == "energy_drink":
        return candidate_family in {"energy_drink", "caffeinated_beverage"}

    if scanned_family == "coffee_drink":
        return candidate_family in {"coffee_drink", "energy_drink", "caffeinated_beverage"}

    if scanned_family == "caffeinated_beverage":
        return candidate_family in {"coffee_drink", "energy_drink", "caffeinated_beverage"}

    if scanned_family == "cola":
        return candidate_family in {"cola", "energy_drink", "caffeinated_beverage"}

    if scanned_family == "dairy_dessert":
        return candidate_family in {"dairy_dessert", "lactate", "fruit_yogurt"} or (
            normalize_search_text(candidate.get("category")) in {"lactate", "deserturi lactate"}
        )

    if scanned_family == "general" and (
        "ramen" in scanned_text
        or "buldak" in scanned_text
        or "iaurt" in scanned_text
        or "yogurt" in scanned_text
    ):
        return candidate_family != "general"

    return True


def get_off_alternative_category(product_data):
    category = normalize_search_text(product_data.get("category"))
    product_text = normalize_search_text(
        " ".join([
            str(product_data.get("name") or ""),
            str(product_data.get("brand") or ""),
            str(product_data.get("ingredients") or ""),
        ])
    )
    category_map = {
        "apa": "en:waters",
        "sucuri": "en:fruit-juices",
        "bauturi racoritoare": "en:soft-drinks",
        "bauturi energizante": "en:energy-drinks",
        "bauturi cu cafea": "en:iced-coffees",
        "bauturi": "en:beverages",
        "lactate": "en:dairies",
        "iaurturi cu fructe": "en:fruit-yogurts",
        "lactate si branzeturi": "en:cheeses",
        "deserturi lactate": "en:dairy-desserts",
        "snacks": "en:snacks",
        "snacks sarate": "en:salty-snacks",
        "dulciuri": "en:sweet-snacks",
        "cereale": "en:breakfast-cereals",
        "carne": "en:meats",
        "peste si fructe de mare": "en:seafood",
        "panificatie": "en:breads",
        "fructe si legume": "en:fruits-and-vegetables",
        "sosuri si condimente": "en:condiments",
        "uleiuri si condimente": "en:condiments",
        "paste orez si leguminoase": "en:pastas",
        "conserve si muraturi": "en:canned-foods",
        "taitei instant": "en:instant-noodles",
        "noodles": "en:instant-noodles",
        "ramen": "en:instant-noodles",
        "inghetata": "en:ice-creams",
        "pizza": "en:pizzas",
        "congelate": "en:frozen-foods",
        "mese gata preparate": "en:ready-meals",
        "alternative vegetale": "en:plant-based-foods-and-beverages",
        "proteine si fitness": "en:sports-nutrition",
        "creme si gemuri": "en:spreads",
        "creme tartinabile": "en:spreads",
        "nuci si seminte": "en:nuts",
    }

    if any(word in product_text for word in ["iaurt", "yogurt", "yoghurt", "skyr", "zuzu"]) and any(word in product_text for word in ["fruct", "fructe", "capsuni", "strawberry", "piersici", "visine", "afine", "zmeura", "padure"]):
        return "en:fruit-yogurts"

    if category in category_map:
        return category_map[category]

    if any(word in product_text for word in ["hell", "red bull", "redbull", "monster", "energiz", "energy", "taurina", "taurine"]):
        return "en:energy-drinks"

    if any(word in product_text for word in ["buldak", "samyang", "ramen", "noodle", "noodles", "taitei", "nongshim", "yakisoba", "udon"]):
        return "en:instant-noodles"

    if any(word in product_text for word in ["coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee", "cold brew", "frappe", "cafeina", "cofeina", "caffeine"]):
        return "en:iced-coffees"

    if any(word in product_text for word in ["danette", "budinca", "pudding", "custard", "desert lactat"]):
        return "en:dairy-desserts"

    if any(word in product_text for word in ["iaurt", "yogurt", "yoghurt", "skyr", "lapte", "milk"]):
        return "en:dairies"

    if any(word in product_text for word in ["inghetata", "ice cream", "gelatelli", "gelato"]):
        return "en:ice-creams"

    if any(word in product_text for word in ["apa", "water", "mineral"]) and not any(word in product_text for word in ["energy", "energiz", "coffee", "cafea", "cola", "pepsi"]):
        return "en:waters"

    if any(word in product_text for word in ["cola", "pepsi", "coca cola", "cocacola", "soda", "soft drink"]):
        return "en:soft-drinks"

    if any(word in product_text for word in ["suc", "juice", "nectar", "smoothie"]):
        return "en:fruit-juices"

    if any(word in product_text for word in ["sos", "mustar", "ketchup", "salsa"]):
        return "en:condiments"

    if any(word in product_text for word in ["chips", "crackers", "popcorn", "pufule", "salty snack"]):
        return "en:salty-snacks"

    if any(word in product_text for word in ["protein", "proteic", "proteina", "whey"]):
        return "en:sports-nutrition"

    if any(word in product_text for word in ["ciocolata", "napolitana", "biscuit", "dulce", "chocolate", "wafer"]):
        return "en:sweet-snacks"

    if any(word in product_text for word in ["cereal", "cereale", "muesli", "granola"]):
        return "en:breakfast-cereals"

    if any(word in product_text for word in ["pizza"]):
        return "en:pizzas"

    if any(word in product_text for word in ["frozen", "congelat", "congelata"]):
        return "en:frozen-foods"

    if any(word in product_text for word in ["ready meal", "sandwich", "supa", "soup", "salata"]):
        return "en:ready-meals"

    if any(word in product_text for word in ["plant based", "vegan", "lapte vegetal", "oat drink", "almond drink"]):
        return "en:plant-based-foods-and-beverages"

    if any(word in product_text for word in ["suc", "cola", "drink", "bautura"]):
        return "en:beverages"

    return None


def get_alternative_numeric_value(product, field):
    value = product.get(field)

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_alternative_normalized_score(products, product, field, prefer_higher):
    values = [
        get_alternative_numeric_value(item, field)
        for item in products
    ]
    values = [value for value in values if value is not None]
    value = get_alternative_numeric_value(product, field)

    if value is None or not values:
        return 0

    minimum = min(values)
    maximum = max(values)

    if minimum == maximum:
        return 1

    normalized = (value - minimum) / (maximum - minimum)
    return normalized if prefer_higher else 1 - normalized


def product_text_for_recommendation(product):
    return normalize_search_text(
        " ".join([
            str(product.get("name") or ""),
            str(product.get("brand") or ""),
            str(product.get("category") or ""),
            str(product.get("tag") or ""),
            str(product.get("reason") or ""),
            str(product.get("ingredients") or ""),
        ])
    )


def is_high_caffeine_candidate(product):
    product_family = get_product_recommendation_family(product)
    product_text = product_text_for_recommendation(product)

    if product_family in {"energy_drink", "coffee_drink", "caffeinated_beverage"}:
        return True

    return any(
        token in product_text
        for token in ["taurina", "taurine", "cafeina", "cofeina", "caffeine"]
    )


def is_caffeine_relevant_candidate(product):
    product_family = get_product_recommendation_family(product)

    if product_family in {"water", "cola", "instant_noodles", "lactate", "fruit_yogurt", "dairy_dessert"}:
        return False

    return product_family in {"energy_drink", "coffee_drink", "caffeinated_beverage"}


def score_off_alternative(products, product, criteria, scanned_product=None):
    score = float(product.get("score") or 0)
    reasons = []
    candidate_family = get_product_recommendation_family(product)
    candidate_text = product_text_for_recommendation(product)

    if scanned_product:
        scanned_family = get_product_recommendation_family(scanned_product)
        beverage_families = {
            "water",
            "cola",
            "beverage",
            "energy_drink",
            "coffee_drink",
            "caffeinated_beverage",
        }

        if candidate_family == scanned_family:
            family_bonus = 18 if scanned_family in {"instant_noodles", "fruit_yogurt"} else 8
            score += family_bonus
            reasons.append("aceeași categorie de produs")
        elif scanned_family == "instant_noodles":
            score -= 80
        elif scanned_family == "fruit_yogurt" and candidate_family not in {"fruit_yogurt", "lactate"}:
            score -= 60
        elif scanned_family not in beverage_families and candidate_family in beverage_families:
            score -= 70
        elif scanned_family in beverage_families and candidate_family not in beverage_families:
            score -= 45
        elif scanned_family in {
            "coffee_drink",
            "energy_drink",
            "caffeinated_beverage",
            "cola",
        } and candidate_family in {
            "coffee_drink",
            "energy_drink",
            "caffeinated_beverage",
            "cola",
        }:
            score += 6
            reasons.append("băutură similară cu cafeină")
        elif scanned_family == "dairy_dessert" and candidate_family in {"dairy_dessert", "lactate"}:
            score += 5
            reasons.append("alternativă lactată apropiată")

    if (
        "cheap" in criteria
        and product.get("price") is not None
        and product.get("priceIsLocal")
    ):
        value = get_alternative_normalized_score(products, product, "price", False)
        score += value * 10
        reasons.append("preț observat mai bun")

    if "protein" in criteria:
        value = get_alternative_normalized_score(products, product, "protein", True)
        score += value * 10
        reasons.append("mai multă proteină")

    if "low_sugar" in criteria:
        value = get_alternative_normalized_score(products, product, "sugar", False)
        score += value * 10
        reasons.append("mai puțin zahăr")

        if safe_float(product.get("sugar")) == 0:
            score += 2
            reasons.append("fără zahăr")

    if "caffeine" in criteria:
        if candidate_family == "energy_drink":
            score += 18
            reasons.append("băutură energizantă")
        elif candidate_family == "coffee_drink":
            score += 14
            reasons.append("băutură cu cafea")
        elif candidate_family == "caffeinated_beverage":
            score += 10
            reasons.append("conține cafeină")
        elif candidate_family == "cola":
            score -= 30
        elif candidate_family == "water":
            score -= 60

        if any(token in candidate_text for token in ["taurina", "taurine", "caffeine", "cafeina", "cofeina"]):
            score += 4
            reasons.append("ingrediente cu efect energizant")

    if "low_calorie" in criteria:
        value = get_alternative_normalized_score(products, product, "calories", False)
        score += value * 10
        reasons.append("mai puține calorii")

    if "value" in criteria:
        score += float(product.get("score") or 0) * 1.5
        reasons.append("scor nutrițional mai bun")

    product["recommendationScore"] = round(score, 2)
    product["recommendationReason"] = (
        "Potrivire calculată pentru " + ", ".join(reasons) + "."
        if reasons
        else "Alternativă ordonată după scorul nutrițional estimat."
    )
    return score


OFF_ALTERNATIVE_FIELDS = (
    "code,product_name,product_name_ro,product_name_en,"
    "generic_name,brands,quantity,categories,image_front_url,image_url,"
    "categories_tags,labels_tags,ingredients_analysis_tags,additives_n,"
    "nutrition_grades,nutriments,ingredients_text,ingredients_text_ro,"
    "ingredients_text_en"
)


def fetch_off_products(params, cache_key):
    cache_item = OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.get(cache_key)
    now = time.time()

    if cache_item and now - cache_item["created_at"] < OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL:
        return cache_item["products"]

    request_params = {
        "page_size": 40,
        "fields": OFF_ALTERNATIVE_FIELDS,
        **params,
    }

    response = requests.get(
        "https://world.openfoodfacts.org/api/v2/search",
        params=request_params,
        headers={
            "User-Agent": "CeAlegApp/1.0 (contact: contact@cealeg.shop)",
            "Accept": "application/json",
        },
        timeout=8,
    )
    response.raise_for_status()
    products = response.json().get("products", [])
    OPEN_FOOD_FACTS_ALTERNATIVES_CACHE[cache_key] = {
        "created_at": now,
        "products": products,
    }
    return products


def fetch_off_product_by_barcode(barcode):
    barcode = str(barcode or "").strip()

    if not barcode:
        return None

    cache_key = f"product:{barcode}"
    cache_item = OPEN_FOOD_FACTS_PRODUCT_CACHE.get(cache_key)
    now = time.time()

    if cache_item and now - cache_item["created_at"] < OPEN_FOOD_FACTS_PRODUCT_CACHE_TTL:
        return cache_item["product"]

    response = requests.get(
        f"https://world.openfoodfacts.org/api/v2/product/{barcode}",
        headers={
            "User-Agent": "CeAlegApp/1.0 (contact: contact@cealeg.shop)",
            "Accept": "application/json",
        },
        timeout=15,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    data = response.json()

    if data.get("status") != 1:
        product = None
    else:
        product = data.get("product") or {}
        product["code"] = str(data.get("code") or product.get("code") or barcode)

    OPEN_FOOD_FACTS_PRODUCT_CACHE[cache_key] = {
        "created_at": now,
        "product": product,
    }
    return product


def fetch_off_category_products(category_tag):
    return fetch_off_products(
        {"categories_tags": category_tag},
        f"category:{category_tag}",
    )


def get_off_search_terms(product_data):
    text = normalize_search_text(
        " ".join([
            str(product_data.get("name") or ""),
            str(product_data.get("brand") or ""),
            str(product_data.get("category") or ""),
        ])
    )
    ignored_words = {
        "produs",
        "altele",
        "vanilie",
        "ciocolata",
        "capsuni",
        "caramel",
        "cu",
        "si",
        "de",
    }
    words = [
        word
        for word in text.split()
        if len(word) >= 3 and word not in ignored_words and not word.isdigit()
    ]

    if any(word in text for word in ["danette", "budinca", "pudding", "custard"]):
        return "dairy dessert pudding"

    if any(word in text for word in ["buldak", "samyang", "ramen", "noodle", "noodles", "taitei", "nongshim", "yakisoba"]):
        if "buldak" in text or "samyang" in text:
            return "samyang buldak ramen instant noodles"
        return "ramen instant noodles"

    if any(word in text for word in ["iaurt", "yogurt", "yoghurt", "zuzu", "skyr"]) and any(
        word in text for word in ["fruct", "fructe", "capsuni", "strawberry", "piersici", "visine", "afine", "zmeura"]
    ):
        if "zuzu" in text:
            return "zuzu iaurt fructe"
        return "fruit yogurt"

    if any(word in text for word in ["inghetata", "gelatelli", "ice cream", "gelato"]):
        if "gelatelli" in text:
            return "gelatelli ice cream"
        return "ice cream"

    if any(word in text for word in ["hell", "red bull", "redbull", "monster", "energiz", "energy"]):
        return "zero sugar energy drink"

    if any(word in text for word in ["coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee", "frappe"]):
        return "zero sugar energy drink iced coffee"

    if words:
        return " ".join(words[:5])

    return ""


def fetch_off_search_products(product_data, category_tag=None):
    search_terms = get_off_search_terms(product_data)

    if not search_terms:
        return []

    params = {"search_terms": search_terms}

    if category_tag:
        params["categories_tags"] = category_tag

    return fetch_off_products(
        params,
        f"search:{category_tag or 'any'}:{search_terms}",
    )


def get_off_text_search_terms(query_text):
    text = normalize_search_text(query_text)

    if not text:
        return ""

    has_zero = any(word in text.split() for word in ["0", "zero"]) or "fara zahar" in text or "no sugar" in text
    has_red_bull = "redbull" in text or "red bull" in text or ("red" in text.split() and "bull" in text.split())

    if "inghetata" in text or "gelatelli" in text or "gelato" in text:
        flavor_terms = []

        if "alune" in text or "aluna" in text:
            flavor_terms.append("hazelnut")
        if "ciocolata" in text:
            flavor_terms.append("chocolate")
        if "vanilie" in text:
            flavor_terms.append("vanilla")
        if "capsuni" in text:
            flavor_terms.append("strawberry")

        brand_terms = "gelatelli " if "gelatelli" in text else ""
        return f"{brand_terms}{' '.join(flavor_terms)} ice cream".strip()

    if any(word in text for word in ["buldak", "samyang", "ramen", "noodle", "noodles", "taitei", "nongshim", "yakisoba"]):
        if "buldak" in text or "samyang" in text:
            return "samyang buldak ramen instant noodles"
        return "ramen instant noodles"

    if any(word in text for word in ["iaurt", "yogurt", "yoghurt", "zuzu", "skyr"]) and any(
        word in text for word in ["fruct", "fructe", "capsuni", "strawberry", "piersici", "visine", "afine", "zmeura"]
    ):
        if "zuzu" in text:
            return "zuzu iaurt fructe"
        return "fruit yogurt"

    if has_red_bull:
        return "red bull zero sugar" if has_zero else "red bull"

    if "monster" in text and has_zero:
        return "monster zero sugar"

    if any(word in text for word in ["hell", "energy", "energiz", "cafea", "coffee", "cappuccino", "capuccino", "latte"]):
        if has_zero:
            return f"{text} zero sugar energy drink"
        return f"{text} energy drink"

    ignored_words = {"produs", "altele", "pret", "lei", "aprox", "magazin", "lidl", "kaufland", "carrefour"}
    words = [
        word
        for word in text.split()
        if (len(word) >= 3 or word == "0") and word not in ignored_words
    ]

    return " ".join(words[:7])


def fetch_off_text_search_products(query_text):
    normalized_query = normalize_search_text(query_text)
    primary_terms = get_off_text_search_terms(query_text)
    query_brand = detect_query_brand(query_text)
    search_variants = []

    for terms in [primary_terms, normalized_query, query_brand]:
        terms = str(terms or "").strip()

        if terms and terms not in search_variants:
            search_variants.append(terms)

    if not search_variants:
        return []

    endpoints = [
        "https://ro.openfoodfacts.org/cgi/search.pl",
        "https://world.openfoodfacts.org/cgi/search.pl",
    ]
    merged_products = []
    seen_barcodes = set()
    last_error = None
    successful_request = False

    for endpoint in endpoints:
        for search_terms in search_variants:
            cache_key = f"legacy-text:{endpoint}:{search_terms}"
            cache_item = OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.get(cache_key)
            now = time.time()

            if (
                cache_item
                and now - cache_item["created_at"]
                < OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL
            ):
                products = cache_item["products"]
                successful_request = True
            else:
                products = None

                for attempt in range(2):
                    try:
                        response = requests.get(
                            endpoint,
                            params={
                                "search_terms": search_terms,
                                "search_simple": 1,
                                "action": "process",
                                "json": 1,
                                "page_size": 40,
                                "fields": OFF_ALTERNATIVE_FIELDS,
                            },
                            headers={
                                "User-Agent": (
                                    "CeAlegApp/1.0 "
                                    "(contact: contact@cealeg.shop)"
                                ),
                                "Accept": "application/json",
                            },
                            timeout=15,
                        )
                        response.raise_for_status()
                        products = response.json().get("products", [])
                        successful_request = True
                        OPEN_FOOD_FACTS_ALTERNATIVES_CACHE[cache_key] = {
                            "created_at": now,
                            "products": products,
                        }
                        break
                    except requests.RequestException as error:
                        last_error = error

                        if attempt == 0:
                            time.sleep(0.35)

                if products is None:
                    app.logger.warning(
                        "Open Food Facts search failed for %s on %s: %s",
                        search_terms,
                        endpoint,
                        last_error,
                    )
                    continue

            for product in products:
                barcode = str(
                    product.get("code") or product.get("_id") or ""
                ).strip()

                if not barcode or barcode in seen_barcodes:
                    continue

                seen_barcodes.add(barcode)
                merged_products.append(product)

        if merged_products:
            break

    if not successful_request and last_error:
        raise last_error

    return merged_products


KNOWN_CATALOG_SEEDS = [
    {
        "barcode": "known-gelatelli-hazelnut-ice-cream",
        "name": "Gelatelli înghețată cu alune",
        "brand": "Gelatelli",
        "store": "Lidl",
        "category": "Înghețată",
        "quantity": "",
        "calories": None,
        "protein": None,
        "sugar": None,
        "fat": None,
        "ingredients": "",
        "score": None,
        "limitedData": True,
    },
    {
        "barcode": "known-red-bull-sugarfree-250ml",
        "name": "Red Bull Sugarfree",
        "brand": "Red Bull",
        "category": "Băuturi energizante",
        "quantity": "250 ml",
        "calories": 3,
        "protein": 0,
        "sugar": 0,
        "fat": 0,
        "ingredients": "apă carbogazoasă, cafeină, taurină, vitamine B, îndulcitori.",
        "score": 8.4,
    },
    {
        "barcode": "known-red-bull-zero-250ml",
        "name": "Red Bull Zero",
        "brand": "Red Bull",
        "category": "Băuturi energizante",
        "quantity": "250 ml",
        "calories": 3,
        "protein": 0,
        "sugar": 0,
        "fat": 0,
        "ingredients": "apă carbogazoasă, cafeină, taurină, vitamine B, îndulcitori.",
        "score": 8.5,
    },
    {
        "barcode": "known-red-bull-energy-250ml",
        "name": "Red Bull Energy Drink",
        "brand": "Red Bull",
        "category": "Băuturi energizante",
        "quantity": "250 ml",
        "calories": 46,
        "protein": 0,
        "sugar": 11,
        "fat": 0,
        "ingredients": "apă carbogazoasă, zahăr, cafeină, taurină, vitamine B.",
        "score": 6.4,
    },
    {
        "barcode": "known-hell-zero-sugar-250ml",
        "name": "HELL Zero Sugar",
        "brand": "HELL",
        "category": "Băuturi energizante",
        "quantity": "250 ml",
        "calories": 3,
        "protein": 0,
        "sugar": 0,
        "fat": 0,
        "ingredients": "apă carbogazoasă, cafeină, taurină, vitamine B, îndulcitori.",
        "score": 8.2,
    },
    {
        "barcode": "known-hell-ice-coffee-cappuccino-250ml",
        "name": "HELL Ice Coffee Cappuccino",
        "brand": "HELL",
        "category": "Băuturi cu cafea",
        "quantity": "250 ml",
        "calories": 50,
        "protein": 2.6,
        "sugar": 7.6,
        "fat": 0.8,
        "ingredients": "lapte, cafea, zahăr, aromă de cappuccino, stabilizatori.",
        "score": 8.1,
    },
    {
        "barcode": "known-monster-ultra-white-500ml",
        "name": "Monster Energy Ultra White",
        "brand": "Monster",
        "category": "Băuturi energizante",
        "quantity": "500 ml",
        "calories": 2,
        "protein": 0,
        "sugar": 0,
        "fat": 0,
        "ingredients": "apă carbogazoasă, cafeină, taurină, vitamine B, îndulcitori.",
        "score": 8.7,
    },
    {
        "barcode": "known-pepsi-max-330ml",
        "name": "Pepsi Max",
        "brand": "Pepsi",
        "category": "Băuturi răcoritoare",
        "quantity": "330 ml",
        "calories": 1,
        "protein": 0,
        "sugar": 0,
        "fat": 0,
        "ingredients": "apă carbogazoasă, colorant caramel, cafeină, îndulcitori.",
        "score": 8.1,
    },
]


def build_known_catalog_product(seed, query_text, store_name=None):
    has_nutrition_data = any(
        seed.get(field) is not None
        for field in ("calories", "protein", "sugar", "fat")
    )
    product_data = {
        "id": seed["barcode"],
        "barcode": seed["barcode"],
        "name": seed["name"],
        "brand": seed["brand"],
        "store": seed.get("store") or "Catalog verificat",
        "category": seed["category"],
        "quantity": seed["quantity"],
        "score": seed["score"],
        "tag": "Date limitate" if seed.get("limitedData") else "Sugestie verificată",
        "image": "",
        "price": None,
        "priceText": "Verifică prețul în magazin",
        "calories": seed["calories"],
        "protein": seed["protein"],
        "sugar": seed["sugar"],
        "fat": seed["fat"],
        "vegan": False,
        "lactoseFree": True,
        "natural": False,
        "source": "curated_catalog",
        "ingredients": seed["ingredients"],
        "limitedData": bool(seed.get("limitedData")),
    }

    if has_nutrition_data:
        product_data["reason"] = generate_product_reason(
            product_data["category"],
            product_data["calories"],
            product_data["protein"],
            product_data["sugar"],
            product_data["fat"],
            product_data["ingredients"],
        )
    else:
        product_data["reason"] = (
            "Produs identificat după nume și marcă. Datele nutriționale trebuie "
            "confirmate de pe etichetă sau prin codul de bare."
        )
    product_data["matchScore"] = product_match_score(product_data, query_text)

    if store_name and store_name != "Fără magazin ales":
        product_data["requestedStore"] = store_name

    return product_data


def get_known_catalog_suggestions(query_text, store_name=None):
    candidates = []

    for seed in KNOWN_CATALOG_SEEDS:
        product_data = build_known_catalog_product(seed, query_text, store_name)
        score = product_data.get("matchScore") or 0

        if score >= 34:
            candidates.append((score, product_data))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [product for _, product in candidates]


def is_same_catalog_product(scanned_product, candidate):
    scanned_barcode = str(scanned_product.get("barcode") or "").strip()
    candidate_barcode = str(candidate.get("barcode") or "").strip()

    if scanned_barcode and candidate_barcode and scanned_barcode == candidate_barcode:
        return True

    scanned_name = normalize_product_name_for_duplicate(scanned_product.get("name"))
    candidate_name = normalize_product_name_for_duplicate(candidate.get("name"))

    if not scanned_name or not candidate_name:
        return False

    if scanned_name == candidate_name:
        return True

    scanned_family = get_product_recommendation_family(scanned_product)
    candidate_family = get_product_recommendation_family(candidate)
    scanned_brand = normalize_search_text(scanned_product.get("brand") or "")
    candidate_brand = normalize_search_text(candidate.get("brand") or "")
    name_similarity = SequenceMatcher(None, scanned_name, candidate_name).ratio()

    if scanned_family == candidate_family and scanned_family != "general":
        if scanned_brand and candidate_brand and scanned_brand != candidate_brand and name_similarity < 0.92:
            return False

        return name_similarity >= 0.82

    return name_similarity >= 0.88


def get_alternative_identity_key(product_data):
    barcode = str(product_data.get("barcode") or "").strip()

    if barcode and re.fullmatch(r"\d{8,14}", barcode):
        return f"barcode:{barcode}"

    name = normalize_product_name_for_duplicate(product_data.get("name"))
    brand = normalize_search_text(product_data.get("brand") or "")
    quantity = normalize_search_text(product_data.get("quantity") or "")

    if not name:
        return ""

    return f"name:{brand}:{name}:{quantity}"


def dedupe_alternatives_by_identity(alternatives):
    deduped = []
    seen_keys = set()

    for candidate in alternatives:
        identity_key = get_alternative_identity_key(candidate)

        if identity_key and identity_key in seen_keys:
            continue

        if any(is_same_catalog_product(existing, candidate) for existing in deduped):
            continue

        deduped.append(candidate)

        if identity_key:
            seen_keys.add(identity_key)

    return deduped


def get_known_catalog_alternatives(scanned_product, criteria):
    alternatives = []
    scanned_family = get_product_recommendation_family(scanned_product)

    if scanned_family not in {
        "coffee_drink",
        "energy_drink",
        "caffeinated_beverage",
        "cola",
        "beverage",
    } and "caffeine" not in criteria:
        return alternatives

    for seed in KNOWN_CATALOG_SEEDS:
        product_data = build_known_catalog_product(seed, seed["name"])

        if is_same_catalog_product(scanned_product, product_data):
            continue

        if not is_compatible_alternative(scanned_product, product_data):
            continue

        if "caffeine" in criteria and not is_caffeine_relevant_candidate(product_data):
            continue

        alternatives.append(product_data)

    return alternatives


def get_local_catalog_alternatives(scanned_product, criteria):
    scanned_family = get_product_recommendation_family(scanned_product)
    category = str(scanned_product.get("category") or "").strip()
    category_family = get_product_recommendation_family({"category": category})
    query = Product.query
    used_category_filter = False

    if scanned_family == "general":
        return []

    if (
        category
        and normalize_search_text(category) not in {"altele", "other"}
        and category_family == scanned_family
    ):
        query = query.filter(Product.category == category)
        used_category_filter = True

    if not used_category_filter:
        family_keywords = {
            "energy_drink": ["energy", "energiz", "red bull", "redbull", "monster", "hell"],
            "coffee_drink": ["coffee", "cafea", "cappuccino", "latte", "espresso"],
            "caffeinated_beverage": ["caffeine", "cafeina", "taurina"],
            "instant_noodles": ["buldak", "samyang", "ramen", "noodle", "taitei"],
            "fruit_yogurt": ["iaurt", "yogurt", "zuzu", "fruct"],
            "lactate": ["iaurt", "yogurt", "lapte", "dairy"],
            "dairy_dessert": ["danette", "budinca", "pudding", "desert"],
            "ice_cream": ["inghetata", "ice cream", "gelato", "gelatelli"],
            "sauce": ["sos", "mustar", "ketchup", "salsa"],
            "salty_snack": ["chips", "crisps", "snack", "pufule"],
            "sweet_snack": ["ciocolata", "chocolate", "biscuit", "wafer"],
            "cereal": ["cereale", "cereal", "granola", "muesli"],
            "water": ["apa", "water", "mineral"],
            "cola": ["cola", "pepsi", "coca"],
            "meat": ["muschi", "file", "filet", "sunca", "ham", "salam", "carne", "porc", "pui", "curcan", "prosciutto"],
            "fish": ["peste", "fish", "ton", "tuna", "somon", "salmon"],
            "spread": ["spread", "crema", "tartinabila", "nutella", "unt arahide", "peanut butter", "gem"],
            "nuts": ["nuci", "alune", "nuts", "seeds", "seminte"],
            "bread": ["paine", "bread", "toast", "bagheta", "chifla"],
            "ready_meal": ["ready meal", "sandwich", "salata", "supa"],
            "frozen": ["frozen", "congelat", "congelata"],
            "pizza": ["pizza"],
        }.get(scanned_family, [])

        if family_keywords:
            query = query.filter(or_(*[
                or_(
                    Product.name.ilike(f"%{keyword}%"),
                    Product.category.ilike(f"%{keyword}%"),
                    Product.ingredients.ilike(f"%{keyword}%"),
                )
                for keyword in family_keywords
            ]))

    products = query.order_by(Product.score.desc()).limit(180).all()
    alternatives = []
    seen_keys = set()

    for product in products:
        product_data = product_to_dict(product)
        candidate_family = get_product_recommendation_family(product_data)

        if is_same_catalog_product(scanned_product, product_data):
            continue

        if candidate_family != scanned_family and scanned_family not in {
            "beverage",
            "caffeinated_beverage",
            "lactate",
        }:
            continue

        if not is_compatible_alternative(scanned_product, product_data):
            continue

        if "caffeine" in criteria and not is_caffeine_relevant_candidate(product_data):
            continue

        key = normalize_search_text(
            f"{product_data.get('barcode') or ''} {product_data.get('name') or ''}"
        )

        if key in seen_keys:
            continue

        alternatives.append(product_data)
        seen_keys.add(key)

    return alternatives[:40]


def build_off_search_result(off_product, query_text, store_name=None):
    barcode = str(off_product.get("code") or off_product.get("_id") or "").strip()

    if not barcode:
        barcode = f"off-{abs(hash(json.dumps(off_product, sort_keys=True, default=str)))}"

    product_data = build_product_from_open_food_facts(
        barcode,
        off_product,
        translate_ingredients=False,
    )
    product_data["source"] = "openfoodfacts"
    product_data["store"] = "Open Food Facts"
    product_data["matchScore"] = product_match_score(product_data, query_text)

    if store_name and store_name != "Fără magazin ales":
        product_data["requestedStore"] = store_name

    return product_data


def find_best_off_product_match(query_text, store_name=None):
    candidates = []
    off_products = fetch_off_text_search_products(query_text)

    for off_product in off_products:
        product_data = build_off_search_result(off_product, query_text, store_name)
        score = product_data.get("matchScore") or 0

        if score >= 34:
            candidates.append((score, product_data))

    candidates.sort(key=lambda item: item[0], reverse=True)

    if not candidates:
        return None, 0

    return candidates[0][1], candidates[0][0]


def fetch_off_seed_products(product_data, category_tag=None):
    scanned_barcode = str(product_data.get("barcode") or "").strip()
    product_text = normalize_search_text(
        " ".join([
            str(product_data.get("name") or ""),
            str(product_data.get("brand") or ""),
            str(product_data.get("category") or ""),
            str(product_data.get("ingredients") or ""),
        ])
    )
    barcodes = []

    if category_tag:
        barcodes.extend(OFF_FALLBACK_BARCODES_BY_CATEGORY.get(category_tag, []))

    if any(word in product_text for word in ["hell", "red bull", "redbull", "monster", "energiz", "energy", "coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee", "frappe", "cafeina", "cofeina", "caffeine"]):
        barcodes.extend(OFF_FALLBACK_BARCODES_BY_CATEGORY["en:iced-coffees"])
        barcodes.extend(OFF_FALLBACK_BARCODES_BY_CATEGORY["en:energy-drinks"])

    if any(word in product_text for word in ["danette", "budinca", "pudding", "custard", "desert lactat"]):
        barcodes.extend(OFF_FALLBACK_BARCODES_BY_CATEGORY["en:dairy-desserts"])

    unique_barcodes = []
    seen_barcodes = {scanned_barcode}

    for barcode in barcodes:
        if barcode and barcode not in seen_barcodes:
            unique_barcodes.append(barcode)
            seen_barcodes.add(barcode)

    products = []

    for barcode in unique_barcodes[:10]:
        try:
            product = fetch_off_product_by_barcode(barcode)
        except requests.RequestException as error:
            app.logger.warning(
                "Open Food Facts fallback product failed for %s: %s",
                barcode,
                error,
            )
            continue

        if product:
            products.append(product)

    return products


def save_product_to_local_database(product_data):
    existing_product = Product.query.filter_by(
        barcode=product_data["barcode"]
    ).first()

    if existing_product:
        return existing_product

    product = Product(
        name=product_data["name"],
        store=product_data["store"],
        category=product_data["category"],
        barcode=product_data["barcode"],
        score=product_data["score"] if product_data["score"] is not None else 5.0,
        tag=product_data["tag"],
        image=product_data["image"],
        price=product_data["price"],
        price_text=product_data["priceText"],
        calories=product_data["calories"],
        protein=product_data["protein"],
        sugar=product_data["sugar"],
        fat=product_data["fat"],
        vegan=product_data["vegan"],
        lactose_free=product_data["lactoseFree"],
        natural=product_data["natural"],
        reason=product_data["reason"],
        ingredients=product_data["ingredients"],
    )

    db.session.add(product)
    db.session.commit()
    return product


@app.route("/barcode/import", methods=["POST"])
def import_barcode_product():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    barcode = str(data.get("barcode") or "").strip()
    name = str(data.get("name") or "").strip()

    category = str(data.get("category") or "Altele").strip() or "Altele"
    ingredients = str(data.get("ingredients") or "").strip()
    calories = parse_optional_float(data.get("calories"))
    protein = parse_optional_float(data.get("protein"))
    sugar = parse_optional_float(data.get("sugar"))
    fat = parse_optional_float(data.get("fat"))
    price = parse_optional_float(data.get("price"))

    validation_errors = [
        validate_barcode(barcode, required=True),
        validate_text_length(name, "Numele produsului", 150, 2),
        validate_text_length(category, "Categoria", 100, 2),
        validate_text_length(ingredients, "Ingredientele", 5000),
        validate_nutrition_values(calories, protein, sugar, fat),
    ]

    if data.get("price") not in (None, "") and price is None:
        validation_errors.append("Prețul trebuie să fie un număr valid.")

    validation_errors = [error for error in validation_errors if error]

    if validation_errors:
        return jsonify({
            "error": validation_errors[0],
            "errors": validation_errors,
        }), 400

    existing_product = Product.query.filter_by(barcode=barcode).first()

    if existing_product:
        return jsonify({
            "message": "Produsul există deja în baza locală.",
            "product": product_to_dict(existing_product),
        })

    score = calculate_product_score(
        category, calories, protein, sugar, fat, ingredients
    )
    tag = generate_product_tag(
        category, calories, protein, sugar, fat, ingredients
    )
    reason = generate_product_reason(
        category, calories, protein, sugar, fat, ingredients
    )

    product = Product(
        name=name,
        store=str(data.get("store") or "Open Food Facts").strip(),
        category=category,
        barcode=barcode,
        score=score,
        tag=tag,
        image=data.get("image"),
        price=price,
        price_text=str(data.get("priceText") or "preț necunoscut").strip(),
        calories=calories,
        protein=protein,
        sugar=sugar,
        fat=fat,
        vegan=bool(data.get("vegan", False)),
        lactose_free=bool(data.get("lactoseFree", False)),
        natural=bool(data.get("natural", False)),
        reason=reason,
        ingredients=ingredients,
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "message": "Produs salvat în baza locală.",
        "product": product_to_dict(product),
    }), 201


@app.route("/ai/identify-product-frame", methods=["POST"])
def identify_product_frame():
    subscription = get_or_create_subscription(g.current_user)

    if not is_paid_subscription(subscription):
        return jsonify({
            "error": "Asistentul live este disponibil in planurile Pro si Family.",
            "code": "paid_plan_required",
            "plan": subscription.plan,
            "requiredPlans": ["pro", "family"],
        }), 402

    vision_enabled = os.environ.get("ENABLE_OPENAI_VISION", "false").lower() == "true"
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not vision_enabled or not api_key:
        return jsonify({
            "error": "Identificarea vizuală nu este configurată încă.",
            "code": "vision_not_configured",
        }), 503

    frame = request.files.get("frame")

    if not frame:
        return jsonify({"error": "Cadrul video lipsește."}), 400

    frame_bytes = frame.read()

    if not frame_bytes:
        return jsonify({"error": "Cadrul video este gol."}), 400

    if len(frame_bytes) > 2 * 1024 * 1024:
        return jsonify({"error": "Cadrul video este prea mare."}), 400

    mime_type = frame.mimetype or "image/jpeg"

    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        return jsonify({"error": "Formatul cadrului video nu este acceptat."}), 400

    image_base64 = base64.b64encode(frame_bytes).decode("ascii")
    model = os.environ.get("OPENAI_VISION_MODEL", "gpt-4.1-mini").strip()

    prompt = """
Analizează cadrul camerei dintr-un supermarket.
Identifică produsul principal ținut aproape de cameră.
Nu inventa date. Dacă numele sau codul de bare nu sunt lizibile, folosește null.
Returnează exclusiv JSON valid cu forma:
{
  "identified": true sau false,
  "product_name": string sau null,
  "brand": string sau null,
  "variant": string sau null,
  "barcode": string numeric sau null,
  "confidence": număr întreg între 0 și 100,
  "needs_barcode": true sau false,
  "message": string scurt în limba română
}
Setează identified=false dacă produsul nu poate fi identificat rezonabil.
"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": [{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "low",
                        },
                    ],
                }],
            },
            timeout=30,
        )

        if response.status_code >= 400:
            app.logger.warning(
                "OpenAI vision returned status %s: %s",
                response.status_code,
                response.text[:500],
            )
            return jsonify({
                "error": "Serviciul vision nu a putut analiza cadrul.",
            }), 502

        vision_result = parse_json_object(
            extract_openai_output_text(response.json())
        )
    except (json.JSONDecodeError, ValueError):
        return jsonify({
            "error": "Serviciul vision a returnat un răspuns invalid."
        }), 502
    except requests.RequestException as error:
        app.logger.warning("OpenAI vision request failed: %s", error)
        return jsonify({
            "error": "Serviciul vision nu este disponibil momentan.",
            "code": "vision_unavailable",
        }), 503

    if not vision_result.get("identified"):
        return jsonify({
            "identified": False,
            "message": vision_result.get("message")
            or "Nu am identificat sigur produsul. Întoarce ambalajul spre codul de bare.",
        })

    product_name = str(vision_result.get("product_name") or "").strip()
    barcode = str(vision_result.get("barcode") or "").strip()
    local_product = None
    match_score = 0

    if barcode and not validate_barcode(barcode):
        local_product = Product.query.filter_by(barcode=barcode).first()

    if not local_product and product_name:
        local_product, match_score = find_best_product_match(product_name)

    try:
        confidence = int(vision_result.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0

    if not local_product:
        return jsonify({
            "identified": False,
            "chargeable": False,
            "message": (
                "Nu am confirmat sigur produsul. Arată codul de bare ca să evităm un rezultat greșit."
            ),
            "candidate": {
                "name": product_name or None,
                "brand": vision_result.get("brand"),
                "variant": vision_result.get("variant"),
                "barcode": barcode or None,
                "confidence": confidence,
                "needs_barcode": True,
                "message": vision_result.get("message")
                or "Confirmă produsul prin codul de bare.",
                "local_match_score": match_score,
            },
        })

    scan_gate = consume_scan_usage(
        g.current_user,
        "live_vision",
        {
            "endpoint": "ai_identify_product_frame",
            "product_name": product_name,
            "barcode": barcode,
            "local_match_score": match_score,
        },
    )

    if not scan_gate["allowed"]:
        return respond_scan_limit(scan_gate)

    return jsonify({
        "identified": True,
        "source": "local" if local_product else "vision",
        "product": product_to_dict(local_product) if local_product else None,
        "candidate": {
            "name": product_name or None,
            "brand": vision_result.get("brand"),
            "variant": vision_result.get("variant"),
            "barcode": barcode or None,
            "confidence": confidence,
            "needs_barcode": vision_result.get("needs_barcode", not barcode),
            "message": vision_result.get("message")
            or "Produs identificat vizual. Confirmă ambalajul sau arată codul de bare.",
            "local_match_score": match_score,
        },
    })


@app.route("/barcode/lookup/<barcode>", methods=["GET"])
def lookup_barcode(barcode):
    barcode = barcode.strip()

    barcode_error = validate_barcode(barcode, required=True)

    if barcode_error:
        return jsonify({"error": barcode_error}), 400

    scan_gate = check_scan_usage_allowed(g.current_user)

    if not scan_gate["allowed"]:
        return respond_scan_limit(scan_gate)

    barcode_candidates = get_barcode_lookup_candidates(barcode)
    matched_barcode = barcode
    local_product = None

    for candidate_barcode in barcode_candidates:
        local_product = Product.query.filter_by(barcode=candidate_barcode).first()

        if local_product:
            matched_barcode = candidate_barcode
            break

    if local_product:
        scan_gate = consume_scan_usage(
            g.current_user,
            "barcode",
            {"barcode": matched_barcode, "source": "local"},
        )

        if not scan_gate["allowed"]:
            return respond_scan_limit(scan_gate)

        return jsonify({
            "found": True,
            "source": "local",
            "matchedBarcode": matched_barcode,
            "product": product_to_dict_with_open_price(local_product),
            "usage": scan_gate["usage"],
        })

    off_product = None
    last_lookup_error = None

    for candidate_barcode in barcode_candidates:
        try:
            candidate_product = fetch_off_product_by_barcode(candidate_barcode)
        except requests.RequestException as error:
            last_lookup_error = error
            app.logger.warning(
                "Open Food Facts barcode lookup failed for %s: %s",
                candidate_barcode,
                error,
            )
            continue
        except Exception as error:
            last_lookup_error = error
            app.logger.warning(
                "Open Food Facts barcode lookup failed for %s: %s",
                candidate_barcode,
                error,
            )
            continue

        if candidate_product:
            off_product = candidate_product
            matched_barcode = candidate_barcode
            break

    if not off_product and last_lookup_error:
        return jsonify({
            "found": False,
            "source": "openfoodfacts",
            "code": "openfoodfacts_unavailable",
            "message": "Open Food Facts nu este disponibil momentan. Poți încerca din nou sau contribui produsul manual.",
        }), 503

    if not off_product:
        record_search_event(
            barcode,
            result_count=0,
            source="barcode_not_found",
            user_id=getattr(g.current_user, "id", None),
        )
        db.session.commit()
        return jsonify({
            "found": False,
            "source": "openfoodfacts",
            "code": "external_product_not_found",
            "message": "Produsul nu a fost găsit după codul de bare.",
            "barcode": barcode,
            "barcodeCandidates": barcode_candidates,
        }), 404

    product_data = build_product_from_open_food_facts(matched_barcode, off_product)
    price_summary = None

    for candidate_barcode in list(dict.fromkeys([matched_barcode, *barcode_candidates])):
        price_summary = get_open_prices_summary(candidate_barcode)

        if price_summary:
            break

    if price_summary:
        product_data.update(price_summary)

    local_product = save_product_to_local_database(product_data)
    scan_gate = consume_scan_usage(
        g.current_user,
        "barcode",
        {"barcode": matched_barcode, "source": "openfoodfacts"},
    )

    if not scan_gate["allowed"]:
        return respond_scan_limit(scan_gate)

    return jsonify({
        "found": True,
        "source": "openfoodfacts",
        "cached": True,
        "matchedBarcode": matched_barcode,
        "product": product_to_dict_with_open_price(local_product),
        "usage": scan_gate["usage"],
    })                                    

with app.app_context():
    db.create_all()
    ensure_database_columns()
    ensure_database_indexes()
    ensure_invite_codes_for_existing_users()
    ensure_configured_admin()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        port=int(os.environ.get("PORT", "5001")),
    )


