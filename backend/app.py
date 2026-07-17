from flask import Flask, request, jsonify, send_from_directory, g
from flask import Response, has_request_context
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
from PIL import Image, ImageOps
from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import csv
import hashlib
import hmac
import json
import logging
import math
import os
import time
import re
import unicodedata
import requests
import smtplib
import threading
from io import BytesIO, StringIO
from uuid import uuid4
from difflib import SequenceMatcher
from email.message import EmailMessage
from html import escape
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
from functools import wraps
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

try:
    import stripe
except ImportError:
    stripe = None

try:
    from redis import Redis
except ImportError:
    Redis = None

try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except ImportError:
    sentry_sdk = None
    FlaskIntegration = None

from database import db
from app_factory import create_app
from ai_provider import get_vision_provider, VisionProviderError, VisionProviderNotConfigured
from api_docs import build_openapi_spec, render_swagger_ui
from catalog_quality import build_catalog_quality_report
from config import DEFAULT_AUTH_SECRET, RuntimeConfig, read_secret_env
from time_utils import utcnow
from routes import register_blueprints, route
from validation import validate_payload
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
    StripeWebhookEvent,
    ConsentRecord,
    ConsentLog,
)


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Load the local file before reading any configuration. Hosted environments keep
# precedence because override=False is the default.
load_dotenv(os.path.join(BACKEND_DIR, ".env"))


OPEN_FOOD_FACTS_ALTERNATIVES_CACHE = {}
OPEN_FOOD_FACTS_PRODUCT_CACHE = {}
OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL = 10 * 60
OPEN_FOOD_FACTS_PRODUCT_CACHE_TTL = 60 * 60
OPEN_FOOD_FACTS_CACHE_MAX_ITEMS = int(os.environ.get("OPEN_FOOD_FACTS_CACHE_MAX_ITEMS", "900"))
PRODUCT_SEARCH_RESULT_CACHE = {}
PRODUCT_SEARCH_RESULT_CACHE_TTL = int(os.environ.get("PRODUCT_SEARCH_RESULT_CACHE_TTL", "900"))
PRODUCT_SEARCH_RESULT_CACHE_MAX_ITEMS = int(os.environ.get("PRODUCT_SEARCH_RESULT_CACHE_MAX_ITEMS", "400"))
OPEN_PRICES_CACHE = {}
OPEN_PRICES_CACHE_TTL = 30 * 60
OPEN_PRICES_CACHE_MAX_ITEMS = int(os.environ.get("OPEN_PRICES_CACHE_MAX_ITEMS", "800"))
AI_STATUS_CACHE = {"created_at": 0, "data": None}
AI_STATUS_CACHE_TTL = 30
LEADERBOARD_CACHE = {}
LEADERBOARD_CACHE_TTL = int(os.environ.get("LEADERBOARD_CACHE_TTL", "60"))
PUBLIC_CATALOG_STATS_CACHE = {"expires_at": 0, "data": None}
PUBLIC_CATALOG_STATS_CACHE_TTL = int(os.environ.get("PUBLIC_CATALOG_STATS_CACHE_TTL", "300"))
RECOMMENDATION_FAMILY_CACHE = {}
PRODUCT_RECOMMENDATION_TEXT_CACHE = {}
RECOMMENDATION_DERIVED_CACHE_MAX_ITEMS = int(os.environ.get("RECOMMENDATION_DERIVED_CACHE_MAX_ITEMS", "6000"))
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
RATE_LIMIT_BUCKETS_LOCK = threading.RLock()
REDIS_CLIENT = None
REDIS_RETRY_AFTER = 0
CACHE_METRICS = {"hits": 0, "misses": 0, "writes": 0, "errors": 0}
RUNTIME_CONFIG = RuntimeConfig.from_env()
APP_ENV = RUNTIME_CONFIG.app_env
PRODUCTION_MODE = RUNTIME_CONFIG.production_mode
EXTERNAL_CATALOG_ENABLED = os.environ.get(
    "EXTERNAL_CATALOG_ENABLED", "true"
).strip().lower() in {"1", "true", "yes", "on"}
OPEN_PRICES_ENABLED = os.environ.get(
    "OPEN_PRICES_ENABLED", "true"
).strip().lower() in {"1", "true", "yes", "on"}
GLOBAL_RATE_LIMIT = int(os.environ.get("GLOBAL_RATE_LIMIT", "300"))
GLOBAL_RATE_LIMIT_WINDOW = int(os.environ.get("GLOBAL_RATE_LIMIT_WINDOW", "60"))
AUTH_RATE_LIMIT = int(os.environ.get("AUTH_RATE_LIMIT", "5"))
AUTH_RATE_LIMIT_WINDOW = int(os.environ.get("AUTH_RATE_LIMIT_WINDOW", str(15 * 60)))
MAX_JSON_BODY_BYTES = int(os.environ.get("MAX_JSON_BODY_BYTES", str(200 * 1024)))


def get_application_version():
    commit = (
        os.environ.get("RENDER_GIT_COMMIT")
        or os.environ.get("VERCEL_GIT_COMMIT_SHA")
        or os.environ.get("GIT_COMMIT")
        or os.environ.get("SOURCE_VERSION")
        or os.environ.get("COMMIT_SHA")
        or "local"
    )
    commit = str(commit).strip() or "local"

    return {
        "service": "ce-aleg-api",
        "environment": APP_ENV,
        "commit": commit,
        "shortCommit": commit[:7] if commit != "local" else "local",
        "buildTime": os.environ.get("BUILD_TIME") or os.environ.get("RENDER_DEPLOY_CREATED_AT") or None,
    }


def set_limited_cache_item(cache, key, value, max_items):
    if key not in cache and len(cache) >= max(1, int(max_items or 1)):
        cache.pop(next(iter(cache)), None)

    cache[key] = value


def get_product_family_cache_key(product_data):
    if not isinstance(product_data, dict):
        product_data = {}

    off_categories = product_data.get("offCategories") or []

    if isinstance(off_categories, str):
        off_categories = (off_categories,)
    elif isinstance(off_categories, (list, tuple, set)):
        off_categories = tuple(str(item or "") for item in off_categories)
    else:
        off_categories = (str(off_categories or ""),)

    return (
        str(product_data.get("name") or ""),
        str(product_data.get("brand") or ""),
        str(product_data.get("category") or ""),
        str(product_data.get("store") or ""),
        str(product_data.get("tag") or ""),
        str(product_data.get("ingredients") or ""),
        off_categories,
    )


def get_product_text_cache_key(product_data):
    if not isinstance(product_data, dict):
        product_data = {}

    return (
        str(product_data.get("name") or ""),
        str(product_data.get("brand") or ""),
        str(product_data.get("category") or ""),
        str(product_data.get("tag") or ""),
        str(product_data.get("reason") or ""),
        str(product_data.get("ingredients") or ""),
    )

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
    "en:beers": [
        "5941314000087",
        "5941300000138",
        "5941314000018",
        "5941284000072",
        "5941284000096",
    ],
    "en:alcoholic-beverages": [
        "5941314000087",
        "5941300000138",
        "5941314000018",
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


app = create_app(__name__, RUNTIME_CONFIG, app_class=Flask)

SENTRY_DSN = read_secret_env("SENTRY_DSN")


def sanitize_sentry_event(event, _hint):
    request_data = event.get("request")

    if isinstance(request_data, dict):
        request_data.pop("data", None)
        request_data.pop("cookies", None)
        request_data["query_string"] = ""
        headers = request_data.get("headers")

        if isinstance(headers, dict):
            for header_name in list(headers):
                if header_name.lower() in {
                    "authorization",
                    "cookie",
                    "set-cookie",
                    "x-api-key",
                }:
                    headers.pop(header_name, None)

    user_data = event.get("user")
    if isinstance(user_data, dict):
        event["user"] = {"id": user_data.get("id")} if user_data.get("id") else {}

    return event

if SENTRY_DSN and sentry_sdk is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        environment=APP_ENV,
        release=get_application_version()["commit"],
        traces_sample_rate=max(
            0.0,
            min(1.0, float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05"))),
        ),
        send_default_pii=False,
        max_request_body_size="never",
        before_send=sanitize_sentry_event,
    )


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if has_request_context():
            payload.update({
                "requestId": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
            })

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


app.logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

if os.environ.get("LOG_FORMAT", "json" if PRODUCTION_MODE else "text").lower() == "json":
    formatter = JsonLogFormatter()
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)


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
CORS(app, resources={r"/*": {"origins": frontend_origins}}, supports_credentials=True)

database_url = RUNTIME_CONFIG.database_url
Image.MAX_IMAGE_PIXELS = RUNTIME_CONFIG.max_image_pixels

db.init_app(app)

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SUBMISSIONS_FOLDER = os.path.join(UPLOAD_FOLDER, "submissions")
os.makedirs(SUBMISSIONS_FOLDER, exist_ok=True)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_ENABLED = os.environ.get("SUPABASE_STORAGE_ENABLED", "true").lower() == "true"
SUPABASE_PRODUCT_IMAGES_BUCKET = os.environ.get(
    "SUPABASE_PRODUCT_IMAGES_BUCKET", "product-images"
)
SUPABASE_SUBMISSIONS_BUCKET = os.environ.get(
    "SUPABASE_SUBMISSIONS_BUCKET", "product-submissions"
)
ALLOW_DEV_TUNNEL_ORIGINS = os.environ.get(
    "ALLOW_DEV_TUNNEL_ORIGINS", "false"
).lower() == "true"
EXPOSE_DEV_AUTH_LINKS = (
    not PRODUCTION_MODE
    and os.environ.get("EXPOSE_DEV_AUTH_LINKS", "false").lower() == "true"
)

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
SUBMISSION_APPROVAL_CECOINS = int(
    os.environ.get("SUBMISSION_APPROVAL_CECOINS", "10")
)
PASSWORD_MIN_LENGTH = max(10, int(os.environ.get("PASSWORD_MIN_LENGTH", "12")))
SUBMISSION_DAILY_LIMIT = max(1, int(os.environ.get("SUBMISSION_DAILY_LIMIT", "10")))
SUBMISSION_PENDING_LIMIT = max(1, int(os.environ.get("SUBMISSION_PENDING_LIMIT", "20")))
RETENTION_ACTIVITY_DAYS = max(30, int(os.environ.get("RETENTION_ACTIVITY_DAYS", "395")))
RETENTION_UNVERIFIED_ACCOUNT_DAYS = max(
    7,
    int(os.environ.get("RETENTION_UNVERIFIED_ACCOUNT_DAYS", "30")),
)
RETENTION_SCAN_FILE_HOURS = max(1, int(os.environ.get("RETENTION_SCAN_FILE_HOURS", "48")))
TERMS_VERSION = os.environ.get("TERMS_VERSION", "2026-07").strip() or "2026-07"
SEARCH_RETENTION_DAYS = max(30, int(os.environ.get("SEARCH_RETENTION_DAYS", "180")))
ANALYTICS_RETENTION_DAYS = max(30, int(os.environ.get("ANALYTICS_RETENTION_DAYS", "365")))
SCAN_FILE_RETENTION_DAYS = max(1, int(os.environ.get("SCAN_FILE_RETENTION_DAYS", "30")))
REJECTED_SUBMISSION_RETENTION_DAYS = max(30, int(os.environ.get("REJECTED_SUBMISSION_RETENTION_DAYS", "90")))
PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "manual").strip().lower()
FRONTEND_PUBLIC_URL = (
    os.environ.get("FRONTEND_PUBLIC_URL", "").strip().rstrip("/")
    or (frontend_origins[0].rstrip("/") if frontend_origins else "http://localhost:3000")
)
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
BREVO_API_KEY = read_secret_env("BREVO_API_KEY")
RESEND_API_KEY = read_secret_env("RESEND_API_KEY")
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "").strip()
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USERNAME = os.environ.get("EMAIL_SMTP_USERNAME", "").strip()
EMAIL_SMTP_PASSWORD = read_secret_env("EMAIL_SMTP_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Ce aleg?").strip()
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "contact@cealeg.shop").strip().lower()
CRON_SECRET = read_secret_env("CRON_SECRET")
REDIS_URL = read_secret_env("REDIS_URL")
if not EMAIL_PROVIDER:
    if BREVO_API_KEY:
        EMAIL_PROVIDER = "brevo"
    elif RESEND_API_KEY:
        EMAIL_PROVIDER = "resend"
    elif EMAIL_SMTP_HOST:
        EMAIL_PROVIDER = "smtp"
    else:
        EMAIL_PROVIDER = "smtp"
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
ADMIN_ALERT_THROTTLE = {}

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
        "seriesId": "streak",
        "metric": "scanStreakDays",
        "icon": "streak",
        "titleTemplate": "{target} zile la rând cu scanări",
        "description": "Revino la raft mai multe zile la rând și primești un bonus de ritm.",
        "targets": [3],
        "coins": 35,
        "bonusScans": 1,
        "daily": False,
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
        "image": "/brand/Bronze.webp",
        "icon": "/brand/Bronze_icon.webp",
    },
    {
        "id": "gold",
        "title": "Gold CeCoins",
        "coins": 1200,
        "priceText": "19,99 lei",
        "priceEnv": "STRIPE_CECOINS_GOLD_PRICE_ID",
        "legacyPriceEnv": "STRIPE_CECOINS_BOOST_PRICE_ID",
        "image": "/brand/Gold.webp",
        "icon": "/brand/Gold_icon.webp",
    },
    {
        "id": "diamond",
        "title": "Diamond CeCoins",
        "coins": 3000,
        "priceText": "39,99 lei",
        "priceEnv": "STRIPE_CECOINS_DIAMOND_PRICE_ID",
        "legacyPriceEnv": "STRIPE_CECOINS_POWER_PRICE_ID",
        "image": "/brand/Diamond.webp",
        "icon": "/brand/Diamond_icon.webp",
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

    if EMAIL_PROVIDER == "smtp":
        return bool(EMAIL_SMTP_HOST and EMAIL_FROM)

    return False


def get_email_configuration_diagnostics():
    issues = []
    provider_key_configured = bool(BREVO_API_KEY or RESEND_API_KEY or EMAIL_SMTP_HOST)

    if EMAIL_PROVIDER not in {"brevo", "resend", "smtp"}:
        issues.append(f"Provider necunoscut: {EMAIL_PROVIDER}. Foloseste brevo, resend sau smtp.")

    if not EMAIL_FROM:
        issues.append("EMAIL_FROM lipseste.")

    if EMAIL_PROVIDER == "brevo" and not BREVO_API_KEY:
        issues.append("BREVO_API_KEY lipseste pentru providerul Brevo.")

    if EMAIL_PROVIDER == "resend" and not RESEND_API_KEY:
        issues.append("RESEND_API_KEY lipseste pentru providerul Resend.")

    if EMAIL_PROVIDER == "smtp" and not EMAIL_SMTP_HOST:
        issues.append("EMAIL_SMTP_HOST lipseste pentru providerul SMTP.")

    email_from_domain = EMAIL_FROM.split("@")[-1].lower() if "@" in EMAIL_FROM else ""
    contact_domain = CONTACT_EMAIL.split("@")[-1].lower() if "@" in CONTACT_EMAIL else ""

    if EMAIL_PROVIDER == "brevo" and EMAIL_FROM.lower().endswith("@gmail.com"):
        issues.append(
            "Brevo poate respinge senderul Gmail. Recomandat: EMAIL_FROM=contact@cealeg.shop si domeniu/sender verificat in Brevo."
        )

    if email_from_domain and contact_domain and email_from_domain != contact_domain:
        issues.append(
            "EMAIL_FROM si CONTACT_EMAIL sunt pe domenii diferite; verifica senderul si reply-to."
        )

    return {
        "provider": EMAIL_PROVIDER,
        "configured": is_email_configured(),
        "from": EMAIL_FROM,
        "fromName": EMAIL_FROM_NAME,
        "replyTo": get_email_reply_to() or EMAIL_FROM,
        "providerKeyOrHostConfigured": provider_key_configured,
        "issues": issues,
        "lastProviderError": LAST_EMAIL_PROVIDER_ERROR,
    }


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
        diagnostics = get_email_configuration_diagnostics()
        set_email_provider_error(
            "Email provider not configured. "
            f"Provider={diagnostics['provider']}, EMAIL_FROM set={bool(EMAIL_FROM)}, "
            f"provider key/host configured={diagnostics['providerKeyOrHostConfigured']}, "
            f"issues={'; '.join(diagnostics['issues']) or 'none'}"
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


def send_admin_alert(
    subject,
    intro,
    details=None,
    alert_key=None,
    min_interval_seconds=3600,
    severity="warning",
):
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    key = alert_key or subject
    now = time.time()
    last_sent_at = ADMIN_ALERT_THROTTLE.get(key, 0)

    if now - last_sent_at < min_interval_seconds:
        return False

    ADMIN_ALERT_THROTTLE[key] = now
    delivered = False
    normalized_severity = severity if severity in {"debug", "info", "warning", "error", "fatal"} else "warning"

    if sentry_sdk is not None and SENTRY_DSN:
        try:
            with sentry_sdk.new_scope() as scope:
                scope.set_tag("alert_key", str(key)[:120])
                scope.set_tag("alert_channel", "application")
                scope.set_extra("alert_intro", str(intro)[:500])
                sentry_sdk.capture_message(subject, level=normalized_severity)
            delivered = True
        except Exception as error:
            app.logger.warning("Sentry alert delivery failed: %s", error)

    webhook_url = read_secret_env("ALERT_WEBHOOK_URL")
    if webhook_url and (webhook_url.startswith("https://") or not PRODUCTION_MODE):
        try:
            webhook_response = requests.post(
                webhook_url,
                json={
                    "text": f"[Ce aleg] {subject}: {intro}",
                    "subject": subject,
                    "intro": intro,
                    "severity": normalized_severity,
                    "details": [str(item)[:500] for item in (details or [])[:20]],
                    "adminUrl": f"{FRONTEND_PUBLIC_URL}/admin",
                },
                timeout=3,
            )
            webhook_response.raise_for_status()
            delivered = True
        except Exception as error:
            app.logger.warning("Alert webhook delivery failed: %s", error)

    text_body = "\n".join([
        subject,
        "",
        intro,
        "",
        *(str(item) for item in (details or [])),
        "",
        f"Admin: {FRONTEND_PUBLIC_URL}/admin",
    ])
    html_body = render_brand_email(
        "Alertă admin",
        subject,
        intro,
        "Deschide admin",
        f"{FRONTEND_PUBLIC_URL}/admin",
        details or [],
        tone="danger",
    )

    if admin_email and is_valid_email_address(admin_email) and is_email_configured():
        delivered = send_transactional_email(
            admin_email,
            f"[Ce aleg] {subject}",
            text_body,
            html_body,
        ) or delivered

    return delivered


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
        "auth_version": int(user.auth_version or 0),
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

    if (
        user.email != payload.get("email")
        or int(user.auth_version or 0) != int(payload.get("auth_version", -1))
        or user.email_verified
    ):
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
        "action": "reset_password",
        "user_id": user.id,
        "email": user.email,
        "auth_version": int(user.auth_version or 0),
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

    if payload.get("action") != "reset_password":
        return None

    user = db.session.get(User, payload.get("user_id"))

    if (
        not user
        or user.email != payload.get("email")
        or int(user.auth_version or 0) != int(payload.get("auth_version", -1))
    ):
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
        "auth_version": int(user.auth_version or 0),
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

    if (
        user.email != payload.get("email")
        or int(user.auth_version or 0) != int(payload.get("auth_version", -1))
    ):
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


def format_email_datetime(value):
    if not value:
        return "indisponibil"

    try:
        return value.strftime("%d.%m.%Y, %H:%M")
    except Exception:
        return str(value)


def send_referral_bonus_email(user, inviter=None):
    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    inviter_name = inviter.name if inviter else "un prieten"
    text_body = (
        f"Salut, {user.name}!\n\n"
        f"Contul tău a fost confirmat cu o invitație de la {inviter_name}.\n"
        f"Ai primit {INVITE_BONUS_DAYS} zile de scanări nelimitate.\n\n"
        f"Deschide dashboardul: {dashboard_url}\n"
    )
    html_body = render_brand_email(
        "Bonus activat",
        "Ai primit scanări nelimitate.",
        f"Emailul a fost confirmat cu invitația de la {inviter_name}. Bonusul tău este activ.",
        "Deschide dashboardul",
        dashboard_url,
        [
            f"{INVITE_BONUS_DAYS} zile de scanări nelimitate.",
            "Bonusul se aplică automat în cont.",
            "Poți invita la rândul tău prieteni din dashboard.",
        ],
    )
    return send_transactional_email(
        user.email,
        "Bonus invitație activat în Ce aleg?",
        text_body,
        html_body,
    )


def send_referral_inviter_email(inviter, invited_user=None):
    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    invited_name = invited_user.name if invited_user else "un prieten"
    text_body = (
        f"Salut, {inviter.name}!\n\n"
        f"{invited_name} și-a confirmat contul folosind codul tău.\n"
        f"Ai primit {INVITE_BONUS_DAYS} zile de scanări nelimitate și 100 CeCoins.\n\n"
        f"Vezi progresul aici: {dashboard_url}\n"
    )
    html_body = render_brand_email(
        "Invitație confirmată",
        "Ai primit 100 CeCoins.",
        f"{invited_name} și-a confirmat contul folosind codul tău. Recompensa a fost adăugată automat.",
        "Vezi recompensele",
        dashboard_url,
        [
            "100 CeCoins adăugați automat.",
            f"{INVITE_BONUS_DAYS} zile de scanări nelimitate.",
            "Poți urmări misiunile și clasamentul în dashboard.",
        ],
    )
    return send_transactional_email(
        inviter.email,
        "Ai primit recompensă pentru invitație",
        text_body,
        html_body,
    )


def send_cecoins_purchase_email(user, pack, session=None):
    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    coins = int(pack.get("coins") or 0)
    title = pack.get("title") or "CeCoins"
    amount = None

    if session:
        amount_total = session.get("amount_total")
        currency = str(session.get("currency") or "ron").upper()
        try:
            if amount_total is not None:
                amount = f"{float(amount_total) / 100:.2f} {currency}"
        except (TypeError, ValueError):
            amount = None

    text_body = (
        f"Salut, {user.name}!\n\n"
        f"Pachetul {title} a fost confirmat.\n"
        f"Ai primit {coins} CeCoins în cont.\n\n"
        f"Deschide dashboardul: {dashboard_url}\n"
    )
    details = [
        f"Pachet: {title}",
        f"CeCoins adăugați: {coins}",
        "Soldul este actualizat automat în dashboard.",
    ]

    if amount:
        details.insert(2, f"Valoare plătită: {amount}")

    html_body = render_brand_email(
        "CeCoins activați",
        f"{coins} CeCoins au fost adăugați.",
        "Plata a fost confirmată și pachetul tău este disponibil în cont.",
        "Deschide dashboardul",
        dashboard_url,
        details,
    )
    return send_transactional_email(
        user.email,
        "CeCoins au fost adăugați în cont",
        text_body,
        html_body,
    )


def send_cecoin_reward_email(user, item):
    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    title = item.get("title") or "Recompensă"
    cost = int(item.get("cost") or 0)
    text_body = (
        f"Salut, {user.name}!\n\n"
        f"Recompensa {title} a fost activată.\n"
        f"Cost: {cost} CeCoins.\n\n"
        f"Vezi contul aici: {dashboard_url}\n"
    )
    details = [
        f"Recompensă: {title}",
        f"Cost: {cost} CeCoins",
    ]

    if item.get("bonusScans"):
        details.append(f"Scanări bonus: {int(item.get('bonusScans') or 0)}")

    if item.get("bonusDays"):
        details.append(f"Acces nelimitat: {int(item.get('bonusDays') or 0)} zile")

    html_body = render_brand_email(
        "Recompensă activată",
        f"{title} este activă.",
        "Recompensa a fost aplicată în contul tău și poate fi folosită imediat.",
        "Deschide dashboardul",
        dashboard_url,
        details,
    )
    return send_transactional_email(
        user.email,
        "Recompensă Ce aleg? activată",
        text_body,
        html_body,
    )


def send_product_submission_approved_email(user, submission, product=None, duplicate=False, reward=None):
    if not user:
        return False

    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    product_name = submission.product_name or (product.name if product else "produsul trimis")
    reward = reward or {}
    awarded_coins = int(reward.get("coins") or 0) if reward.get("claimed") else 0
    coin_line = (
        f"Ai primit și {awarded_coins} CeCoins.\n"
        if awarded_coins > 0
        else "Misiunea de catalog pentru azi era deja revendicată.\n"
    )
    text_body = (
        f"Salut, {user.name}!\n\n"
        f"Produsul {product_name} a fost aprobat în catalogul Ce aleg?.\n"
        f"Ai primit {SUBMISSION_APPROVAL_BONUS_CREDITS} scanare bonus.\n\n"
        f"{coin_line}\n"
        f"Vezi dashboardul: {dashboard_url}\n"
    )
    details = [
        f"Produs: {product_name}",
        f"Magazin: {submission.store or 'nespecificat'}",
        f"Scanări bonus: +{SUBMISSION_APPROVAL_BONUS_CREDITS}",
        f"CeCoins: +{awarded_coins}",
        (
            "Produsul exista deja în catalog, iar propunerea ta a fost confirmată."
            if duplicate
            else "Produsul a fost publicat în catalog."
        ),
    ]
    html_body = render_brand_email(
        "Produs aprobat",
        "Contribuția ta a fost aprobată.",
        "Mulțumim pentru completarea catalogului. Recompensa a fost adăugată automat în cont.",
        "Vezi dashboardul",
        dashboard_url,
        details,
    )
    return send_transactional_email(
        user.email,
        "Produs aprobat în Ce aleg?",
        text_body,
        html_body,
    )


def send_alternative_report_fixed_email(user, scanned_product, alternative_product, old_category, new_category):
    if not user:
        return False

    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    scanned_name = str(scanned_product.get("name") or "produsul scanat").strip()
    alternative_name = str(alternative_product.get("name") or "alternativa raportată").strip()
    old_category = old_category or "neconfirmată"
    new_category = new_category or "categorie actualizată"
    text_body = (
        f"Salut, {user.name}!\n\n"
        "Îți mulțumim că ai raportat o alternativă nepotrivită.\n"
        f"Am verificat produsul {alternative_name} și am actualizat categoria lui din "
        f"{old_category} în {new_category}, ca recomandările viitoare să fie mai precise.\n\n"
        f"Produs scanat: {scanned_name}\n"
        f"Deschide dashboardul: {dashboard_url}\n"
    )
    html_body = render_brand_email(
        "Raportare remediată",
        "Am corectat alternativa raportată.",
        "Îți mulțumim pentru raportare. Am verificat produsul și am actualizat categoria lui, ca recomandările viitoare să fie mai precise.",
        "Deschide dashboardul",
        dashboard_url,
        [
            f"Produs scanat: {scanned_name}",
            f"Alternativă raportată: {alternative_name}",
            f"Categorie veche: {old_category}",
            f"Categorie nouă: {new_category}",
            "Ne cerem scuze pentru recomandarea nepotrivită. Raportările ajută catalogul să devină mai bun.",
        ],
    )
    return send_transactional_email(
        user.email,
        "Am corectat alternativa raportată",
        text_body,
        html_body,
    )


PRODUCT_CORRECTION_EMAIL_EVENT_TYPE = "product_correction_email"


def product_notification_snapshot(product):
    if not product:
        return {}

    return {
        "id": product.id,
        "name": product.name,
        "barcode": product.barcode,
        "store": product.store,
        "category": product.category,
        "score": product.score,
        "tag": product.tag,
        "reason": product.reason,
        "ingredients": product.ingredients,
        "calories": product.calories,
        "protein": product.protein,
        "sugar": product.sugar,
        "fat": product.fat,
    }


def product_update_has_user_visible_change(previous_snapshot, product):
    current_snapshot = product_notification_snapshot(product)

    for key in [
        "name",
        "barcode",
        "store",
        "category",
        "tag",
        "reason",
        "ingredients",
    ]:
        if normalize_search_text(previous_snapshot.get(key)) != normalize_search_text(current_snapshot.get(key)):
            return True

    for key in ["score", "calories", "protein", "sugar", "fat"]:
        previous_value = previous_snapshot.get(key)
        current_value = current_snapshot.get(key)

        if previous_value is None and current_value is None:
            continue

        try:
            if round(float(previous_value or 0), 3) != round(float(current_value or 0), 3):
                return True
        except (TypeError, ValueError):
            if str(previous_value or "") != str(current_value or ""):
                return True

    return False


def product_score_text(score):
    try:
        return f"{round(float(score), 1)}/10"
    except (TypeError, ValueError):
        return "neconfirmat"


def send_product_corrected_email(user, product, previous_snapshot=None):
    if not user or not product:
        return False

    catalog_url = f"{FRONTEND_PUBLIC_URL}/catalog-romania"
    product_name = str(product.name or "produsul urmărit").strip()
    old_category = str((previous_snapshot or {}).get("category") or "").strip()
    new_category = str(product.category or "categorie actualizată").strip()
    details = [
        f"Produs: {product_name}",
        f"Categoria actuală: {new_category}",
        f"Scor actual: {product_score_text(product.score)}",
        "Îți mulțumim pentru scanări și raportări. Ele ajută catalogul să devină mai precis.",
    ]

    if old_category and normalize_search_text(old_category) != normalize_search_text(new_category):
        details.insert(1, f"Categoria veche: {old_category}")

    text_body = (
        f"Salut, {user.name}!\n\n"
        "Am corectat un produs cu care ai interacționat în Ce aleg?.\n"
        f"Produs: {product_name}\n"
        f"Categoria actuală: {new_category}\n"
        f"Scor actual: {product_score_text(product.score)}\n\n"
        f"Vezi Catalog România: {catalog_url}\n"
    )
    html_body = render_brand_email(
        "Produs corectat",
        "Am actualizat un produs din catalog.",
        "Un produs pe care l-ai scanat sau raportat a fost verificat de admin. Recomandările viitoare ar trebui să fie mai precise.",
        "Vezi Catalog România",
        catalog_url,
        details,
    )
    return send_transactional_email(
        user.email,
        "Am corectat un produs în Ce aleg?",
        text_body,
        html_body,
    )


def product_matches_notification_candidate(product, candidate):
    if not product or not isinstance(candidate, dict):
        return False

    product_barcode = str(product.barcode or "").strip()
    candidate_barcode = str(candidate.get("barcode") or "").strip()

    if product_barcode and candidate_barcode and product_barcode == candidate_barcode:
        return True

    product_name = normalize_search_text(product.name)
    candidate_name = normalize_search_text(candidate.get("name"))

    return bool(product_name and candidate_name and product_name == candidate_name)


def user_can_receive_product_notification(user):
    return bool(
        user
        and is_valid_email_address(user.email)
        and bool(getattr(user, "email_verified", True))
    )


def product_correction_email_recently_sent(user_id, product, cooldown_days=14):
    if not user_id or not product:
        return True

    since = utcnow() - timedelta(days=cooldown_days)
    product_id = product.id
    product_barcode = str(product.barcode or "").strip()
    recent_events = (
        UsageEvent.query
        .filter(
            UsageEvent.user_id == user_id,
            UsageEvent.event_type == PRODUCT_CORRECTION_EMAIL_EVENT_TYPE,
            UsageEvent.created_at >= since,
        )
        .order_by(UsageEvent.created_at.desc())
        .limit(25)
        .all()
    )

    for event in recent_events:
        metadata = parse_usage_metadata(event)

        if product_id and metadata.get("productId") == product_id:
            return True

        if product_barcode and str(metadata.get("barcode") or "").strip() == product_barcode:
            return True

    return False


def collect_product_correction_recipients(product, limit=25):
    if not product:
        return []

    recipients = {}
    since = utcnow() - timedelta(days=120)
    report_events = (
        UsageEvent.query
        .filter(
            UsageEvent.event_type == "alternative_report",
            UsageEvent.created_at >= since,
        )
        .order_by(UsageEvent.created_at.desc())
        .limit(500)
        .all()
    )

    for event in report_events:
        metadata = parse_usage_metadata(event)

        if (
            product_matches_notification_candidate(product, metadata.get("alternativeProduct"))
            or product_matches_notification_candidate(product, metadata.get("scannedProduct"))
        ):
            user = event.user

            if user_can_receive_product_notification(user):
                recipients.setdefault(user.id, user)

        if len(recipients) >= limit:
            break

    normalized_product_name = normalize_search_text(product.name)

    if normalized_product_name and len(recipients) < limit:
        history_items = (
            ScanHistory.query
            .filter(ScanHistory.scanned_at >= since)
            .order_by(ScanHistory.scanned_at.desc())
            .limit(500)
            .all()
        )

        for item in history_items:
            if normalize_search_text(item.product_name) != normalized_product_name:
                continue

            user = item.user

            if user_can_receive_product_notification(user):
                recipients.setdefault(user.id, user)

            if len(recipients) >= limit:
                break

    return list(recipients.values())[:limit]


def notify_users_about_product_correction(product, previous_snapshot=None, limit=25):
    if not is_email_configured():
        return 0

    if not product_update_has_user_visible_change(previous_snapshot or {}, product):
        return 0

    sent_count = 0

    for user in collect_product_correction_recipients(product, limit=limit):
        if product_correction_email_recently_sent(user.id, product):
            continue

        if send_product_corrected_email(user, product, previous_snapshot):
            record_user_event(
                user.id,
                PRODUCT_CORRECTION_EMAIL_EVENT_TYPE,
                "admin_product_update",
                {
                    "productId": product.id,
                    "barcode": product.barcode,
                    "category": product.category,
                    "score": product.score,
                },
                commit=False,
            )
            sent_count += 1

    if sent_count:
        db.session.commit()

    return sent_count


def plan_display_name(plan):
    normalized = str(plan or "").strip().lower()
    return {
        "pro": "Pro",
        "family": "Family",
        "free": "Free",
    }.get(normalized, normalized.capitalize() or "Plan")


def send_subscription_activated_email(user, plan, subscription=None):
    pricing_url = f"{FRONTEND_PUBLIC_URL}/pricing"
    plan_name = plan_display_name(plan)
    period_end = (
        format_email_datetime(subscription.current_period_end)
        if subscription and subscription.current_period_end
        else None
    )
    details = [
        f"Plan activ: {plan_name}",
        "Scanările și beneficiile planului sunt disponibile imediat în cont.",
        "Abonamentul poate fi administrat din pagina Planuri.",
    ]

    if period_end:
        details.insert(1, f"Perioadă activă până la: {period_end}")

    text_body = (
        f"Salut, {user.name}!\n\n"
        f"Planul {plan_name} este activ în contul tău Ce aleg?.\n"
        "Îl poți administra oricând din pagina Planuri.\n\n"
        f"Deschide pagina Planuri: {pricing_url}\n"
    )
    html_body = render_brand_email(
        "Plan activ",
        f"Planul {plan_name} este activ.",
        "Plata a fost confirmată și beneficiile abonamentului au fost activate în cont.",
        "Administrează abonamentul",
        pricing_url,
        details,
    )
    return send_transactional_email(
        user.email,
        f"Planul {plan_name} este activ în Ce aleg?",
        text_body,
        html_body,
    )


def send_subscription_checkout_email_once(user, plan, session, subscription=None):
    session_id = str((session or {}).get("id") or "").strip()

    if not user or not session_id:
        return False

    idempotency_key = f"stripe:subscription-email:{session_id}"

    if usage_event_by_idempotency_key(idempotency_key):
        return False

    sent = send_subscription_activated_email(user, plan, subscription)
    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="subscription_checkout_email",
            source="stripe_checkout",
            idempotency_key=idempotency_key,
            metadata_json=json.dumps({
                "sessionId": session_id,
                "plan": plan,
                "sent": bool(sent),
                "sentAt": utcnow().isoformat() + "Z",
            }),
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False
    return sent


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
        subscription.updated_at = utcnow()
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
    ConsentRecord.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    User.query.filter_by(referred_by_user_id=user_id).update(
        {User.referred_by_user_id: None},
        synchronize_session=False,
    )
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

    normalized_column = func.upper(User.invite_code)

    for separator in ("-", "_", " "):
        normalized_column = func.replace(normalized_column, separator, "")

    return User.query.filter(normalized_column == normalized_code).first()


def bonus_unlimited_is_active(user, now=None):
    now = now or utcnow()
    return bool(user.bonus_unlimited_until and user.bonus_unlimited_until > now)


def extend_bonus_unlimited(user, days=INVITE_BONUS_DAYS, source="invite", metadata=None):
    if not user or days <= 0:
        return

    now = utcnow()
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


def find_existing_catalog_entry_by_barcode(barcode):
    normalized_barcode = str(barcode or "").strip()

    if not normalized_barcode:
        return None

    return Product.query.filter_by(barcode=normalized_barcode).first()


def find_active_submission_by_barcode(barcode):
    normalized_barcode = str(barcode or "").strip()

    if not normalized_barcode:
        return None

    return (
        ProductSubmission.query.filter(
            ProductSubmission.barcode == normalized_barcode,
            ProductSubmission.status != "approved",
        )
        .order_by(ProductSubmission.created_at.desc())
        .first()
    )


def auto_claim_catalog_submission_reward(user, submission, product=None, duplicate=False):
    if not user or not submission or SUBMISSION_APPROVAL_CECOINS <= 0:
        return {"claimed": False, "coins": 0, "reason": "disabled"}

    user = lock_user_for_update(user.id)

    if not user:
        return {"claimed": False, "coins": 0, "reason": "user_missing"}

    day_start = get_day_start()
    idempotency_key = f"mission:{user.id}:catalog-auto:{day_start.date().isoformat()}"

    if usage_event_by_idempotency_key(idempotency_key):
        return {"claimed": False, "coins": 0, "reason": "daily_already_claimed"}

    already_claimed_today = bool(get_mission_claim_events(
        user.id,
        series_id="catalog",
        since=day_start,
    ))

    if already_claimed_today:
        return {"claimed": False, "coins": 0, "reason": "daily_already_claimed"}

    mission = next(
        (
            item for item in MISSION_CATALOG
            if item.get("seriesId") == "catalog" and int(item.get("target") or 0) == 1
        ),
        None,
    )
    mission_id = mission.get("id") if mission else "catalog_1"
    reward = {
        "coins": SUBMISSION_APPROVAL_CECOINS,
        "bonusScans": 0,
        "bonusDays": 0,
    }

    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="mission_claim",
            source=mission_id,
            idempotency_key=idempotency_key,
            metadata_json=json.dumps({
                "reward": reward,
                "seriesId": "catalog",
                "daily": True,
                "current": 1,
                "target": 1,
                "claimedAt": utcnow().isoformat() + "Z",
                "dayStart": day_start.isoformat() + "Z",
                "autoClaimed": True,
                "submissionId": submission.id,
                "productId": getattr(product, "id", None),
                "duplicate": bool(duplicate),
            }),
        )
    )

    return {"claimed": True, "coins": SUBMISSION_APPROVAL_CECOINS, "reason": "auto_claimed"}


def apply_referral_bonus_after_verification(user):
    if not user or not user.referred_by_user_id:
        return False

    idempotency_key = f"referral:verified:{user.id}"
    locked_users = (
        db.session.query(User)
        .filter(User.id.in_(sorted({user.id, user.referred_by_user_id})))
        .order_by(User.id)
    )

    if db.engine.dialect.name != "sqlite":
        locked_users = locked_users.with_for_update()

    locked_by_id = {item.id: item for item in locked_users.all()}
    user = locked_by_id.get(user.id)

    if not user or usage_event_by_idempotency_key(idempotency_key):
        return False

    inviter = locked_by_id.get(user.referred_by_user_id)

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
            idempotency_key=idempotency_key,
            metadata_json=json.dumps({
                "coins": 100,
                "invitedUserId": user.id,
                "awardedAt": utcnow().isoformat() + "Z",
            }),
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False
    clear_leaderboard_cache()
    send_referral_bonus_email(user, inviter)
    send_referral_inviter_email(inviter, user)
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
        "processingRestricted": bool(getattr(user, "processing_restricted", False)),
        "processingRestrictedAt": (
            user.processing_restricted_at.isoformat() + "Z"
            if user.processing_restricted_at else None
        ),
        "analyticsConsent": getattr(user, "analytics_consent", None),
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

    if subscription.current_period_end and subscription.current_period_end <= utcnow():
        return False

    return True


def set_auth_cookie(response, user):
    token = get_auth_serializer().dumps({
        "user_id": user.id,
        "auth_version": int(user.auth_version or 0),
    })
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=AUTH_MAX_AGE,
        httponly=True,
        secure=PRODUCTION_MODE or os.environ.get("COOKIE_SECURE", "false").lower() == "true",
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

    user = db.session.get(User, payload.get("user_id"))

    if not user:
        return None

    if int(payload.get("auth_version", -1)) != int(user.auth_version or 0):
        return None

    return user


def lock_user_for_update(user_id):
    query = db.session.query(User).filter(User.id == int(user_id))

    if db.engine.dialect.name != "sqlite":
        query = query.with_for_update()

    return query.one_or_none()


def lock_catalog_key(value):
    normalized_value = str(value or "").strip()

    if normalized_value and db.engine.dialect.name == "postgresql":
        db.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:catalog_key))"),
            {"catalog_key": normalized_value[:500]},
        )


def usage_event_by_idempotency_key(idempotency_key):
    if not idempotency_key:
        return None

    return UsageEvent.query.filter_by(idempotency_key=idempotency_key).first()


def require_auth(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        user = get_current_user()

        if not user:
            return jsonify({"error": "Autentificare necesară.", "code": "auth_required"}), 401

        g.current_user = user
        return handler(*args, **kwargs)

    return wrapped


def require_admin(handler):
    @wraps(handler)
    @require_auth
    def wrapped(*args, **kwargs):
        if not g.current_user.is_admin:
            return jsonify({"error": "Acces rezervat administratorului.", "code": "admin_required"}), 403

        return handler(*args, **kwargs)

    return wrapped


def require_same_user(user_id):
    return g.current_user.is_admin or int(user_id) == g.current_user.id


def get_redis_client():
    global REDIS_CLIENT, REDIS_RETRY_AFTER

    now = time.time()

    if not REDIS_URL or Redis is None or now < REDIS_RETRY_AFTER:
        return None

    try:
        if REDIS_CLIENT is None:
            REDIS_CLIENT = Redis.from_url(
                REDIS_URL,
                socket_connect_timeout=0.35,
                socket_timeout=0.5,
                decode_responses=True,
            )
            REDIS_CLIENT.ping()

        return REDIS_CLIENT
    except Exception as error:
        app.logger.warning("Redis unavailable; using local fallback: %s", error)
        REDIS_CLIENT = None
        REDIS_RETRY_AFTER = now + 30
        CACHE_METRICS["errors"] += 1
        return None


def distributed_cache_key(namespace, key):
    digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
    return f"cealeg:cache:{namespace}:{digest}"


def distributed_cache_get(namespace, key):
    client = get_redis_client()

    if client is None:
        return None

    try:
        cached = client.get(distributed_cache_key(namespace, key))
        if cached is None:
            CACHE_METRICS["misses"] += 1
            return None
        CACHE_METRICS["hits"] += 1
        return json.loads(cached)
    except Exception as error:
        CACHE_METRICS["errors"] += 1
        app.logger.warning("Redis cache read failed for %s: %s", namespace, error)
        return None


def distributed_cache_set(namespace, key, value, ttl_seconds):
    client = get_redis_client()

    if client is None:
        return False

    try:
        client.setex(
            distributed_cache_key(namespace, key),
            max(1, int(ttl_seconds)),
            json.dumps(value, ensure_ascii=False),
        )
        CACHE_METRICS["writes"] += 1
        return True
    except Exception as error:
        CACHE_METRICS["errors"] += 1
        app.logger.warning("Redis cache write failed for %s: %s", namespace, error)
        return False


def rate_limit(scope, limit, window_seconds, identity_value=None):
    remote_address = str(identity_value or request.remote_addr or "unknown")
    now = time.time()
    identity = hmac.new(
        app.config["AUTH_SECRET"].encode("utf-8"),
        remote_address.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]

    redis_client = get_redis_client()

    if redis_client is not None:
        try:
            window = max(1, int(window_seconds))
            bucket = int(now // window)
            redis_key = f"cealeg:rate:{scope}:{identity}:{bucket}"
            pipeline = redis_client.pipeline(transaction=True)
            pipeline.incr(redis_key)
            pipeline.expire(redis_key, window + 2)
            current_count, _ = pipeline.execute()
            return int(current_count) <= int(limit)
        except Exception as error:
            app.logger.warning("Redis rate limiter unavailable; using local fallback: %s", error)

    key = f"{scope}:{identity}"

    with RATE_LIMIT_BUCKETS_LOCK:
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
        email_diagnostics = get_email_configuration_diagnostics()
        warnings.append(
            "Emailurile tranzacționale nu sunt configurate corect: "
            + ("; ".join(email_diagnostics["issues"]) or "verifica providerul si EMAIL_FROM.")
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
    reference = reference or utcnow()
    start = reference - timedelta(days=reference.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_day_start(reference=None):
    reference = reference or utcnow()
    return reference.replace(hour=0, minute=0, second=0, microsecond=0)


def get_next_day_start(reference=None):
    return get_day_start(reference) + timedelta(days=1)


def get_month_start(reference=None):
    reference = reference or utcnow()
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
    stripe.max_network_retries = max(
        0,
        min(5, int(os.environ.get("STRIPE_MAX_NETWORK_RETRIES", "2"))),
    )
    configured_api_version = os.environ.get("STRIPE_API_VERSION", "").strip()
    if configured_api_version:
        stripe.api_version = configured_api_version
    return True


def build_stripe_idempotency_key(scope, user_id, *parts, window_seconds=120):
    supplied_key = request.headers.get("Idempotency-Key", "").strip()

    if supplied_key and not re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", supplied_key):
        supplied_key = ""

    operation_marker = supplied_key or str(int(time.time() // max(30, window_seconds)))
    raw_value = ":".join([
        str(scope),
        str(user_id),
        *(str(part) for part in parts),
        operation_marker,
    ])
    digest = hmac.new(
        app.config["AUTH_SECRET"].encode("utf-8"),
        raw_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"cealeg:{scope}:{digest}"[:255]


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
    subscription.updated_at = utcnow()
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


def create_checkout_session_with_stale_customer_retry(
    checkout_params,
    subscription,
    user,
    idempotency_key,
):
    try:
        return stripe.checkout.Session.create(
            **checkout_params,
            idempotency_key=idempotency_key,
        )
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
            return stripe.checkout.Session.create(
                **retry_params,
                idempotency_key=f"{idempotency_key}:stale-retry"[:255],
            )

        raise


def datetime_from_unix(timestamp):
    if not timestamp:
        return None

    try:
        return datetime.fromtimestamp(int(timestamp), timezone.utc).replace(tzinfo=None)
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
    subscription.updated_at = utcnow()
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

    idempotency_key = f"stripe:cecoins:{session_id}"

    if usage_event_by_idempotency_key(idempotency_key):
        return None

    try:
        user = lock_user_for_update(int(user_id))
    except (TypeError, ValueError):
        user = None

    if not user:
        app.logger.warning("Stripe CeCoins checkout ignored: user %s not found.", user_id)
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
            subscription.updated_at = utcnow()

    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="cecoin_purchase",
            source=pack["id"],
            idempotency_key=idempotency_key,
            metadata_json=json.dumps({
                "coins": int(pack["coins"]),
                "packId": pack["id"],
                "sessionId": session_id,
                "paymentStatus": payment_status,
                "priceEnv": pack["priceEnv"],
            }),
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    clear_leaderboard_cache()
    send_cecoins_purchase_email(user, pack, session)
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
            send_subscription_checkout_email_once(
                user,
                synced_subscription.plan,
                session,
                synced_subscription,
            )
            return synced_subscription

    fallback_status = "active" if payment_status in {"paid", "no_payment_required"} else "incomplete"

    local_subscription = update_local_subscription_from_stripe(
        user=user,
        plan=plan,
        status=fallback_status,
        customer_id=session.get("customer"),
        subscription_id=subscription_id,
    )
    send_subscription_checkout_email_once(user, plan, session, local_subscription)
    return local_subscription


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


def coerce_scan_day(value):
    if not value:
        return None

    if hasattr(value, "date"):
        return value.date()

    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (TypeError, ValueError):
        return None


def calculate_scan_streak_days(user_id, since=None):
    scan_dates = set()
    scan_events_query = UsageEvent.query.filter_by(
        user_id=user_id,
        event_type="scan",
    )
    history_query = ScanHistory.query.filter_by(user_id=user_id)

    if since:
        scan_events_query = scan_events_query.filter(UsageEvent.created_at >= since)
        history_query = history_query.filter(ScanHistory.scanned_at >= since)

    event_day = func.date(UsageEvent.created_at)
    history_day = func.date(ScanHistory.scanned_at)

    for value in (
        scan_events_query
        .with_entities(event_day.label("scan_day"))
        .distinct()
        .order_by(event_day.desc())
        .limit(120)
        .all()
    ):
        scan_day = coerce_scan_day(value.scan_day)

        if scan_day:
            scan_dates.add(scan_day)

    for value in (
        history_query
        .with_entities(history_day.label("scan_day"))
        .distinct()
        .order_by(history_day.desc())
        .limit(120)
        .all()
    ):
        scan_day = coerce_scan_day(value.scan_day)

        if scan_day:
            scan_dates.add(scan_day)

    if not scan_dates:
        return 0

    today = utcnow().date()
    yesterday = today - timedelta(days=1)

    if today in scan_dates:
        cursor = today
    elif yesterday in scan_dates:
        cursor = yesterday
    else:
        return 0

    streak_days = 0

    while cursor in scan_dates:
        streak_days += 1
        cursor -= timedelta(days=1)

    return streak_days


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
        "scanStreakDays": calculate_scan_streak_days(user_id, since=since),
        "historyCount": history_count,
        "favoritesCount": favorites_count,
        "cartCount": max(int(cart_count or 0), cart_event_count),
        "approvedSubmissions": approved_submissions,
        "confirmedInvites": confirmed_invites,
    }


def get_bulk_user_gamification_metrics(user_ids, since=None):
    """Load leaderboard metrics in a fixed number of queries."""
    safe_user_ids = [int(user_id) for user_id in user_ids if user_id is not None]

    if not safe_user_ids:
        return {}

    metrics_by_user = {
        user_id: {
            "scanCount": 0,
            "scanStreakDays": 0,
            "historyCount": 0,
            "favoritesCount": 0,
            "cartCount": 0,
            "approvedSubmissions": 0,
            "confirmedInvites": 0,
        }
        for user_id in safe_user_ids
    }

    def apply_counts(rows, key):
        for user_id, value in rows:
            if user_id in metrics_by_user:
                metrics_by_user[user_id][key] = int(value or 0)

    scan_query = db.session.query(
        UsageEvent.user_id,
        func.count(UsageEvent.id),
    ).filter(
        UsageEvent.user_id.in_(safe_user_ids),
        UsageEvent.event_type == "scan",
    )
    history_query = db.session.query(
        ScanHistory.user_id,
        func.count(ScanHistory.id),
    ).filter(ScanHistory.user_id.in_(safe_user_ids))
    favorites_query = db.session.query(
        Favorite.user_id,
        func.count(Favorite.id),
    ).filter(Favorite.user_id.in_(safe_user_ids))
    cart_query = db.session.query(
        CartItem.user_id,
        func.coalesce(func.sum(CartItem.quantity), 0),
    ).filter(CartItem.user_id.in_(safe_user_ids))
    cart_event_query = db.session.query(
        UsageEvent.user_id,
        func.count(UsageEvent.id),
    ).filter(
        UsageEvent.user_id.in_(safe_user_ids),
        UsageEvent.event_type == "cart_add",
    )
    submissions_query = db.session.query(
        ProductSubmission.user_id,
        func.count(ProductSubmission.id),
    ).filter(
        ProductSubmission.user_id.in_(safe_user_ids),
        ProductSubmission.status == "approved",
    )
    invites_query = db.session.query(
        UsageEvent.user_id,
        func.count(UsageEvent.id),
    ).filter(
        UsageEvent.user_id.in_(safe_user_ids),
        UsageEvent.event_type == "bonus_unlimited",
        UsageEvent.source == "referral_inviter",
    )
    streak_query = db.session.query(
        UsageEvent.user_id,
        func.date(UsageEvent.created_at),
    ).filter(
        UsageEvent.user_id.in_(safe_user_ids),
        UsageEvent.event_type == "scan",
    )

    if since:
        scan_query = scan_query.filter(UsageEvent.created_at >= since)
        history_query = history_query.filter(ScanHistory.scanned_at >= since)
        favorites_query = favorites_query.filter(Favorite.created_at >= since)
        cart_query = cart_query.filter(CartItem.created_at >= since)
        cart_event_query = cart_event_query.filter(UsageEvent.created_at >= since)
        submissions_query = submissions_query.filter(ProductSubmission.created_at >= since)
        invites_query = invites_query.filter(UsageEvent.created_at >= since)
        streak_query = streak_query.filter(UsageEvent.created_at >= since)

    apply_counts(scan_query.group_by(UsageEvent.user_id).all(), "scanCount")
    apply_counts(history_query.group_by(ScanHistory.user_id).all(), "historyCount")
    apply_counts(favorites_query.group_by(Favorite.user_id).all(), "favoritesCount")
    apply_counts(cart_query.group_by(CartItem.user_id).all(), "cartCount")

    cart_event_counts = dict(
        cart_event_query.group_by(UsageEvent.user_id).all()
    )
    apply_counts(
        submissions_query.group_by(ProductSubmission.user_id).all(),
        "approvedSubmissions",
    )
    apply_counts(invites_query.group_by(UsageEvent.user_id).all(), "confirmedInvites")

    scan_dates_by_user = {user_id: set() for user_id in safe_user_ids}
    for user_id, scan_day_value in streak_query.distinct().all():
        scan_day = coerce_scan_day(scan_day_value)
        if scan_day and user_id in scan_dates_by_user:
            scan_dates_by_user[user_id].add(scan_day)

    today = utcnow().date()
    yesterday = today - timedelta(days=1)

    for user_id, metrics in metrics_by_user.items():
        metrics["scanCount"] = max(
            int(metrics["scanCount"]),
            int(metrics["historyCount"]),
        )
        metrics["cartCount"] = max(
            int(metrics["cartCount"]),
            int(cart_event_counts.get(user_id, 0) or 0),
        )

        scan_dates = scan_dates_by_user[user_id]
        if today in scan_dates:
            cursor = today
        elif yesterday in scan_dates:
            cursor = yesterday
        else:
            continue

        while cursor in scan_dates:
            metrics["scanStreakDays"] += 1
            cursor -= timedelta(days=1)

    return metrics_by_user


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
        + int(metrics.get("scanStreakDays", 0)) * 12
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


def calculate_bulk_user_coins(user_ids, metrics_by_user=None):
    safe_user_ids = [int(user_id) for user_id in user_ids if user_id is not None]

    if not safe_user_ids:
        return {}

    totals = {
        user_id: {
            "missions": 0,
            "claimedInvite": 0,
            "purchased": 0,
            "recordedReferral": 0,
            "spent": 0,
        }
        for user_id in safe_user_ids
    }
    events = UsageEvent.query.filter(
        UsageEvent.user_id.in_(safe_user_ids),
        UsageEvent.event_type.in_([
            "mission_claim",
            "cecoin_purchase",
            "referral_cecoin_bonus",
            "cecoin_spend",
        ]),
    ).all()

    for event in events:
        values = totals.get(event.user_id)
        if values is None:
            continue

        metadata = parse_usage_metadata(event)

        if event.event_type == "mission_claim":
            coins = int((metadata.get("reward") or {}).get("coins") or 0)
            values["missions"] += coins
            if str(event.source or "").startswith("invite_"):
                values["claimedInvite"] += coins
        elif event.event_type == "cecoin_purchase":
            values["purchased"] += int(metadata.get("coins") or 0)
        elif event.event_type == "referral_cecoin_bonus":
            values["recordedReferral"] += int(metadata.get("coins") or 0)
        elif event.event_type == "cecoin_spend":
            values["spent"] += int(metadata.get("cost") or 0)

    metrics_by_user = metrics_by_user or get_bulk_user_gamification_metrics(safe_user_ids)
    result = {}

    for user_id, values in totals.items():
        confirmed_invites = int((metrics_by_user.get(user_id) or {}).get("confirmedInvites", 0) or 0)
        expected_referral = max(0, confirmed_invites * 100 - values["claimedInvite"])
        referral = max(values["recordedReferral"], expected_referral)
        result[user_id] = max(
            0,
            values["missions"] + values["purchased"] + referral - values["spent"],
        )

    return result


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
                "scanStreakDays": metrics.get("scanStreakDays", 0),
            }),
            "scanCount": metrics.get("scanCount", 0),
            "scanStreakDays": metrics.get("scanStreakDays", 0),
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

    if series_id == "streak":
        return f"{target} zile la rând cu scanări"

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
        mission_claimed = not is_daily and mission["id"] in claimed_ids
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
        elif mission_claimed:
            display_target = int(mission["target"])
            raw_current = display_target
            display_current = display_target
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
            "claimed": mission_claimed,
            "claimedToday": claimed_today,
            "claimable": completed and not mission_claimed,
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


MISSION_DIGEST_EVENT_TYPE = "mission_digest_email"
MISSION_DIGEST_COOLDOWN_DAYS = 6


def get_mission_action_href(series_id):
    if series_id in {"scan", "streak"}:
        return "/barcode-scan"

    if series_id == "catalog":
        return "/submit-product"

    if series_id == "cart":
        return "/cart"

    if series_id == "favorite":
        return "/favorites"

    return "/missions"


def format_mission_reward(reward):
    reward = reward or {}
    parts = []

    if int(reward.get("coins") or 0) > 0:
        parts.append(f"{int(reward.get('coins') or 0)} CeCoins")

    if int(reward.get("bonusScans") or 0) > 0:
        parts.append(f"{int(reward.get('bonusScans') or 0)} scanari bonus")

    if int(reward.get("bonusDays") or 0) > 0:
        parts.append(f"{int(reward.get('bonusDays') or 0)} zile bonus")

    return " + ".join(parts) or "recompensa"


def build_mission_nudge_items(user, limit=3, min_progress=60):
    if not user:
        return []

    safe_limit = max(1, min(int(limit or 3), 5))
    safe_progress = max(1, min(int(min_progress or 60), 95))
    metrics = get_user_gamification_metrics(user.id)
    missions = build_mission_statuses(user.id, metrics)
    nudges = []

    for mission in missions:
        if mission.get("automatic") or mission.get("daily"):
            continue

        if mission.get("claimed") or mission.get("claimedToday") or mission.get("claimable"):
            continue

        target = int(mission.get("target") or 0)
        current = int(mission.get("current") or 0)
        progress = int(mission.get("progress") or 0)
        remaining = max(0, target - current)

        if target <= 0 or remaining <= 0 or progress < safe_progress:
            continue

        reward_text = format_mission_reward(mission.get("reward"))
        nudges.append({
            "id": mission.get("id"),
            "seriesId": mission.get("seriesId"),
            "title": mission.get("title"),
            "current": current,
            "target": target,
            "remaining": remaining,
            "progress": progress,
            "reward": mission.get("reward") or {},
            "rewardText": reward_text,
            "href": get_mission_action_href(mission.get("seriesId")),
        })

    nudges.sort(
        key=lambda item: (
            item["progress"],
            int((item.get("reward") or {}).get("coins") or 0),
            -item["remaining"],
        ),
        reverse=True,
    )
    return nudges[:safe_limit]


def mission_digest_was_recently_sent(user_id, cooldown_days=MISSION_DIGEST_COOLDOWN_DAYS):
    since = utcnow() - timedelta(days=max(1, int(cooldown_days or 1)))
    return bool(
        UsageEvent.query.filter(
            UsageEvent.user_id == user_id,
            UsageEvent.event_type == MISSION_DIGEST_EVENT_TYPE,
            UsageEvent.created_at >= since,
        ).first()
    )


def send_mission_digest_email(user, nudges):
    if not user or not nudges:
        return False

    details = [
        (
            f"{item['title']}: mai ai {item['remaining']} pana la tinta. "
            f"Recompensa: {item['rewardText']}."
        )
        for item in nudges
    ]
    text_body = "\n".join([
        "Ai misiuni aproape gata in Ce aleg?.",
        "",
        *details,
        "",
        f"Deschide misiunile: {FRONTEND_PUBLIC_URL}/missions",
    ])
    html_body = render_brand_email(
        "Misiuni aproape gata",
        "Ai recompense aproape de deblocat.",
        "Mai ai cativa pasi pana la urmatoarele CeCoins. Intra in pagina de misiuni si finalizeaza ce este aproape gata.",
        "Deschide misiunile",
        f"{FRONTEND_PUBLIC_URL}/missions",
        details,
    )

    return send_transactional_email(
        user.email,
        "Ai misiuni aproape gata in Ce aleg?",
        text_body,
        html_body,
    )


def build_mission_digest_batch(limit=100, apply_changes=False):
    safe_limit = max(1, min(int(limit or 100), 500))
    users = (
        User.query
        .filter(User.email.isnot(None), User.email != "")
        .order_by(User.id.asc())
        .limit(safe_limit)
        .all()
    )
    recipients = []
    skipped_recent = 0
    skipped_unverified = 0
    sent = 0
    failed = 0

    for user in users:
        if not is_valid_email_address(user.email):
            continue

        if not bool(getattr(user, "email_verified", True)):
            skipped_unverified += 1
            continue

        if mission_digest_was_recently_sent(user.id):
            skipped_recent += 1
            continue

        nudges = build_mission_nudge_items(user)

        if not nudges:
            continue

        recipients.append({
            "userId": user.id,
            "email": user.email,
            "name": user.name,
            "missions": nudges,
            "topMission": nudges[0]["title"],
            "topProgress": nudges[0]["progress"],
        })

        if apply_changes:
            if send_mission_digest_email(user, nudges):
                sent += 1
                record_user_event(
                    user.id,
                    MISSION_DIGEST_EVENT_TYPE,
                    "admin",
                    {
                        "missionIds": [item["id"] for item in nudges],
                        "topProgress": nudges[0]["progress"],
                        "sentAt": utcnow().isoformat() + "Z",
                    },
                    commit=False,
                )
            else:
                failed += 1

    if apply_changes and (sent or failed):
        db.session.commit()

    return {
        "scanned": len(users),
        "eligible": len(recipients),
        "sent": sent,
        "failed": failed,
        "skippedRecent": skipped_recent,
        "skippedUnverified": skipped_unverified,
        "applied": bool(apply_changes),
        "recipients": recipients[:25],
    }


def build_user_leaderboard(current_user_id=None, limit=10, since=None):
    safe_limit = max(1, min(limit, 25))
    since_key = since.isoformat() if since else "all_time"
    cache_key = (safe_limit, since_key)
    cached = LEADERBOARD_CACHE.get(cache_key)

    if cached and time.time() - cached["created_at"] < LEADERBOARD_CACHE_TTL:
        rows = [dict(row) for row in cached["rows"]]
    else:
        users = User.query.order_by(User.created_at.asc()).all()
        metrics_by_user = get_bulk_user_gamification_metrics(
            [user.id for user in users],
            since=since,
        )
        coins_by_user = (
            calculate_bulk_user_coins([user.id for user in users], metrics_by_user)
            if since is None
            else {}
        )
        rows = []

        for user in users:
            metrics = metrics_by_user.get(user.id) or {
                "scanCount": 0,
                "scanStreakDays": 0,
                "favoritesCount": 0,
                "cartCount": 0,
                "approvedSubmissions": 0,
                "confirmedInvites": 0,
            }
            score = calculate_activity_score(metrics)
            coins = coins_by_user.get(user.id, 0) if since is None else score

            rows.append({
                "userId": user.id,
                "name": (user.name or "Utilizator").split()[0],
                "coins": coins,
                "score": score,
                "scanCount": metrics["scanCount"],
                "scanStreakDays": metrics.get("scanStreakDays", 0),
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
    "get_admin_monitoring",
    "get_admin_submissions",
    "get_admin_search_misses",
    "search_admin_products",
    "export_admin_search_misses",
    "export_admin_alternative_reports",
    "export_admin_payment_events",
    "resolve_admin_alternative_report",
    "recategorize_admin_catalog",
    "get_admin_catalog_quality",
    "send_admin_mission_digest",
    "run_admin_retention",
    "update_admin_product",
    "delete_admin_product",
    "admin_update_user_plan",
    "get_readiness",
    "send_admin_email_test",
    "admin_resend_email_verification",
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
    "get_gamification_leaderboard",
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
    "get_account_data",
    "record_privacy_consent",
    "get_account_privacy",
    "export_account_data",
    "update_account_consent",
    "update_processing_restriction",
    "report_alternative_issue",
    "report_product_issue",
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


def endpoint_name(value):
    return str(value or "").rsplit(".", 1)[-1]


@app.before_request
def enforce_access_controls():
    g.request_id = get_request_id()
    g.request_started_at = time.perf_counter()

    if sentry_sdk is not None and SENTRY_DSN:
        sentry_sdk.set_tag("request_id", g.request_id)
    endpoint = endpoint_name(request.endpoint)

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

    camera_limit = 6 if endpoint == "identify_product_frame" else 45

    if endpoint in {"identify_product_frame", "lookup_barcode"} and not rate_limit(
        endpoint, camera_limit, 60
    ):
        return jsonify({"error": "Prea multe cereri. Reîncearcă în câteva secunde."}), 429

    if endpoint == "translate_text" and not rate_limit(endpoint, 120, 60):
        return jsonify({"error": "Prea multe traduceri. Reîncearcă în câteva secunde."}), 429

    if endpoint in {"ai_extract_product_info", "get_open_food_facts_alternatives"} and not rate_limit(
        endpoint, 30, 60
    ):
        return jsonify({"error": "Prea multe cereri. Reîncearcă în câteva secunde."}), 429

    if endpoint in {"contact_support", "track_analytics_event", "report_alternative_issue", "report_product_issue"} and not rate_limit(
        endpoint, 20, 60
    ):
        return jsonify({"error": "Prea multe cereri. Reîncearcă în câteva secunde."}), 429

    endpoint_limits = {
        "analyze_product": (12, 60),
        "add_product_submission": (8, 3600),
        "search_products": (30, 60),
        "search_products_by_label": (20, 60),
        "import_barcode_product": (12, 60),
        "claim_gamification_mission": (20, 60),
        "redeem_cecoin_reward": (10, 60),
    }
    endpoint_limit = endpoint_limits.get(endpoint)

    if endpoint_limit and not rate_limit(endpoint, *endpoint_limit):
        return jsonify({
            "error": "Prea multe cereri pentru această acțiune. Reîncearcă mai târziu.",
            "code": "rate_limit_exceeded",
        }), 429

    needs_auth = (
        endpoint in AUTH_ENDPOINTS
        or endpoint in ADMIN_ENDPOINTS
        or endpoint in USER_PATH_ENDPOINTS
    )

    if not needs_auth:
        return validate_endpoint_input(endpoint)

    user = get_current_user()

    if not user:
        return jsonify({"error": "Autentificare necesară.", "code": "auth_required"}), 401

    g.current_user = user

    restriction_exceptions = {
        "update_processing_restriction",
        "export_account_data",
        "get_account_data",
        "get_account_privacy",
        "update_account_consent",
        "record_privacy_consent",
        "request_account_deletion",
        "confirm_account_deletion",
        "logout",
        "start_billing_portal",
    }

    if (
        user.processing_restricted
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and endpoint not in restriction_exceptions
        and endpoint not in ADMIN_ENDPOINTS
    ):
        return jsonify({
            "error": "Prelucrarea datelor acestui cont este restricționată.",
            "code": "processing_restricted",
        }), 423

    if user.processing_restricted and endpoint in RESTRICTED_PROCESSING_ENDPOINTS:
        return jsonify({
            "error": "Prelucrarea opțională este restricționată pentru acest cont.",
            "code": "processing_restricted",
        }), 423

    if endpoint in ADMIN_ENDPOINTS and not user.is_admin:
        return jsonify({"error": "Acces rezervat administratorului.", "code": "admin_required"}), 403

    if endpoint in USER_PATH_ENDPOINTS:
        user_id = request.view_args.get("user_id")

        if user_id is not None and not require_same_user(user_id):
            return jsonify({"error": "Nu poți accesa datele altui cont.", "code": "wrong_account"}), 403

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

    return validate_endpoint_input(endpoint)


@app.after_request
def add_security_headers(response):
    endpoint = endpoint_name(request.endpoint)
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

    if endpoint == "api_docs":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; frame-ancestors 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://validator.swagger.io; connect-src 'self'"
        )
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    response.headers.setdefault(
        "X-Request-ID",
        getattr(g, "request_id", uuid4().hex),
    )

    request_started_at = getattr(g, "request_started_at", None)
    if request_started_at is not None:
        duration_ms = max(0, (time.perf_counter() - request_started_at) * 1000)
        response.headers.setdefault("Server-Timing", f"app;dur={duration_ms:.1f}")

    if is_sensitive_response:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"

    if PRODUCTION_MODE:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    if response.status_code >= 400 and response.is_json:
        payload = response.get_json(silent=True)

        if isinstance(payload, dict):
            payload.setdefault("requestId", getattr(g, "request_id", uuid4().hex))
            payload.setdefault("code", {
                400: "invalid_request",
                401: "auth_required",
                403: "forbidden",
                404: "not_found",
                409: "conflict",
                413: "payload_too_large",
                423: "processing_restricted",
                429: "rate_limit_exceeded",
                500: "internal_error",
                502: "upstream_error",
                503: "service_unavailable",
            }.get(response.status_code, "request_failed"))
            response.set_data(json.dumps(payload, ensure_ascii=False))
            response.content_type = "application/json; charset=utf-8"

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
        "image": "/products/skyr.webp",
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


def record_user_event(user_id, event_type, source=None, metadata=None, commit=False):
    if not user_id or not db.session.get(User, user_id):
        return None

    event = UsageEvent(
        user_id=user_id,
        event_type=str(event_type or "event").strip()[:40],
        source=str(source or "").strip()[:40] or None,
        metadata_json=json.dumps(metadata or {}),
    )
    db.session.add(event)

    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Monitoring event could not be saved.")
            return None

    return event


ALLOWED_ANALYTICS_EVENTS = {
    "landing_cta",
    "scan_started",
    "barcode_lookup",
    "product_found",
    "product_missing",
    "add_to_cart",
    "add_to_favorites",
    "alternative_report",
    "checkout_started",
    "pricing_checkout",
    "cecoins_checkout",
    "subscription_started",
    "support_message",
    "product_report",
    "register_started",
    "login_success",
}

RESTRICTED_PROCESSING_ENDPOINTS = {
    "analyze_product",
    "ai_extract_product_info",
    "identify_product_frame",
    "add_product_submission",
    "report_local_price",
    "report_alternative_issue",
    "report_product_issue",
}

REQUEST_VALIDATOR_RULES = {
    "register": ("register", "json"),
    "login": ("login", "json"),
    "verify_email": ("token", "json"),
    "resend_email_verification": ("email", "json"),
    "forgot_password": ("email", "json"),
    "reset_password": ("reset_password", "json"),
    "start_checkout": ("subscription_checkout", "json"),
    "start_cecoin_checkout": ("cecoin_checkout", "json"),
    "sync_cecoin_checkout_session": ("checkout_sync", "json"),
    "track_analytics_event": ("analytics", "json"),
    "contact_support": ("support", "json"),
    "report_alternative_issue": ("alternative_feedback", "json"),
    "report_product_issue": ("product_feedback", "json"),
    "search_products": ("product_search", "query"),
    "import_barcode_product": ("barcode_import", "json"),
    "get_open_food_facts_alternatives": ("alternatives", "json"),
    "analyze_product": ("analysis", "form"),
    "add_product_submission": ("product_submission", "form"),
}


def validate_endpoint_input(endpoint):
    rule = REQUEST_VALIDATOR_RULES.get(endpoint)

    if not rule:
        return None

    validator_name, source = rule
    if source == "query":
        raw_data = request.args.to_dict(flat=True)
    elif source == "form":
        raw_data = request.form.to_dict(flat=True)
    else:
        raw_data = request.get_json(silent=True)

    options = {}
    if validator_name in {"register", "reset_password"}:
        options["password_min_length"] = PASSWORD_MIN_LENGTH

    result = validate_payload(validator_name, raw_data, **options)

    if not result.ok:
        return jsonify(result.error_payload()), 400

    g.validated_data = result.data
    return None


@route("/analytics/event", methods=["POST"])
def track_analytics_event():
    data = request.get_json(silent=True) or {}
    event_name = str(data.get("name") or "").strip().lower().replace(" ", "_")

    if event_name not in ALLOWED_ANALYTICS_EVENTS:
        return jsonify({"ok": True, "ignored": True})

    user = get_current_user()

    if user and (user.processing_restricted or user.analytics_consent is False):
        return jsonify({"ok": True, "ignored": True, "reason": "privacy_preference"})
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    safe_metadata = {
        str(key)[:50]: str(value)[:250]
        for key, value in metadata.items()
        if value is not None
    }

    if user:
        record_user_event(
            user.id,
            f"ui_{event_name}",
            "frontend",
            safe_metadata,
            commit=True,
        )

    return jsonify({"ok": True})


@route("/feedback/alternative", methods=["POST"])
def report_alternative_issue():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    alternative_product = data.get("product") if isinstance(data.get("product"), dict) else {}
    scanned_product = data.get("scannedProduct") if isinstance(data.get("scannedProduct"), dict) else {}
    alternative_name = str(alternative_product.get("name") or "").strip()
    scanned_name = str(scanned_product.get("name") or "").strip()
    store = str(data.get("store") or "").strip()[:100]
    request_text = str(data.get("request") or "").strip()[:250]
    reason = str(data.get("reason") or "wrong_recommendation").strip()[:80]

    if not alternative_name:
        return jsonify({"error": "Alternativa raportată nu este validă."}), 400

    reported_category = str(alternative_product.get("category") or "").strip()
    reported_family = str(get_product_recommendation_family(alternative_product)).strip()

    metadata = {
        "reason": reason,
        "store": store,
        "request": request_text,
        "scannedProduct": {
            "name": scanned_name,
            "barcode": str(scanned_product.get("barcode") or "").strip()[:32],
            "category": str(scanned_product.get("category") or "").strip()[:120],
            "family": get_product_recommendation_family(scanned_product),
        },
        "alternativeProduct": {
            "name": alternative_name,
            "barcode": str(alternative_product.get("barcode") or "").strip()[:32],
            "brand": str(alternative_product.get("brand") or "").strip()[:120],
            "category": reported_category[:120],
            "source": str(alternative_product.get("source") or "").strip()[:80],
            "family": reported_family,
        },
    }

    record_user_event(user.id, "alternative_report", "alternatives", metadata, commit=False)
    record_search_event(
        scanned_name or metadata["scannedProduct"]["barcode"] or alternative_name,
        store=store,
        result_count=0,
        source="alternative_report",
        user_id=user.id,
    )
    db.session.commit()

    send_admin_alert(
        "Alternativă raportată",
        "Un utilizator a marcat o recomandare ca nepotrivită.",
        [
            f"Utilizator: {user.email}",
            f"Produs scanat: {scanned_name or '-'}",
            f"Alternativă: {alternative_name}",
            f"Magazin: {store or '-'}",
            f"Cerință: {request_text or '-'}",
            "Corecție automată: nu; raportul așteaptă verificarea adminului",
        ],
        alert_key="alternative_report",
        min_interval_seconds=900,
    )

    return jsonify({
        "message": "Mulțumim. Raportarea a fost salvată pentru verificare.",
        "fixed": False,
        "category": reported_category or None,
    })


PRODUCT_REPORT_REASONS = {
    "wrong_product": "Produs greșit",
    "wrong_price": "Preț greșit",
    "wrong_nutrition": "Date nutriționale greșite",
    "wrong_score": "Scor/verdict greșit",
    "wrong_image": "Imagine greșită",
    "missing_data": "Date incomplete",
    "other": "Altă problemă",
}


@route("/feedback/product", methods=["POST"])
def report_product_issue():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    product_name = str(product.get("name") or "").strip()
    barcode = str(product.get("barcode") or "").strip()[:80]
    store = str(data.get("store") or product.get("store") or "").strip()[:100]
    reason = str(data.get("reason") or "other").strip()
    details = str(data.get("details") or "").strip()

    if reason not in PRODUCT_REPORT_REASONS:
        reason = "other"

    if not product_name and not barcode:
        return jsonify({"error": "Produsul raportat nu este valid."}), 400

    if len(details) > 1000:
        return jsonify({"error": "Detaliile sunt prea lungi. Te rugăm să le scurtezi."}), 400

    metadata = {
        "reason": reason,
        "reasonLabel": PRODUCT_REPORT_REASONS[reason],
        "details": details[:1000],
        "store": store,
        "source": str(data.get("source") or "result").strip()[:80],
        "product": {
            "name": product_name[:160],
            "barcode": barcode,
            "brand": str(product.get("brand") or "").strip()[:120],
            "category": str(product.get("category") or "").strip()[:120],
            "score": str(product.get("score") or "").strip()[:40],
            "price": str(product.get("price") or "").strip()[:100],
            "image": str(product.get("image") or "").strip()[:255],
        },
    }

    record_user_event(user.id, "product_report", "result", metadata, commit=False)
    record_search_event(
        product_name or barcode,
        store=store,
        result_count=0,
        source="product_report",
        user_id=user.id,
    )
    db.session.commit()

    send_admin_alert(
        "Produs raportat",
        "Un utilizator a semnalat date greșite sau incomplete pe pagina de rezultat.",
        [
            f"Utilizator: {user.email}",
            f"Produs: {product_name or '-'}",
            f"Barcode: {barcode or '-'}",
            f"Magazin: {store or '-'}",
            f"Motiv: {PRODUCT_REPORT_REASONS[reason]}",
            f"Detalii: {details or '-'}",
        ],
        alert_key="product_report",
        min_interval_seconds=900,
    )

    return jsonify({
        "message": "Mulțumim. Raportarea a fost salvată și apare în admin pentru corectare.",
    })


@route("/support/contact", methods=["POST"])
def contact_support():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    topic = str(data.get("topic") or "Suport").strip()[:120]
    message = str(data.get("message") or "").strip()
    user = get_current_user()

    if not is_valid_email_address(email):
        return jsonify({"error": "Introdu o adresă de email validă."}), 400

    if len(message) < 10:
        return jsonify({"error": "Scrie câteva detalii despre problemă."}), 400

    if len(message) > 4000:
        return jsonify({"error": "Mesajul este prea lung. Te rugăm să îl scurtezi."}), 400

    support_email = get_email_reply_to()

    if not support_email or not is_email_configured():
        return jsonify({"error": "Emailul de suport nu este configurat complet."}), 503

    details = [
        f"De la: {email}",
        f"Cont logat: {user.email if user else 'nu'}",
        f"Subiect: {topic}",
    ]
    html_body = render_brand_email(
        "Mesaj suport",
        f"Mesaj nou: {topic}",
        message,
        "Deschide admin",
        f"{FRONTEND_PUBLIC_URL}/admin",
        details,
        tone="standard",
    )
    text_body = "\n".join([
        f"Mesaj nou: {topic}",
        "",
        message,
        "",
        *details,
    ])

    sent = send_transactional_email(
        support_email,
        f"[Ce aleg] Suport: {topic}",
        text_body,
        html_body,
    )

    if not sent:
        return jsonify({"error": "Mesajul nu a putut fi trimis momentan."}), 502

    if user:
        record_user_event(
            user.id,
            "support_message",
            "support",
            {"topic": topic, "email": email},
            commit=True,
        )

    return jsonify({"message": "Mesajul a fost trimis. Îți răspundem cât mai curând."})


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

    if any(token in text_value for token in ["alta aroma", "alta aromă", "alt gust", "gust diferit", "aroma diferita", "aromă diferită", "alt sortiment", "alta varianta", "altă variantă"]):
        criteria.append("different_flavor")

    return list(dict.fromkeys(criteria))


def get_cached_product_search_results(cache_key):
    distributed = distributed_cache_get("product-search", cache_key)

    if isinstance(distributed, list):
        return [dict(item) for item in distributed if isinstance(item, dict)]

    cache_item = PRODUCT_SEARCH_RESULT_CACHE.get(cache_key)

    if not cache_item:
        return None

    if time.time() - cache_item["created_at"] > PRODUCT_SEARCH_RESULT_CACHE_TTL:
        PRODUCT_SEARCH_RESULT_CACHE.pop(cache_key, None)
        return None

    return [dict(item) for item in cache_item["results"]]


def set_cached_product_search_results(cache_key, results):
    distributed_cache_set(
        "product-search",
        cache_key,
        results,
        PRODUCT_SEARCH_RESULT_CACHE_TTL,
    )
    set_limited_cache_item(
        PRODUCT_SEARCH_RESULT_CACHE,
        cache_key,
        {
            "created_at": time.time(),
            "results": [dict(item) for item in results],
        },
        PRODUCT_SEARCH_RESULT_CACHE_MAX_ITEMS,
    )


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
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    return parsed if math.isfinite(parsed) else None


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


def get_local_product_search_results(search_text, store_name=None, limit=10):
    normalized_query = normalize_search_text(search_text)
    query_words = [
        word for word in normalized_query.split()
        if len(word) >= 2 and not word.isdigit()
    ][:8]
    filters = []

    if re.fullmatch(r"\d{4,}", str(search_text or "").strip()):
        filters.append(Product.barcode == str(search_text).strip())

    for word in query_words:
        pattern = f"%{word}%"
        filters.extend([
            Product.name.ilike(pattern),
            Product.category.ilike(pattern),
            Product.store.ilike(pattern),
        ])

    if not filters:
        return []

    candidates = Product.query.filter(or_(*filters)).limit(160).all()
    scored = []

    for product in candidates:
        score = product_match_score(product, search_text)

        if product.barcode and product.barcode == str(search_text).strip():
            score += 160
        if store_name and store_name != "Fără magazin ales" and product.store == store_name:
            score += 15
        if score < 34:
            continue

        product_data = product_to_dict(product)
        product_data["matchScore"] = score
        product_data["source"] = "local_catalog"
        scored.append((score, product.id, product_data))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored[:max(1, min(int(limit or 10), 20))]]


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
    return SUPABASE_STORAGE_ENABLED and bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


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


def save_scan_image(file, user_id):
    if not file or not allowed_image_file(file.filename):
        raise ValueError("Format imagine invalid. Sunt acceptate: JPG, JPEG, PNG, WEBP.")

    try:
        image = ImageOps.exif_transpose(Image.open(file.stream))
        image.verify()
        file.stream.seek(0)
        image = ImageOps.exif_transpose(Image.open(file.stream)).convert("RGB")
        image.thumbnail((1800, 1800))
        filename = f"scan_{int(user_id)}_{uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        image.save(filepath, "JPEG", quality=86, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ValueError(
            "Imaginea nu a putut fi procesată. Încearcă alt fișier JPG, PNG sau WEBP."
        )

    user_prefix = f"scan_{int(user_id)}_"
    user_files = []

    for candidate in os.scandir(UPLOAD_FOLDER):
        if candidate.is_file() and candidate.name.startswith(user_prefix):
            user_files.append(candidate)

    for old_file in sorted(user_files, key=lambda item: item.stat().st_mtime, reverse=True)[25:]:
        try:
            os.remove(old_file.path)
        except OSError:
            app.logger.warning("Could not remove expired scan image %s", old_file.name)

    return filename


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
                "users auth_version",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS auth_version INTEGER NOT NULL DEFAULT 0",
            ),
            (
                "users processing restricted",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS processing_restricted BOOLEAN NOT NULL DEFAULT FALSE",
            ),
            (
                "users processing restricted at",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS processing_restricted_at TIMESTAMP NULL",
            ),
            (
                "users processing restriction reason",
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS processing_restriction_reason VARCHAR(500)",
            ),
            (
                "usage events idempotency key",
                "ALTER TABLE usage_events "
                "ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(180)",
            ),
            ("users terms_version", "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version VARCHAR(30)"),
            ("users terms_accepted_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP NULL"),
            ("users age_confirmed_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS age_confirmed_at TIMESTAMP NULL"),
            ("users analytics_consent", "ALTER TABLE users ADD COLUMN IF NOT EXISTS analytics_consent BOOLEAN NULL"),
            ("users analytics_consent_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS analytics_consent_at TIMESTAMP NULL"),
            ("users processing_restricted", "ALTER TABLE users ADD COLUMN IF NOT EXISTS processing_restricted BOOLEAN NOT NULL DEFAULT FALSE"),
            ("users processing_restricted_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS processing_restricted_at TIMESTAMP NULL"),
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
    add_column_if_missing("users", "auth_version", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("users", "processing_restricted", "BOOLEAN NOT NULL DEFAULT 0")
    add_column_if_missing("users", "processing_restricted_at", "DATETIME")
    add_column_if_missing("users", "processing_restriction_reason", "VARCHAR(500)")
    add_column_if_missing("usage_events", "idempotency_key", "VARCHAR(180)")
    add_column_if_missing("users", "terms_version", "VARCHAR(30)")
    add_column_if_missing("users", "terms_accepted_at", "DATETIME")
    add_column_if_missing("users", "age_confirmed_at", "DATETIME")
    add_column_if_missing("users", "analytics_consent", "BOOLEAN")
    add_column_if_missing("users", "analytics_consent_at", "DATETIME")
    add_column_if_missing("users", "processing_restricted", "BOOLEAN NOT NULL DEFAULT 0")
    add_column_if_missing("users", "processing_restricted_at", "DATETIME")
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
        (
            "usage event idempotency",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_usage_events_idempotency_key "
            "ON usage_events (idempotency_key) WHERE idempotency_key IS NOT NULL",
        ),
        (
            "usage events user type date",
            "CREATE INDEX IF NOT EXISTS ix_usage_events_user_type_created "
            "ON usage_events (user_id, event_type, created_at)",
        ),
        (
            "usage events user type source",
            "CREATE INDEX IF NOT EXISTS ix_usage_events_user_type_source "
            "ON usage_events (user_id, event_type, source)",
        ),
        (
            "submissions user status date",
            "CREATE INDEX IF NOT EXISTS ix_product_submissions_user_status_created "
            "ON product_submissions (user_id, status, created_at)",
        ),
        (
            "submissions barcode status",
            "CREATE INDEX IF NOT EXISTS ix_product_submissions_barcode_status "
            "ON product_submissions (barcode, status)",
        ),
        (
            "subscriptions provider customer",
            "CREATE INDEX IF NOT EXISTS ix_subscriptions_provider_customer "
            "ON subscriptions (provider, provider_customer_id)",
        ),
        (
            "subscriptions provider subscription",
            "CREATE INDEX IF NOT EXISTS ix_subscriptions_provider_subscription "
            "ON subscriptions (provider, provider_subscription_id)",
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

@route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Backend Ce Aleg funcționează.",
        "database": "Supabase Postgres" if database_url else "SQLite local",
    })


@route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "service": "ce-aleg-api",
    })


@route("/version", methods=["GET"])
def get_version():
    return jsonify({
        "ok": True,
        **get_application_version(),
    })


def flask_rule_to_openapi(rule):
    parameters = []

    def replace_parameter(match):
        converter = (match.group(1) or "string").strip()
        name = match.group(2)
        schema_type = "integer" if converter == "int" else "string"
        parameters.append({
            "name": name,
            "in": "path",
            "required": True,
            "schema": {"type": schema_type},
        })
        return "{" + name + "}"

    path = re.sub(r"<(?:([^:>]+):)?([^>]+)>", replace_parameter, rule)
    return path, parameters


@route("/openapi.json", methods=["GET"])
@route("/api/openapi.json", methods=["GET"])
def get_openapi_spec():
    version = get_application_version()["shortCommit"]
    document = build_openapi_spec(
        server_url=request.host_url.rstrip("/"),
        version=version,
        contact_email=CONTACT_EMAIL,
        auth_cookie_name=AUTH_COOKIE_NAME,
        password_min_length=PASSWORD_MIN_LENGTH,
    )
    paths = document["paths"]
    operation_ids = {
        operation.get("operationId")
        for path_item in paths.values()
        for operation in path_item.values()
        if isinstance(operation, dict) and operation.get("operationId")
    }

    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue

        normalized_endpoint = endpoint_name(rule.endpoint)
        path, parameters = flask_rule_to_openapi(rule.rule)
        operations = paths.setdefault(path, {})

        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            method_name = method.lower()

            if method_name in operations:
                continue

            requires_admin = normalized_endpoint in ADMIN_ENDPOINTS
            requires_auth = (
                requires_admin
                or normalized_endpoint in AUTH_ENDPOINTS
                or normalized_endpoint in USER_PATH_ENDPOINTS
            )
            operation_id = f"{normalized_endpoint}_{method_name}"

            if operation_id in operation_ids:
                path_suffix = re.sub(r"[^A-Za-z0-9]+", "_", path).strip("_")
                operation_id = f"{operation_id}_{path_suffix or 'root'}"

            suffix = 2
            unique_operation_id = operation_id
            while unique_operation_id in operation_ids:
                unique_operation_id = f"{operation_id}_{suffix}"
                suffix += 1
            operation_ids.add(unique_operation_id)

            operation = {
                "operationId": unique_operation_id,
                "summary": normalized_endpoint.replace("_", " ").capitalize(),
                "parameters": parameters,
                "responses": {
                    "200": {"description": "Successful response"},
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        },
                    },
                },
            }

            if requires_auth:
                operation["security"] = [{"sessionCookie": []}]
                operation["responses"]["401"] = {"description": "Authentication required"}

            if requires_admin:
                operation["responses"]["403"] = {"description": "Administrator access required"}

            operations[method_name] = operation

    return jsonify(document)


@route("/docs", methods=["GET"])
@route("/api/docs", methods=["GET"])
def api_docs():
    spec_url = "/api/openapi.json" if request.path.startswith("/api/") else "/openapi.json"
    return Response(
        render_swagger_ui(spec_url),
        mimetype="text/html",
    )


@route("/readiness", methods=["GET"])
def get_readiness():
    return jsonify(get_publication_readiness())


@route("/admin/email-test", methods=["POST"])
def send_admin_email_test():
    data = request.get_json(silent=True) or {}
    diagnostics = get_email_configuration_diagnostics()
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
            "diagnostics": diagnostics,
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
        record_user_event(
            g.current_user.id,
            "email_test",
            EMAIL_PROVIDER,
            {
                "sent": False,
                "to": to_email,
                "from": EMAIL_FROM,
                "providerError": provider_error,
            },
            commit=True,
        )
        return jsonify({
            "sent": False,
            "error": f"Emailul de test nu a putut fi trimis. {provider_error}",
            "provider": EMAIL_PROVIDER,
            "from": EMAIL_FROM,
            "to": to_email,
            "diagnostics": get_email_configuration_diagnostics(),
        }), 502

    record_user_event(
        g.current_user.id,
        "email_test",
        EMAIL_PROVIDER,
        {
            "sent": True,
            "to": to_email,
            "from": EMAIL_FROM,
        },
        commit=True,
    )

    return jsonify({
        "sent": True,
        "message": f"Email de test trimis către {to_email}. Verifică inboxul și Spam.",
        "from": EMAIL_FROM,
        "to": to_email,
        "diagnostics": get_email_configuration_diagnostics(),
    })


@route("/admin/users/resend-verification", methods=["POST"])
def admin_resend_email_verification():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()

    if not is_valid_email_address(email):
        return jsonify({
            "code": "invalid_email",
            "error": "Introdu o adresă de email validă.",
        }), 400

    user = User.query.filter(func.lower(User.email) == email).first()

    if not user:
        return jsonify({
            "code": "user_not_found",
            "error": "Nu există niciun cont cu această adresă de email.",
        }), 404

    if bool(user.email_verified):
        return jsonify({
            "code": "email_already_verified",
            "error": "Contul are deja adresa de email confirmată.",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "emailVerified": True,
            },
        }), 409

    if not is_email_configured():
        return jsonify({
            "code": "email_not_configured",
            "error": "Sistemul email nu este configurat complet.",
            "diagnostics": get_email_configuration_diagnostics(),
        }), 503

    sent, _verification_url = send_email_verification_email(user)

    if not sent:
        return jsonify({
            "code": "verification_email_failed",
            "error": "Emailul de confirmare nu a putut fi trimis momentan.",
            "diagnostics": get_email_configuration_diagnostics(),
        }), 502

    record_user_event(
        g.current_user.id,
        "admin_verification_email",
        "admin",
        {
            "targetUserId": user.id,
            "targetEmail": user.email,
            "provider": EMAIL_PROVIDER,
            "sentAt": utcnow().isoformat() + "Z",
        },
        commit=True,
    )

    return jsonify({
        "sent": True,
        "message": f"Emailul de confirmare a fost retrimis către {user.email}.",
        "provider": EMAIL_PROVIDER,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "emailVerified": False,
        },
    })


@route("/ai/status", methods=["GET"])
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


@route("/init-db", methods=["GET"])
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

@route("/register", methods=["POST"])
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
        terms_version=TERMS_VERSION,
        terms_accepted_at=utcnow(),
        age_confirmed_at=utcnow(),
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

    if not verification_sent and EXPOSE_DEV_AUTH_LINKS:
        email_status["devVerificationLink"] = verification_url

    response = jsonify({
        "message": "Cont creat. Verifică emailul ca să activezi contul.",
        "user": user_to_dict(new_user),
        "emailStatus": email_status,
    })
    return response, 201


@route("/auth/verify-email", methods=["POST"])
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
    user.email_verified_at = utcnow()
    user.auth_version = int(user.auth_version or 0) + 1
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


@route("/auth/resend-verification", methods=["POST"])
def resend_email_verification():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Emailul este obligatoriu."}), 400

    if not rate_limit("resend-verification-email", 3, 3600, email):
        return jsonify({
            "message": "Dacă există un cont neconfirmat cu acest email, trimitem un nou link de confirmare.",
        })

    user = User.query.filter_by(email=email).first()
    dev_verification_link = None

    if user and not user.email_verified:
        sent, verification_url = send_email_verification_email(user)
        if not sent and EXPOSE_DEV_AUTH_LINKS:
            dev_verification_link = verification_url

    response = {
        "message": "Dacă există un cont neconfirmat cu acest email, trimitem un nou link de confirmare.",
    }

    if dev_verification_link:
        response["devVerificationLink"] = dev_verification_link

    return jsonify(response)


@route("/login", methods=["POST"])
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


@route("/auth/password-strength", methods=["POST"])
def get_password_strength():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    return jsonify(validate_password_strength(password))


@route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Emailul este obligatoriu."}), 400

    if not rate_limit("forgot-password-email", 3, 3600, email):
        return jsonify({
            "message": "Dacă există un cont cu acest email, vei primi un link pentru resetarea parolei.",
        })

    user = User.query.filter_by(email=email).first()
    dev_reset_link = None

    if user:
        sent, reset_url = send_password_reset_email(user)
        if not sent and EXPOSE_DEV_AUTH_LINKS:
            dev_reset_link = reset_url

    response = {
        "message": "Dacă există un cont cu acest email, vei primi un link pentru resetarea parolei.",
    }

    if dev_reset_link:
        response["devResetLink"] = dev_reset_link

    return jsonify(response)


@route("/reset-password", methods=["POST"])
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
    user.auth_version = int(user.auth_version or 0) + 1
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = utcnow()
    db.session.commit()

    response = jsonify({
        "message": "Parola a fost schimbată. Te-am autentificat automat.",
        "user": user_to_dict(user),
    })
    return set_auth_cookie(response, user)


@route("/account/delete/request", methods=["POST"])
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

    if not sent and EXPOSE_DEV_AUTH_LINKS:
        response["devDeletionLink"] = deletion_url
        response["message"] = (
            "Emailul nu a putut fi trimis în mediul local. Folosește linkul de test pentru confirmare."
        )

    return jsonify(response)


@route("/account/privacy", methods=["GET"])
def get_account_privacy():
    user = g.current_user
    return jsonify({
        "termsVersion": user.terms_version,
        "termsAcceptedAt": admin_iso(user.terms_accepted_at),
        "ageConfirmedAt": admin_iso(user.age_confirmed_at),
        "analyticsConsent": user.analytics_consent,
        "analyticsConsentAt": admin_iso(user.analytics_consent_at),
        "processingRestricted": bool(user.processing_restricted),
        "processingRestrictedAt": admin_iso(user.processing_restricted_at),
    })


@route("/account/consent", methods=["POST"])
def update_account_consent():
    data = request.get_json(silent=True) or {}

    if not isinstance(data.get("analytics"), bool):
        return jsonify({"error": "Valoarea analytics trebuie să fie true sau false."}), 400

    user = g.current_user
    user.analytics_consent = data["analytics"]
    user.analytics_consent_at = utcnow()
    record_user_event(
        user.id,
        "privacy_consent",
        "account",
        {"analytics": bool(data["analytics"]), "termsVersion": TERMS_VERSION},
    )
    db.session.commit()
    return jsonify({
        "message": "Preferința de consimțământ a fost salvată.",
        "analyticsConsent": user.analytics_consent,
        "analyticsConsentAt": admin_iso(user.analytics_consent_at),
    })


@route("/account/delete/confirm", methods=["POST"])
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


@route("/auth/me", methods=["GET"])
def get_authenticated_user():
    user = get_current_user()

    if not user:
        return jsonify({"error": "Autentificare necesara."}), 401

    return jsonify({"user": user_to_dict(user)})


def build_account_export(user):
    subscription = Subscription.query.filter_by(user_id=user.id).first()
    return {
        "exportedAt": utcnow().isoformat() + "Z",
        "formatVersion": "1.0",
        "account": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "emailVerified": bool(user.email_verified),
            "createdAt": user.created_at.isoformat() + "Z" if user.created_at else None,
            "inviteCode": user.invite_code,
            "referredByUserId": user.referred_by_user_id,
            "processingRestricted": bool(user.processing_restricted),
            "processingRestrictedAt": (
                user.processing_restricted_at.isoformat() + "Z"
                if user.processing_restricted_at else None
            ),
            "processingRestrictionReason": user.processing_restriction_reason,
        },
        "subscription": subscription_to_billing_dict(subscription) if subscription else None,
        "familyProfiles": [
            {
                "id": item.id,
                "name": item.name,
                "color": item.color,
                "avatar": item.avatar,
                "isPrimary": bool(item.is_primary),
                "createdAt": item.created_at.isoformat() + "Z",
            }
            for item in FamilyProfile.query.filter_by(user_id=user.id).all()
        ],
        "cart": [cart_item_to_dict(item) for item in CartItem.query.filter_by(user_id=user.id).all()],
        "favorites": [favorite_item_to_dict(item) for item in Favorite.query.filter_by(user_id=user.id).all()],
        "scanHistory": [scan_history_item_to_dict(item) for item in ScanHistory.query.filter_by(user_id=user.id).all()],
        "productSubmissions": [
            product_submission_to_dict(item)
            for item in ProductSubmission.query.filter_by(user_id=user.id).all()
        ],
        "priceObservations": [
            {
                "id": item.id,
                "barcode": item.product_barcode,
                "store": item.store,
                "price": item.price,
                "currency": item.currency,
                "observedAt": item.observed_at.isoformat() + "Z",
            }
            for item in PriceObservation.query.filter_by(user_id=user.id).all()
        ],
        "searches": [
            {
                "id": item.id,
                "query": item.search_text,
                "store": item.store,
                "resultCount": item.result_count,
                "source": item.source,
                "createdAt": item.created_at.isoformat() + "Z",
            }
            for item in SearchEvent.query.filter_by(user_id=user.id).all()
        ],
        "usageEvents": [
            {
                "id": item.id,
                "type": item.event_type,
                "source": item.source,
                "metadata": parse_usage_metadata(item),
                "createdAt": item.created_at.isoformat() + "Z",
            }
            for item in UsageEvent.query.filter_by(user_id=user.id).all()
        ],
        "consents": [
            {
                "type": item.consent_type,
                "granted": bool(item.granted),
                "policyVersion": item.policy_version,
                "source": item.source,
                "createdAt": item.created_at.isoformat() + "Z",
            }
            for item in ConsentRecord.query.filter_by(user_id=user.id).all()
        ],
    }


@route("/account/data", methods=["GET"])
def get_account_data():
    payload = build_account_export(g.current_user)
    return jsonify({
        "account": payload["account"],
        "subscription": payload["subscription"],
        "counts": {
            key: len(value)
            for key, value in payload.items()
            if isinstance(value, list)
        },
        "exportUrl": "/account/export",
    })


@route("/account/export", methods=["GET"])
@route("/account/data-export", methods=["GET"])
def export_account_data():
    payload = build_account_export(g.current_user)
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="ce-aleg-data-export-{g.current_user.id}.json"'
            ),
        },
    )


@route("/account/restriction", methods=["POST"])
def update_processing_restriction():
    data = request.get_json(silent=True) or {}
    restricted = data.get("restricted", True)

    if not isinstance(restricted, bool):
        return jsonify({"error": "Câmpul restricted trebuie să fie boolean."}), 400

    reason = str(data.get("reason") or "").strip()
    if len(reason) > 500:
        return jsonify({"error": "Motivul poate avea maximum 500 de caractere."}), 400

    user = g.current_user
    user.processing_restricted = restricted
    user.processing_restricted_at = utcnow() if restricted else None
    user.processing_restriction_reason = reason or None if restricted else None
    record_user_event(
        user.id,
        "processing_restriction_changed",
        "privacy",
        {"restricted": restricted, "reason": reason[:500]},
    )
    db.session.commit()
    return jsonify({
        "message": (
            "Prelucrarea datelor a fost restricționată."
            if restricted
            else "Restricția de prelucrare a fost ridicată."
        ),
        "restricted": restricted,
        "processingRestricted": restricted,
    })


@route("/privacy/consent", methods=["POST"])
def record_privacy_consent():
    data = request.get_json(silent=True) or {}
    consent_type = str(data.get("type") or "").strip().lower()
    granted = data.get("granted")
    allowed_types = {"analytics", "marketing", "functional", "privacy", "terms"}

    if consent_type not in allowed_types or not isinstance(granted, bool):
        return jsonify({"error": "Consimțământ invalid."}), 400

    policy_version = str(data.get("policyVersion") or "2026-07").strip()[:40]
    identity_hash = hmac.new(
        app.config["AUTH_SECRET"].encode("utf-8"),
        (request.remote_addr or "unknown").encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    record = ConsentRecord(
        user_id=g.current_user.id,
        consent_type=consent_type,
        granted=granted,
        policy_version=policy_version,
        source=str(data.get("source") or "web").strip()[:80] or "web",
        request_identity_hash=identity_hash,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"recorded": True, "consentId": record.id}), 201


@route("/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Deconectare reusita."})
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@app.after_request
def persist_login_session(response):
    if endpoint_name(request.endpoint) == "login" and response.status_code < 300:
        data = response.get_json(silent=True) or {}
        user_id = (data.get("user") or {}).get("id")
        user = db.session.get(User, user_id) if user_id else None

        if user:
            set_auth_cookie(response, user)

    return response

@route("/users", methods=["GET"])
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


@route("/billing/status", methods=["GET"])
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


@route("/dashboard/summary", methods=["GET"])
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


@route("/family/profiles", methods=["GET"])
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


@route("/family/profiles", methods=["POST"])
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


@route("/family/profiles/<int:profile_id>", methods=["PATCH"])
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


@route("/family/profiles/<int:profile_id>", methods=["DELETE"])
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


@route("/billing/checkout", methods=["POST"])
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
            idempotency_key = build_stripe_idempotency_key(
                "subscription-checkout",
                user.id,
                plan,
                billing_interval,
                price_id,
            )
            checkout_session = create_checkout_session_with_stale_customer_retry(
                checkout_params,
                subscription,
                user,
                idempotency_key,
            )
        except Exception as error:
            app.logger.warning("Stripe checkout session failed: %s", error)
            record_user_event(
                user.id,
                "payment_error",
                "subscription_checkout",
                {
                    "plan": plan,
                    "billingInterval": billing_interval,
                    "priceEnv": price_env_name,
                    "error": str(error)[:500],
                },
                commit=True,
            )
            send_admin_alert(
                "Eroare checkout abonament",
                "Stripe nu a putut porni o plată pentru abonament.",
                [
                    f"Utilizator: {user.email}",
                    f"Plan: {plan}",
                    f"Perioadă: {billing_interval}",
                    f"Price env: {price_env_name}",
                    f"Eroare: {str(error)[:300]}",
                ],
                alert_key="subscription_checkout_error",
                min_interval_seconds=900,
            )
            return jsonify({
                "error": "Plata nu a putut fi pornita momentan.",
                "code": "stripe_checkout_failed",
            }), 502

        record_user_event(
            user.id,
            "payment_checkout_started",
            "subscription_checkout",
            {
                "plan": plan,
                "billingInterval": billing_interval,
                "sessionId": checkout_session.id,
                "priceEnv": price_env_name,
            },
            commit=True,
        )

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


@route("/billing/portal", methods=["POST"])
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
            idempotency_key=build_stripe_idempotency_key(
                "billing-portal",
                user.id,
                subscription.provider_customer_id,
                window_seconds=60,
            ),
        )
    except Exception as error:
        app.logger.warning("Stripe billing portal failed: %s", error)
        return jsonify({
            "error": "Portalul de abonament nu poate fi deschis momentan.",
            "code": "stripe_portal_failed",
        }), 502

    return jsonify({"portalUrl": portal_session.url})


@route("/billing/stripe/webhook", methods=["POST"])
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
    event_id = str(event.get("id") or "").strip()
    event_object = (event.get("data") or {}).get("object") or {}

    if not event_id:
        return jsonify({"error": "Evenimentul Stripe nu are identificator."}), 400

    webhook_record = StripeWebhookEvent.query.filter_by(
        provider_event_id=event_id,
    ).first()
    retry_before = utcnow() - timedelta(minutes=10)

    if webhook_record and webhook_record.status == "processed":
        return jsonify({"received": True, "duplicate": True})

    if (
        webhook_record
        and webhook_record.status == "processing"
        and webhook_record.updated_at > retry_before
    ):
        return jsonify({"received": True, "processing": True}), 202

    if webhook_record:
        webhook_record.status = "processing"
        webhook_record.event_type = event_type or "unknown"
        webhook_record.attempts = int(webhook_record.attempts or 0) + 1
        webhook_record.last_error = None
        webhook_record.updated_at = utcnow()
    else:
        webhook_record = StripeWebhookEvent(
            provider_event_id=event_id,
            event_type=event_type or "unknown",
            status="processing",
            attempts=1,
            updated_at=utcnow(),
        )
        db.session.add(webhook_record)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"received": True, "duplicate": True}), 202

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
    except Exception as error:
        db.session.rollback()
        failed_record = StripeWebhookEvent.query.filter_by(
            provider_event_id=event_id,
        ).first()
        if failed_record:
            failed_record.status = "failed"
            failed_record.last_error = str(error)[:2000]
            failed_record.updated_at = utcnow()
            db.session.commit()
        app.logger.exception(
            "Stripe webhook handler failed for event %s",
            event_type,
        )
        send_admin_alert(
            "Eroare critică webhook Stripe",
            "Un eveniment Stripe valid nu a putut fi procesat.",
            [
                f"Event ID: {event_id}",
                f"Tip: {event_type or 'unknown'}",
                f"Încercare: {failed_record.attempts if failed_record else 1}",
                f"Eroare: {str(error)[:500]}",
            ],
            alert_key=f"stripe_webhook_failed:{event_type or 'unknown'}",
            min_interval_seconds=300,
            severity="error",
        )
        return jsonify({
            "code": "stripe_webhook_handler_failed",
            "error": "Evenimentul Stripe nu a putut fi procesat momentan.",
        }), 500

    processed_record = StripeWebhookEvent.query.filter_by(
        provider_event_id=event_id,
    ).first()
    if processed_record:
        processed_record.status = "processed"
        processed_record.processed_at = utcnow()
        processed_record.updated_at = utcnow()
        processed_record.last_error = None
        db.session.commit()

    return jsonify({"received": True})


# =========================
# Gamification
# =========================

@route("/gamification/coin-packs", methods=["GET"])
def get_cecoin_packs():
    return jsonify({"coinPacks": get_public_cecoin_packs()})


@route("/gamification/summary", methods=["GET"])
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


@route("/gamification/leaderboard", methods=["GET"])
def get_gamification_leaderboard():
    try:
        period = str(request.args.get("period") or "weekly").strip().lower()
        since = get_week_start() if period == "weekly" else None
        return jsonify({
            "period": period,
            "leaderboard": build_user_leaderboard(
                g.current_user.id,
                since=since,
            ),
        })
    except Exception:
        app.logger.exception("Gamification leaderboard failed")
        return jsonify({
            "code": "gamification_leaderboard_failed",
            "error": "Clasamentul nu s-a putut încărca momentan.",
        }), 500


@route("/gamification/claim", methods=["POST"])
def claim_gamification_mission():
    data = request.get_json(silent=True) or {}
    mission_id = str(data.get("missionId") or "").strip()
    locked_user = lock_user_for_update(g.current_user.id)

    if not locked_user:
        return jsonify({"error": "Contul nu mai este disponibil."}), 404

    missions = build_mission_statuses(locked_user.id)
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
    claim_scope = get_day_start().date().isoformat() if mission.get("daily") else "once"
    idempotency_key = f"mission:{locked_user.id}:{mission_id}:{claim_scope}"

    if usage_event_by_idempotency_key(idempotency_key):
        return jsonify({
            "error": "Recompensa a fost deja revendicată.",
            "summary": get_gamification_summary_for_user(locked_user),
        }), 409

    if reward.get("bonusScans"):
        add_bonus_scan_credits(
            locked_user,
            int(reward.get("bonusScans") or 0),
            "mission_reward",
            {"missionId": mission_id},
        )

    if reward.get("bonusDays"):
        extend_bonus_unlimited(
            locked_user,
            int(reward.get("bonusDays") or 0),
            "mission_reward",
            {"missionId": mission_id},
        )

    db.session.add(
        UsageEvent(
            user_id=locked_user.id,
            event_type="mission_claim",
            source=mission_id,
            idempotency_key=idempotency_key,
            metadata_json=json.dumps({
                "reward": reward,
                "seriesId": mission.get("seriesId"),
                "daily": bool(mission.get("daily")),
                "current": mission.get("current"),
                "target": mission.get("target"),
                "claimedAt": utcnow().isoformat() + "Z",
                "dayStart": (
                    get_day_start().isoformat() + "Z"
                    if mission.get("daily")
                    else None
                ),
            }),
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Recompensa a fost deja revendicată.",
            "summary": get_gamification_summary_for_user(locked_user),
        }), 409
    clear_leaderboard_cache()

    return jsonify({
        "message": "Recompensă revendicată.",
        "reward": reward,
        "summary": get_gamification_summary_for_user(locked_user),
    })


@route("/gamification/redeem", methods=["POST"])
def redeem_cecoin_reward():
    data = request.get_json(silent=True) or {}
    item_id = str(data.get("itemId") or "").strip()
    item = next((entry for entry in CECOIN_SHOP_ITEMS if entry["id"] == item_id), None)

    if not item:
        return jsonify({"error": "Recompensă invalidă."}), 400

    locked_user = lock_user_for_update(g.current_user.id)

    if not locked_user:
        return jsonify({"error": "Contul nu mai este disponibil."}), 404

    current_coins = calculate_user_coins(locked_user.id)
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
            locked_user,
            int(item["bonusScans"]),
            "cecoin_shop",
            {"itemId": item_id},
        )

    if item.get("bonusDays"):
        extend_bonus_unlimited(
            locked_user,
            int(item["bonusDays"]),
            "cecoin_shop",
            {"itemId": item_id},
        )

    db.session.add(
        UsageEvent(
            user_id=locked_user.id,
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
    send_cecoin_reward_email(locked_user, item)

    return jsonify({
        "message": "Recompensa a fost activată.",
        "item": item,
        "summary": get_gamification_summary_for_user(locked_user),
    })


@route("/gamification/coin-checkout", methods=["POST"])
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
        idempotency_key = build_stripe_idempotency_key(
            "cecoins-checkout",
            user.id,
            pack["id"],
            price_id,
        )
        checkout_session = create_checkout_session_with_stale_customer_retry(
            checkout_params,
            subscription,
            user,
            idempotency_key,
        )
    except Exception as error:
        app.logger.warning("Stripe CeCoins checkout failed: %s", error)
        detail = str(error).strip()
        message = "Cumpărarea de CeCoins nu a putut fi pornită momentan."

        if detail:
            message = f"{message} Detalii Stripe: {detail[:280]}"

        record_user_event(
            user.id,
            "payment_error",
            "cecoins_checkout",
            {
                "packId": pack["id"],
                "coins": int(pack["coins"]),
                "priceEnv": pack["priceEnv"],
                "error": detail[:500],
            },
            commit=True,
        )
        send_admin_alert(
            "Eroare checkout CeCoins",
            "Stripe nu a putut porni o plată pentru CeCoins.",
            [
                f"Utilizator: {user.email}",
                f"Pachet: {pack['id']}",
                f"CeCoins: {pack['coins']}",
                f"Price env: {pack['priceEnv']}",
                f"Eroare: {detail[:300]}",
            ],
            alert_key="cecoins_checkout_error",
            min_interval_seconds=900,
        )

        return jsonify({
            "error": message,
            "code": "cecoins_checkout_failed",
        }), 502

    record_user_event(
        user.id,
        "payment_checkout_started",
        "cecoins_checkout",
        {
            "packId": pack["id"],
            "coins": int(pack["coins"]),
            "sessionId": checkout_session.id,
            "priceEnv": pack["priceEnv"],
        },
        commit=True,
    )

    return jsonify({
        "mode": "stripe",
        "pack": pack["id"],
        "checkoutUrl": checkout_session.url,
        "sessionId": checkout_session.id,
    })


@route("/gamification/coin-checkout/sync", methods=["POST"])
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

def admin_iso(value):
    return value.isoformat() + "Z" if value else None


def get_usage_event_user_email(event):
    user = db.session.get(User, event.user_id) if event and event.user_id else None
    return user.email if user else "cont șters"


def usage_event_to_admin_dict(event):
    metadata = parse_usage_metadata(event)
    return {
        "id": event.id,
        "type": event.event_type,
        "source": event.source,
        "userId": event.user_id,
        "userEmail": get_usage_event_user_email(event),
        "createdAt": admin_iso(event.created_at),
        "metadata": metadata,
    }


def search_event_to_admin_dict(event):
    return {
        "id": event.id,
        "query": event.search_text,
        "store": event.store or "Fără magazin ales",
        "source": event.source or "search",
        "resultCount": int(event.result_count or 0),
        "createdAt": admin_iso(event.created_at),
    }


def csv_response(filename, headers, rows):
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()

    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    for row in rows:
        writer.writerow({header: safe_cell(row.get(header, "")) for header in headers})

    return Response(
        buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


UNCATEGORIZED_CATEGORY_TERMS = [
    "altele",
    "other",
    "general",
    "categorie neconfirmata",
    "categorie neconfirmată",
    "neconfirmata",
    "neconfirmată",
]


def uncategorized_product_filter():
    return or_(
        Product.category.is_(None),
        *[
            Product.category.ilike(term)
            for term in UNCATEGORIZED_CATEGORY_TERMS
        ],
    )


def count_uncategorized_products():
    return Product.query.filter(uncategorized_product_filter()).count()


def is_placeholder_catalog_product_name(name):
    return bool(re.fullmatch(r"produs [0-9]{6,}", normalize_search_text(name)))


def get_catalog_quality_snapshot():
    return build_catalog_quality_report(
        db.session,
        Product,
        uncategorized_terms=UNCATEGORIZED_CATEGORY_TERMS,
    )


def public_catalog_stats_cache_is_fresh():
    return (
        PUBLIC_CATALOG_STATS_CACHE.get("data") is not None
        and PUBLIC_CATALOG_STATS_CACHE.get("expires_at", 0) > time.time()
    )


def public_contributor_name(name, rank):
    clean_name = str(name or "").strip()

    if not clean_name or "@" in clean_name:
        return f"Contribuitor #{rank}"

    first_name = clean_name.split()[0].strip()
    return first_name[:32] or f"Contribuitor #{rank}"


def build_public_catalog_romania_stats():
    now = utcnow()
    since = now - timedelta(days=30)
    quality = get_catalog_quality_snapshot()

    category_rows = (
        db.session.query(
            Product.category.label("category"),
            func.count(Product.id).label("count"),
        )
        .filter(Product.category.isnot(None), Product.category != "")
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
        .limit(8)
        .all()
    )
    store_rows = (
        db.session.query(
            Product.store.label("store"),
            func.count(Product.id).label("count"),
        )
        .filter(Product.store.isnot(None), Product.store != "")
        .group_by(Product.store)
        .order_by(func.count(Product.id).desc())
        .limit(8)
        .all()
    )
    missing_store_rows = (
        db.session.query(
            SearchEvent.store.label("store"),
            func.count(SearchEvent.id).label("count"),
            func.max(SearchEvent.created_at).label("last_seen"),
        )
        .filter(SearchEvent.created_at >= since, SearchEvent.result_count == 0)
        .group_by(SearchEvent.store)
        .order_by(func.count(SearchEvent.id).desc())
        .limit(6)
        .all()
    )
    contributor_rows = (
        db.session.query(
            User.name.label("name"),
            func.count(ProductSubmission.id).label("count"),
        )
        .join(User, User.id == ProductSubmission.user_id)
        .filter(ProductSubmission.status == "approved")
        .group_by(User.id, User.name)
        .order_by(func.count(ProductSubmission.id).desc())
        .limit(6)
        .all()
    )
    recent_submissions = (
        ProductSubmission.query.filter(ProductSubmission.status == "approved")
        .order_by(ProductSubmission.created_at.desc())
        .limit(6)
        .all()
    )
    last_approved_submission_at = (
        db.session.query(func.max(ProductSubmission.created_at))
        .filter(ProductSubmission.status == "approved")
        .scalar()
    )

    return {
        **quality,
        "approvedSubmissions": ProductSubmission.query.filter_by(status="approved").count(),
        "pendingSubmissions": ProductSubmission.query.filter(
            ProductSubmission.status != "approved"
        ).count(),
        "contributors": int(
            db.session.query(func.count(func.distinct(ProductSubmission.user_id)))
            .filter(ProductSubmission.status == "approved")
            .scalar()
            or 0
        ),
        "searchesLast30Days": SearchEvent.query.filter(SearchEvent.created_at >= since).count(),
        "missingProductsLast30Days": SearchEvent.query.filter(
            SearchEvent.created_at >= since,
            SearchEvent.result_count == 0,
        ).count(),
        "lastApprovedSubmissionAt": admin_iso(last_approved_submission_at),
        "generatedAt": admin_iso(now),
        "categories": [
            {"name": row.category or "Altele", "count": int(row.count or 0)}
            for row in category_rows
        ],
        "stores": [
            {"name": row.store or "Fără magazin ales", "count": int(row.count or 0)}
            for row in store_rows
        ],
        "missingByStore": [
            {
                "name": row.store or "Fără magazin ales",
                "count": int(row.count or 0),
                "lastSeen": admin_iso(row.last_seen),
            }
            for row in missing_store_rows
        ],
        "topContributors": [
            {
                "rank": index + 1,
                "name": public_contributor_name(row.name, index + 1),
                "approvedSubmissions": int(row.count or 0),
            }
            for index, row in enumerate(contributor_rows)
        ],
        "recentCommunityProducts": [
            {
                "name": item.product_name,
                "brand": item.brand,
                "store": item.store,
                "category": item.category,
                "createdAt": admin_iso(item.created_at),
            }
            for item in recent_submissions
        ],
    }


@route("/catalog/romania/stats", methods=["GET"])
def get_public_catalog_romania_stats():
    if public_catalog_stats_cache_is_fresh():
        return jsonify(PUBLIC_CATALOG_STATS_CACHE["data"])

    data = build_public_catalog_romania_stats()
    PUBLIC_CATALOG_STATS_CACHE["data"] = data
    PUBLIC_CATALOG_STATS_CACHE["expires_at"] = time.time() + PUBLIC_CATALOG_STATS_CACHE_TTL
    return jsonify(data)


def recategorize_catalog_products(
    limit=300,
    apply_changes=False,
    include_all=False,
    min_id=None,
    category=None,
):
    safe_limit = max(1, min(int(limit or 300), 1000))
    query = Product.query.order_by(Product.id.asc())
    safe_min_id = None
    category_filter = str(category or "").strip()

    if min_id is not None:
        try:
            safe_min_id = max(1, int(min_id))
        except (TypeError, ValueError):
            safe_min_id = None

    if safe_min_id:
        query = query.filter(Product.id >= safe_min_id)

    if category_filter:
        query = query.filter(Product.category == category_filter)

    if not include_all:
        query = query.filter(uncategorized_product_filter())

    products = query.limit(safe_limit).all()
    last_scanned_id = products[-1].id if products else None
    next_min_id = None
    has_more = False

    if last_scanned_id:
        has_more = bool(
            query.filter(Product.id > last_scanned_id)
            .with_entities(Product.id)
            .first()
        )
        if has_more:
            next_min_id = last_scanned_id + 1

    changes = []

    for product in products:
        product_data = product_to_dict(product)
        old_category = product.category or "Altele"
        new_category = infer_catalog_category(product_data)
        reset_placeholder_category = (
            is_placeholder_catalog_product_name(product.name)
            and is_repairable_catalog_category(old_category)
        )

        if reset_placeholder_category:
            new_category = "Altele"
        elif not should_update_reported_product_category(old_category, new_category):
            continue

        if catalog_category_key(old_category) == catalog_category_key(new_category):
            continue

        changes.append({
            "id": product.id,
            "name": product.name,
            "barcode": product.barcode,
            "oldCategory": old_category,
            "newCategory": new_category,
        })

        if apply_changes:
            product.category = new_category[:100]
            product.score = calculate_product_score(
                product.category,
                product.calories,
                product.protein,
                product.sugar,
                product.fat,
                product.ingredients,
            )
            product.tag = generate_product_tag(
                product.category,
                product.calories,
                product.protein,
                product.sugar,
                product.fat,
                product.ingredients,
            )
            product.reason = generate_product_reason(
                product.category,
                product.calories,
                product.protein,
                product.sugar,
                product.fat,
                product.ingredients,
            )

    if apply_changes and changes:
        db.session.commit()

    return {
        "scanned": len(products),
        "changed": len(changes),
        "applied": bool(apply_changes),
        "minId": safe_min_id,
        "lastScannedId": last_scanned_id,
        "nextMinId": next_min_id,
        "hasMore": has_more,
        "category": category_filter or None,
        "changes": changes[:120],
    }


@route("/admin/monitoring", methods=["GET"])
def get_admin_monitoring():
    days = request.args.get("days", default=7, type=int)
    limit = request.args.get("limit", default=16, type=int)
    safe_days = max(1, min(days or 7, 90))
    safe_limit = max(5, min(limit or 16, 50))
    since = utcnow() - timedelta(days=safe_days)
    readiness = get_publication_readiness()

    issue_filter = or_(
        SearchEvent.result_count == 0,
        SearchEvent.source == "alternatives_low",
    )
    issue_query = SearchEvent.query.filter(
        SearchEvent.created_at >= since,
        issue_filter,
    )

    issue_source_rows = (
        db.session.query(
            SearchEvent.source.label("source"),
            func.count(SearchEvent.id).label("count"),
            func.max(SearchEvent.created_at).label("last_seen"),
        )
        .filter(
            SearchEvent.created_at >= since,
            issue_filter,
        )
        .group_by(SearchEvent.source)
        .order_by(func.count(SearchEvent.id).desc())
        .all()
    )

    recent_issue_events = issue_query.order_by(
        SearchEvent.created_at.desc()
    ).limit(safe_limit).all()

    payment_event_types = [
        "payment_checkout_started",
        "payment_error",
        "cecoin_purchase",
    ]
    payment_events = UsageEvent.query.filter(
        UsageEvent.event_type.in_(payment_event_types),
        UsageEvent.created_at >= since,
    ).order_by(UsageEvent.created_at.desc()).limit(safe_limit).all()

    alternative_report_events = UsageEvent.query.filter(
        UsageEvent.event_type == "alternative_report",
        UsageEvent.created_at >= since,
    ).order_by(UsageEvent.created_at.desc()).limit(safe_limit).all()

    product_report_events = UsageEvent.query.filter(
        UsageEvent.event_type == "product_report",
        UsageEvent.created_at >= since,
    ).order_by(UsageEvent.created_at.desc()).limit(safe_limit).all()

    cecoin_purchase_events = UsageEvent.query.filter(
        UsageEvent.event_type == "cecoin_purchase",
        UsageEvent.created_at >= since,
    ).all()
    cecoin_purchase_total = 0
    cecoin_revenue_events = 0

    for event in cecoin_purchase_events:
        metadata = parse_usage_metadata(event)
        cecoin_purchase_total += int(metadata.get("coins") or 0)
        cecoin_revenue_events += 1

    email_test_events = UsageEvent.query.filter(
        UsageEvent.event_type == "email_test",
        UsageEvent.created_at >= since,
    ).order_by(UsageEvent.created_at.desc()).limit(safe_limit).all()

    active_subscriptions = Subscription.query.filter(
        Subscription.plan.in_(["pro", "family"]),
        Subscription.status == "active",
    ).count()
    recent_subscription_updates = Subscription.query.filter(
        Subscription.updated_at >= since,
    ).order_by(Subscription.updated_at.desc()).limit(safe_limit).all()

    return jsonify({
        "windowDays": safe_days,
        "generatedAt": admin_iso(utcnow()),
        "backend": {
            "ready": bool(readiness.get("ready")),
            "environment": readiness.get("environment"),
            "database": readiness.get("database"),
            "version": get_application_version(),
            "blockers": readiness.get("blockers", []),
            "warnings": readiness.get("warnings", []),
            "renderNote": "Dacă Render anunță health check timeout, verifică Logs și Metrics pentru cold start, conexiuni DB sau request-uri lente.",
        },
        "cache": {
            "distributed": bool(REDIS_URL),
            "connected": get_redis_client() is not None,
            **CACHE_METRICS,
            "hitRate": round(
                CACHE_METRICS["hits"]
                / max(1, CACHE_METRICS["hits"] + CACHE_METRICS["misses"]),
                4,
            ),
        },
        "scanIssues": {
            "total": issue_query.count(),
            "barcodeNotFound": SearchEvent.query.filter(
                SearchEvent.created_at >= since,
                SearchEvent.source == "barcode_not_found",
            ).count(),
            "analysisNotFound": SearchEvent.query.filter(
                SearchEvent.created_at >= since,
                SearchEvent.source == "analysis_not_found",
            ).count(),
            "alternativesLow": SearchEvent.query.filter(
                SearchEvent.created_at >= since,
                SearchEvent.source == "alternatives_low",
            ).count(),
            "alternativeReports": UsageEvent.query.filter(
                UsageEvent.event_type == "alternative_report",
                UsageEvent.created_at >= since,
            ).count(),
            "productReports": UsageEvent.query.filter(
                UsageEvent.event_type == "product_report",
                UsageEvent.created_at >= since,
            ).count(),
            "bySource": [
                {
                    "source": row.source or "search",
                    "count": int(row.count or 0),
                    "lastSeen": admin_iso(row.last_seen),
                }
                for row in issue_source_rows
            ],
            "recent": [search_event_to_admin_dict(event) for event in recent_issue_events],
            "reportedAlternatives": [
                usage_event_to_admin_dict(event) for event in alternative_report_events
            ],
            "reportedProducts": [
                usage_event_to_admin_dict(event) for event in product_report_events
            ],
        },
        "payments": {
            "activeSubscriptions": active_subscriptions,
            "proUsers": Subscription.query.filter_by(plan="pro", status="active").count(),
            "familyUsers": Subscription.query.filter_by(plan="family", status="active").count(),
            "checkoutErrors": UsageEvent.query.filter(
                UsageEvent.event_type == "payment_error",
                UsageEvent.created_at >= since,
            ).count(),
            "checkoutStarted": UsageEvent.query.filter(
                UsageEvent.event_type == "payment_checkout_started",
                UsageEvent.created_at >= since,
            ).count(),
            "cecoinPurchases": cecoin_revenue_events,
            "cecoinsSold": cecoin_purchase_total,
            "recentEvents": [usage_event_to_admin_dict(event) for event in payment_events],
            "recentSubscriptions": [
                {
                    "userId": subscription.user_id,
                    "userEmail": subscription.user.email if subscription.user else "cont șters",
                    "plan": subscription.plan,
                    "status": subscription.status,
                    "provider": subscription.provider,
                    "currentPeriodEnd": admin_iso(subscription.current_period_end),
                    "updatedAt": admin_iso(subscription.updated_at),
                }
                for subscription in recent_subscription_updates
            ],
        },
        "email": {
            "configured": is_email_configured(),
            "provider": EMAIL_PROVIDER,
            "from": EMAIL_FROM,
            "replyTo": get_email_reply_to() or EMAIL_FROM,
            "lastProviderError": LAST_EMAIL_PROVIDER_ERROR,
            "diagnostics": get_email_configuration_diagnostics(),
            "testCount": UsageEvent.query.filter(
                UsageEvent.event_type == "email_test",
                UsageEvent.created_at >= since,
            ).count(),
            "missionDigests": UsageEvent.query.filter(
                UsageEvent.event_type == MISSION_DIGEST_EVENT_TYPE,
                UsageEvent.created_at >= since,
            ).count(),
            "recentTests": [usage_event_to_admin_dict(event) for event in email_test_events],
        },
        "catalog": {
            **get_catalog_quality_snapshot(),
            "pendingSubmissions": ProductSubmission.query.filter(
                ProductSubmission.status != "approved"
            ).count(),
            "priceObservations": PriceObservation.query.count(),
            "searches": SearchEvent.query.filter(SearchEvent.created_at >= since).count(),
        },
    })


@route("/admin/export/search-misses.csv", methods=["GET"])
def export_admin_search_misses():
    days = request.args.get("days", default=30, type=int)
    safe_days = max(1, min(days or 30, 180))
    since = utcnow() - timedelta(days=safe_days)
    rows = (
        db.session.query(
            SearchEvent.search_text.label("query"),
            SearchEvent.store.label("store"),
            SearchEvent.source.label("source"),
            func.count(SearchEvent.id).label("count"),
            func.max(SearchEvent.created_at).label("last_seen"),
        )
        .filter(SearchEvent.created_at >= since)
        .filter(
            or_(
                SearchEvent.result_count == 0,
                SearchEvent.source.in_(["alternatives_low", "alternative_report"]),
            )
        )
        .group_by(SearchEvent.search_text, SearchEvent.store, SearchEvent.source)
        .order_by(func.count(SearchEvent.id).desc(), func.max(SearchEvent.created_at).desc())
        .limit(2000)
        .all()
    )

    return csv_response(
        "ce-aleg-search-misses.csv",
        ["query", "store", "source", "count", "lastSeen"],
        [
            {
                "query": row.query,
                "store": row.store or "Fără magazin ales",
                "source": row.source or "search",
                "count": int(row.count or 0),
                "lastSeen": admin_iso(row.last_seen),
            }
            for row in rows
        ],
    )


@route("/admin/export/alternative-reports.csv", methods=["GET"])
def export_admin_alternative_reports():
    days = request.args.get("days", default=30, type=int)
    safe_days = max(1, min(days or 30, 180))
    since = utcnow() - timedelta(days=safe_days)
    events = UsageEvent.query.filter(
        UsageEvent.event_type == "alternative_report",
        UsageEvent.created_at >= since,
    ).order_by(UsageEvent.created_at.desc()).limit(2000).all()

    rows = []

    for event in events:
        metadata = parse_usage_metadata(event)
        scanned_product = metadata.get("scannedProduct") or {}
        alternative_product = metadata.get("alternativeProduct") or {}
        rows.append({
            "createdAt": admin_iso(event.created_at),
            "userEmail": get_usage_event_user_email(event),
            "store": metadata.get("store") or "",
            "request": metadata.get("request") or "",
            "reason": metadata.get("reason") or "",
            "scannedProduct": scanned_product.get("name") or metadata.get("scannedProductName") or "",
            "scannedBarcode": scanned_product.get("barcode") or "",
            "alternativeProduct": alternative_product.get("name") or "",
            "alternativeBarcode": alternative_product.get("barcode") or "",
            "alternativeSource": alternative_product.get("source") or "",
        })

    return csv_response(
        "ce-aleg-alternative-reports.csv",
        [
            "createdAt",
            "userEmail",
            "store",
            "request",
            "reason",
            "scannedProduct",
            "scannedBarcode",
            "alternativeProduct",
            "alternativeBarcode",
            "alternativeSource",
        ],
        rows,
    )


@route("/admin/export/payment-events.csv", methods=["GET"])
def export_admin_payment_events():
    days = request.args.get("days", default=30, type=int)
    safe_days = max(1, min(days or 30, 180))
    since = utcnow() - timedelta(days=safe_days)
    events = UsageEvent.query.filter(
        UsageEvent.event_type.in_([
            "payment_checkout_started",
            "payment_error",
            "cecoin_purchase",
            "cecoin_spend",
        ]),
        UsageEvent.created_at >= since,
    ).order_by(UsageEvent.created_at.desc()).limit(2000).all()

    rows = []

    for event in events:
        metadata = parse_usage_metadata(event)
        rows.append({
            "createdAt": admin_iso(event.created_at),
            "userEmail": get_usage_event_user_email(event),
            "type": event.event_type,
            "source": event.source or "",
            "plan": metadata.get("plan") or "",
            "billingInterval": metadata.get("billingInterval") or "",
            "packId": metadata.get("packId") or "",
            "coins": metadata.get("coins") or "",
            "priceEnv": metadata.get("priceEnv") or "",
            "sessionId": metadata.get("sessionId") or metadata.get("stripeSessionId") or "",
            "error": metadata.get("error") or "",
        })

    return csv_response(
        "ce-aleg-payment-events.csv",
        [
            "createdAt",
            "userEmail",
            "type",
            "source",
            "plan",
            "billingInterval",
            "packId",
            "coins",
            "priceEnv",
            "sessionId",
            "error",
        ],
        rows,
    )


@route("/admin/overview", methods=["GET"])
def get_admin_overview():
    return jsonify({
        "users": User.query.count(),
        "products": Product.query.count(),
        "uncategorizedProducts": count_uncategorized_products(),
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


@route("/admin/submissions", methods=["GET"])
def get_admin_submissions():
    submissions = ProductSubmission.query.order_by(
        ProductSubmission.created_at.desc()
    ).all()
    return jsonify([product_submission_to_dict(item) for item in submissions])


@route("/admin/search-misses", methods=["GET"])
def get_admin_search_misses():
    days = request.args.get("days", default=30, type=int)
    limit = request.args.get("limit", default=50, type=int)
    safe_days = max(1, min(days or 30, 365))
    safe_limit = max(1, min(limit or 50, 200))
    since = utcnow() - timedelta(days=safe_days)

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


def parse_admin_optional_float(data, key, label):
    if key not in data:
        return None, None, False

    value = data.get(key)

    if value is None or str(value).strip() == "":
        return None, None, True

    try:
        return float(value), None, True
    except (TypeError, ValueError):
        return None, f"{label} trebuie sa fie numar valid.", True


@route("/admin/products/search", methods=["GET"])
def search_admin_products():
    query_text = str(request.args.get("q", "") or "").strip()
    limit = request.args.get("limit", default=20, type=int)
    safe_limit = max(1, min(limit or 20, 50))
    products_query = Product.query

    if query_text:
        like_term = f"%{query_text}%"
        normalized_query = normalize_search_text(query_text)
        filters = [
            Product.name.ilike(like_term),
            Product.category.ilike(like_term),
            Product.store.ilike(like_term),
        ]

        if re.fullmatch(r"\d{4,}", query_text):
            filters.insert(0, Product.barcode == query_text)

        products_query = products_query.filter(or_(*filters))
        products = products_query.order_by(
            Product.id.desc()
        ).limit(safe_limit).all()

        products.sort(
            key=lambda product: (
                product.barcode == query_text,
                normalize_search_text(product.name).startswith(normalized_query),
                normalize_search_text(product.category) not in {"altele", "other", "general"},
                product.id,
            ),
            reverse=True,
        )
    else:
        products = (
            products_query
            .filter(uncategorized_product_filter())
            .order_by(Product.id.desc())
            .limit(safe_limit)
            .all()
        )

    return jsonify([product_to_dict(product) for product in products])


@route("/admin/products/<int:product_id>", methods=["PATCH"])
def update_admin_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"error": "Produsul nu exista."}), 404

    data = request.get_json(silent=True) or {}
    previous_snapshot = product_notification_snapshot(product)
    text_fields = {
        "name": ("Numele produsului", 150, 2),
        "store": ("Magazinul", 100, 2),
        "category": ("Categoria", 100, 2),
        "barcode": ("Codul de bare", 80, 0),
        "image": ("Imaginea", 255, 0),
        "priceText": ("Pretul afisat", 100, 0),
        "tag": ("Eticheta", 100, 0),
        "reason": ("Motivul", 5000, 0),
        "ingredients": ("Ingredientele", 5000, 0),
    }
    errors = []

    for key, (label, max_length, min_length) in text_fields.items():
        if key not in data:
            continue

        value = str(data.get(key) or "").strip()
        error = validate_text_length(value, label, max_length, min_length)

        if error:
            errors.append(error)
            continue

        if key == "barcode":
            barcode_error = validate_barcode(value)

            if barcode_error:
                errors.append(barcode_error)
                continue

        field_name = "price_text" if key == "priceText" else key
        setattr(product, field_name, value or None)

    numeric_fields = {
        "price": "Pretul",
        "calories": "Caloriile",
        "protein": "Proteina",
        "sugar": "Zaharul",
        "fat": "Grasimile",
    }
    parsed_numbers = {}

    for key, label in numeric_fields.items():
        value, error, provided = parse_admin_optional_float(data, key, label)

        if error:
            errors.append(error)
        elif provided:
            parsed_numbers[key] = value

    nutrition_error = validate_nutrition_values(
        parsed_numbers.get("calories", product.calories),
        parsed_numbers.get("protein", product.protein),
        parsed_numbers.get("sugar", product.sugar),
        parsed_numbers.get("fat", product.fat),
    )

    if nutrition_error:
        errors.append(nutrition_error)

    if errors:
        return jsonify({"error": " ".join(errors)}), 400

    for key, value in parsed_numbers.items():
        setattr(product, key, value)

    for key, field_name in {
        "vegan": "vegan",
        "lactoseFree": "lactose_free",
        "natural": "natural",
    }.items():
        if key in data:
            setattr(product, field_name, bool(data.get(key)))

    recalculate = bool(data.get("recalculate", False))

    if recalculate:
        inferred_category = infer_catalog_category(product_to_dict(product))

        if should_update_reported_product_category(product.category, inferred_category):
            product.category = inferred_category[:100]

        product.score = calculate_product_score(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        product.tag = generate_product_tag(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        product.reason = generate_product_reason(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
    elif "score" in data:
        score, error, provided = parse_admin_optional_float(data, "score", "Scorul")

        if error:
            return jsonify({"error": error}), 400

        if provided:
            if score is not None and (score < 0 or score > 10):
                return jsonify({"error": "Scorul trebuie sa fie intre 0 si 10."}), 400
            product.score = score if score is not None else 0

    db.session.add(product)
    notify_users = data.get("notifyUsers") is True
    record_user_event(
        g.current_user.id,
        "admin_product_updated",
        "admin",
        {
            "productId": product.id,
            "barcode": product.barcode,
            "recalculate": recalculate,
            "notifyUsers": notify_users,
        },
        commit=False,
    )
    db.session.commit()

    notified_users = 0
    notification_error = None

    if notify_users:
        try:
            notified_users = notify_users_about_product_correction(product, previous_snapshot)
        except Exception as error:
            db.session.rollback()
            notification_error = str(error)
            app.logger.exception("Product correction notifications could not be sent.")

    message = "Produs actualizat."

    if notified_users:
        message = f"Produs actualizat. Am anuntat {notified_users} utilizatori."
    elif notify_users and not is_email_configured():
        message = "Produs actualizat. Emailul nu este configurat, deci nu am trimis notificari."
    elif notification_error:
        message = "Produs actualizat, dar notificarile nu au putut fi trimise."

    return jsonify({
        "message": message,
        "notifications": {
            "requested": notify_users,
            "sent": notified_users,
            "emailConfigured": is_email_configured(),
            "error": notification_error,
        },
        "product": product_to_dict(product),
    })


@route("/admin/catalog/quality", methods=["GET"])
def get_admin_catalog_quality():
    report = get_catalog_quality_snapshot()
    report["generatedAt"] = utcnow().isoformat() + "Z"
    return jsonify(report)


@route("/admin/catalog/recategorize", methods=["GET", "POST"])
def recategorize_admin_catalog():
    data = request.get_json(silent=True) or {}
    limit = request.args.get("limit", data.get("limit", 300), type=int)
    include_all = str(
        request.args.get("include_all", data.get("includeAll", "false"))
    ).lower() in {"1", "true", "yes", "on"}
    min_id = request.args.get("min_id", data.get("minId"), type=int)
    category = request.args.get("category", data.get("category", ""), type=str)
    apply_changes = request.method == "POST" and str(
        request.args.get("apply", data.get("apply", "false"))
    ).lower() in {"1", "true", "yes", "on"}

    result = recategorize_catalog_products(
        limit=limit,
        apply_changes=apply_changes,
        include_all=include_all,
        min_id=min_id,
        category=category,
    )

    if apply_changes and result["changed"]:
        record_user_event(
            g.current_user.id,
            "catalog_recategorized",
            "admin",
            {
                "changed": result["changed"],
                "scanned": result["scanned"],
                "includeAll": include_all,
                "minId": result.get("minId"),
                "category": result.get("category"),
            },
            commit=True,
        )

    return jsonify({
        **result,
        "message": (
            f"Am actualizat {result['changed']} produse."
            if apply_changes
            else f"Am găsit {result['changed']} produse care pot fi recategorizate."
        ),
        "catalog": get_catalog_quality_snapshot(),
    })


@route("/admin/missions/digest", methods=["GET", "POST"])
def send_admin_mission_digest():
    data = request.get_json(silent=True) or {}
    limit = request.args.get("limit", data.get("limit", 100), type=int)
    apply_changes = request.method == "POST" and str(
        request.args.get("apply", data.get("apply", "false"))
    ).lower() in {"1", "true", "yes", "on"}

    if apply_changes and not is_email_configured():
        return jsonify({
            "error": "Emailul nu este configurat. Seteaza providerul inainte de trimitere.",
            "emailConfigured": False,
        }), 400

    result = build_mission_digest_batch(
        limit=limit,
        apply_changes=apply_changes,
    )

    return jsonify({
        **result,
        "emailConfigured": is_email_configured(),
        "cooldownDays": MISSION_DIGEST_COOLDOWN_DAYS,
        "message": (
            f"Am trimis {result['sent']} emailuri cu misiuni aproape gata."
            if apply_changes
            else f"Am gasit {result['eligible']} utilizatori cu misiuni aproape gata."
        ),
    })


def cron_request_is_authorized():
    if not CRON_SECRET:
        return False

    supplied = request.headers.get("Authorization", "")
    expected = f"Bearer {CRON_SECRET}"
    return hmac.compare_digest(supplied, expected)


def get_cron_recategorize_min_id(limit):
    max_product_id = db.session.query(func.max(Product.id)).scalar() or 1
    safe_limit = max(1, int(limit or 1))
    day_number = utcnow().date().toordinal()
    return 1 + ((day_number * safe_limit) % max(1, int(max_product_id)))


def run_retention_cleanup(apply_changes=False):
    now = utcnow()
    activity_cutoff = now - timedelta(days=RETENTION_ACTIVITY_DAYS)
    analytics_cutoff = now - timedelta(days=ANALYTICS_RETENTION_DAYS)
    search_cutoff = now - timedelta(days=SEARCH_RETENTION_DAYS)
    account_cutoff = now - timedelta(days=RETENTION_UNVERIFIED_ACCOUNT_DAYS)
    rejected_submission_cutoff = now - timedelta(days=REJECTED_SUBMISSION_RETENTION_DAYS)
    scan_cutoff = time.time() - RETENTION_SCAN_FILE_HOURS * 3600
    ephemeral_event_types = {
        "alternative_report",
        "email_test",
        "mission_digest_email",
        "payment_checkout_started",
        "payment_error",
        "product_report",
        "support_message",
    }
    usage_query = UsageEvent.query.filter(
        or_(
            (
                UsageEvent.created_at < activity_cutoff
            ) & UsageEvent.event_type.in_(ephemeral_event_types),
            (
                UsageEvent.created_at < analytics_cutoff
            ) & UsageEvent.event_type.like("ui_%"),
        ),
    )
    search_query = SearchEvent.query.filter(SearchEvent.created_at < search_cutoff)
    webhook_query = StripeWebhookEvent.query.filter(
        StripeWebhookEvent.status == "processed",
        StripeWebhookEvent.updated_at < activity_cutoff,
    )
    unverified_users = (
        User.query.outerjoin(Subscription, Subscription.user_id == User.id)
        .filter(
            User.email_verified.is_(False),
            User.created_at < account_cutoff,
            or_(Subscription.id.is_(None), Subscription.plan == "free"),
        )
        .all()
    )
    rejected_submissions = ProductSubmission.query.filter(
        ProductSubmission.status.in_(["rejected", "ai_rejected"]),
        ProductSubmission.created_at < rejected_submission_cutoff,
    ).all()
    expired_scan_files = []

    if os.path.isdir(UPLOAD_FOLDER):
        for candidate in os.scandir(UPLOAD_FOLDER):
            try:
                if (
                    candidate.is_file()
                    and candidate.name.startswith("scan_")
                    and candidate.stat().st_mtime < scan_cutoff
                ):
                    expired_scan_files.append(candidate.path)
            except OSError:
                continue

    result = {
        "applied": bool(apply_changes),
        "activityCutoff": activity_cutoff.isoformat() + "Z",
        "analyticsCutoff": analytics_cutoff.isoformat() + "Z",
        "searchCutoff": search_cutoff.isoformat() + "Z",
        "unverifiedAccountCutoff": account_cutoff.isoformat() + "Z",
        "rejectedSubmissionCutoff": rejected_submission_cutoff.isoformat() + "Z",
        "usageEvents": usage_query.count(),
        "searchEvents": search_query.count(),
        "webhookEvents": webhook_query.count(),
        "unverifiedAccounts": len(unverified_users),
        "rejectedSubmissions": len(rejected_submissions),
        "scanFiles": len(expired_scan_files),
    }

    if not apply_changes:
        return result

    for user in unverified_users:
        delete_account_data(user)

    for submission in rejected_submissions:
        delete_submission_file(submission.front_image)
        delete_submission_file(submission.nutrition_image)
        db.session.delete(submission)

    usage_query.delete(synchronize_session=False)
    search_query.delete(synchronize_session=False)
    webhook_query.delete(synchronize_session=False)
    db.session.commit()

    for filepath in expired_scan_files:
        try:
            os.remove(filepath)
        except OSError as error:
            app.logger.warning("Retention could not remove scan file %s: %s", filepath, error)

    return result


@route("/admin/retention", methods=["GET", "POST"])
def run_admin_retention():
    apply_changes = request.method == "POST" and (
        str((request.get_json(silent=True) or {}).get("apply", "false")).lower()
        in {"1", "true", "yes", "on"}
    )
    return jsonify(run_retention_cleanup(apply_changes=apply_changes))


@route("/internal/cron/maintenance", methods=["POST"])
def run_cron_maintenance():
    if not cron_request_is_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    recategorize_limit = max(1, min(int(data.get("recategorizeLimit") or 300), 500))
    digest_limit = max(1, min(int(data.get("digestLimit") or 100), 250))
    send_digest = str(data.get("sendDigest", "true")).lower() in {"1", "true", "yes", "on"}
    run_recategorize = str(data.get("recategorize", "true")).lower() in {"1", "true", "yes", "on"}
    run_retention = str(data.get("retention", "true")).lower() in {"1", "true", "yes", "on"}
    run_catalog_quality = str(data.get("catalogQuality", "true")).lower() in {
        "1", "true", "yes", "on",
    }
    result = {
        "ok": True,
        "generatedAt": utcnow().isoformat() + "Z",
        "recategorize": None,
        "missionDigest": None,
        "retention": None,
        "catalogQuality": None,
    }

    if run_recategorize:
        recategorize_min_id = get_cron_recategorize_min_id(recategorize_limit)
        result["recategorize"] = recategorize_catalog_products(
            limit=recategorize_limit,
            apply_changes=True,
            min_id=recategorize_min_id,
        )

    if send_digest:
        result["missionDigest"] = build_mission_digest_batch(
            limit=digest_limit,
            apply_changes=is_email_configured(),
        )
        result["missionDigest"]["emailConfigured"] = is_email_configured()

    if run_retention:
        result["retention"] = run_retention_cleanup(apply_changes=True)

    if run_catalog_quality:
        result["catalogQuality"] = get_catalog_quality_snapshot()
        try:
            configured_threshold = float(
                os.environ.get("CATALOG_QUALITY_ALERT_THRESHOLD", "65")
            )
        except (TypeError, ValueError):
            configured_threshold = 65.0
        threshold = max(0.0, min(100.0, configured_threshold))
        quality = result["catalogQuality"]
        if quality["products"] and quality["healthScore"] < threshold:
            send_admin_alert(
                "Calitatea catalogului este sub prag",
                "Raportul automat a detectat prea multe produse incomplete sau invalide.",
                [
                    f"Scor: {quality['healthScore']}/100",
                    f"Prag: {threshold}",
                    f"Fără categorie: {quality['uncategorizedProducts']}",
                    f"Fără nutriție: {quality['missingNutrition']}",
                    f"Barcode-uri duplicate: {quality['duplicateBarcodes']}",
                ],
                alert_key="catalog_quality_below_threshold",
                min_interval_seconds=86400,
                severity="warning",
            )

    return jsonify(result)


@route("/admin/alternative-reports/<int:event_id>/resolve", methods=["POST"])
def resolve_admin_alternative_report(event_id):
    event = UsageEvent.query.filter_by(
        id=event_id,
        event_type="alternative_report",
    ).first()

    if not event:
        return jsonify({"error": "Raportarea nu exista."}), 404

    data = request.get_json(silent=True) or {}
    metadata = parse_usage_metadata(event)
    alternative_product = metadata.get("alternativeProduct")

    if not isinstance(alternative_product, dict) or not alternative_product.get("name"):
        return jsonify({"error": "Raportarea nu contine alternativa valida."}), 400

    manual_category = str(data.get("category") or "").strip()
    method = "manual" if manual_category else "auto"

    if manual_category:
        product = materialize_reported_alternative_product(alternative_product)

        if not product:
            return jsonify({"error": "Produsul raportat nu a putut fi gasit sau creat."}), 400

        old_category = product.category
        product.category = manual_category[:100]
        product.score = calculate_product_score(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        product.tag = generate_product_tag(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        product.reason = generate_product_reason(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        db.session.add(product)
        fix_result = {
            "fixed": normalize_search_text(old_category) != normalize_search_text(product.category),
            "product": product,
            "oldCategory": old_category,
            "newCategory": product.category,
            "family": get_product_recommendation_family(product_to_dict(product)),
        }
    else:
        fix_result = auto_fix_reported_alternative_category(alternative_product)

    if not fix_result or not fix_result.get("product"):
        return jsonify({"error": "Nu am putut rezolva raportarea automat."}), 400

    product = fix_result["product"]
    new_category = str(fix_result.get("newCategory") or product.category or "").strip()
    old_category = str(fix_result.get("oldCategory") or "").strip()
    fixed_product = product_to_dict(product)

    metadata["alternativeProduct"] = {
        **alternative_product,
        "id": product.id,
        "category": new_category,
        "family": fix_result.get("family") or get_product_recommendation_family(fixed_product),
        "source": alternative_product.get("source") or product.store,
    }
    metadata["adminReview"] = {
        "reviewedAt": admin_iso(utcnow()),
        "reviewedBy": g.current_user.email,
        "method": method,
        "fixed": bool(fix_result.get("fixed")),
        "productId": product.id,
        "oldCategory": old_category,
        "newCategory": new_category,
    }
    event.metadata_json = json.dumps(metadata, ensure_ascii=False)

    record_user_event(
        g.current_user.id,
        "alternative_report_resolved",
        "admin",
        {
            "reportId": event.id,
            "productId": product.id,
            "method": method,
            "fixed": bool(fix_result.get("fixed")),
            "oldCategory": old_category,
            "newCategory": new_category,
        },
        commit=False,
    )
    db.session.commit()

    return jsonify({
        "message": (
            f"Raportarea a fost rezolvata: {old_category or 'fara categorie'} -> {new_category}."
            if fix_result.get("fixed")
            else f"Raportarea a fost verificata. Categoria ramane {new_category or 'neschimbata'}."
        ),
        "fixed": bool(fix_result.get("fixed")),
        "product": fixed_product,
        "event": usage_event_to_admin_dict(event),
    })


@route("/admin/products/<int:product_id>", methods=["DELETE"])
def delete_admin_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"error": "Produsul nu exista."}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Produs șters din catalog."})


@route("/admin/users/<int:user_id>/plan", methods=["PATCH"])
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
    subscription.updated_at = utcnow()
    db.session.commit()

    return jsonify({
        "message": "Plan actualizat.",
        "user": user_to_dict(user),
        "usage": get_usage_summary(user),
    })



# =========================
# Products
# =========================

@route("/products/seed", methods=["GET"])
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


@route("/products", methods=["GET"])
def get_products():
    store = request.args.get("store")
    limit = min(max(request.args.get("limit", default=200, type=int) or 200, 1), 500)
    offset = max(request.args.get("offset", default=0, type=int) or 0, 0)

    query = Product.query

    if store:
        query = query.filter_by(store=store)

    products = query.order_by(Product.score.desc()).offset(offset).limit(limit).all()

    return jsonify([product_to_dict(product) for product in products])


@route("/products/search", methods=["GET"])
def search_products():
    query_text = request.args.get("q", "").strip()
    store_id = request.args.get("store", "").strip()
    current_user = get_current_user()

    if not query_text:
        return jsonify({"error": "Parametrul q este obligatoriu."}), 400

    store_name = get_store_name_from_id(store_id) if store_id else None

    results = get_local_product_search_results(query_text, store_name, limit=10)
    seen_keys = {
        normalize_search_text(f"{item.get('barcode') or ''} {item.get('name') or ''}")
        for item in results
    }
    seen_names = {
        normalize_search_text(item.get("name") or "")
        for item in results
    }
    cache_key = f"product-search:{normalize_search_text(query_text)}:{normalize_search_text(store_name or '')}"
    cached_results = get_cached_product_search_results(cache_key)
    external_results = []
    external_seen_keys = set()
    external_seen_names = set()
    external_unavailable = False
    exact_local_match = bool(results and (results[0].get("matchScore") or 0) >= 150)
    use_external_catalog = EXTERNAL_CATALOG_ENABLED and not exact_local_match
    source = "local_catalog" if results or not EXTERNAL_CATALOG_ENABLED else "openfoodfacts"

    if use_external_catalog and cached_results is not None:
        external_results = cached_results
        source = "local+openfoodfacts-cache" if results else "openfoodfacts-cache"
    elif use_external_catalog and len(query_text) >= 3:
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

                if (
                    key in seen_keys
                    or name_key in seen_names
                    or key in external_seen_keys
                    or name_key in external_seen_names
                ):
                    continue

                product_data["matchScore"] = score
                external_results.append(product_data)
                external_seen_keys.add(key)
                external_seen_names.add(name_key)
        except requests.RequestException as error:
            app.logger.warning("Open Food Facts suggestions failed: %s", error)
            external_unavailable = True

        if not external_unavailable:
            external_results.sort(key=lambda item: item.get("matchScore", 0), reverse=True)
            external_results = external_results[:10]
            set_cached_product_search_results(cache_key, external_results)
            source = "local+openfoodfacts" if results else "openfoodfacts"

    for product_data in external_results:
        key = normalize_search_text(
            f"{product_data.get('barcode') or ''} {product_data.get('name') or ''}"
        )
        name_key = normalize_search_text(product_data.get("name") or "")

        if key in seen_keys or name_key in seen_names:
            continue

        results.append(product_data)
        seen_keys.add(key)
        seen_names.add(name_key)

    results.sort(key=lambda item: item.get("matchScore", 0), reverse=True)
    results = results[:10]

    if external_unavailable:
        if not results:
            return jsonify({
                "error": "Catalogul extern nu este disponibil momentan.",
                "code": "external_catalog_unavailable",
                "source": "openfoodfacts",
            }), 502
        source = "local-fallback"

    record_search_event(
        query_text,
        store=store_name,
        result_count=len(results),
        source=source,
        user_id=current_user.id if current_user else None,
    )
    db.session.commit()

    response = jsonify(results)
    response.headers["X-Product-Source"] = source
    if external_unavailable:
        response.headers["X-External-Catalog"] = "unavailable"
    elif not EXTERNAL_CATALOG_ENABLED:
        response.headers["X-External-Catalog"] = "disabled"
    return response


@route("/products/search-label", methods=["GET"])
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


@route("/alternatives/open-food-facts", methods=["POST"])
def get_open_food_facts_alternatives():
    data = request.get_json(silent=True) or {}
    scanned_product = data.get("product") or {}
    preferences = data.get("preferences") or {}
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

    if not prefer_local_catalog and "caffeine" in criteria and scanned_family in {
        "coffee_drink",
        "energy_drink",
        "zero_energy_drink",
        "energy_shot",
        "caffeinated_beverage",
        "cola",
        "cola_zero",
        "cola_regular",
        "isotonic_drink",
    }:
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

        if product_violates_user_preferences(candidate, preferences):
            continue

        if "caffeine" in criteria and not is_caffeine_relevant_candidate(candidate):
            continue

        alternatives.append(candidate)

    existing_alternative_keys = {
        normalize_search_text(f"{item.get('barcode') or ''} {item.get('name') or ''}")
        for item in alternatives
    }

    for candidate in local_seed_alternatives:
        if product_violates_user_preferences(candidate, preferences):
            continue

        candidate_key = normalize_search_text(
            f"{candidate.get('barcode') or ''} {candidate.get('name') or ''}"
        )

        if candidate_key in existing_alternative_keys:
            continue

        alternatives.append(candidate)
        existing_alternative_keys.add(candidate_key)

    normalization_stats = build_alternative_normalization_stats(alternatives)

    for alternative in alternatives:
        score_off_alternative(
            alternatives,
            alternative,
            criteria,
            scanned_product,
            normalization_stats,
        )

    alternatives.sort(
        key=lambda product: product["recommendationScore"],
        reverse=True,
    )

    price_lookup_limit = 24 if "cheap" in criteria else 8
    attach_open_prices(alternatives[:price_lookup_limit])

    if "cheap" in criteria:
        normalization_stats = build_alternative_normalization_stats(alternatives)

        for alternative in alternatives:
            score_off_alternative(
                alternatives,
                alternative,
                criteria,
                scanned_product,
                normalization_stats,
            )

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
    used_local_fallback = bool(
        lookup_errors
        and local_seed_alternatives
        and not off_products
    )

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
        send_admin_alert(
            "Alternative insuficiente",
            "Un produs scanat a primit prea puține alternative utile.",
            [
                f"Produs: {scanned_product.get('name') or '-'}",
                f"Cod: {barcode or '-'}",
                f"Categorie: {category_tag or '-'}",
                f"Familie: {scanned_family or '-'}",
                f"Rezultate: {len(products)}",
            ],
            alert_key="alternatives_low",
            min_interval_seconds=6 * 3600,
        )

    return jsonify({
        "source": (
            "catalog"
            if prefer_local_catalog
            else "local-fallback"
            if used_local_fallback
            else "openfoodfacts"
        ),
        "category": category_tag,
        "products": products,
        "message": (
            (
                "Alternative calculate rapid din catalogul intern."
                if prefer_local_catalog
                else "Catalogul extern nu este disponibil momentan. Am folosit alternative verificate din catalogul intern."
                if used_local_fallback
                else "Alternative calculate din catalogul Open Food Facts."
            )
            if alternatives
            else "Nu am gasit suficiente alternative externe pentru produsul scanat."
        ),
    })


@route("/analyze", methods=["POST"])
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

    try:
        filename = save_scan_image(image, g.current_user.id)
    except ValueError as error:
        return jsonify({"error": str(error), "code": "invalid_scan_image"}), 400

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

@route("/cart/<int:user_id>", methods=["GET"])
def get_cart(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    requested_profile_id = get_requested_family_profile_id()
    profile = resolve_cart_profile(user, requested_profile_id)
    items = cart_query_for_profile(user, profile).order_by(
        CartItem.created_at.desc()
    ).all()

    return jsonify([cart_item_to_dict(item) for item in items])


@route("/cart/add", methods=["POST"])
def add_to_cart():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    user_id = data.get("user_id")
    product_name = data.get("name")
    store = data.get("store", "Fără magazin ales")

    if not user_id or not product_name:
        return jsonify({"error": "user_id și name sunt obligatorii."}), 400

    user = db.session.get(User, user_id)

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


@route("/cart/item/<int:item_id>", methods=["PATCH"])
def update_cart_item(item_id):
    item = db.session.get(CartItem, item_id)

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


@route("/cart/item/<int:item_id>", methods=["DELETE"])
def delete_cart_item(item_id):
    item = db.session.get(CartItem, item_id)

    if not item:
        return jsonify({"error": "Produsul din coș nu există."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Produs șters din coș."})


@route("/cart/clear/<int:user_id>", methods=["DELETE"])
def clear_cart(user_id):
    user = db.session.get(User, user_id)

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

@route("/favorites/<int:user_id>", methods=["GET"])
def get_favorites(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    items = Favorite.query.filter_by(user_id=user_id).order_by(
        Favorite.created_at.desc()
    ).all()

    return jsonify([favorite_item_to_dict(item) for item in items])


@route("/favorites/add", methods=["POST"])
def add_to_favorites():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    user_id = data.get("user_id")
    product_name = data.get("name")
    store = data.get("store", "Fără magazin ales")

    if not user_id or not product_name:
        return jsonify({"error": "user_id și name sunt obligatorii."}), 400

    user = db.session.get(User, user_id)

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


@route("/favorites/item/<int:favorite_id>", methods=["DELETE"])
def delete_favorite_item(favorite_id):
    item = db.session.get(Favorite, favorite_id)

    if not item:
        return jsonify({"error": "Produsul favorit nu există."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Produs șters din favorite."})


@route("/favorites/clear/<int:user_id>", methods=["DELETE"])
def clear_favorites(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    Favorite.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return jsonify({"message": "Favoritele au fost șterse."})


# =========================
# History
# =========================

@route("/history/<int:user_id>", methods=["GET"])
def get_scan_history(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    items = ScanHistory.query.filter_by(user_id=user_id).order_by(
        ScanHistory.scanned_at.desc()
    ).all()

    return jsonify([scan_history_item_to_dict(item) for item in items])


@route("/history/add", methods=["POST"])
def add_scan_history():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nu ai trimis date JSON."}), 400

    user_id = data.get("user_id")
    product_name = data.get("name")
    store = data.get("store", "Fără magazin ales")

    if not user_id or not product_name:
        return jsonify({"error": "user_id și name sunt obligatorii."}), 400

    user = db.session.get(User, user_id)

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


@route("/history/item/<int:history_id>", methods=["DELETE"])
def delete_scan_history_item(history_id):
    item = db.session.get(ScanHistory, history_id)

    if not item:
        return jsonify({"error": "Scanarea nu există."}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Scanare ștearsă din istoric."})


@route("/history/clear/<int:user_id>", methods=["DELETE"])
def clear_scan_history(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    ScanHistory.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return jsonify({"message": "Istoricul scanărilor a fost șters."})


# =========================
# Product submissions
# =========================

@route("/uploads/submissions/<path:filename>", methods=["GET"])
def get_submission_image(filename):
    image_path = f"/uploads/submissions/{filename}"

    if not user_can_access_submission_image(image_path):
        return jsonify({"error": "Nu poți accesa această imagine."}), 403

    return send_from_directory(SUBMISSIONS_FOLDER, filename)


@route("/uploads/scans/<path:filename>", methods=["GET"])
@require_auth
def get_scan_image(filename):
    expected_prefix = f"scan_{g.current_user.id}_"

    if not g.current_user.is_admin and not filename.startswith(expected_prefix):
        return jsonify({"error": "Nu poți accesa această imagine."}), 403

    return send_from_directory(UPLOAD_FOLDER, filename)


@route("/uploads/supabase-submissions/<path:object_path>", methods=["GET"])
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


@route("/submissions/<int:user_id>", methods=["GET"])
def get_user_submissions(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    submissions = ProductSubmission.query.filter_by(user_id=user_id).order_by(
        ProductSubmission.created_at.desc()
    ).all()

    return jsonify([product_submission_to_dict(item) for item in submissions])


@route("/submissions/add", methods=["POST"])
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

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"error": "Utilizatorul nu există."}), 404

    pending_count = ProductSubmission.query.filter(
        ProductSubmission.user_id == user.id,
        ProductSubmission.status.in_(["pending", "ai_approved"]),
    ).count()
    submitted_today = ProductSubmission.query.filter(
        ProductSubmission.user_id == user.id,
        ProductSubmission.created_at >= get_day_start(),
    ).count()

    if pending_count >= SUBMISSION_PENDING_LIMIT:
        return jsonify({
            "error": "Ai prea multe propuneri în verificare. Așteaptă aprobarea lor înainte să mai trimiți.",
            "code": "submission_pending_limit",
            "limit": SUBMISSION_PENDING_LIMIT,
        }), 429

    if submitted_today >= SUBMISSION_DAILY_LIMIT:
        return jsonify({
            "error": "Ai atins limita zilnică de propuneri. Revino mâine.",
            "code": "submission_daily_limit",
            "limit": SUBMISSION_DAILY_LIMIT,
        }), 429

    if barcode:
        lock_catalog_key(f"submission:{barcode}")
        existing_product = find_existing_catalog_entry_by_barcode(barcode)

        if existing_product:
            return jsonify({
                "code": "product_already_exists",
                "message": "Produsul există deja în catalog. Îl poți scana direct.",
                "product": product_to_dict(existing_product),
            }), 409

        existing_submission = find_active_submission_by_barcode(barcode)

        if existing_submission:
            same_user = existing_submission.user_id == user_id
            return jsonify({
                "code": "submission_already_pending",
                "message": (
                    "Ai trimis deja acest cod de bare. Propunerea este în verificare."
                    if same_user
                    else "Produsul este deja în verificare în coada catalogului."
                ),
                "item": product_submission_to_dict(existing_submission) if same_user or user.is_admin else None,
                "status": existing_submission.status,
            }), 409

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


@route("/submissions/item/<int:submission_id>", methods=["DELETE"])
def delete_product_submission(submission_id):
    submission = db.session.get(ProductSubmission, submission_id)

    if not submission:
        return jsonify({"error": "Propunerea nu există."}), 404

    db.session.delete(submission)
    db.session.commit()

    return jsonify({"message": "Propunerea a fost ștearsă."})


@route("/submissions/ai-review/<int:submission_id>", methods=["POST"])
def ai_review_product_submission(submission_id):
    submission = db.session.get(ProductSubmission, submission_id)

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


@route("/submissions/approve/<int:submission_id>", methods=["POST"])
def approve_product_submission(submission_id):
    submission = db.session.get(ProductSubmission, submission_id)

    if not submission:
        return jsonify({"error": "Propunerea nu există."}), 404

    if submission.status != "ai_approved":
        return jsonify({
            "error": "Produsul poate fi publicat doar dacă are status ai_approved."
        }), 400

    existing_product = None

    if submission.barcode:
        existing_product = find_existing_catalog_entry_by_barcode(submission.barcode)

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
        reward = auto_claim_catalog_submission_reward(
            contributor,
            submission,
            existing_product,
            duplicate=True,
        )
        db.session.commit()
        clear_leaderboard_cache()
        send_product_submission_approved_email(
            contributor,
            submission,
            existing_product,
            duplicate=True,
            reward=reward,
        )

        return jsonify({
            "message": "Produsul exista deja în baza oficială. Propunerea a fost aprobată, iar recompensa a fost sincronizată.",
            "reward": {
                "bonusScans": SUBMISSION_APPROVAL_BONUS_CREDITS,
                "coins": int(reward.get("coins") or 0) if reward.get("claimed") else 0,
                "claimed": bool(reward.get("claimed")),
            },
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
    reward = auto_claim_catalog_submission_reward(
        contributor,
        submission,
        new_product,
        duplicate=False,
    )
    db.session.commit()
    clear_leaderboard_cache()
    send_product_submission_approved_email(
        contributor,
        submission,
        new_product,
        duplicate=False,
        reward=reward,
    )

    return jsonify({
        "message": "Produsul a fost publicat în baza oficială, iar recompensa a fost sincronizată.",
        "reward": {
            "bonusScans": SUBMISSION_APPROVAL_BONUS_CREDITS,
            "coins": int(reward.get("coins") or 0) if reward.get("claimed") else 0,
            "claimed": bool(reward.get("claimed")),
        },
        "product": product_to_dict(new_product),
        "submission": product_submission_to_dict(submission),
    })

@route("/ai/extract-product-info", methods=["POST"])
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


@route("/products/cleanup-duplicates", methods=["POST", "GET"])
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


@route("/translate", methods=["POST"])
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
    label_text = normalize_search_text(
        " ".join([product_name, brands, categories, tags_text])
    )
    product_text = normalize_search_text(
        " ".join([product_name, brands, categories, tags_text, ingredients or ""])
    )

    def has_any(tokens):
        return any(token in product_text for token in tokens)

    def label_has_precise(tokens):
        for token in tokens:
            normalized_token = normalize_search_text(token)

            if not normalized_token:
                continue

            if " " not in normalized_token and normalized_token.isalpha():
                if re.search(rf"(^|[^a-z0-9]){re.escape(normalized_token)}([^a-z0-9]|$)", label_text):
                    return True
            elif normalized_token in label_text:
                return True

        return False

    if has_any(["buldak", "samyang", "ramen", "instant noodles", "cup noodles", "noodle", "noodles", "taitei", "nongshim", "yakisoba", "udon"]):
        category = "Tăiței instant"
    elif has_any(["ice cream", "icecream", "gelato", "sorbet", "inghetata"]):
        category = "Înghețată"
    elif has_any(["energy drink", "energiz", "red bull", "redbull", "monster", "hell", "burn", "rockstar", "taurina", "taurine"]) or "energy-drinks" in tags_text:
        category = "Băuturi energizante"
    elif has_any(["bere", "beer", "ursus", "timisoreana", "timișoreana", "ciuc", "bergenbier", "heineken", "silva", "tuborg", "carlsberg", "peroni", "stella", "corona", "kozel", "lager", "pilsner", "radler"]) or "beers" in tags_text:
        category = "Bere"
    elif label_has_precise(["alcool", "alcohol", "vin", "wine", "vodka", "whisky", "rom", "rum", "gin", "cidru", "cider", "lichior"]) or "alcoholic-beverages" in tags_text:
        category = "Băuturi alcoolice"
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
    elif has_any(["baby food", "baby milk", "infant", "bebelus", "bebeluș", "copii", "piure bebelusi", "piure bebeluși"]):
        category = "Alimente pentru copii"
    elif has_any(["cheese", "branza", "branzeturi", "brânză", "brânzeturi", "cascaval", "cașcaval", "mozzarella", "telemea", "feta", "cheddar", "gouda"]):
        category = "Lactate și brânzeturi"
    elif "plant-based-milks" in tags_text or has_any(["lapte vegetal", "plant based milk", "oat drink", "almond drink", "soy drink", "bautura vegetala", "băutură vegetală"]):
        category = "Alternative vegetale"
    elif "yogurt" in categories_lower or "dairy" in categories_lower or has_any(["iaurt", "yogurt", "yoghurt", "skyr", "kefir", "chefir", "sana", "lapte batut", "lapte bătut", "lapte", "milk"]):
        category = "Lactate"
    elif has_any(["protein bar", "protein", "proteic", "proteina", "proteină", "whey", "sports nutrition", "protein powder"]):
        category = "Proteine și fitness"
    elif has_any(["chips", "crisps", "crackers", "popcorn", "salty snack", "pufule"]):
        category = "Snacks sărate"
    elif "cereal" in categories_lower or has_any(["cereale", "cereal", "muesli", "granola", "oatmeal", "fulgi ovaz", "fulgi ovăz"]):
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
    elif has_any(["pasta", "paste", "rice", "orez", "beans", "lentils", "linte", "naut", "năut", "chickpeas", "fasole"]):
        category = "Paste, orez și leguminoase"
    elif has_any(["canned", "conserva", "conservă", "conserve", "pickles", "muraturi", "murături", "olives", "masline", "măsline"]):
        category = "Conserve și murături"
    elif has_any(["oil", "ulei", "vinegar", "otet", "oțet", "spice", "condiment"]):
        category = "Uleiuri și condimente"
    elif "meat" in categories_lower or has_any(["carne", "meat", "salam", "sausage", "carnati", "cârnați", "ham", "sunca", "șuncă", "muschi", "mușchi", "file", "filet", "pastrama", "pastramă", "bacon", "prosciutto", "mortadella", "parizer"]):
        category = "Carne"
    elif has_any(["fish", "peste", "tuna", "ton", "somon", "salmon", "seafood"]):
        category = "Pește și fructe de mare"
    elif "fruit" in categories_lower or "vegetable" in categories_lower or has_any(["fruct", "vegetable", "legume", "salata"]):
        category = "Fructe și legume"
    elif has_any(["spread", "crema tartinabila", "cremă tartinabilă", "hazelnut spread", "peanut butter", "unt arahide", "gem", "jam", "miere", "honey"]):
        category = "Creme și gemuri"
    elif has_any(["nuts", "nuci", "alune", "seeds", "seminte", "dried fruits"]):
        category = "Nuci și semințe"
    elif "sweet" in categories_lower or "candy" in categories_lower or "chocolate" in categories_lower or has_any(["ciocolata", "chocolate", "biscuit", "wafer", "napolitana", "dulce", "candy"]):
        category = "Dulciuri"
    elif "beverage" in categories_lower or "drink" in categories_lower:
        category = "Băuturi"

    inferred_family = get_product_recommendation_family({
        "name": product_name,
        "brand": brands,
        "category": category,
        "ingredients": ingredients,
        "offCategories": categories_tags,
    })
    inferred_category = CATEGORY_BY_RECOMMENDATION_FAMILY.get(inferred_family)
    broad_categories = {
        "Altele",
        "Băuturi",
        "Lactate",
        "Dulciuri",
        "Snacks sărate",
        "Cereale",
        "Congelate",
        "Mese gata preparate",
        "Carne",
        "Alternative vegetale",
    }

    if inferred_category and category in broad_categories:
        category = inferred_category

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
    if not OPEN_PRICES_ENABLED or not barcode:
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

    set_limited_cache_item(
        OPEN_PRICES_CACHE,
        barcode,
        {
            "created_at": now,
            "summary": summary,
        },
        OPEN_PRICES_CACHE_MAX_ITEMS,
    )
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


@route("/prices/report", methods=["POST"])
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

    if not user_id or not db.session.get(User, user_id):
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


@route("/prices/<barcode>", methods=["GET"])
def get_latest_local_price(barcode):
    barcode_error = validate_barcode(barcode, required=True)

    if barcode_error:
        return jsonify({"error": barcode_error}), 400

    summary = get_local_price_summary(barcode)

    return jsonify({
        "found": bool(summary),
        "price": summary,
    })


def _compute_product_recommendation_family(product_data):
    off_categories = product_data.get("offCategories") or []

    if isinstance(off_categories, str):
        off_categories = [off_categories]

    label_parts = [
            str(product_data.get("name") or ""),
            str(product_data.get("brand") or ""),
            str(product_data.get("category") or ""),
            str(product_data.get("store") or ""),
            str(product_data.get("tag") or ""),
            " ".join(off_categories),
    ]
    ingredients_part = str(product_data.get("ingredients") or "")
    label_text_value = normalize_search_text(" ".join(label_parts))
    text_value = normalize_search_text(" ".join([*label_parts, ingredients_part]))

    def text_has_any(tokens):
        return any(normalize_search_text(token) in text_value for token in tokens)

    def label_has_any(tokens):
        return any(normalize_search_text(token) in label_text_value for token in tokens)

    def has_precise_token(source_text, token):
        normalized_token = normalize_search_text(token)

        if not normalized_token:
            return False

        if len(normalized_token) <= 3 and normalized_token.isalpha():
            return bool(re.search(rf"(^|[^a-z0-9]){re.escape(normalized_token)}([^a-z0-9]|$)", source_text))

        return normalized_token in source_text

    def label_has_precise(tokens):
        return any(has_precise_token(label_text_value, token) for token in tokens)

    def text_has_precise(tokens):
        return any(has_precise_token(text_value, token) for token in tokens)

    if text_has_any(["buldak", "samyang", "shin ramyun", "ramen", "instant noodles", "taitei instant", "tăiței instant", "cup noodles", "noodles cup", "taitei la pahar", "tăiței la pahar"]):
        if text_has_any(["cup noodles", "noodles cup", "taitei la pahar", "tăiței la pahar"]):
            return "cup_noodles"
        return "ramen_noodles"

    if label_has_precise([
        "otet",
        "oțet",
        "vinegar",
        "vinaigre",
        "vinagre",
        "aceto balsamico",
        "balsamic vinegar",
        "rice vinegar",
        "apple cider vinegar",
        "white wine vinegar",
    ]):
        return "vinegar"

    if label_has_precise(["sare", "salt", "salz", "sel de mer", "sea salt", "iodized salt", "iodised salt"]):
        return "salt"

    if label_has_precise(["piper", "pepper", "poivre", "pfeffer", "pimienta"]):
        return "pepper"

    if label_has_precise(["boia", "paprika", "pimenton", "pimentón"]):
        return "paprika"

    if label_has_precise([
        "curry",
        "curcuma",
        "turmeric",
        "ginger",
        "gingembre",
        "coriander",
        "coriandre",
        "cinnamon",
        "cannelle",
        "oregano",
        "oregano",
        "busuioc",
        "basil",
        "seasoning",
        "assaisonnement",
        "melange pour",
        "mélange pour",
        "epices",
        "épices",
        "spice",
        "spices",
        "condiment",
        "condimente",
    ]):
        return "spice_mix"

    if label_has_precise([
        "vanilla extract",
        "extract vanilie",
        "extrait de vanille",
        "vanille arôme",
        "vanilla aroma",
        "aroma vainilla",
        "arome naturel",
        "arôme naturel",
    ]):
        return "flavor_extract"

    if label_has_precise([
        "ceai",
        "thé",
        "the vert",
        "the noir",
        "tea bags",
        "black tea",
        "green tea",
        "earl grey",
        "infusion",
        "infuzie",
        "tisane",
        "rooibos",
        "menthe",
    ]) and not label_has_precise(["ice tea", "iced tea", "ceai rece", "kombucha"]):
        return "tea_bags"

    if text_has_any(["ice coffee", "iced coffee", "cafea", "coffee", "cappuccino", "capuccino", "latte", "mocha", "espresso", "cold brew", "frappe"]):
        return "coffee_drink"

    priority_family_rules = [
        ("sparkling_water", ["apa minerala", "apa carbogazoasa", "apă carbogazoasă", "sparkling water", "mineral water", "carbogazoasa"]),
        ("still_water", ["apa plata", "apă plată", "still water", "spring water"]),
        ("zero_energy_drink", ["red bull zero", "redbull zero", "monster zero", "monster ultra", "hell zero", "zero sugar energy", "energy zero", "energizant zero", "fara zahar energy", "fără zahăr energy"]),
        ("energy_shot", ["energy shot", "shot energizant"]),
        ("cola_zero", ["cola zero", "pepsi max", "pepsi zero", "coca cola zero", "coca-cola zero", "coke zero"]),
        ("cola_regular", ["coca cola", "coca-cola", "cocacola", "pepsi", "cola original", "cola regular"]),
        ("orange_soda", ["fanta", "mirinda", "orange soda", "portocale carbogazoasa", "portocală carbogazoasă"]),
        ("lemon_lime_soda", ["sprite", "7up", "seven up", "lemon lime", "lamaie carbogazoasa", "lămâie carbogazoasă"]),
        ("tonic_soda", ["schweppes", "tonic", "bitter lemon"]),
        ("lemonade", ["limonada", "limonadă", "lemonade"]),
        ("iced_tea", ["ice tea", "iced tea", "ceai rece", "fuzetea", "lipton ice tea"]),
        ("kombucha", ["kombucha"]),
        ("cocoa_drink", ["cacao bautura", "cacao băutură", "choco drink", "hot chocolate", "ciocolata calda", "ciocolată caldă"]),
        ("drinkable_yogurt", ["iaurt de baut", "iaurt de băut", "drinkable yogurt", "yogurt drink", "actimel", "kefir drink"]),
        ("protein_yogurt", ["iaurt proteic", "protein yogurt", "skyr proteic", "high protein yogurt"]),
        ("greek_yogurt", ["iaurt grecesc", "greek yogurt"]),
        ("sour_cream", ["smantana", "smântână", "sour cream"]),
        ("whipped_cream", ["frisca", "frișcă", "whipping cream", "hulala", "spray cream"]),
        ("cheese_spread", ["crema de branza", "cremă de brânză", "cream cheese", "branza topita tartinabila", "brânză topită tartinabilă"]),
        ("processed_cheese", ["branza topita", "brânză topită", "processed cheese"]),
        ("hard_cheese", ["cascaval", "cașcaval", "cheddar", "gouda", "emmental", "parmesan"]),
        ("soft_cheese", ["mozzarella", "brie", "camembert", "mascarpone"]),
        ("feta_telemea", ["telemea", "feta", "branza sarata", "brânză sărată"]),
        ("milk_chocolate", ["ciocolata cu lapte", "ciocolată cu lapte", "milk chocolate"]),
        ("dark_chocolate", ["ciocolata neagra", "ciocolată neagră", "dark chocolate", "amaruie", "amăruie"]),
        ("white_chocolate", ["ciocolata alba", "ciocolată albă", "white chocolate"]),
        ("filled_chocolate", ["ciocolata umpluta", "ciocolată umplută", "filled chocolate", "praline"]),
        ("wafers", ["napolitana", "napolitană", "wafer", "wafers"]),
        ("cookies", ["cookies", "biscuiti", "biscuiți", "biscuit"]),
        ("croissant", ["croissant"]),
        ("sweet_bakery", ["gogoasa", "gogoașă", "brioche", "cozonac", "chec", "muffin", "brownie"]),
        ("cereal_bar", ["cereal bar", "baton cereale", "baton cu cereale"]),
        ("protein_bar", ["protein bar", "baton proteic", "proteic bar"]),
        ("potato_chips", ["potato chips", "cartofi chips", "chips cartofi", "lay's", "lays", "pringles"]),
        ("tortilla_chips", ["tortilla chips", "nachos", "doritos"]),
        ("puffs", ["pufuleti", "pufuleți", "pufulet", "porumb expandat", "snack porumb"]),
        ("pretzels", ["covrigei", "pretzels", "sticks", "saratele", "sărățele"]),
        ("roasted_nuts", ["arahide prajite", "arahide prăjite", "alune prajite", "alune prăjite", "migdale", "caju", "cashew", "pistachio", "fistic"]),
        ("dried_fruit", ["fructe uscate", "stafide", "curmale", "prune uscate", "dried fruit"]),
        ("tomato_sauce", ["sos de rosii", "sos de roșii", "tomato sauce", "passata", "bulion"]),
        ("hot_sauce", ["sos iute", "hot sauce", "chili sauce", "tabasco", "sriracha"]),
        ("soy_sauce", ["sos de soia", "soy sauce"]),
        ("salad_dressing", ["dressing", "salad dressing", "vinegret"]),
        ("pesto_sauce", ["pesto"]),
        ("pasta_sauce", ["sos paste", "sos pentru paste", "pasta sauce", "bolognese", "carbonara"]),
        ("olive_oil", ["ulei de masline", "ulei de măsline", "olive oil"]),
        ("sunflower_oil", ["ulei floarea soarelui", "ulei de floarea soarelui", "sunflower oil"]),
        ("tomato_canned", ["conserva rosii", "conservă roșii", "canned tomatoes", "rosii cuburi", "roșii cuburi"]),
        ("corn_canned", ["conserva porumb", "conservă porumb", "canned corn", "porumb dulce"]),
        ("bean_canned", ["conserva fasole", "conservă fasole", "canned beans", "fasole conserva", "fasole conservă"]),
        ("tuna_canned", ["conserva ton", "conservă ton", "canned tuna", "ton conserva", "ton conservă"]),
        ("pate", ["pate", "pateu"]),
        ("olives", ["masline", "măsline", "olives"]),
        ("pickled_cucumbers", ["castraveti murati", "castraveți murați", "pickled cucumbers"]),
        ("spaghetti_pasta", ["spaghetti", "spaghete"]),
        ("short_pasta", ["penne", "fusilli", "farfalle", "macaroni", "macaroane"]),
        ("basmati_rice", ["basmati"]),
        ("round_rice", ["orez bob rotund", "round rice", "risotto"]),
        ("wheat_flour", ["faina alba", "făină albă", "wheat flour", "faina grau", "făină grâu"]),
        ("cornmeal", ["malai", "mălai", "cornmeal"]),
        ("cocoa_powder", ["cacao pudra", "cacao pudră", "cocoa powder"]),
        ("yeast_baking", ["drojdie", "yeast", "praf de copt", "baking powder"]),
        ("chicken_meat", ["pui", "chicken"]),
        ("pork_meat", ["porc", "pork"]),
        ("beef_meat", ["vita", "vită", "beef"]),
        ("turkey_meat", ["curcan", "turkey"]),
        ("minced_meat", ["carne tocata", "carne tocată", "minced meat"]),
        ("salami", ["salam", "salami"]),
        ("ham", ["sunca", "șuncă", "ham", "jambon", "prosciutto", "muschi file", "mușchi file"]),
        ("sausages", ["carnati", "cârnați", "sausage", "sausages", "cremvursti", "crenvurști"]),
        ("smoked_fish", ["peste afumat", "pește afumat", "smoked fish", "somon afumat"]),
        ("frozen_pizza", ["pizza congelata", "pizza congelată", "frozen pizza"]),
        ("frozen_fries", ["cartofi congelati", "cartofi congelați", "frozen fries", "french fries"]),
        ("hummus", ["hummus", "humus"]),
        ("ready_pasta", ["paste gata", "ready pasta", "pasta salad"]),
        ("ready_salad", ["salata gata", "salată gata", "ready salad"]),
        ("ready_soup", ["supa", "supă", "ciorba", "ciorbă", "soup", "instant soup"]),
        ("baby_puree_fruit", ["piure fructe bebelusi", "piure fructe bebeluși", "baby fruit puree"]),
        ("baby_puree_vegetable", ["piure legume bebelusi", "piure legume bebeluși", "baby vegetable puree"]),
    ]
    priority_family_rules.extend([
        ("flavoured_water", ["apa aromata", "apă aromată", "flavoured water", "flavored water", "vitamin water"]),
        ("apple_juice", ["suc de mere", "apple juice"]),
        ("orange_juice", ["suc de portocale", "orange juice"]),
        ("multivitamin_juice", ["multivitamin", "multi vitamin", "suc multifruct", "suc tropical"]),
        ("smoothie", ["smoothie"]),
        ("nectar", ["nectar"]),
        ("isotonic_drink", ["isotonic", "izotonic", "gatorade", "powerade", "sport drink", "sports drink"]),
        ("alcohol_free_beer", ["bere fara alcool", "bere fără alcool", "non alcoholic beer", "alcohol free beer", "0.0 beer", "0,0 beer"]),
        ("radler_beer", ["radler"]),
        ("lager_beer", ["lager", "pilsner", "pils", "bere blonda", "bere blondă"]),
        ("wheat_beer", ["bere nefiltrata", "bere nefiltrată", "weissbier", "weizen", "wheat beer"]),
        ("dark_beer", ["bere bruna", "bere brună", "dark beer", "stout", "porter"]),
        ("uht_milk", ["lapte uht", "uht milk"]),
        ("lactose_free_milk", ["lapte fara lactoza", "lapte fără lactoză", "lactose free milk"]),
        ("oat_milk", ["bautura ovaz", "băutură ovăz", "lapte ovaz", "oat drink", "oat milk"]),
        ("almond_milk", ["bautura migdale", "băutură migdale", "lapte migdale", "almond drink", "almond milk"]),
        ("soy_milk", ["bautura soia", "băutură soia", "lapte soia", "soy drink", "soy milk"]),
        ("kefir", ["kefir", "chefir", "sana", "lapte batut", "lapte bătut"]),
        ("protein_pudding", ["budinca proteica", "budincă proteică", "protein pudding"]),
        ("pudding", ["budinca", "budincă", "pudding", "danette"]),
        ("rice_pudding", ["orez cu lapte", "rice pudding"]),
        ("custard_dessert", ["crema desert", "cremă desert", "custard"]),
        ("ice_cream_bar", ["inghetata baton", "înghețată baton", "ice cream bar", "magnum", "snickers ice cream"]),
        ("ice_cream_cone", ["inghetata cornet", "înghețată cornet", "ice cream cone", "cornet"]),
        ("ice_cream_cup", ["inghetata cupa", "înghețată cupă", "ice cream cup", "gelatelli"]),
        ("sorbet", ["sorbet"]),
        ("cornflakes", ["corn flakes", "fulgi de porumb"]),
        ("muesli", ["muesli", "musli"]),
        ("granola", ["granola"]),
        ("oats", ["ovaz", "ovăz", "oat flakes", "fulgi de ovaz", "fulgi de ovăz"]),
        ("rice_cakes", ["rondele orez", "rice cakes", "puffed rice cakes"]),
        ("sunflower_seeds", ["seminte floarea soarelui", "semințe floarea soarelui", "sunflower seeds"]),
        ("pumpkin_seeds", ["seminte dovleac", "semințe dovleac", "pumpkin seeds"]),
        ("trail_mix", ["mix fructe uscate", "trail mix", "student mix"]),
        ("bbq_sauce", ["sos barbeque", "sos barbecue", "bbq sauce"]),
        ("garlic_sauce", ["sos usturoi", "garlic sauce"]),
        ("salsa_sauce", ["salsa", "chunky salsa"]),
        ("sweet_chili_sauce", ["sweet chili", "sos chili dulce"]),
        ("dijon_mustard", ["dijon"]),
        ("light_mayonnaise", ["maioneza light", "maioneză light", "light mayonnaise"]),
        ("salt", ["sare", "salt"]),
        ("pepper", ["piper", "pepper"]),
        ("paprika", ["boia", "paprika"]),
        ("spice_mix", ["mix condimente", "amestec condimente", "seasoning mix", "condimente pentru"]),
        ("stock_cube", ["cub supa", "cub supă", "stock cube", "bouillon"]),
        ("toast_bread", ["paine toast", "pâine toast", "toast bread"]),
        ("sliced_bread", ["paine feliata", "pâine feliată", "sliced bread"]),
        ("wholegrain_bread", ["paine integrala", "pâine integrală", "wholegrain bread", "whole wheat bread"]),
        ("buns", ["chifle", "burger buns", "hot dog buns"]),
        ("tortilla_wrap", ["tortilla wrap", "lipie", "wrap"]),
        ("cup_noodles", ["cup noodles", "noodles cup", "taitei la pahar", "tăiței la pahar"]),
        ("ramen_noodles", ["ramen", "buldak", "samyang", "shin ramyun"]),
        ("whey_protein", ["whey protein", "proteina zer", "protein powder", "pudra proteica", "pudră proteică"]),
        ("canned_sardines", ["sardine", "sardines"]),
        ("canned_mackerel", ["macrou conserva", "macrou conservă", "canned mackerel"]),
        ("canned_peas", ["mazare conserva", "mazăre conservă", "canned peas"]),
        ("canned_chickpeas", ["naut conserva", "năut conservă", "canned chickpeas"]),
        ("canned_lentils", ["linte conserva", "linte conservă", "canned lentils"]),
        ("vegetable_spread", ["pasta vegetala", "pastă vegetală", "vegetable spread", "zacusca", "zacuscă"]),
        ("jam", ["gem", "dulceata", "dulceață", "marmelada", "marmeladă"]),
        ("honey", ["miere", "honey"]),
        ("frozen_fruit", ["fructe congelate", "frozen fruit"]),
        ("frozen_vegetable_mix", ["mix legume congelate", "amestec legume congelate", "frozen vegetable mix"]),
        ("frozen_dessert", ["desert congelat", "frozen dessert"]),
        ("baby_biscuits", ["biscuiti bebelusi", "biscuiți bebeluși", "baby biscuits"]),
        ("baby_snack", ["snack bebelusi", "snack bebeluși", "baby snack"]),
    ])

    label_only_priority_families = {
        "sparkling_water",
        "still_water",
        "olive_oil",
        "sunflower_oil",
        "wheat_flour",
        "cornmeal",
        "cocoa_powder",
        "yeast_baking",
    }

    for family, tokens in priority_family_rules:
        source_text = label_text_value if family in label_only_priority_families else text_value
        if any(normalize_search_text(token) in source_text for token in tokens):
            return family

    yogurt_words = ["iaurt", "yogurt", "yoghurt", "zuzu", "activia", "skyr"]
    yogurt_fruit_words = [
        "fruct",
        "fructe",
        "capsuni",
        "căpșuni",
        "strawberry",
        "zmeura",
        "zmeură",
        "raspberry",
        "afine",
        "blueberry",
        "piersica",
        "piersică",
        "peach",
        "cirese",
        "cireșe",
        "cherry",
        "vanilie",
        "vanilla",
        "caise",
        "apricot",
    ]
    if text_has_any(yogurt_words):
        if text_has_any(yogurt_fruit_words):
            return "fruit_yogurt"
        return "plain_yogurt"

    if label_has_any(["salam", "carnati", "cârnați", "ham", "prosciutto", "jambon", "sunca", "șuncă", "muschi file", "mușchi file", "bacon", "parizer", "mortadella", "pastrama", "pastramă", "mezel", "mezeluri"]):
        return "processed_meat"

    if label_has_any(["cafea boabe", "cafea macinata", "cafea măcinată", "ground coffee", "coffee beans", "instant coffee", "ness", "nescafe", "espresso capsules", "capsule cafea"]):
        return "coffee_beans"

    if label_has_any(["ceai plic", "ceai plicuri", "ceai plante", "ceai negru", "ceai verde", "herbal tea", "tea bags", "infuzie", "infusion"]) and not label_has_any(["ice tea", "iced tea", "ceai rece", "kombucha"]):
        return "tea_bags"

    if label_has_any(["peste congelat", "pește congelat", "frozen fish", "fish fingers", "creveti congelati", "creveți congelați"]):
        return "frozen_fish"

    if label_has_any(["carne congelata", "carne congelată", "frozen meat", "pui congelat", "chicken frozen"]):
        return "frozen_meat"

    if label_has_any(["legume congelate", "frozen vegetables", "frozen vegetable"]):
        return "frozen_vegetable"

    detailed_family_rules = [
        (
            "instant_noodles",
            [
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
            ],
        ),
        ("baby_food", ["baby food", "baby milk", "infant", "bebelus", "bebeluș", "piure bebelusi", "piure bebeluși"]),
        ("beer", ["bere", "beer", "ursus", "timisoreana", "timișoreana", "ciuc", "bergenbier", "heineken", "silva", "tuborg", "carlsberg", "peroni", "stella", "corona", "kozel", "lager", "pilsner", "radler", "en beers"]),
        ("alcoholic_drink", ["alcool", "alcohol", "vin", "wine", "vodka", "whisky", "cidru", "cider", "lichior", "liqueur", "spirits", "alcoholic beverages"]),
        ("energy_drink", ["energy", "energiz", "red bull", "redbull", "monster", "hell", "burn", "rockstar", "taurina", "taurine", "en energy-drinks"]),
        ("coffee_drink", ["coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee", "cold brew", "frappe", "en iced-coffees"]),
        ("coffee_beans", ["cafea boabe", "cafea macinata", "cafea măcinată", "ground coffee", "coffee beans", "instant coffee", "ness", "nescafe", "espresso capsules", "capsule cafea"]),
        ("cola", ["cola", "pepsi", "coca cola", "coca-cola", "cocacola"]),
        ("tea_drink", ["ice tea", "iced tea", "ceai rece", "ceai verde", "tea drink", "kombucha"]),
        ("tea_bags", ["ceai plic", "ceai plicuri", "ceai plante", "ceai negru", "ceai verde", "herbal tea", "tea bags", "infuzie", "infusion"]),
        ("sports_drink", ["isotonic", "sport drink", "sports drink", "gatorade", "powerade", "electrolyte"]),
        ("carbonated_soft_drink", ["bautura carbogazoasa", "băutură carbogazoasă", "soft drink", "soda", "fanta", "sprite", "mirinda", "schweppes", "tonic", "7up"]),
        ("fruit_juice", ["suc", "juice", "nectar", "smoothie", "limonada", "limonadă", "orange juice", "apple juice", "en fruit-juices"]),
        ("syrup_concentrate", ["sirop", "syrup", "concentrat", "concentrate", "cordial"]),
        ("flavoured_water", ["apa aromata", "apă aromată", "flavoured water", "flavored water", "vitamin water"]),
        ("water", ["apa", "water", "mineral", "minerala", "minerale", "eau", "sidi", "aquafina", "ain atlas", "spring", "en waters"]),
        ("ice_cream", ["inghetata", "înghețată", "ice cream", "icecream", "gelato", "sorbet", "gelatelli", "en ice-creams"]),
        ("dairy_dessert", ["danette", "budinca", "budincă", "pudding", "custard", "desert lactat", "dairy dessert", "crema desert", "crème dessert"]),
        ("fruit_yogurt", ["iaurt cu fruct", "iaurt fructe", "yogurt fruit", "fruit yogurt", "yoghurt fruit", "zuzu fruct", "activia fruct", "en fruit-yogurts"]),
        ("plain_yogurt", ["iaurt natural", "iaurt grecesc", "greek yogurt", "plain yogurt", "yoghurt natural", "skyr", "en plain-yogurts"]),
        ("kefir", ["kefir", "chefir", "sana", "lapte batut", "lapte bătut", "ayran"]),
        ("butter", ["unt", "butter", "unt gras", "unt tartinabil"]),
        ("cream", ["smantana", "smântână", "sour cream", "frisca", "frișcă", "whipping cream", "cooking cream"]),
        ("cottage_cheese", ["branza proaspata", "brânză proaspătă", "branza de vaci", "brânză de vaci", "cottage cheese", "ricotta", "urda"]),
        ("cheese", ["branza", "brânză", "branzeturi", "brânzeturi", "cascaval", "cașcaval", "mozzarella", "telemea", "feta", "cheddar", "gouda", "emmental", "parmesan", "cream cheese", "brie", "camembert", "en cheeses"]),
        ("milk", ["lapte", "milk", "uht", "semi-skimmed milk", "whole milk", "en milks"]),
        ("plant_milk", ["lapte vegetal", "bautura vegetala", "băutură vegetală", "oat drink", "almond drink", "soy drink", "rice drink", "coconut drink", "plant-based milk", "plant based milk", "en plant-based-milks"]),
        ("plant_yogurt", ["iaurt vegetal", "yogurt vegetal", "soy yogurt", "coconut yogurt", "plant-based yogurt", "plant based yogurt"]),
        ("protein", ["protein", "proteic", "proteina", "proteină", "whey", "fitness", "protein bar", "protein powder", "sports nutrition"]),
        ("chips", ["chips", "crisps", "cartofi chips", "potato chips", "nachos", "tortilla chips"]),
        ("crackers", ["crackers", "saratele", "sărățele", "sticks", "covrigei", "pretzels"]),
        ("popcorn", ["popcorn", "porumb expandat"]),
        ("chocolate", ["ciocolata", "ciocolată", "chocolate", "praline", "trufe", "cacao bar"]),
        ("biscuits_wafers", ["biscuit", "biscuiti", "biscuiți", "wafer", "napolitana", "napolitană", "cookies", "wafers"]),
        ("candy", ["candy", "bomboane", "jeleuri", "caramele", "dropsuri", "lollipop"]),
        ("cakes", ["chec", "cake", "tort", "prajitura", "prăjitură", "muffin", "brownie", "cozonac"]),
        ("oats_granola", ["ovaz", "ovăz", "oat", "oats", "oatmeal", "porridge", "granola", "muesli"]),
        ("breakfast_cereal", ["cereale", "cereal", "corn flakes", "flakes", "fulgi", "en breakfast-cereals"]),
        ("ketchup", ["ketchup"]),
        ("mustard", ["mustar", "muștar", "mustard"]),
        ("mayonnaise", ["maioneza", "maioneză", "mayonnaise"]),
        ("sauce", ["sos", "sauce", "salsa", "barbecue sauce", "dressing", "pesto", "sos paste"]),
        ("oil", ["ulei", "oil", "olive oil", "sunflower oil"]),
        ("vinegar", ["otet", "oțet", "vinegar", "balsamic"]),
        ("spices", ["spice", "condiment", "boia", "piper", "sare", "salt", "oregano", "busuioc", "curry", "scortisoara", "scorțișoară"]),
        ("pasta", ["paste", "pasta", "spaghetti", "penne", "fusilli", "tagliatelle"]),
        ("rice", ["orez", "rice", "basmati", "jasmine", "risotto"]),
        ("legumes", ["fasole", "beans", "linte", "lentils", "naut", "năut", "chickpeas", "mazare uscata", "mazăre uscată"]),
        ("canned_fish", ["conserva ton", "conservă ton", "canned tuna", "sardine conserva", "sardines", "macrou conserva", "mackerel canned"]),
        ("canned_meat", ["carne conserva", "carne conservă", "pate", "pateu", "luncheon meat", "corned beef"]),
        ("canned_vegetables", ["conserva porumb", "conservă porumb", "conserva rosii", "conservă roșii", "canned tomatoes", "canned corn", "conserva legume", "conserve legume"]),
        ("pickles_olives", ["muraturi", "murături", "pickles", "castraveti murati", "castraveți murați", "masline", "măsline", "olives"]),
        ("canned_pickles", ["conserva", "conservă", "conserve", "canned", "muraturi", "murături", "pickles", "masline", "măsline", "olives"]),
        ("bread", ["paine", "pâine", "bread", "toast", "bagheta", "baghetă", "chifla", "chiflă", "lipie", "pita"]),
        ("bakery_pastry", ["croissant", "foietaj", "patiserie", "pastry", "gogoasa", "gogoașă", "brioche", "placinta", "plăcintă"]),
        ("flour_baking", ["faina", "făină", "flour", "malai", "mălai", "cornmeal", "drojdie", "yeast", "praf de copt", "baking powder", "cacao pudra", "cocoa powder"]),
        ("sugar_sweetener", ["zahar", "zahăr", "sugar", "indulcitor", "sweetener", "stevia", "eritritol", "xylitol"]),
        ("processed_meat", ["salam", "sausage", "carnati", "cârnați", "ham", "prosciutto", "jambon", "sunca", "șuncă", "muschi file", "mușchi file", "bacon", "parizer", "mortadella", "pastrama", "pastramă"]),
        ("fresh_meat", ["carne", "meat", "porc", "pork", "pui", "chicken", "curcan", "turkey", "vita", "vită", "beef"]),
        ("fish", ["peste", "pește", "fish", "ton", "tuna", "somon", "salmon", "seafood", "creveti", "creveți", "sardine"]),
        ("eggs", ["oua", "ouă", "egg", "eggs"]),
        ("chocolate_spread", ["nutella", "crema alune", "cremă alune", "hazelnut spread", "chocolate spread"]),
        ("peanut_butter", ["peanut butter", "unt arahide", "unt de arahide"]),
        ("jam_honey", ["gem", "jam", "dulceata", "dulceață", "marmelada", "marmeladă", "miere", "honey"]),
        ("spread", ["spread", "crema tartinabila", "cremă tartinabilă", "nutella", "peanut butter", "unt arahide", "gem", "jam", "miere", "honey", "hazelnut spread"]),
        ("nuts", ["nuts", "nuci", "alune", "migdale", "almond", "cashew", "seeds", "seminte", "semințe", "dried fruits"]),
        ("ready_soup", ["supa", "supă", "soup", "ciorba", "ciorbă", "instant soup"]),
        ("sandwich_salad", ["sandwich", "salata", "salată", "wrap", "ready salad"]),
        ("pizza", ["pizza"]),
        ("frozen_vegetable", ["legume congelate", "frozen vegetables", "frozen vegetable"]),
        ("frozen_fish", ["peste congelat", "pește congelat", "frozen fish", "fish fingers", "creveti congelati", "creveți congelați"]),
        ("frozen_meat", ["carne congelata", "carne congelată", "frozen meat", "pui congelat", "chicken frozen"]),
        ("frozen_meal", ["frozen meal", "mancare congelata", "mâncare congelată", "lasagna congelata", "fish fingers"]),
        ("fresh_fruit", ["mere", "apple", "banane", "banana", "portocale", "orange", "lamaie", "lămâie", "struguri", "grapes", "fructe proaspete"]),
        ("fresh_vegetable", ["rosii", "roșii", "tomate", "tomatoes", "castraveti", "castraveți", "cartofi", "potatoes", "ceapa", "ceapă", "morcovi", "carrots", "legume proaspete"]),
        ("baby_formula", ["lapte praf bebelusi", "lapte praf bebeluși", "infant formula", "formula lapte", "baby formula"]),
        ("baby_puree", ["piure bebelusi", "piure bebeluși", "baby puree", "borcanel bebelusi", "borcănel bebeluși"]),
        ("fruit_vegetable", ["fructe", "fruits", "legume", "vegetables", "salata verde", "roșii", "rosii", "mere", "banane"]),
    ]

    for family, tokens in detailed_family_rules:
        if text_has_any(tokens):
            label_only_families = {
                "water",
                "flavoured_water",
                "oil",
                "vinegar",
                "spices",
                "oil_vinegar_spices",
                "sugar_sweetener",
                "flour_baking",
                "coffee_beans",
                "tea_bags",
            }
            if family in label_only_families and not label_has_any(tokens):
                continue
            if family == "water" and text_has_any(["energy", "energiz", "coffee", "cafea", "cola", "pepsi", "beer", "bere"]):
                continue
            return family

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
    beer_words = [
        "bere",
        "beer",
        "ursus",
        "timisoreana",
        "timișoreana",
        "ciuc",
        "bergenbier",
        "heineken",
        "silva",
        "tuborg",
        "carlsberg",
        "peroni",
        "stella",
        "corona",
        "kozel",
        "lager",
        "pilsner",
        "pils",
        "radler",
    ]
    alcohol_words = [
        "alcool",
        "alcohol",
        "vin",
        "wine",
        "vodka",
        "whisky",
        "rom",
        "rum",
        "gin",
        "cidru",
        "cider",
        "lichior",
        "liqueur",
        "spirits",
    ]
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
    baby_food_words = ["baby food", "baby milk", "infant", "bebelus", "bebeluș", "piure bebelusi", "piure bebeluși"]
    plant_based_words = ["plant based", "vegan", "vegetal", "lapte vegetal", "bautura vegetala", "băutură vegetală"]

    if any(word in text_value for word in instant_noodle_words):
        return "instant_noodles"

    if any(word in text_value for word in baby_food_words):
        return "baby_food"

    if any(word in text_value for word in ice_cream_words):
        return "ice_cream"

    if label_has_precise(beer_words) or "en beers" in label_text_value:
        return "beer"

    if (label_has_precise(alcohol_words) or "alcoholic beverages" in label_text_value) and not label_has_precise(["vinegar", "vinaigre", "vinagre", "otet", "oțet"]):
        return "alcoholic_drink"

    if label_has_precise(water_words) and not text_has_precise(
        energy_words + coffee_words + caffeine_words + cola_words
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

    if any(word in text_value for word in plant_based_words):
        return "plant_based"

    if any(word in text_value for word in sweet_snack_words):
        return "sweet_snack"

    if "bauturi" in text_value or "beverage" in text_value or "drink" in text_value:
        return "beverage"

    return "general"


def get_product_recommendation_family(product_data):
    cache_key = get_product_family_cache_key(product_data)
    cached_family = RECOMMENDATION_FAMILY_CACHE.get(cache_key)

    if cached_family:
        return cached_family

    family = _compute_product_recommendation_family(product_data)
    set_limited_cache_item(
        RECOMMENDATION_FAMILY_CACHE,
        cache_key,
        family,
        RECOMMENDATION_DERIVED_CACHE_MAX_ITEMS,
    )
    return family


FLAVOR_KEYWORDS = {
    "vanilla": ["vanilie", "vanilla"],
    "chocolate": ["ciocolata", "ciocolată", "chocolate", "cacao", "cocoa"],
    "strawberry": ["capsuni", "căpșuni", "strawberry"],
    "raspberry": ["zmeura", "zmeură", "raspberry"],
    "blueberry": ["afine", "blueberry"],
    "peach": ["piersica", "piersică", "peach"],
    "apricot": ["caise", "apricot"],
    "cherry": ["cirese", "cireșe", "visine", "vișine", "cherry"],
    "forest_fruit": ["fructe de padure", "fructe de pădure", "berries", "forest fruits"],
    "banana": ["banana", "banane"],
    "apple": ["mar", "măr", "mere", "apple"],
    "orange": ["portocale", "portocala", "portocală", "orange"],
    "lemon": ["lamaie", "lămâie", "lemon"],
    "lime": ["lime"],
    "cola": ["cola"],
    "grape": ["struguri", "grape"],
    "mango": ["mango"],
    "pineapple": ["ananas", "pineapple"],
    "coconut": ["cocos", "coconut"],
    "caramel": ["caramel"],
    "hazelnut": ["alune", "hazelnut"],
    "peanut": ["arahide", "peanut"],
    "pistachio": ["fistic", "pistachio"],
    "bbq": ["bbq", "barbecue"],
    "cheese": ["branza", "brânză", "cheese"],
    "onion": ["ceapa", "ceapă", "onion"],
    "paprika": ["paprika", "boia"],
    "spicy": ["picant", "iute", "spicy", "hot"],
    "salted": ["sarat", "sărat", "salted"],
    "natural": ["natural", "plain", "simplu", "original", "classic", "clasic"],
    "zero": ["zero", "fara zahar", "fără zahăr", "no sugar"],
}


def extract_product_flavor(product_data):
    text_value = product_text_for_recommendation(product_data)

    for flavor, tokens in FLAVOR_KEYWORDS.items():
        if any(normalize_search_text(token) in text_value for token in tokens):
            return flavor

    return None


CATEGORY_BY_RECOMMENDATION_FAMILY = {
    "still_water": "Apă plată",
    "sparkling_water": "Apă minerală carbogazoasă",
    "water": "Apă",
    "flavoured_water": "Apă aromată",
    "lemonade": "Limonade",
    "fruit_juice": "Sucuri și nectaruri",
    "iced_tea": "Ceaiuri reci",
    "kombucha": "Kombucha",
    "tea_drink": "Ceaiuri reci",
    "tea_bags": "Ceaiuri și infuzii",
    "sports_drink": "Băuturi pentru sport",
    "orange_soda": "Băuturi carbogazoase cu portocale",
    "lemon_lime_soda": "Băuturi carbogazoase cu lămâie",
    "tonic_soda": "Băuturi tonice",
    "carbonated_soft_drink": "Băuturi carbogazoase",
    "syrup_concentrate": "Siropuri și concentrate",
    "cola_zero": "Cola fără zahăr",
    "cola_regular": "Cola clasică",
    "cola": "Băuturi răcoritoare",
    "beverage": "Băuturi",
    "zero_energy_drink": "Băuturi energizante fără zahăr",
    "energy_shot": "Shot-uri energizante",
    "energy_drink": "Băuturi energizante",
    "cocoa_drink": "Băuturi cu cacao",
    "coffee_drink": "Băuturi cu cafea",
    "coffee_beans": "Cafea boabe și măcinată",
    "caffeinated_beverage": "Băuturi cu cafeină",
    "beer": "Bere",
    "alcoholic_drink": "Băuturi alcoolice",
    "dairy_dessert": "Deserturi lactate",
    "drinkable_yogurt": "Iaurturi de băut",
    "protein_yogurt": "Iaurturi proteice",
    "greek_yogurt": "Iaurturi grecești",
    "fruit_yogurt": "Iaurturi cu fructe",
    "plain_yogurt": "Iaurturi simple",
    "kefir": "Kefir și lapte bătut",
    "butter": "Unt",
    "sour_cream": "Smântână",
    "whipped_cream": "Frișcă",
    "cream": "Smântână și frișcă",
    "cottage_cheese": "Brânză proaspătă",
    "cheese_spread": "Creme de brânză",
    "processed_cheese": "Brânză topită",
    "hard_cheese": "Cașcaval și brânzeturi tari",
    "soft_cheese": "Brânzeturi moi",
    "feta_telemea": "Telemea și feta",
    "cheese": "Brânzeturi",
    "milk": "Lapte",
    "lactate": "Lactate",
    "plant_milk": "Băuturi vegetale",
    "plant_yogurt": "Iaurturi vegetale",
    "protein": "Proteine și fitness",
    "salty_snack": "Snacks sărate",
    "chips": "Chipsuri",
    "potato_chips": "Chipsuri din cartofi",
    "tortilla_chips": "Chipsuri tortilla",
    "puffs": "Pufuleți și snacks din porumb",
    "crackers": "Crackers și covrigei",
    "pretzels": "Covrigei și sticksuri",
    "popcorn": "Popcorn",
    "sweet_snack": "Dulciuri",
    "milk_chocolate": "Ciocolată cu lapte",
    "dark_chocolate": "Ciocolată neagră",
    "white_chocolate": "Ciocolată albă",
    "filled_chocolate": "Ciocolată umplută",
    "chocolate": "Ciocolată",
    "wafers": "Napolitane",
    "cookies": "Biscuiți",
    "biscuits_wafers": "Biscuiți și napolitane",
    "candy": "Bomboane și jeleuri",
    "croissant": "Croissante",
    "sweet_bakery": "Patiserie dulce",
    "cereal_bar": "Batoane de cereale",
    "protein_bar": "Batoane proteice",
    "cakes": "Prăjituri și checuri",
    "cereal": "Cereale",
    "breakfast_cereal": "Cereale pentru mic dejun",
    "oats_granola": "Ovăz, muesli și granola",
    "sauce": "Sosuri",
    "tomato_sauce": "Sosuri de roșii",
    "hot_sauce": "Sosuri iuți",
    "soy_sauce": "Sosuri de soia",
    "salad_dressing": "Dressinguri pentru salată",
    "pesto_sauce": "Pesto",
    "pasta_sauce": "Sosuri pentru paste",
    "ketchup": "Ketchup",
    "mustard": "Muștar",
    "mayonnaise": "Maioneză",
    "olive_oil": "Ulei de măsline",
    "sunflower_oil": "Ulei de floarea-soarelui",
    "oil": "Uleiuri",
    "vinegar": "Oțet",
    "spices": "Condimente",
    "oil_vinegar_spices": "Uleiuri, oțet și condimente",
    "pasta_rice_legumes": "Paste, orez și leguminoase",
    "pasta": "Paste",
    "spaghetti_pasta": "Spaghete",
    "short_pasta": "Paste scurte",
    "rice": "Orez",
    "basmati_rice": "Orez basmati",
    "round_rice": "Orez pentru risotto și deserturi",
    "legumes": "Leguminoase",
    "wheat_flour": "Făină de grâu",
    "cornmeal": "Mălai",
    "cocoa_powder": "Cacao pudră",
    "yeast_baking": "Drojdie și praf de copt",
    "flavor_extract": "Arome și extracte pentru copt",
    "canned_fish": "Conserve de pește",
    "tuna_canned": "Conserve de ton",
    "canned_meat": "Conserve de carne și pateuri",
    "pate": "Pateuri",
    "canned_vegetables": "Conserve de legume",
    "tomato_canned": "Conserve de roșii",
    "corn_canned": "Porumb la conservă",
    "bean_canned": "Fasole la conservă",
    "pickles_olives": "Murături și măsline",
    "olives": "Măsline",
    "pickled_cucumbers": "Castraveți murați",
    "canned_pickles": "Conserve și murături",
    "ice_cream": "Înghețată",
    "pizza": "Pizza",
    "frozen": "Congelate",
    "frozen_vegetable": "Legume congelate",
    "frozen_fries": "Cartofi congelați",
    "frozen_fish": "Pește congelat",
    "frozen_meat": "Carne congelată",
    "frozen_meal": "Mâncare congelată",
    "frozen_pizza": "Pizza congelată",
    "ready_meal": "Mese gata preparate",
    "ready_pasta": "Paste gata preparate",
    "ready_salad": "Salate gata preparate",
    "hummus": "Hummus",
    "ready_soup": "Supe și ciorbe",
    "sandwich_salad": "Sandwichuri și salate",
    "bread": "Panificație",
    "bakery_pastry": "Patiserie",
    "flour_baking": "Făină și ingrediente pentru copt",
    "sugar_sweetener": "Zahăr și îndulcitori",
    "meat": "Carne",
    "processed_meat": "Mezeluri",
    "salami": "Salam",
    "ham": "Șuncă și mușchi file",
    "sausages": "Cârnați și crenvurști",
    "fresh_meat": "Carne proaspătă",
    "chicken_meat": "Carne de pui",
    "pork_meat": "Carne de porc",
    "beef_meat": "Carne de vită",
    "turkey_meat": "Carne de curcan",
    "minced_meat": "Carne tocată",
    "fish": "Pește și fructe de mare",
    "smoked_fish": "Pește afumat",
    "eggs": "Ouă",
    "fresh_fruit": "Fructe proaspete",
    "fresh_vegetable": "Legume proaspete",
    "fruit_vegetable": "Fructe și legume",
    "chocolate_spread": "Creme de ciocolată",
    "peanut_butter": "Unt de arahide",
    "jam_honey": "Gemuri și miere",
    "spread": "Creme și gemuri",
    "nuts": "Nuci și semințe",
    "roasted_nuts": "Nuci și semințe prăjite",
    "dried_fruit": "Fructe uscate",
    "baby_food": "Alimente pentru copii",
    "baby_formula": "Lapte praf pentru bebeluși",
    "baby_puree": "Piureuri pentru bebeluși",
    "baby_puree_fruit": "Piureuri de fructe pentru bebeluși",
    "baby_puree_vegetable": "Piureuri de legume pentru bebeluși",
    "plant_based": "Alternative vegetale",
    "instant_noodles": "Tăiței instant",
}
CATEGORY_BY_RECOMMENDATION_FAMILY.update({
    "apple_juice": "Suc de mere",
    "orange_juice": "Suc de portocale",
    "multivitamin_juice": "Sucuri multifruct",
    "smoothie": "Smoothie-uri",
    "nectar": "Nectaruri",
    "isotonic_drink": "Băuturi izotonice",
    "alcohol_free_beer": "Bere fără alcool",
    "radler_beer": "Radler",
    "lager_beer": "Bere blondă lager",
    "wheat_beer": "Bere nefiltrată",
    "dark_beer": "Bere brună",
    "uht_milk": "Lapte UHT",
    "lactose_free_milk": "Lapte fără lactoză",
    "oat_milk": "Băuturi vegetale din ovăz",
    "almond_milk": "Băuturi vegetale din migdale",
    "soy_milk": "Băuturi vegetale din soia",
    "protein_pudding": "Budinci proteice",
    "pudding": "Budinci și deserturi cremoase",
    "rice_pudding": "Orez cu lapte",
    "custard_dessert": "Creme desert",
    "ice_cream_bar": "Înghețată pe băț",
    "ice_cream_cone": "Înghețată la cornet",
    "ice_cream_cup": "Înghețată la cupă",
    "sorbet": "Sorbet",
    "cornflakes": "Fulgi de porumb",
    "muesli": "Muesli",
    "granola": "Granola",
    "oats": "Fulgi de ovăz",
    "rice_cakes": "Rondele de orez",
    "sunflower_seeds": "Semințe de floarea-soarelui",
    "pumpkin_seeds": "Semințe de dovleac",
    "trail_mix": "Mixuri de nuci și fructe uscate",
    "bbq_sauce": "Sosuri barbeque",
    "garlic_sauce": "Sosuri de usturoi",
    "salsa_sauce": "Salsa",
    "sweet_chili_sauce": "Sosuri sweet chili",
    "dijon_mustard": "Muștar Dijon",
    "light_mayonnaise": "Maioneză light",
    "salt": "Sare",
    "pepper": "Piper",
    "paprika": "Boia",
    "spice_mix": "Mixuri de condimente",
    "stock_cube": "Cuburi pentru supă",
    "toast_bread": "Pâine toast",
    "sliced_bread": "Pâine feliată",
    "wholegrain_bread": "Pâine integrală",
    "buns": "Chifle",
    "tortilla_wrap": "Lipii și tortilla",
    "cup_noodles": "Tăiței instant la pahar",
    "ramen_noodles": "Ramen instant",
    "whey_protein": "Pudre proteice",
    "canned_sardines": "Conserve de sardine",
    "canned_mackerel": "Conserve de macrou",
    "canned_peas": "Mazăre la conservă",
    "canned_chickpeas": "Năut la conservă",
    "canned_lentils": "Linte la conservă",
    "vegetable_spread": "Paste vegetale tartinabile",
    "jam": "Gemuri și dulcețuri",
    "honey": "Miere",
    "frozen_fruit": "Fructe congelate",
    "frozen_vegetable_mix": "Mixuri de legume congelate",
    "frozen_dessert": "Deserturi congelate",
    "baby_biscuits": "Biscuiți pentru bebeluși",
    "baby_snack": "Gustări pentru bebeluși",
})


GENERIC_CATALOG_CATEGORY_KEYS = {
    "altele",
    "other",
    "general",
    "neconfirmata",
    "neconfirmată",
    "categorie neconfirmata",
    "categorie neconfirmată",
}

BROAD_CATALOG_CATEGORY_KEYS = GENERIC_CATALOG_CATEGORY_KEYS | {
    "bauturi",
    "dulciuri",
    "snacks sarate",
    "cereale",
    "congelate",
    "mese gata preparate",
    "carne",
    "fructe si legume",
    "sosuri si condimente",
    "uleiuri si condimente",
    "paste orez si leguminoase",
    "conserve si muraturi",
    "lactate",
    "alternative vegetale",
}

REPAIRABLE_CATALOG_CATEGORY_KEYS = BROAD_CATALOG_CATEGORY_KEYS | {
    "apa",
    "apa plata",
    "bauturi alcoolice",
    "cafea boabe si macinata",
    "carne de vita",
    "gemuri si dulceturi",
    "mixuri de condimente",
    "mustar dijon",
    "nectaruri",
    "pateuri",
    "paste",
    "paine",
    "orez",
    "peste si fructe de mare",
    "piper",
    "sare",
    "suc de mere",
    "sucuri si nectaruri",
    "sunca si muschi file",
    "zahar si indulcitori",
    "legume proaspete",
    "fructe proaspete",
}


def catalog_category_key(category):
    return normalize_search_text(category)


def is_generic_catalog_category(category):
    return catalog_category_key(category) in GENERIC_CATALOG_CATEGORY_KEYS


def is_broad_catalog_category(category):
    return catalog_category_key(category) in BROAD_CATALOG_CATEGORY_KEYS


def is_repairable_catalog_category(category):
    return catalog_category_key(category) in REPAIRABLE_CATALOG_CATEGORY_KEYS


def label_has_catalog_token(label_text, token):
    normalized_token = normalize_search_text(token)

    if not normalized_token:
        return False

    if " " not in normalized_token and normalized_token.isalpha():
        return bool(re.search(rf"(^|[^a-z0-9]){re.escape(normalized_token)}([^a-z0-9]|$)", label_text))

    return normalized_token in label_text


def label_has_explicit_alcohol_token(product_data):
    product_data = product_data or {}
    label_text = normalize_search_text(" ".join([
        str(product_data.get("name") or ""),
        str(product_data.get("brand") or ""),
    ]))
    alcohol_free_tokens = [
        "sans alcool",
        "fara alcool",
        "fără alcool",
        "non alcoholic",
        "non-alcoholic",
        "alcohol free",
        "0.0",
        "0,0",
    ]
    explicit_alcohol_tokens = [
        "vin",
        "vino",
        "wine",
        "vin de",
        "vin blanc",
        "vin rouge",
        "vin rose",
        "vin rosé",
        "vin mousseux",
        "mousseux",
        "bordeaux",
        "sidi brahim",
        "champagne",
        "prosecco",
        "cidre",
        "vodka",
        "whisky",
        "tequila",
        "cognac",
        "brandy",
        "cointreau",
        "genepi",
        "génépi",
        "chartreuse",
        "liqueur",
        "beer",
        "biere",
        "bière",
        "bere",
        "alcool",
        "alcohol",
    ]

    if any(
        label_has_catalog_token(label_text, token)
        for token in alcohol_free_tokens
    ):
        return False

    return any(
        label_has_catalog_token(label_text, token)
        for token in explicit_alcohol_tokens
    )


def infer_catalog_category_from_label(product_data, use_family_fallback=True):
    product_data = product_data or {}
    off_categories = product_data.get("offCategories") or []

    if isinstance(off_categories, str):
        off_categories = [off_categories]

    label_text = normalize_search_text(" ".join([
        str(product_data.get("name") or ""),
        str(product_data.get("brand") or ""),
        " ".join(str(item or "") for item in off_categories),
    ]))

    def has(tokens):
        return any(label_has_catalog_token(label_text, token) for token in tokens)

    ingredient_text = normalize_search_text(str(product_data.get("ingredients") or ""))

    def ingredients_have(tokens):
        return any(label_has_catalog_token(ingredient_text, token) for token in tokens)

    if not label_text:
        return None

    if re.search(r"^(huile|ulei|olive oil|sunflower oil)", label_text):
        return "Uleiuri"

    if has(["bere fara alcool", "bere fără alcool", "non alcoholic beer", "non-alcoholic beer", "alcohol free beer", "0.0 beer", "0,0 beer"]):
        return "Bere fără alcool"

    if has(["sans alcool", "fara alcool", "fără alcool", "non alcoholic", "non-alcoholic", "alcohol free"]):
        return "Băuturi răcoritoare"

    if has(["olives", "masline", "măsline"]) and not re.search(r"^(huile|ulei)", label_text):
        return "Murături și măsline"

    label_rules = [
        ("Băuturi alcoolice", ["vin", "vino", "wine", "vin de", "vin blanc", "vin rouge", "vin rose", "vin rosé", "vin mousseux", "mousseux", "bordeaux", "sidi brahim", "champagne", "prosecco", "cidre", "cider", "vodka", "whisky", "scotch whisky", "liqueur", "cointreau", "génépi", "genepi", "chartreuse", "chateau", "château", "domaine la", "pineau", "eau de vie", "medoc", "médoc", "cotes de provence", "côtes de provence", "coteaux varois", "côteaux varois"]),
        ("Castraveți murați", ["cornichon", "cornichons", "gherkin", "pickled cucumber", "castraveti murati", "castraveți murați"]),
        ("Murături și măsline", ["tapenade", "capers", "capres", "câpres", "caperberries"]),
        ("Conserve de legume", ["canned prepared fine peas", "canned peas", "petits pois", "petit pois", "pois doux", "groszek", "zoldborso", "zöldborsó", "erbsen mit mohrchen", "erbsen mit möhrchen", "kukurica", "kukuruz", "goldmais", "mais doux", "maïs doux", "porumb dulce", "ciuperci feliate", "sliced mushrooms", "mushrooms", "champignons", "гъби", "горох", "mexico mix", "mexico mixt", "creatif mexico", "créatif mexico"]),
        ("Leguminoase", ["kichererbsen", "pois chiches", "chickpeas", "naut", "năut"]),
        ("Paste", ["ravioli", "raviolis", "linguine", "tagliatelle", "coquillettes", "chifferini", "farfalle", "pipe regate", "macaroni", "fusilli", "torti"]),
        ("Cuburi pentru supă", ["bouillon", "stock cube"]),
        ("Supe și ciorbe", ["potagere", "potagère", "potage", "veloute", "velouté", "soupe", "supa"]),
        ("Mese gata preparate", ["hachis parmentier", "moussaka", "parmentier", "bouchees a la reine", "bouchées à la reine"]),
        ("Paste", ["spatzle", "spätzle", "lasagnettes", "cannelloni", "lasagnes", "lasagna", "fettuccine", "torsades", "bolognaise"]),
        ("Sosuri pentru paste", ["carbonara"]),
        ("Sosuri de roșii", ["napoletana", "rajcatova omacka", "rajčatová omáčka", "sauce italienne", "sauce bolognaise", "pesto", "basilic", "confit de tomate", "tomate sechee", "tomate séchée"]),
        ("Muștar", ["mustard", "senf", "moutarde", "mustar", "muștar"]),
        ("Pizza", ["pizza"]),
        ("Patiserie", ["pies", "pie", "feuilletes", "feuilletés", "tarte"]),
        ("Patiserie dulce", ["flan patissier", "flan pâtissier", "amandine", "after eight", "wonk", "pain chocolat", "donuts", "donut", "muffins", "muffin"]),
        ("Biscuiți", ["petit brun", "petit ecolier", "petit écolier", "dormi", "dörmi", "belvita", "galletas", "biscuits", "cookies"]),
        ("Pateuri", ["pate vegetal", "pate de foie", "le pate", "chicken pate", "pateu"]),
        ("Cârnați și crenvurști", ["butifarra", "chipolata", "merguez", "kielbasa", "kiełbasa", "saucisses", "sausage", "sausages"]),
        ("Salam", ["saucisson", "salami", "salam"]),
        ("Carne de pui", ["volaille", "kipdrumsticks", "pui", "poulet", "chicken", "kip", "drumsticks"]),
        ("Carne de curcan", ["dinde", "turkey", "pavo"]),
        ("Carne de porc", ["svinjski", "svinjska", "svinjetina", "boczek", "golonka", "rebra", "chorizo", "porc", "pork", "wieprzowa"]),
        ("Carne tocată", ["carne tocata", "carne tocată", "carne picada", "mljevena"]),
        ("Carne", ["canard", "lapin", "mouton"]),
        ("Conserve de ton", ["thon", "tuna", "canned tuna"]),
        ("Conserve de sardine", ["sardine", "sardines"]),
        ("Pește și fructe de mare", ["pilchards", "harengs", "hareng", "truite", "anchois"]),
        ("Uleiuri", ["huile d olive", "huile d'olive", "huile d’olive", "huile de colza", "olive oil", "ulei de masline", "ulei de măsline"]),
        ("Murături și măsline", ["muraturi", "murături", "pickles", "kimchi", "masline", "măsline", "olives", "creatif olive", "créatif olive"]),
        ("Orez cu lapte", ["riz au lait", "rice pudding"]),
        ("Creme de ciocolată", ["pate a tartiner", "pâte à tartiner", "hazelnut spread"]),
        ("Salam", ["saucisson", "salami", "salam"]),
        ("Șuncă și mușchi file", ["sunca", "șuncă", "ham", "jambon", "prosciutto"]),
        ("Mezeluri", ["sunculita", "șunculiță", "parizer", "pastrami", "pastrama", "slaninuta", "slăninuță"]),
        ("Carne de vită", ["boeuf", "bœuf", "carne de vita", "carne de vită", "buey", "veau", "beef", "vita", "vită", "bovine", "rumsteck", "steak", "junetina", "wagyu"]),
        ("Brânzeturi", ["rouy", "chandor", "reblochon", "cantal", "gouda", "babybel", "kiri", "fromaga", "frommage", "vache qui rit", "tartine et cuisine", "cantadou", "cantorel", "ptit basque", "p'tit basque", "tomme", "brebis", "salakis", "livarot", "roq croque", "roq'croque", "saint albray", "saint agur", "pave de brebis", "pavé de brebis", "ovci syr", "ovčí sýr", "fromage", "cheese", "branza", "brânză", "comte", "comté", "morbier", "fourme", "roquefort", "gruyere", "gruyère", "edam", "parmigiano", "parmesan", "belval"]),
        ("Pește și fructe de mare", ["anchovy", "anchovies", "losos", "lososa", "pstrag", "pstrąg", "trout"]),
        ("Oțet", ["otet", "oțet", "vinegar", "vinaigre", "vinagre", "essig", "reisessig", "apfelessig", "aceto", "cremaceto", "melfor", "melfort", "aceto balsamico", "balsamic vinegar", "balsamique"]),
        ("Uleiuri", ["ulei", "oil", "huile", "huiles"]),
        ("Nuci și semințe", ["cacahuete", "cacahuètes", "cacahuetes", "peanut", "peanuts", "erdnusse", "erdnüsse"]),
        ("Cacao pudră", ["cacao", "cocoa"]),
        ("Băuturi cu cacao", ["banania", "nesquik", "nesquick", "ovomaltine", "ovaltine", "bourn vita", "ptit dejeuner", "p'tit dejeuner", "boisson cacaotee", "boisson cacaotée", "cacaotee", "cacaotée", "kaomix", "goody cao"]),
        ("Ciocolată", ["schoko", "lebkuchen", "chocolate", "chocolat", "ciocolata", "ciocolată", "schokolade", "schokokiss", "nugat", "belgian choc"]),
        ("Gemuri și dulcețuri", ["confiture", "jam"]),
        ("Miere", ["pastilles miel", "miel de", "honey"]),
        ("Kombucha", ["kombucha"]),
        ("Băuturi energizante", ["monster", "red bull", "redbull", "mango loco", "khaotic", "ultra vice", "ultra peachy", "peachy keen", "juneberry", "power king", "colossus", "pipeline punch", "golden eagle", "booster", "absolute zero", "bebida energetica", "bebida energética", "kong strong", "awake koffein", "dragon", "lucozade", "energy drink"]),
        ("Băuturi pentru sport", ["hydrate perform", "hydrate & perform", "hidra iso", "thirst quencher", "gatorade", "powerade"]),
        ("Apă aromată", ["volvic tee", "volvic aro", "volvic essence", "touch of fruit", "vitamin water", "eau fruitiee", "eau fruitiée", "saveur cassis"]),
        ("Apă", ["evian", "vittel", "volvic water", "eau volvic", "hepar", "hépar", "perrier", "st amand eau", "eau minerale", "eau minérale", "mineral water", "spring water", "sparkling spring water", "non carbonated natural mineral water"]),
        ("Băuturi răcoritoare", ["sparkling white peach", "sparkling grape", "grape rush", "white peach", "boisson petillante", "boisson pétillante", "fruit punch", "fruity", "wassermelone", "kaktusfrucht"]),
        ("Limonade", ["lemonade", "limonada", "limonadă"]),
        ("Băuturi răcoritoare", ["fiz citron", "juiced berry"]),
        ("Siropuri și concentrate", ["sirop"]),
        ("Pizza", ["pizza"]),
        ("Sandwichuri și salate", ["sandwich", "sándwich", "sandvis", "salad", "salata", "salată"]),
        ("Cașcaval și brânzeturi tari", ["beaufort", "emmental", "cheddar", "parmesan", "fromage de brebis"]),
        ("Brânzeturi moi", ["camembert", "brie"]),
        ("Brânză proaspătă", ["ricotta", "cottage cheese", "cream cheese"]),
        ("Telemea și feta", ["feta", "telemea"]),
        ("Lapte", ["lait concentre", "lait concentré", "milkshake", "lactaline"]),
        ("Deserturi lactate", ["neige de lait", "recette d abricot", "recette de framboise", "recette cremeuse", "recette crémeuse", "danette", "activia", "actimel", "gervais", "gervita", "jockey", "taillefine", "light and free", "light free", "danio", "liegeois", "liégeois", "la chocolaterie", "petit frais", "lait entier", "bicouche", "brasse", "brassé", "dessert fondant", "fondant a la vanille", "fondant à la vanille", "crousti 3 choco", "yaourt", "yaourts", "yogurt", "kvarg", "maronsui", "maronsui's", "la laitiere", "la laitière", "milkybar mousse", "secret de mousse", "mousse", "semoule au lait", "petit pot de creme", "petit pot de crème", "creme dessert", "crème dessert", "creme caramel", "crème caramel", "creme brulee", "crème brûlée", "velours de creme", "velours de crème", "ferme fondant", "ferme et fondant", "sveltesse", "dalky", "clafoutis", "far aux pruneaux"]),
        ("Smântână", ["creme entiere", "crème entière", "prix choc", "societe creme", "société crème", "creme 23", "crème 23", "creme fraiche", "crème fraîche"]),
        ("Băuturi vegetale", ["oat original", "plant based vegan drink", "whole oat plant based", "vegan drink"]),
        ("Boia", ["boia", "paprika", "pimenton", "pimentón"]),
        ("Piper", ["piper", "poivre", "pepper", "pimienta", "pfeffer"]),
        ("Unt", ["beurre pasteurise", "beurre pasteurisé", "beurre doux", "beurre bio", "beurre tendre", "beurre moule", "beurre moulé", "motte beurre", "beurre demi sel", "beurre demi-sel", "demi sel", "demi-sel", "salted butter", "president salted butter", "unsalted butter", "unt"]),
        ("Sare", ["sare de mare", "sea salt", "iodized salt", "iodised salt", "sel de mer"]),
        ("Arome și extracte pentru copt", ["vanilla extract", "extract vanilie", "extrait de vanille", "vanilla aroma", "aroma vainilla"]),
        ("Arome și extracte pentru copt", ["fleurs d oranger", "fleurs doranger", "fleur d oranger", "fleur doranger", "eau de fleurs", "orange blossom water"]),
        ("Unt", ["beurre pasteurise", "beurre pasteurisé", "beurre doux", "beurre bio", "beurre tendre", "beurre moule", "beurre moulé", "motte beurre", "beurre demi sel", "beurre demi-sel", "demi sel", "demi-sel", "salted butter", "president salted butter", "unsalted butter", "unt"]),
        ("Zahăr și îndulcitori", ["cassonade", "stevia", "edulcorant", "edulcorants", "sweetener", "sweeteners", "sucre", "zahar", "zahăr", "brown sugar"]),
        ("Ceaiuri și infuzii", ["ceai", "tea", "the vert", "the noir", "thé vert", "thé noir", "black tea", "green tea", "earl grey", "tea bags", "infusion", "infuzie", "tisane", "rooibos"]),
        ("Ceaiuri reci", ["ice tea", "iced tea", "ceai rece"]),
        ("Băuturi cu cafea", ["iced coffee", "ice coffee", "cold brew"]),
        ("Sosuri de roșii", ["sos de rosii", "sos de roșii", "sauce tomate", "sauce aux tomates", "tomato sauce", "tomato paste", "passata", "bulion", "salsa dip", "mild tomato"]),
        ("Conserve de roșii", ["tomat crushed", "crushed tomatoes", "star tomat", "tomat sachy", "tomate triturado", "tomates pelees", "tomates pelées", "tomate pelee", "tomate pelée", "tomates pelee", "tomates pelée", "tomatenpuree", "chopped tomatoes", "pulpe de tomates", "puree de tomates", "purée de tomates", "polpa", "paradajky"]),
        ("Leguminoase", ["lentilles", "lentils", "linte", "pois chiches", "pois casses", "pois cassés", "chickpeas", "naut", "năut", "haricots blancs", "haricots rouges", "flageolets", "fasole", "bean", "beans", "dal", "alubia", "garbanzo", "garbazo", "grao de bico", "grão de bico"]),
        ("Salate gata preparate", ["salade", "salata", "salată", "coleslaw"]),
        ("Mixuri de legume congelate", ["poelee", "poêlée", "wok de legumes", "wok de légumes", "vegetable mix", "vegetables mixture"]),
        ("Chipsuri din cartofi", ["lay's", "lays"]),
        ("Chipsuri tortilla", ["tortillas chips", "tortilla chips"]),
        ("Cartofi congelați", ["cartofi prajiti", "cartofi prăjiți", "french fries"]),
        ("Legume proaspete", ["krumpir", "bratpaprika"]),
        ("Legume proaspete", ["truffes de chine", "truffes", "asperges", "asparagus", "macedoine", "macédoine", "mazare", "mazăre", "haricots bruns", "avocat", "avocado", "mache", "mâche", "palmito", "epinards", "épinards", "choux", "mais", "maïs", "porumb", "guisantes", "haricot vert", "haricots beurre", "dovlecei", "romatomaten", "carottes", "carrots", "morcovi", "aubergine", "aubergines", "auberginen", "artichaut", "artichauts", "artichoke", "palmiers", "betterave", "celeri", "céleri", "chou", "courgettes", "poivrons", "haricots verts", "petits pois", "pois", "tomates", "tomatoes", "broccoli", "legumes", "légumes", "vegetables", "legumes grilles", "légumes grillés"]),
        ("Ratatouille", ["ratatouille"]),
        ("Sucuri și nectaruri", ["rafraichissant", "gwozey", "boisson hp", "boisson sans sucres", "suc", "juice", "jus de pomme", "jus orange", "jus d orange", "jus d'orange", "jus multifruit", "smoothie", "innocent", "nectar"]),
        ("Fructe proaspete", ["clementine", "clémentine", "compotes", "compote", "fruits rouges", "fruits jaunes", "platano", "plátano", "mandarine", "fraise", "fraises", "cerises", "poire", "ananas", "pineapple", "banana", "banane", "bananes", "mangue", "mangues", "mango", "peche", "pêche", "peches", "pêches", "peaches", "cerise", "cherry", "figues", "figs", "dattes", "dates", "pomme", "apple"]),
        ("Paste", ["gnocchi", "spaghetti", "penne", "fusilli", "macaroni", "paste", "pasta"]),
        ("Orez", ["orez", "riz", "rice", "risotto"]),
        ("Orez cu lapte", ["riz au lait", "rice pudding"]),
        ("Cuscus", ["couscous"]),
        ("Cereale", ["ptites billes", "p'tites billes", "billes miel", "amarante", "epeautre", "épeautre", "quinoa", "bonduelle ceriali"]),
        ("Hummus", ["hummus", "humus"]),
        ("Mese gata preparate", ["galette", "galettes", "vegetable summer rolls", "assortiment asiatique"]),
        ("Pâine", ["flame baked roti", "carrément mie", "carrement mie", "pain maxi", "pane bianco", "pain de mie", "jacquet", "pave aux graines", "pavé aux graines", "gressins", "panini", "bread", "paine", "pâine", "bagheta", "baguette", "blinis", "toast francais", "toast français"]),
        ("Granola", ["granola"]),
        ("Biscuiți", ["petit beurre", "madeleine", "madeleines", "boudoirs", "galletas", "biscuits", "cookies", "belvita"]),
        ("Bomboane și jeleuri", ["car en sac", "haribo", "bubblizz", "long fizz", "tirlibibi", "schtroumpfs"]),
        ("Budinci și deserturi cremoase", ["pudding", "budinca", "budincă"]),
        ("Făină și ingrediente pentru copt", ["agar agar", "preparation en poudre pour gateau", "préparation en poudre pour gâteau", "gateau de semoule", "gâteau de semoule", "bigarreaux confits"]),
        ("Patiserie dulce", ["flan patissier", "flan pâtissier", "amandine", "after eight", "wonk", "ecler", "bagel", "bagels", "krafna", "krafne", "donuts", "donut", "muffins", "muffin", "pain chocolat"]),
        ("Napolitane", ["wafer", "wafers", "napolitana", "napolitană"]),
        ("Snacks sărate", ["souffles gout bacon", "soufflés goût bacon"]),
        ("Batoane proteice", ["protein bar", "baton proteic"]),
        ("Proteine și fitness", ["protein powder", "whey protein", "proteina zer"]),
        ("Alternative vegetale", ["cap vegetal", "cap végétal", "seitan", "plant based burger", "plant based burgers"]),
        ("Băuturi vegetale", ["boisson soja", "soy drink", "oat drink", "almond drink", "bautura vegetala", "băutură vegetală"]),
        ("Conserve de ton", ["conserva ton", "conservă ton", "canned tuna", "tuna"]),
        ("Conserve de sardine", ["sardine"]),
        ("Pește și fructe de mare", ["maquereaux", "maquereau", "colin", "saumon", "salmon", "poisson", "fish"]),
        ("Pește afumat", ["somon afumat", "smoked salmon", "peste afumat", "pește afumat"]),
        ("Pește și fructe de mare", ["losos", "lososa", "pstrag", "pstrąg", "trout", "anchovy", "anchovies"]),
        ("Carne de pui", ["pui", "poulet", "chicken", "kip", "drumsticks"]),
        ("Carne de porc", ["chorizo", "porc", "pork", "wieprzowa"]),
        ("Carne", ["agneau", "lamb", "miel"]),
        ("Pateuri", ["rillettes", "rillettes de volaille", "rillettes d oie"]),
        ("Șuncă și mușchi file", ["sunca", "șuncă", "ham", "jambon", "prosciutto", "tendrissime"]),
        ("Ceaiuri și infuzii", ["chicoree", "chicorée", "menta poleo", "hierba luisa", "manzanilla"]),
        ("Ceaiuri reci", ["the limone", "thè limone", "tea limone"]),
        ("Nuci și semințe", ["dakatine", "arachides", "noix de cajou", "noisettes", "amandes"]),
        ("Fructe uscate", ["pruneaux d agen", "pruneaux d'agen", "pruneaux dagen"]),
        ("Fructe proaspete", ["gariguette"]),
        ("Legume proaspete", ["avocats en morceaux"]),
        ("Paste", ["langue d oiseau", "langue d' oiseau", "langue doiseau"]),
        ("Lapte praf pentru bebeluși", ["nursie croissance", "bledilait croissance", "blédilait croissance"]),
        ("Proteine și fitness", ["forever lite ultra"]),
        ("Mixuri de condimente", ["melange provencal", "mélange provençal", "tomillo", "romero", "coriander", "seasoning", "piment et ail", "jengibre molido", "ginger powder", "spice mix", "condimente"]),
    ]

    for category, tokens in label_rules:
        if has(tokens):
            return category

    if ingredient_text:
        ingredient_rules = [
            ("Carne de porc", ["schweinebauch", "viande de porc", "gorge de porc", "gras de porc"]),
            ("Carne de pui", ["poulet", "viande de poulet", "chicken"]),
            ("Carne de vită", ["viande bovine", "viande de boeuf", "viande de bœuf", "beef"]),
            ("Șuncă și mușchi file", ["jambon", "noix de jambon"]),
            ("Pateuri", ["foie gras", "foie et gras de porc", "rillettes"]),
            ("Pește și fructe de mare", ["poissons", "poisson", "morue", "brochet", "chair helix"]),
            ("Sosuri pentru paste", ["smantana proaspata", "smântână proaspătă", "bacon"]),
            ("Sosuri de roșii", ["rajskym", "rajčatovým", "tomatenmark", "concentre de tomates", "concentré de tomates", "puree de tomates", "purée de tomates", "pulpe de tomates"]),
            ("Supe și ciorbe", ["croutons", "croûtons", "poireaux", "fumet de poissons"]),
            ("Brânzeturi", ["cheese", "cheeses", "cow's milk cheese", "pasteurisierte milch", "tvaroh", "fromage", "fromages", "ferments lactiques"]),
            ("Deserturi lactate", ["yaourt", "lait ecreme", "lait écrémé", "creme dessert", "crème dessert"]),
            ("Lapte", ["lait entier en poudre", "lait ecreme en poudre", "lait écrémé en poudre"]),
            ("Băuturi cu cacao", ["cacao fortement degraisse", "cacao fortement dégraissé"]),
            ("Ciocolată", ["beurre de cacao", "pate de cacao", "pâte de cacao", "cocoa mass", "kakaobutter"]),
            ("Bomboane și jeleuri", ["sirop de glucose", "sirop de glucose fructose", "sorbitols"]),
            ("Biscuiți", ["beurre patissier", "beurre pâtissier", "oeufs frais", "œufs frais"]),
            ("Paste", ["semoule de ble dur", "semoule de blé dur"]),
            ("Legume proaspete", ["aubergines", "champignons", "poivron", "concombre", "tomates", "oignon", "carotte"]),
            ("Mixuri de condimente", ["ciboulette", "persil", "echalote"]),
            ("Legume proaspete", ["feuille de chene", "feuille de chêne", "red chard"]),
            ("Nuci și semințe", ["arachides", "noisettes", "amandes", "noix de cajou"]),
            ("Sucuri și nectaruri", ["jus de pomme", "jus d orange", "jus d'orange", "jus de citron"]),
            ("Apă", ["botte non carbonated natural mineral water", "eau minerale naturelle", "eau minérale naturelle", "spring water"]),
        ]

        for category, tokens in ingredient_rules:
            if ingredients_have(tokens):
                return category

    if not use_family_fallback:
        return None

    family_data = {
        **product_data,
        "category": "",
        "ingredients": "",
        "tag": "",
        "reason": "",
    }
    family = get_product_recommendation_family(family_data)
    inferred = CATEGORY_BY_RECOMMENDATION_FAMILY.get(family)

    if inferred:
        return inferred

    return None


def infer_catalog_category(product_data):
    product_data = product_data or {}
    current_category = str(product_data.get("category") or "").strip()
    use_family_fallback = (
        not current_category
        or is_generic_catalog_category(current_category)
        or is_broad_catalog_category(current_category)
    )
    label_inferred = infer_catalog_category_from_label(
        product_data,
        use_family_fallback=use_family_fallback,
    )

    if label_inferred:
        if (
            not current_category
            or is_generic_catalog_category(current_category)
            or is_broad_catalog_category(current_category)
            or is_repairable_catalog_category(current_category)
        ):
            return label_inferred

    if (
        catalog_category_key(current_category) == "bauturi alcoolice"
        and not label_has_explicit_alcohol_token(product_data)
    ):
        return "Altele"

    if catalog_category_key(current_category) in {"apa", "sare", "zahar si indulcitori"}:
        return "Altele"

    if current_category and not is_generic_catalog_category(current_category):
        return current_category[:100]

    return "Altele"


def should_update_reported_product_category(old_category, new_category):
    old_normalized = normalize_search_text(old_category)
    new_normalized = normalize_search_text(new_category)

    if not new_normalized:
        return False

    if not old_normalized or old_normalized in GENERIC_CATALOG_CATEGORY_KEYS:
        return True

    if new_normalized in {"altele", "other", "general"}:
        return old_normalized == "bauturi alcoolice"

    if old_normalized in BROAD_CATALOG_CATEGORY_KEYS:
        return old_normalized != new_normalized

    if old_normalized in REPAIRABLE_CATALOG_CATEGORY_KEYS:
        return old_normalized != new_normalized

    return False


def find_local_product_for_reported_alternative(product_data):
    if not isinstance(product_data, dict):
        return None

    product_id = product_data.get("id")

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        product_id = None

    if product_id:
        product = db.session.get(Product, product_id)

        if product:
            return product

    barcode = str(product_data.get("barcode") or "").strip()

    if barcode and not barcode.startswith("off-"):
        product = Product.query.filter_by(barcode=barcode).first()

        if product:
            return product

    name = str(product_data.get("name") or "").strip()

    if not name:
        return None

    normalized_name = normalize_search_text(name)
    tokens = [
        token for token in normalized_name.split()
        if len(token) >= 3 and not token.isdigit()
    ][:4]

    if not tokens:
        return None

    query = Product.query.filter(or_(*[
        Product.name.ilike(f"%{token}%")
        for token in tokens
    ]))
    store = str(product_data.get("store") or "").strip()

    if store and store not in {"Open Food Facts", "Catalog online"}:
        query = query.filter(or_(Product.store == store, Product.store == "Open Food Facts"))

    best_product = None
    best_ratio = 0

    for product in query.limit(80).all():
        ratio = SequenceMatcher(None, normalized_name, normalize_search_text(product.name)).ratio()

        if ratio > best_ratio:
            best_product = product
            best_ratio = ratio

    return best_product if best_ratio >= 0.9 else None


def materialize_reported_alternative_product(product_data):
    product = find_local_product_for_reported_alternative(product_data)

    if product:
        return product

    barcode = str(product_data.get("barcode") or "").strip()

    if barcode and not barcode.startswith("off-"):
        try:
            off_product = fetch_off_product_by_barcode(barcode)
        except requests.RequestException as error:
            app.logger.info("OFF product fetch failed during alternative report fix: %s", error)
            off_product = None

        if off_product:
            try:
                off_data = build_product_from_open_food_facts(barcode, off_product, translate_ingredients=False)
                product = save_product_to_local_database(off_data)
                setattr(product, "_created_from_report", True)
                db.session.add(product)
                return product
            except Exception:
                db.session.rollback()
                app.logger.exception("Reported alternative could not be imported from OFF.")

    name = str(product_data.get("name") or "").strip()

    if not name:
        return None

    category = infer_catalog_category(product_data)
    ingredients = str(product_data.get("ingredients") or "").strip()
    calories = parse_optional_float(product_data.get("calories"))
    protein = parse_optional_float(product_data.get("protein"))
    sugar = parse_optional_float(product_data.get("sugar"))
    fat = parse_optional_float(product_data.get("fat"))
    score = parse_optional_float(product_data.get("score"))

    if score is None:
        score = calculate_product_score(category, calories, protein, sugar, fat, ingredients)

    product = Product(
        name=name[:150],
        store=str(product_data.get("store") or product_data.get("source") or "Catalog online").strip()[:100] or "Catalog online",
        category=category[:100],
        barcode=barcode[:80] or None,
        score=score if score is not None else 5.0,
        tag=str(product_data.get("tag") or generate_product_tag(category, calories, protein, sugar, fat, ingredients) or "")[:100],
        image=str(product_data.get("image") or "")[:255] or None,
        price=parse_optional_float(product_data.get("price")),
        price_text=str(product_data.get("priceText") or product_data.get("price_text") or "preț necunoscut")[:100],
        calories=calories,
        protein=protein,
        sugar=sugar,
        fat=fat,
        vegan=bool(product_data.get("vegan")),
        lactose_free=bool(product_data.get("lactoseFree") or product_data.get("lactose_free")),
        natural=bool(product_data.get("natural")),
        reason=str(product_data.get("reason") or generate_product_reason(category, calories, protein, sugar, fat, ingredients) or "")[:5000],
        ingredients=ingredients[:5000] or None,
    )
    setattr(product, "_created_from_report", True)
    db.session.add(product)
    db.session.flush()
    return product


def auto_fix_reported_alternative_category(product_data):
    product = materialize_reported_alternative_product(product_data)

    if not product:
        return None

    product_dict = product_to_dict(product)
    merged_data = {**product_dict, **(product_data or {})}
    inferred_category = infer_catalog_category(merged_data)
    old_category = product.category
    created_from_report = bool(getattr(product, "_created_from_report", False))

    if should_update_reported_product_category(old_category, inferred_category):
        product.category = inferred_category[:100]
        product.tag = generate_product_tag(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        product.reason = generate_product_reason(
            product.category,
            product.calories,
            product.protein,
            product.sugar,
            product.fat,
            product.ingredients,
        )
        db.session.add(product)

        return {
            "fixed": True,
            "product": product,
            "oldCategory": old_category,
            "newCategory": product.category,
            "family": get_product_recommendation_family(product_to_dict(product)),
        }

    if created_from_report and normalize_search_text(product.category) not in {"altele", "other", "general"}:
        return {
            "fixed": True,
            "product": product,
            "oldCategory": str((product_data or {}).get("category") or "neconfirmată").strip() or "neconfirmată",
            "newCategory": product.category,
            "family": get_product_recommendation_family(product_to_dict(product)),
        }

    return {
        "fixed": False,
        "product": product,
        "oldCategory": old_category,
        "newCategory": product.category,
        "family": get_product_recommendation_family(product_to_dict(product)),
    }


FAMILY_COMPATIBILITY = {
    "still_water": {"still_water", "sparkling_water", "water"},
    "sparkling_water": {"sparkling_water", "still_water", "water"},
    "water": {"water", "still_water", "sparkling_water"},
    "flavoured_water": {"flavoured_water", "still_water", "sparkling_water", "water"},
    "fruit_juice": {"fruit_juice", "lemonade"},
    "lemonade": {"lemonade", "fruit_juice"},
    "iced_tea": {"iced_tea", "tea_drink"},
    "kombucha": {"kombucha", "tea_drink"},
    "tea_drink": {"tea_drink", "iced_tea", "kombucha", "fruit_juice"},
    "tea_bags": {"tea_bags"},
    "sports_drink": {"sports_drink", "energy_drink"},
    "orange_soda": {"orange_soda", "lemon_lime_soda", "tonic_soda", "carbonated_soft_drink"},
    "lemon_lime_soda": {"lemon_lime_soda", "orange_soda", "tonic_soda", "carbonated_soft_drink"},
    "tonic_soda": {"tonic_soda", "orange_soda", "lemon_lime_soda", "carbonated_soft_drink"},
    "carbonated_soft_drink": {"carbonated_soft_drink", "orange_soda", "lemon_lime_soda", "tonic_soda", "cola", "cola_zero", "cola_regular"},
    "syrup_concentrate": {"syrup_concentrate"},
    "cola_zero": {"cola_zero", "cola", "cola_regular", "energy_drink", "zero_energy_drink"},
    "cola_regular": {"cola_regular", "cola", "cola_zero"},
    "cola": {"cola", "cola_zero", "cola_regular"},
    "beverage": {"beverage", "fruit_juice", "lemonade", "iced_tea", "kombucha", "tea_drink", "sports_drink", "cola", "cola_zero", "cola_regular", "carbonated_soft_drink", "orange_soda", "lemon_lime_soda", "tonic_soda", "flavoured_water"},
    "zero_energy_drink": {"zero_energy_drink", "energy_drink", "coffee_drink", "caffeinated_beverage", "cola_zero"},
    "energy_shot": {"energy_shot", "energy_drink", "caffeinated_beverage"},
    "energy_drink": {"energy_drink", "zero_energy_drink", "energy_shot", "coffee_drink", "caffeinated_beverage"},
    "cocoa_drink": {"cocoa_drink", "coffee_drink"},
    "coffee_drink": {"coffee_drink", "energy_drink", "zero_energy_drink", "caffeinated_beverage", "cocoa_drink"},
    "coffee_beans": {"coffee_beans"},
    "caffeinated_beverage": {"coffee_drink", "energy_drink", "zero_energy_drink", "energy_shot", "caffeinated_beverage", "cola_zero"},
    "beer": {"beer"},
    "alcoholic_drink": {"alcoholic_drink", "beer"},
    "dairy_dessert": {"dairy_dessert", "fruit_yogurt", "plain_yogurt", "greek_yogurt"},
    "drinkable_yogurt": {"drinkable_yogurt", "fruit_yogurt", "plain_yogurt", "protein_yogurt", "kefir", "lactate"},
    "protein_yogurt": {"protein_yogurt", "greek_yogurt", "plain_yogurt", "fruit_yogurt", "drinkable_yogurt", "lactate"},
    "greek_yogurt": {"greek_yogurt", "plain_yogurt", "protein_yogurt", "fruit_yogurt", "lactate"},
    "fruit_yogurt": {"fruit_yogurt", "plain_yogurt", "greek_yogurt", "protein_yogurt", "drinkable_yogurt", "kefir", "lactate", "plant_yogurt"},
    "plain_yogurt": {"plain_yogurt", "greek_yogurt", "protein_yogurt", "drinkable_yogurt", "fruit_yogurt", "kefir", "lactate", "plant_yogurt"},
    "kefir": {"kefir", "drinkable_yogurt", "plain_yogurt", "lactate"},
    "butter": {"butter"},
    "sour_cream": {"sour_cream", "cream"},
    "whipped_cream": {"whipped_cream", "cream"},
    "cream": {"cream", "sour_cream", "whipped_cream"},
    "cottage_cheese": {"cottage_cheese", "cheese", "cheese_spread"},
    "cheese_spread": {"cheese_spread", "processed_cheese", "cottage_cheese", "cheese"},
    "processed_cheese": {"processed_cheese", "cheese_spread", "cheese"},
    "hard_cheese": {"hard_cheese", "soft_cheese", "feta_telemea", "cheese"},
    "soft_cheese": {"soft_cheese", "hard_cheese", "feta_telemea", "cheese"},
    "feta_telemea": {"feta_telemea", "hard_cheese", "soft_cheese", "cheese"},
    "cheese": {"cheese", "hard_cheese", "soft_cheese", "feta_telemea", "processed_cheese", "cheese_spread", "cottage_cheese"},
    "milk": {"milk", "plant_milk", "kefir"},
    "lactate": {"lactate", "plain_yogurt", "greek_yogurt", "protein_yogurt", "drinkable_yogurt", "fruit_yogurt", "kefir", "cheese", "hard_cheese", "soft_cheese", "feta_telemea", "processed_cheese", "cheese_spread", "cottage_cheese", "milk", "butter", "cream", "sour_cream", "whipped_cream", "dairy_dessert", "plant_milk", "plant_yogurt"},
    "plant_milk": {"plant_milk", "milk"},
    "plant_yogurt": {"plant_yogurt", "plain_yogurt", "fruit_yogurt"},
    "plant_based": {"plant_based", "plant_milk", "plant_yogurt"},
    "protein": {"protein", "protein_bar", "protein_yogurt"},
    "protein_bar": {"protein_bar", "cereal_bar", "protein"},
    "chips": {"chips", "potato_chips", "tortilla_chips", "puffs", "crackers", "pretzels", "popcorn", "salty_snack"},
    "potato_chips": {"potato_chips", "chips", "tortilla_chips", "puffs", "salty_snack"},
    "tortilla_chips": {"tortilla_chips", "chips", "potato_chips", "puffs", "salty_snack"},
    "puffs": {"puffs", "chips", "potato_chips", "tortilla_chips", "popcorn", "salty_snack"},
    "crackers": {"crackers", "pretzels", "chips", "popcorn", "salty_snack"},
    "pretzels": {"pretzels", "crackers", "chips", "salty_snack"},
    "popcorn": {"popcorn", "puffs", "chips", "crackers", "salty_snack"},
    "salty_snack": {"salty_snack", "chips", "potato_chips", "tortilla_chips", "puffs", "crackers", "pretzels", "popcorn", "roasted_nuts"},
    "milk_chocolate": {"milk_chocolate", "dark_chocolate", "white_chocolate", "filled_chocolate", "chocolate"},
    "dark_chocolate": {"dark_chocolate", "milk_chocolate", "white_chocolate", "filled_chocolate", "chocolate"},
    "white_chocolate": {"white_chocolate", "milk_chocolate", "dark_chocolate", "filled_chocolate", "chocolate"},
    "filled_chocolate": {"filled_chocolate", "milk_chocolate", "dark_chocolate", "white_chocolate", "chocolate"},
    "chocolate": {"chocolate", "milk_chocolate", "dark_chocolate", "white_chocolate", "filled_chocolate"},
    "wafers": {"wafers", "cookies", "biscuits_wafers"},
    "cookies": {"cookies", "wafers", "biscuits_wafers"},
    "biscuits_wafers": {"biscuits_wafers", "wafers", "cookies"},
    "candy": {"candy"},
    "croissant": {"croissant", "bakery_pastry", "sweet_bakery"},
    "sweet_bakery": {"sweet_bakery", "croissant", "cakes", "bakery_pastry"},
    "cereal_bar": {"cereal_bar", "protein_bar", "breakfast_cereal", "oats_granola"},
    "cakes": {"cakes", "sweet_bakery", "bakery_pastry"},
    "sweet_snack": {"sweet_snack", "chocolate", "milk_chocolate", "dark_chocolate", "white_chocolate", "filled_chocolate", "biscuits_wafers", "wafers", "cookies", "candy", "cakes", "sweet_bakery", "cereal_bar"},
    "breakfast_cereal": {"breakfast_cereal", "oats_granola", "cereal", "cereal_bar"},
    "oats_granola": {"oats_granola", "breakfast_cereal", "cereal"},
    "cereal": {"cereal", "breakfast_cereal", "oats_granola"},
    "sauce": {"sauce", "tomato_sauce", "hot_sauce", "soy_sauce", "salad_dressing", "pesto_sauce", "pasta_sauce", "ketchup", "mustard", "mayonnaise"},
    "tomato_sauce": {"tomato_sauce", "pasta_sauce", "sauce", "ketchup"},
    "hot_sauce": {"hot_sauce", "sauce", "tomato_sauce"},
    "soy_sauce": {"soy_sauce", "sauce"},
    "salad_dressing": {"salad_dressing", "sauce", "mayonnaise"},
    "pesto_sauce": {"pesto_sauce", "pasta_sauce", "sauce"},
    "pasta_sauce": {"pasta_sauce", "tomato_sauce", "pesto_sauce", "sauce"},
    "ketchup": {"ketchup", "tomato_sauce", "mustard", "mayonnaise", "sauce"},
    "mustard": {"mustard", "ketchup", "mayonnaise", "sauce"},
    "mayonnaise": {"mayonnaise", "salad_dressing", "ketchup", "mustard", "sauce"},
    "olive_oil": {"olive_oil", "sunflower_oil", "oil"},
    "sunflower_oil": {"sunflower_oil", "olive_oil", "oil"},
    "oil": {"oil", "olive_oil", "sunflower_oil"},
    "vinegar": {"vinegar"},
    "spices": {"spices"},
    "oil_vinegar_spices": {"oil_vinegar_spices", "oil", "vinegar", "spices"},
    "pasta_rice_legumes": {"pasta_rice_legumes", "pasta", "rice", "legumes"},
    "pasta": {"pasta", "spaghetti_pasta", "short_pasta"},
    "spaghetti_pasta": {"spaghetti_pasta", "short_pasta", "pasta"},
    "short_pasta": {"short_pasta", "spaghetti_pasta", "pasta"},
    "rice": {"rice", "basmati_rice", "round_rice"},
    "basmati_rice": {"basmati_rice", "round_rice", "rice"},
    "round_rice": {"round_rice", "basmati_rice", "rice"},
    "legumes": {"legumes"},
    "wheat_flour": {"wheat_flour", "cornmeal", "flour_baking"},
    "cornmeal": {"cornmeal", "wheat_flour", "flour_baking"},
    "cocoa_powder": {"cocoa_powder", "flour_baking"},
    "yeast_baking": {"yeast_baking", "flour_baking"},
    "flour_baking": {"flour_baking", "wheat_flour", "cornmeal", "cocoa_powder", "yeast_baking"},
    "sugar_sweetener": {"sugar_sweetener"},
    "tuna_canned": {"tuna_canned", "canned_fish", "fish"},
    "canned_fish": {"canned_fish", "tuna_canned", "fish"},
    "pate": {"pate", "canned_meat", "processed_meat"},
    "canned_meat": {"canned_meat", "pate", "processed_meat"},
    "tomato_canned": {"tomato_canned", "corn_canned", "bean_canned", "canned_vegetables"},
    "corn_canned": {"corn_canned", "tomato_canned", "bean_canned", "canned_vegetables"},
    "bean_canned": {"bean_canned", "tomato_canned", "corn_canned", "canned_vegetables", "legumes"},
    "canned_vegetables": {"canned_vegetables", "tomato_canned", "corn_canned", "bean_canned", "pickles_olives"},
    "olives": {"olives", "pickles_olives"},
    "pickled_cucumbers": {"pickled_cucumbers", "pickles_olives"},
    "pickles_olives": {"pickles_olives", "olives", "pickled_cucumbers", "canned_vegetables"},
    "canned_pickles": {"canned_pickles", "canned_vegetables", "pickles_olives", "olives", "pickled_cucumbers"},
    "ice_cream": {"ice_cream"},
    "pizza": {"pizza", "frozen_pizza", "frozen_meal"},
    "frozen_pizza": {"frozen_pizza", "pizza", "frozen_meal"},
    "frozen": {"frozen", "frozen_meal", "frozen_vegetable", "frozen_fries", "frozen_fish", "frozen_meat", "pizza", "frozen_pizza"},
    "frozen_vegetable": {"frozen_vegetable", "frozen"},
    "frozen_fries": {"frozen_fries", "frozen_vegetable", "frozen"},
    "frozen_fish": {"frozen_fish", "fish"},
    "frozen_meat": {"frozen_meat", "fresh_meat"},
    "frozen_meal": {"frozen_meal", "frozen", "pizza", "frozen_pizza"},
    "hummus": {"hummus", "sandwich_salad", "ready_meal"},
    "ready_pasta": {"ready_pasta", "ready_meal", "sandwich_salad"},
    "ready_salad": {"ready_salad", "sandwich_salad", "ready_meal", "hummus"},
    "ready_meal": {"ready_meal", "ready_soup", "sandwich_salad", "ready_pasta", "ready_salad", "hummus"},
    "ready_soup": {"ready_soup", "ready_meal"},
    "sandwich_salad": {"sandwich_salad", "ready_salad", "hummus", "ready_meal"},
    "bread": {"bread"},
    "bakery_pastry": {"bakery_pastry", "croissant", "sweet_bakery"},
    "meat": {"meat", "processed_meat", "salami", "ham", "sausages", "fresh_meat", "chicken_meat", "pork_meat", "beef_meat", "turkey_meat", "minced_meat"},
    "processed_meat": {"processed_meat", "salami", "ham", "sausages"},
    "salami": {"salami", "ham", "sausages", "processed_meat"},
    "ham": {"ham", "salami", "sausages", "processed_meat"},
    "sausages": {"sausages", "salami", "ham", "processed_meat"},
    "fresh_meat": {"fresh_meat", "chicken_meat", "pork_meat", "beef_meat", "turkey_meat", "minced_meat", "meat"},
    "chicken_meat": {"chicken_meat", "turkey_meat", "fresh_meat"},
    "pork_meat": {"pork_meat", "beef_meat", "minced_meat", "fresh_meat"},
    "beef_meat": {"beef_meat", "pork_meat", "minced_meat", "fresh_meat"},
    "turkey_meat": {"turkey_meat", "chicken_meat", "fresh_meat"},
    "minced_meat": {"minced_meat", "pork_meat", "beef_meat", "fresh_meat"},
    "smoked_fish": {"smoked_fish", "fish", "canned_fish"},
    "fish": {"fish", "smoked_fish", "canned_fish", "tuna_canned"},
    "eggs": {"eggs"},
    "fresh_fruit": {"fresh_fruit", "fruit_vegetable"},
    "fresh_vegetable": {"fresh_vegetable", "fruit_vegetable"},
    "fruit_vegetable": {"fruit_vegetable", "fresh_fruit", "fresh_vegetable"},
    "chocolate_spread": {"chocolate_spread", "spread"},
    "peanut_butter": {"peanut_butter", "spread", "nuts"},
    "jam_honey": {"jam_honey", "spread"},
    "spread": {"spread", "chocolate_spread", "peanut_butter", "jam_honey"},
    "roasted_nuts": {"roasted_nuts", "nuts", "salty_snack"},
    "dried_fruit": {"dried_fruit", "nuts"},
    "nuts": {"nuts", "roasted_nuts", "dried_fruit"},
    "baby_food": {"baby_food", "baby_formula", "baby_puree", "baby_puree_fruit", "baby_puree_vegetable"},
    "baby_formula": {"baby_formula"},
    "baby_puree_fruit": {"baby_puree_fruit", "baby_puree", "baby_food"},
    "baby_puree_vegetable": {"baby_puree_vegetable", "baby_puree", "baby_food"},
    "baby_puree": {"baby_puree", "baby_puree_fruit", "baby_puree_vegetable", "baby_food"},
    "instant_noodles": {"instant_noodles"},
}
FAMILY_COMPATIBILITY.update({
    "apple_juice": {"apple_juice", "fruit_juice", "nectar", "smoothie", "multivitamin_juice"},
    "orange_juice": {"orange_juice", "fruit_juice", "nectar", "smoothie", "multivitamin_juice"},
    "multivitamin_juice": {"multivitamin_juice", "fruit_juice", "apple_juice", "orange_juice", "nectar", "smoothie"},
    "smoothie": {"smoothie", "fruit_juice", "nectar", "apple_juice", "orange_juice", "multivitamin_juice"},
    "nectar": {"nectar", "fruit_juice", "apple_juice", "orange_juice", "multivitamin_juice", "smoothie"},
    "isotonic_drink": {"isotonic_drink", "sports_drink", "energy_drink", "zero_energy_drink"},
    "alcohol_free_beer": {"alcohol_free_beer", "beer", "radler_beer", "lager_beer"},
    "radler_beer": {"radler_beer", "beer", "alcohol_free_beer", "lager_beer"},
    "lager_beer": {"lager_beer", "beer", "radler_beer", "alcohol_free_beer", "wheat_beer", "dark_beer"},
    "wheat_beer": {"wheat_beer", "beer", "lager_beer", "dark_beer"},
    "dark_beer": {"dark_beer", "beer", "lager_beer", "wheat_beer"},
    "uht_milk": {"uht_milk", "milk", "lactose_free_milk"},
    "lactose_free_milk": {"lactose_free_milk", "milk", "uht_milk", "plant_milk"},
    "oat_milk": {"oat_milk", "plant_milk", "almond_milk", "soy_milk"},
    "almond_milk": {"almond_milk", "plant_milk", "oat_milk", "soy_milk"},
    "soy_milk": {"soy_milk", "plant_milk", "oat_milk", "almond_milk"},
    "protein_pudding": {"protein_pudding", "pudding", "dairy_dessert", "protein_yogurt"},
    "pudding": {"pudding", "protein_pudding", "rice_pudding", "custard_dessert", "dairy_dessert"},
    "rice_pudding": {"rice_pudding", "pudding", "custard_dessert", "dairy_dessert"},
    "custard_dessert": {"custard_dessert", "pudding", "rice_pudding", "dairy_dessert"},
    "ice_cream_bar": {"ice_cream_bar", "ice_cream_cone", "ice_cream_cup", "sorbet", "ice_cream"},
    "ice_cream_cone": {"ice_cream_cone", "ice_cream_bar", "ice_cream_cup", "sorbet", "ice_cream"},
    "ice_cream_cup": {"ice_cream_cup", "ice_cream_bar", "ice_cream_cone", "sorbet", "ice_cream"},
    "sorbet": {"sorbet", "ice_cream", "ice_cream_bar", "ice_cream_cone", "ice_cream_cup"},
    "cornflakes": {"cornflakes", "breakfast_cereal", "muesli", "granola"},
    "muesli": {"muesli", "breakfast_cereal", "granola", "oats", "cornflakes"},
    "granola": {"granola", "breakfast_cereal", "muesli", "oats", "cereal_bar"},
    "oats": {"oats", "oats_granola", "muesli", "granola"},
    "rice_cakes": {"rice_cakes", "salty_snack", "crackers"},
    "sunflower_seeds": {"sunflower_seeds", "pumpkin_seeds", "roasted_nuts", "nuts"},
    "pumpkin_seeds": {"pumpkin_seeds", "sunflower_seeds", "roasted_nuts", "nuts"},
    "trail_mix": {"trail_mix", "nuts", "roasted_nuts", "dried_fruit"},
    "bbq_sauce": {"bbq_sauce", "sauce", "hot_sauce", "tomato_sauce"},
    "garlic_sauce": {"garlic_sauce", "sauce", "mayonnaise", "salad_dressing"},
    "salsa_sauce": {"salsa_sauce", "sauce", "tomato_sauce", "hot_sauce"},
    "sweet_chili_sauce": {"sweet_chili_sauce", "sauce", "hot_sauce"},
    "dijon_mustard": {"dijon_mustard", "mustard", "sauce"},
    "light_mayonnaise": {"light_mayonnaise", "mayonnaise", "sauce", "salad_dressing"},
    "salt": {"salt", "spices"},
    "pepper": {"pepper", "spices"},
    "paprika": {"paprika", "spices", "spice_mix"},
    "spice_mix": {"spice_mix", "spices", "paprika", "stock_cube"},
    "stock_cube": {"stock_cube", "spice_mix", "spices"},
    "toast_bread": {"toast_bread", "sliced_bread", "wholegrain_bread", "bread"},
    "sliced_bread": {"sliced_bread", "toast_bread", "wholegrain_bread", "bread"},
    "wholegrain_bread": {"wholegrain_bread", "sliced_bread", "toast_bread", "bread"},
    "buns": {"buns", "bread", "toast_bread", "sliced_bread"},
    "tortilla_wrap": {"tortilla_wrap", "bread", "bakery_pastry"},
    "cup_noodles": {"cup_noodles", "ramen_noodles", "instant_noodles"},
    "ramen_noodles": {"ramen_noodles", "cup_noodles", "instant_noodles"},
    "whey_protein": {"whey_protein", "protein", "protein_bar"},
    "canned_sardines": {"canned_sardines", "canned_fish", "tuna_canned", "canned_mackerel", "fish"},
    "canned_mackerel": {"canned_mackerel", "canned_fish", "tuna_canned", "canned_sardines", "fish"},
    "canned_peas": {"canned_peas", "canned_vegetables", "canned_chickpeas", "canned_lentils", "legumes"},
    "canned_chickpeas": {"canned_chickpeas", "canned_vegetables", "canned_peas", "canned_lentils", "legumes"},
    "canned_lentils": {"canned_lentils", "canned_vegetables", "canned_peas", "canned_chickpeas", "legumes"},
    "vegetable_spread": {"vegetable_spread", "spread", "hummus", "plant_based"},
    "jam": {"jam", "jam_honey", "honey", "spread"},
    "honey": {"honey", "jam", "jam_honey", "spread"},
    "frozen_fruit": {"frozen_fruit", "frozen"},
    "frozen_vegetable_mix": {"frozen_vegetable_mix", "frozen_vegetable", "frozen"},
    "frozen_dessert": {"frozen_dessert", "ice_cream", "sorbet", "frozen"},
    "baby_biscuits": {"baby_biscuits", "baby_snack", "baby_food"},
    "baby_snack": {"baby_snack", "baby_biscuits", "baby_food"},
})
FAMILY_COMPATIBILITY["fruit_juice"].update({"apple_juice", "orange_juice", "multivitamin_juice", "smoothie", "nectar"})
FAMILY_COMPATIBILITY["sports_drink"].update({"isotonic_drink", "zero_energy_drink"})
FAMILY_COMPATIBILITY["beer"].update({"alcohol_free_beer", "radler_beer", "lager_beer", "wheat_beer", "dark_beer"})
FAMILY_COMPATIBILITY["milk"].update({"uht_milk", "lactose_free_milk", "oat_milk", "almond_milk", "soy_milk"})
FAMILY_COMPATIBILITY["plant_milk"].update({"oat_milk", "almond_milk", "soy_milk", "lactose_free_milk"})
FAMILY_COMPATIBILITY["dairy_dessert"].update({"pudding", "protein_pudding", "rice_pudding", "custard_dessert"})
FAMILY_COMPATIBILITY["ice_cream"].update({"ice_cream_bar", "ice_cream_cone", "ice_cream_cup", "sorbet", "frozen_dessert"})
FAMILY_COMPATIBILITY["breakfast_cereal"].update({"cornflakes", "muesli", "granola", "oats"})
FAMILY_COMPATIBILITY["oats_granola"].update({"oats", "muesli", "granola", "cornflakes"})
FAMILY_COMPATIBILITY["salty_snack"].update({"rice_cakes", "sunflower_seeds", "pumpkin_seeds", "trail_mix"})
FAMILY_COMPATIBILITY["nuts"].update({"sunflower_seeds", "pumpkin_seeds", "trail_mix"})
FAMILY_COMPATIBILITY["sauce"].update({"bbq_sauce", "garlic_sauce", "salsa_sauce", "sweet_chili_sauce", "dijon_mustard", "light_mayonnaise"})
FAMILY_COMPATIBILITY["mustard"].update({"dijon_mustard"})
FAMILY_COMPATIBILITY["mayonnaise"].update({"light_mayonnaise", "garlic_sauce"})
FAMILY_COMPATIBILITY["spices"].update({"salt", "pepper", "paprika", "spice_mix", "stock_cube"})
FAMILY_COMPATIBILITY["flour_baking"].update({"flavor_extract", "yeast_baking", "cocoa_powder"})
FAMILY_COMPATIBILITY["bread"].update({"toast_bread", "sliced_bread", "wholegrain_bread", "buns", "tortilla_wrap"})
FAMILY_COMPATIBILITY["instant_noodles"].update({"cup_noodles", "ramen_noodles"})
FAMILY_COMPATIBILITY["protein"].update({"whey_protein", "protein_pudding"})
FAMILY_COMPATIBILITY["canned_fish"].update({"canned_sardines", "canned_mackerel"})
FAMILY_COMPATIBILITY["canned_vegetables"].update({"canned_peas", "canned_chickpeas", "canned_lentils"})
FAMILY_COMPATIBILITY["legumes"].update({"canned_peas", "canned_chickpeas", "canned_lentils", "bean_canned"})
FAMILY_COMPATIBILITY["spread"].update({"vegetable_spread", "jam", "honey"})
FAMILY_COMPATIBILITY["jam_honey"].update({"jam", "honey"})
FAMILY_COMPATIBILITY["frozen"].update({"frozen_fruit", "frozen_vegetable_mix", "frozen_dessert"})
FAMILY_COMPATIBILITY["frozen_vegetable"].update({"frozen_vegetable_mix"})
FAMILY_COMPATIBILITY["baby_food"].update({"baby_biscuits", "baby_snack"})


def get_compatible_recommendation_families(family):
    return FAMILY_COMPATIBILITY.get(family, {family})


def is_compatible_alternative(scanned_product, candidate):
    scanned_family = get_product_recommendation_family(scanned_product)
    candidate_family = get_product_recommendation_family(candidate)
    scanned_text = product_text_for_recommendation(scanned_product)
    candidate_text = product_text_for_recommendation(candidate)
    beverage_families = {
        "still_water",
        "sparkling_water",
        "water",
        "apple_juice",
        "orange_juice",
        "multivitamin_juice",
        "smoothie",
        "nectar",
        "fruit_juice",
        "lemonade",
        "iced_tea",
        "kombucha",
        "tea_drink",
        "flavoured_water",
        "sports_drink",
        "isotonic_drink",
        "orange_soda",
        "lemon_lime_soda",
        "tonic_soda",
        "carbonated_soft_drink",
        "syrup_concentrate",
        "cola_zero",
        "cola_regular",
        "cola",
        "beverage",
        "zero_energy_drink",
        "energy_shot",
        "energy_drink",
        "cocoa_drink",
        "coffee_drink",
        "coffee_beans",
        "tea_bags",
        "caffeinated_beverage",
        "beer",
        "alcohol_free_beer",
        "radler_beer",
        "lager_beer",
        "wheat_beer",
        "dark_beer",
        "alcoholic_drink",
    }
    lactate_families = {
        "lactate",
        "drinkable_yogurt",
        "protein_yogurt",
        "greek_yogurt",
        "fruit_yogurt",
        "plain_yogurt",
        "kefir",
        "dairy_dessert",
        "protein_pudding",
        "pudding",
        "rice_pudding",
        "custard_dessert",
        "butter",
        "sour_cream",
        "whipped_cream",
        "cream",
        "cottage_cheese",
        "cheese_spread",
        "processed_cheese",
        "hard_cheese",
        "soft_cheese",
        "feta_telemea",
        "cheese",
        "milk",
        "uht_milk",
        "lactose_free_milk",
        "plant_milk",
        "oat_milk",
        "almond_milk",
        "soy_milk",
        "plant_yogurt",
    }
    strict_food_families = {
        "protein",
        "whey_protein",
        "protein_bar",
        "salty_snack",
        "rice_cakes",
        "sunflower_seeds",
        "pumpkin_seeds",
        "trail_mix",
        "potato_chips",
        "tortilla_chips",
        "puffs",
        "pretzels",
        "sweet_snack",
        "milk_chocolate",
        "dark_chocolate",
        "white_chocolate",
        "filled_chocolate",
        "wafers",
        "cookies",
        "croissant",
        "sweet_bakery",
        "cereal_bar",
        "breakfast_cereal",
        "oats_granola",
        "cornflakes",
        "muesli",
        "granola",
        "oats",
        "cereal",
        "sauce",
        "tomato_sauce",
        "hot_sauce",
        "soy_sauce",
        "salad_dressing",
        "pesto_sauce",
        "pasta_sauce",
        "bbq_sauce",
        "garlic_sauce",
        "salsa_sauce",
        "sweet_chili_sauce",
        "ketchup",
        "mustard",
        "dijon_mustard",
        "mayonnaise",
        "light_mayonnaise",
        "olive_oil",
        "sunflower_oil",
        "oil",
        "vinegar",
        "spices",
        "salt",
        "pepper",
        "paprika",
        "spice_mix",
        "stock_cube",
        "pasta",
        "spaghetti_pasta",
        "short_pasta",
        "rice",
        "basmati_rice",
        "round_rice",
        "legumes",
        "wheat_flour",
        "cornmeal",
        "cocoa_powder",
        "yeast_baking",
        "flour_baking",
        "sugar_sweetener",
        "canned_fish",
        "tuna_canned",
        "canned_sardines",
        "canned_mackerel",
        "canned_meat",
        "pate",
        "canned_vegetables",
        "tomato_canned",
        "corn_canned",
        "bean_canned",
        "canned_peas",
        "canned_chickpeas",
        "canned_lentils",
        "pickles_olives",
        "olives",
        "pickled_cucumbers",
        "canned_pickles",
        "ice_cream",
        "ice_cream_bar",
        "ice_cream_cone",
        "ice_cream_cup",
        "sorbet",
        "pizza",
        "frozen",
        "frozen_vegetable",
        "frozen_fries",
        "frozen_fish",
        "frozen_meat",
        "frozen_meal",
        "frozen_pizza",
        "frozen_fruit",
        "frozen_vegetable_mix",
        "frozen_dessert",
        "ready_meal",
        "ready_soup",
        "ready_pasta",
        "ready_salad",
        "sandwich_salad",
        "hummus",
        "bread",
        "toast_bread",
        "sliced_bread",
        "wholegrain_bread",
        "buns",
        "tortilla_wrap",
        "meat",
        "processed_meat",
        "salami",
        "ham",
        "sausages",
        "fresh_meat",
        "chicken_meat",
        "pork_meat",
        "beef_meat",
        "turkey_meat",
        "minced_meat",
        "fish",
        "smoked_fish",
        "eggs",
        "fresh_fruit",
        "fresh_vegetable",
        "fruit_vegetable",
        "chocolate_spread",
        "peanut_butter",
        "jam_honey",
        "jam",
        "honey",
        "spread",
        "vegetable_spread",
        "nuts",
        "roasted_nuts",
        "dried_fruit",
        "baby_food",
        "baby_formula",
        "baby_puree",
        "baby_puree_fruit",
        "baby_puree_vegetable",
        "baby_biscuits",
        "baby_snack",
        "plant_based",
        "cup_noodles",
        "ramen_noodles",
    }
    non_food_beverage_blocks = beverage_families | {
        "instant_noodles",
        "lactate",
        "fruit_yogurt",
        "dairy_dessert",
        "plain_yogurt",
        "kefir",
        "cheese",
        "milk",
        "butter",
        "cream",
        "cottage_cheese",
        "protein",
        "salty_snack",
        "sweet_snack",
        "cereal",
        "sauce",
        "ketchup",
        "mustard",
        "mayonnaise",
        "oil",
        "vinegar",
        "spices",
        "pasta_rice_legumes",
        "pasta",
        "spaghetti_pasta",
        "short_pasta",
        "rice",
        "basmati_rice",
        "round_rice",
        "legumes",
        "wheat_flour",
        "cornmeal",
        "cocoa_powder",
        "yeast_baking",
        "flour_baking",
        "sugar_sweetener",
        "tuna_canned",
        "canned_fish",
        "pate",
        "canned_meat",
        "tomato_canned",
        "corn_canned",
        "bean_canned",
        "canned_vegetables",
        "olives",
        "pickled_cucumbers",
        "pickles_olives",
        "canned_pickles",
        "ice_cream",
        "pizza",
        "frozen_pizza",
        "frozen",
        "frozen_fish",
        "frozen_meat",
        "frozen_vegetable",
        "frozen_fries",
        "frozen_meal",
        "ready_meal",
        "ready_pasta",
        "ready_salad",
        "hummus",
        "bread",
        "bakery_pastry",
        "meat",
        "salami",
        "ham",
        "sausages",
        "processed_meat",
        "chicken_meat",
        "pork_meat",
        "beef_meat",
        "turkey_meat",
        "minced_meat",
        "fresh_meat",
        "smoked_fish",
        "fish",
        "eggs",
        "fresh_fruit",
        "fresh_vegetable",
        "fruit_vegetable",
        "chocolate_spread",
        "peanut_butter",
        "jam_honey",
        "spread",
        "nuts",
        "roasted_nuts",
        "dried_fruit",
        "baby_food",
        "baby_formula",
        "baby_puree_fruit",
        "baby_puree_vegetable",
        "baby_puree",
        "plant_based",
        "beer",
        "alcoholic_drink",
    }
    non_food_beverage_blocks.update({
        "cup_noodles",
        "ramen_noodles",
        "protein_pudding",
        "pudding",
        "rice_pudding",
        "custard_dessert",
        "greek_yogurt",
        "protein_yogurt",
        "drinkable_yogurt",
        "uht_milk",
        "lactose_free_milk",
        "plant_milk",
        "oat_milk",
        "almond_milk",
        "soy_milk",
        "whey_protein",
        "rice_cakes",
        "sunflower_seeds",
        "pumpkin_seeds",
        "trail_mix",
        "breakfast_cereal",
        "cornflakes",
        "muesli",
        "granola",
        "oats",
        "dijon_mustard",
        "light_mayonnaise",
        "bbq_sauce",
        "garlic_sauce",
        "salsa_sauce",
        "sweet_chili_sauce",
        "salt",
        "pepper",
        "paprika",
        "spice_mix",
        "stock_cube",
        "canned_sardines",
        "canned_mackerel",
        "canned_peas",
        "canned_chickpeas",
        "canned_lentils",
        "ice_cream_bar",
        "ice_cream_cone",
        "ice_cream_cup",
        "sorbet",
        "frozen_dessert",
        "frozen_fruit",
        "frozen_vegetable_mix",
        "ready_soup",
        "sandwich_salad",
        "toast_bread",
        "sliced_bread",
        "wholegrain_bread",
        "buns",
        "tortilla_wrap",
        "baby_biscuits",
        "baby_snack",
    })
    incompatible_families = {
        "instant_noodles": non_food_beverage_blocks - {"instant_noodles"},
        "energy_drink": non_food_beverage_blocks - {"energy_drink", "coffee_drink", "caffeinated_beverage"},
        "coffee_drink": non_food_beverage_blocks - {"coffee_drink", "energy_drink", "caffeinated_beverage"},
        "coffee_beans": non_food_beverage_blocks - {"coffee_beans"},
        "tea_bags": non_food_beverage_blocks - {"tea_bags"},
        "caffeinated_beverage": non_food_beverage_blocks - {"coffee_drink", "energy_drink", "caffeinated_beverage"},
        "carbonated_soft_drink": non_food_beverage_blocks - {"carbonated_soft_drink", "cola"},
        "syrup_concentrate": non_food_beverage_blocks - {"syrup_concentrate"},
        "cola": non_food_beverage_blocks - {"cola", "carbonated_soft_drink", "energy_drink", "caffeinated_beverage"},
        "beer": non_food_beverage_blocks - {"beer"},
        "alcoholic_drink": non_food_beverage_blocks - {"alcoholic_drink", "beer"},
        "water": non_food_beverage_blocks - {"water"},
        "flavoured_water": non_food_beverage_blocks - {"flavoured_water", "water"},
        "fruit_yogurt": non_food_beverage_blocks - {"fruit_yogurt", "lactate"},
        "lactate": non_food_beverage_blocks - {"fruit_yogurt", "plain_yogurt", "kefir", "lactate", "dairy_dessert", "cheese", "milk", "butter", "cream", "cottage_cheese"},
        "dairy_dessert": non_food_beverage_blocks - {"dairy_dessert", "lactate", "fruit_yogurt"},
        "plain_yogurt": non_food_beverage_blocks - {"plain_yogurt", "fruit_yogurt", "kefir", "lactate"},
        "kefir": non_food_beverage_blocks - {"kefir", "plain_yogurt", "lactate"},
        "cheese": non_food_beverage_blocks - {"cheese", "cottage_cheese"},
        "butter": non_food_beverage_blocks - {"butter"},
        "cream": non_food_beverage_blocks - {"cream"},
        "cottage_cheese": non_food_beverage_blocks - {"cottage_cheese", "cheese"},
        "meat": non_food_beverage_blocks - {"meat"},
        "processed_meat": non_food_beverage_blocks - {"processed_meat"},
        "fresh_meat": non_food_beverage_blocks - {"fresh_meat", "meat"},
        "fish": non_food_beverage_blocks - {"fish"},
        "canned_fish": non_food_beverage_blocks - {"canned_fish", "fish"},
        "ice_cream": non_food_beverage_blocks - {"ice_cream"},
        "sauce": non_food_beverage_blocks - {"sauce"},
        "ketchup": non_food_beverage_blocks - {"ketchup", "mustard", "mayonnaise", "sauce"},
        "mustard": non_food_beverage_blocks - {"mustard", "ketchup", "mayonnaise", "sauce"},
        "mayonnaise": non_food_beverage_blocks - {"mayonnaise", "ketchup", "mustard", "sauce"},
        "spread": non_food_beverage_blocks - {"spread", "nuts", "chocolate_spread", "peanut_butter", "jam_honey"},
        "baby_food": non_food_beverage_blocks - {"baby_food", "baby_formula", "baby_puree"},
        "plant_based": non_food_beverage_blocks - {"plant_based", "lactate", "fruit_yogurt"},
    }

    if candidate_family in incompatible_families.get(scanned_family, set()):
        return False

    if scanned_family == "general":
        signal_rules = [
            (["buldak", "ramen", "noodle", "taitei", "taitel"], {"instant_noodles"}),
            (["iaurt", "yogurt", "yoghurt", "zuzu", "skyr"], {"fruit_yogurt", "lactate"}),
            (["energiz", "red bull", "redbull", "monster", "hell", "taurina"], {"energy_drink", "caffeinated_beverage"}),
            (["cafea", "coffee", "cappuccino", "latte", "espresso"], {"coffee_drink", "energy_drink", "caffeinated_beverage"}),
            (["bere", "beer", "ursus", "timisoreana", "timișoreana", "ciuc", "bergenbier"], {"beer"}),
            (["muschi", "mușchi", "file", "filet", "sunca", "șuncă", "salam", "prosciutto"], {"meat"}),
        ]

        for tokens, allowed_families in signal_rules:
            if any(token in scanned_text for token in tokens):
                return candidate_family in allowed_families

    allowed_families = get_compatible_recommendation_families(scanned_family)

    if scanned_family != "general" and allowed_families and candidate_family not in allowed_families:
        return False

    water_like_families = {"water", "still_water", "sparkling_water", "flavoured_water"}
    beer_like_families = {"beer", "alcohol_free_beer", "radler_beer", "lager_beer", "wheat_beer", "dark_beer"}

    if candidate_family in water_like_families and scanned_family not in water_like_families:
        return False

    if scanned_family in water_like_families:
        return candidate_family in get_compatible_recommendation_families(scanned_family)

    if scanned_family in beer_like_families:
        return candidate_family in get_compatible_recommendation_families(scanned_family)

    if candidate_family in beer_like_families and scanned_family not in beer_like_families:
        return False

    if scanned_family == "alcoholic_drink":
        return candidate_family in {"alcoholic_drink", "beer"}

    if candidate_family == "alcoholic_drink" and scanned_family != "alcoholic_drink":
        return False

    if scanned_family not in beverage_families and candidate_family in beverage_families:
        return False

    if scanned_family in beverage_families and candidate_family not in beverage_families:
        return False

    if scanned_family == "instant_noodles":
        return candidate_family == "instant_noodles"

    if candidate_family == "instant_noodles":
        return scanned_family == "instant_noodles"

    if scanned_family == "fruit_yogurt":
        if candidate_family not in get_compatible_recommendation_families("fruit_yogurt"):
            return False
        return any(token in candidate_text for token in ["iaurt", "yogurt", "yoghurt", "skyr", "zuzu", "fruct", "protein", "grecesc"])

    if scanned_family == "lactate":
        return candidate_family in lactate_families

    if candidate_family in lactate_families and scanned_family not in lactate_families:
        return False

    if scanned_family in strict_food_families:
        return candidate_family in allowed_families

    if candidate_family in strict_food_families and scanned_family != candidate_family:
        return False

    if scanned_family == "energy_drink":
        return candidate_family in {"energy_drink", "zero_energy_drink", "energy_shot", "caffeinated_beverage", "coffee_drink", "cola_zero"}

    if scanned_family == "coffee_drink":
        return candidate_family in {"coffee_drink", "cocoa_drink", "energy_drink", "zero_energy_drink", "caffeinated_beverage"}

    if scanned_family == "caffeinated_beverage":
        return candidate_family in {"coffee_drink", "cocoa_drink", "energy_drink", "zero_energy_drink", "energy_shot", "caffeinated_beverage", "cola_zero"}

    if scanned_family == "cola":
        return candidate_family in {"cola", "cola_zero", "cola_regular", "energy_drink", "zero_energy_drink", "caffeinated_beverage"}

    if scanned_family in {"cola_zero", "cola_regular"}:
        return candidate_family in {"cola", "cola_zero", "cola_regular", "energy_drink", "zero_energy_drink", "caffeinated_beverage"}

    if scanned_family == "dairy_dessert":
        return candidate_family in {"dairy_dessert", "pudding", "protein_pudding", "rice_pudding", "custard_dessert", "lactate", "fruit_yogurt", "plain_yogurt"} or (
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
    label_text = normalize_search_text(
        " ".join([
            str(product_data.get("name") or ""),
            str(product_data.get("brand") or ""),
            str(product_data.get("category") or ""),
        ])
    )

    def label_has_precise(tokens):
        return any(label_has_catalog_token(label_text, token) for token in tokens)

    category_map = {
        "apa plata": "en:spring-waters",
        "apa minerala carbogazoasa": "en:sparkling-waters",
        "apa": "en:waters",
        "apa aromata": "en:flavoured-waters",
        "limonade": "en:lemonades",
        "sucuri": "en:fruit-juices",
        "sucuri si nectaruri": "en:fruit-juices",
        "kombucha": "en:kombuchas",
        "ceaiuri reci": "en:iced-teas",
        "ceaiuri si infuzii": "en:teas",
        "bauturi pentru sport": "en:sports-drinks",
        "bauturi carbogazoase cu portocale": "en:orange-soft-drinks",
        "bauturi carbogazoase cu lamaie": "en:lemon-lime-soft-drinks",
        "bauturi tonice": "en:tonic-drinks",
        "bauturi carbogazoase": "en:carbonated-drinks",
        "siropuri si concentrate": "en:syrups",
        "cola fara zahar": "en:diet-colas",
        "cola clasica": "en:colas",
        "bauturi racoritoare": "en:soft-drinks",
        "bauturi energizante fara zahar": "en:energy-drinks",
        "shot-uri energizante": "en:energy-drinks",
        "bauturi energizante": "en:energy-drinks",
        "bauturi cu cacao": "en:chocolate-drinks",
        "bauturi cu cafea": "en:iced-coffees",
        "cafea boabe si macinata": "en:coffees",
        "bauturi cu cafeina": "en:caffeinated-beverages",
        "bere": "en:beers",
        "bauturi alcoolice": "en:alcoholic-beverages",
        "bauturi": "en:beverages",
        "lactate": "en:dairies",
        "iaurturi cu fructe": "en:fruit-yogurts",
        "iaurturi simple": "en:yogurts",
        "kefir si lapte batut": "en:fermented-milks",
        "unt": "en:butters",
        "smantana si frisca": "en:creams",
        "branza proaspata": "en:fresh-cheeses",
        "branzeturi": "en:cheeses",
        "lapte": "en:milks",
        "lactate si branzeturi": "en:cheeses",
        "deserturi lactate": "en:dairy-desserts",
        "iaurturi de baut": "en:drinkable-yogurts",
        "iaurturi proteice": "en:high-protein-yogurts",
        "iaurturi grecesti": "en:greek-yogurts",
        "snacks": "en:snacks",
        "snacks sarate": "en:salty-snacks",
        "chipsuri": "en:chips-and-fries",
        "chipsuri din cartofi": "en:chips-and-fries",
        "chipsuri tortilla": "en:tortilla-chips",
        "pufuleti si snacks din porumb": "en:corn-snacks",
        "crackers si covrigei": "en:crackers",
        "covrigei si sticksuri": "en:pretzels",
        "popcorn": "en:popcorn",
        "dulciuri": "en:sweet-snacks",
        "ciocolata cu lapte": "en:milk-chocolates",
        "ciocolata neagra": "en:dark-chocolates",
        "ciocolata alba": "en:white-chocolates",
        "ciocolata umpluta": "en:filled-chocolates",
        "ciocolata": "en:chocolates",
        "napolitane": "en:wafers",
        "biscuiti": "en:biscuits",
        "biscuiti si napolitane": "en:biscuits-and-cakes",
        "bomboane si jeleuri": "en:candies",
        "croissante": "en:croissants",
        "patiserie dulce": "en:pastries",
        "batoane de cereale": "en:cereal-bars",
        "batoane proteice": "en:protein-bars",
        "prajituri si checuri": "en:cakes",
        "cereale": "en:breakfast-cereals",
        "cereale pentru mic dejun": "en:breakfast-cereals",
        "ovaz muesli si granola": "en:mueslis",
        "carne": "en:meats",
        "mezeluri": "en:processed-meats",
        "carne proaspata": "en:meats",
        "peste si fructe de mare": "en:seafood",
        "peste afumat": "en:smoked-fishes",
        "oua": "en:eggs",
        "panificatie": "en:breads",
        "patiserie": "en:pastries",
        "fructe si legume": "en:fruits-and-vegetables",
        "fructe proaspete": "en:fresh-fruits",
        "legume proaspete": "en:fresh-vegetables",
        "ketchup": "en:ketchups",
        "sosuri de rosii": "en:tomato-sauces",
        "sosuri iuti": "en:hot-sauces",
        "sosuri de soia": "en:soy-sauces",
        "dressinguri pentru salata": "en:salad-dressings",
        "pesto": "en:pestos",
        "sosuri pentru paste": "en:pasta-sauces",
        "mustar": "en:mustards",
        "maioneza": "en:mayonnaises",
        "ulei de masline": "en:olive-oils",
        "ulei de floarea-soarelui": "en:sunflower-oils",
        "uleiuri": "en:oils",
        "otet": "en:vinegars",
        "condimente": "en:spices",
        "sosuri si condimente": "en:condiments",
        "uleiuri si condimente": "en:condiments",
        "uleiuri otet si condimente": "en:condiments",
        "paste orez si leguminoase": "en:pastas",
        "paste": "en:pastas",
        "spaghete": "en:spaghettis",
        "paste scurte": "en:pastas",
        "orez": "en:rices",
        "orez basmati": "en:basmati-rices",
        "orez pentru risotto si deserturi": "en:rices",
        "leguminoase": "en:legumes",
        "faina de grau": "en:wheat-flours",
        "malai": "en:cornmeals",
        "cacao pudra": "en:cocoa-powders",
        "drojdie si praf de copt": "en:baking-powders",
        "faina si ingrediente pentru copt": "en:baking-decorations",
        "zahar si indulcitori": "en:sugars",
        "conserve de peste": "en:canned-fishes",
        "conserve de ton": "en:canned-tunas",
        "conserve de carne si pateuri": "en:pates",
        "pateuri": "en:pates",
        "conserve de legume": "en:canned-vegetables",
        "conserve de rosii": "en:canned-tomatoes",
        "porumb la conserva": "en:canned-corn",
        "fasole la conserva": "en:canned-beans",
        "muraturi si masline": "en:pickles",
        "masline": "en:olives",
        "castraveti murati": "en:pickled-cucumbers",
        "conserve si muraturi": "en:canned-foods",
        "taitei instant": "en:instant-noodles",
        "noodles": "en:instant-noodles",
        "ramen": "en:instant-noodles",
        "inghetata": "en:ice-creams",
        "pizza": "en:pizzas",
        "congelate": "en:frozen-foods",
        "legume congelate": "en:frozen-vegetables",
        "cartofi congelati": "en:frozen-potatoes",
        "peste congelat": "en:frozen-fishes",
        "carne congelata": "en:frozen-meats",
        "mancare congelata": "en:frozen-ready-meals",
        "pizza congelata": "en:frozen-pizzas",
        "mese gata preparate": "en:ready-meals",
        "paste gata preparate": "en:ready-meals",
        "salate gata preparate": "en:salads",
        "hummus": "en:hummus",
        "supe si ciorbe": "en:soups",
        "sandwichuri si salate": "en:sandwiches",
        "alternative vegetale": "en:plant-based-foods-and-beverages",
        "bauturi vegetale": "en:plant-based-milks",
        "iaurturi vegetale": "en:plant-based-yogurts",
        "proteine si fitness": "en:sports-nutrition",
        "creme de ciocolata": "en:chocolate-spreads",
        "unt de arahide": "en:peanut-butters",
        "gemuri si miere": "en:jams",
        "creme si gemuri": "en:spreads",
        "creme tartinabile": "en:spreads",
        "nuci si seminte": "en:nuts",
        "nuci si seminte prajite": "en:roasted-nuts",
        "fructe uscate": "en:dried-fruits",
        "alimente pentru copii": "en:baby-foods",
        "lapte praf pentru bebelusi": "en:baby-milks",
        "piureuri pentru bebelusi": "en:baby-foods",
        "piureuri de fructe pentru bebelusi": "en:baby-foods",
        "piureuri de legume pentru bebelusi": "en:baby-foods",
    }

    if any(word in product_text for word in ["iaurt", "yogurt", "yoghurt", "skyr", "zuzu"]) and any(word in product_text for word in ["fruct", "fructe", "capsuni", "strawberry", "piersici", "visine", "afine", "zmeura", "padure"]):
        return "en:fruit-yogurts"

    if any(word in product_text for word in ["branza", "brânză", "cascaval", "cașcaval", "telemea", "mozzarella", "feta", "cheddar", "gouda"]):
        return "en:cheeses"

    if any(word in product_text for word in ["salam", "sunca", "șuncă", "muschi file", "mușchi file", "carnati", "cârnați", "bacon", "prosciutto", "parizer"]):
        return "en:processed-meats"

    if any(word in product_text for word in ["chips", "crisps", "nachos", "tortilla chips"]):
        return "en:chips-and-fries"

    if any(word in product_text for word in ["biscuit", "napolitana", "napolitană", "wafer", "cookies"]):
        return "en:biscuits-and-cakes"

    if any(word in product_text for word in ["ciocolata", "ciocolată", "chocolate", "praline"]):
        return "en:chocolates"

    if any(word in product_text for word in ["ovaz", "ovăz", "oat", "muesli", "granola"]):
        return "en:mueslis"

    if category in category_map:
        return category_map[category]

    if any(word in product_text for word in ["hell", "red bull", "redbull", "monster", "energiz", "energy", "taurina", "taurine"]):
        return "en:energy-drinks"

    if any(word in product_text for word in ["bere", "beer", "ursus", "timisoreana", "timișoreana", "ciuc", "bergenbier", "heineken", "silva", "tuborg", "carlsberg", "peroni", "stella", "corona", "kozel", "lager", "pilsner", "radler"]):
        return "en:beers"

    alcohol_tokens = [
        "alcool",
        "alcohol",
        "vin",
        "wine",
        "vodka",
        "whisky",
        "rom",
        "rum",
        "gin",
        "cidru",
        "cider",
        "lichior",
        "liqueur",
        "spirits",
    ]
    vinegar_tokens = ["vinegar", "vinaigre", "vinagre", "otet", "oțet"]

    if label_has_precise(alcohol_tokens) and not label_has_precise(vinegar_tokens):
        return "en:alcoholic-beverages"

    if any(word in product_text for word in ["buldak", "samyang", "ramen", "noodle", "noodles", "taitei", "nongshim", "yakisoba", "udon"]):
        return "en:instant-noodles"

    if any(word in product_text for word in ["cafea boabe", "cafea macinata", "cafea măcinată", "ground coffee", "coffee beans", "instant coffee", "capsule cafea"]):
        return "en:coffees"

    if any(word in product_text for word in ["coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee", "cold brew", "frappe", "cafeina", "cofeina", "caffeine"]):
        return "en:iced-coffees"

    if any(word in product_text for word in ["danette", "budinca", "pudding", "custard", "desert lactat"]):
        return "en:dairy-desserts"

    if any(word in product_text for word in ["iaurt", "yogurt", "yoghurt", "skyr", "lapte", "milk"]):
        return "en:dairies"

    if any(word in product_text for word in ["baby food", "baby milk", "bebelus", "bebelusi", "piure bebelusi"]):
        return "en:baby-foods"

    if any(word in product_text for word in ["inghetata", "ice cream", "gelatelli", "gelato"]):
        return "en:ice-creams"

    if any(word in product_text for word in ["apa aromata", "apă aromată", "flavoured water", "flavored water", "vitamin water"]):
        return "en:flavoured-waters"

    if any(word in product_text for word in ["apa", "water", "mineral"]) and not any(word in product_text for word in ["energy", "energiz", "coffee", "cafea", "cola", "pepsi", "aromata", "flavoured", "flavored"]):
        return "en:waters"

    if any(word in product_text for word in ["cola", "pepsi", "coca cola", "cocacola", "soda", "soft drink"]):
        return "en:soft-drinks"

    if any(word in product_text for word in ["suc", "juice", "nectar", "smoothie"]):
        return "en:fruit-juices"

    if any(word in product_text for word in ["sos", "mustar", "ketchup", "salsa"]):
        return "en:condiments"

    if any(word in product_text for word in ["paste", "pasta", "spaghetti", "penne", "fusilli"]):
        return "en:pastas"

    if any(word in product_text for word in ["orez", "rice", "basmati", "jasmine"]):
        return "en:rices"

    if any(word in product_text for word in ["fasole", "linte", "lentils", "naut", "năut", "chickpeas"]):
        return "en:legumes"

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
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    return parsed if math.isfinite(parsed) else None


def build_alternative_normalization_stats(products):
    stats = {}

    for field in ("price", "protein", "sugar", "calories"):
        values = [
            get_alternative_numeric_value(item, field)
            for item in products
        ]
        values = [value for value in values if value is not None]

        if values:
            stats[field] = (min(values), max(values))

    return stats


def get_alternative_normalized_score(
    products,
    product,
    field,
    prefer_higher,
    normalization_stats=None,
):
    value = get_alternative_numeric_value(product, field)

    if value is None:
        return 0

    if normalization_stats and field in normalization_stats:
        minimum, maximum = normalization_stats[field]
    else:
        values = [
            get_alternative_numeric_value(item, field)
            for item in products
        ]
        values = [item_value for item_value in values if item_value is not None]

        if not values:
            return 0

        minimum = min(values)
        maximum = max(values)

    if minimum == maximum:
        return 1

    normalized = (value - minimum) / (maximum - minimum)
    return normalized if prefer_higher else 1 - normalized


def product_text_for_recommendation(product):
    cache_key = get_product_text_cache_key(product)
    cached_text = PRODUCT_RECOMMENDATION_TEXT_CACHE.get(cache_key)

    if cached_text is not None:
        return cached_text

    text_value = normalize_search_text(
        " ".join([
            cache_key[0],
            cache_key[1],
            cache_key[2],
            cache_key[3],
            cache_key[4],
            cache_key[5],
        ])
    )
    set_limited_cache_item(
        PRODUCT_RECOMMENDATION_TEXT_CACHE,
        cache_key,
        text_value,
        RECOMMENDATION_DERIVED_CACHE_MAX_ITEMS,
    )
    return text_value


def is_high_caffeine_candidate(product):
    product_family = get_product_recommendation_family(product)
    product_text = product_text_for_recommendation(product)

    if product_family in {"energy_drink", "zero_energy_drink", "energy_shot", "coffee_drink", "caffeinated_beverage"}:
        return True

    return any(
        token in product_text
        for token in ["taurina", "taurine", "cafeina", "cofeina", "caffeine"]
    )


def is_caffeine_relevant_candidate(product):
    product_family = get_product_recommendation_family(product)

    if product_family in {
        "water",
        "still_water",
        "sparkling_water",
        "flavoured_water",
        "beer",
        "alcohol_free_beer",
        "radler_beer",
        "lager_beer",
        "wheat_beer",
        "dark_beer",
        "alcoholic_drink",
        "instant_noodles",
        "cup_noodles",
        "ramen_noodles",
        "lactate",
        "fruit_yogurt",
        "plain_yogurt",
        "greek_yogurt",
        "protein_yogurt",
        "dairy_dessert",
        "pudding",
        "rice_pudding",
        "ice_cream",
    }:
        return False

    return product_family in {
        "energy_drink",
        "zero_energy_drink",
        "energy_shot",
        "coffee_drink",
        "cocoa_drink",
        "caffeinated_beverage",
        "cola_zero",
        "cola_regular",
    }


def product_has_meaningful_nutrition(product):
    values = [
        safe_float(product.get(field))
        for field in ("calories", "protein", "sugar", "fat")
    ]
    numeric_values = [value for value in values if value is not None]

    if not numeric_values:
        return False

    if all(abs(value) < 0.01 for value in numeric_values):
        return get_product_recommendation_family(product) == "water"

    return True


def get_catalog_quality_adjustment(product):
    score = 0
    category = normalize_search_text(product.get("category") or "")
    family = get_product_recommendation_family(product)

    if product.get("image"):
        score += 2
    else:
        score -= 2

    if category and category not in {"altele", "other", "general"} and family != "general":
        score += 3
    else:
        score -= 4

    nutrition_fields = [
        safe_float(product.get(field))
        for field in ("calories", "protein", "sugar", "fat")
    ]
    known_nutrition_count = sum(value is not None for value in nutrition_fields)
    score += min(known_nutrition_count, 4)

    if known_nutrition_count == 0:
        score -= 7
    elif not product_has_meaningful_nutrition(product):
        score -= 5

    if product.get("ingredients"):
        score += 1.5
    else:
        score -= 1

    if product.get("priceIsLocal") and product.get("price") is not None:
        score += 1

    if family == "general":
        score -= 6

    return score


def has_clean_ingredient_profile(product):
    if product.get("natural"):
        return True

    text = product_text_for_recommendation(product)
    additive_hits = len(re.findall(r"\be\s*-?\d{3,4}[a-z]?\b", text))
    risky_terms = [
        "colorant",
        "conservant",
        "potentiator",
        "potențiator",
        "glutamat",
        "aspartam",
        "acesulfam",
        "ulei de palmier",
        "palm oil",
    ]

    if additive_hits >= 3 or any(term in text for term in risky_terms):
        return False

    ingredients = normalize_search_text(product.get("ingredients") or "")
    ingredient_tokens = [
        token.strip()
        for token in re.split(r"[,;]", ingredients)
        if token.strip()
    ]

    return bool(ingredient_tokens) and len(ingredient_tokens) <= 8


def product_matches_vegan_preference(product):
    family = get_product_recommendation_family(product)
    text = product_text_for_recommendation(product)

    if product.get("vegan") or family in {"plant_based", "plant_milk", "plant_yogurt"}:
        return True

    return any(token in text for token in ["vegan", "de post", "vegetal", "plant based", "plant-based"])


def product_likely_contains_lactose(product):
    family = get_product_recommendation_family(product)
    text = product_text_for_recommendation(product)

    if family in {"plant_based", "plant_milk", "plant_yogurt"}:
        return False

    lactose_terms = [
        "lapte",
        "milk",
        "lactoza",
        "lactose",
        "zer",
        "whey",
        "smantana",
        "smântână",
        "cream",
        "branza",
        "brânză",
        "iaurt",
        "yogurt",
    ]

    return family in {
        "lactate",
        "fruit_yogurt",
        "plain_yogurt",
        "kefir",
        "dairy_dessert",
        "cheese",
        "milk",
    } or any(term in text for term in lactose_terms)


PREFERENCE_ALLERGEN_KEYWORDS = {
    "gluten": ["gluten", "grau", "wheat", "barley", "orz", "rye", "secara"],
    "lactose": ["lapte", "milk", "lactoza", "lactose", "whey", "zer", "smantana", "smântână", "cream"],
    "peanuts": ["arahide", "peanuts", "peanut"],
    "nuts": ["alune", "hazelnut", "hazelnuts", "migdale", "almond", "cashew", "nuci", "walnut"],
    "soy": ["soia", "soy", "soya"],
    "egg": ["ou", "egg", "eggs"],
    "fish": ["peste", "pește", "fish", "ton", "tuna", "somon", "salmon"],
    "sesame": ["susan", "sesame"],
}


def split_preference_avoid_terms(value):
    return [
        item.strip()
        for item in re.split(r"[,;\n]+", normalize_search_text(value or ""))
        if len(item.strip()) >= 3
    ]


def product_violates_user_preferences(product, preferences):
    if not isinstance(preferences, dict):
        return False

    text = product_text_for_recommendation(product)
    selected_criteria = preferences.get("criteria") or []
    selected_allergies = preferences.get("allergies") or []

    if not isinstance(selected_criteria, list):
        selected_criteria = []

    if not isinstance(selected_allergies, list):
        selected_allergies = []

    selected_criteria = {str(item).strip().lower() for item in selected_criteria}

    if "vegan" in selected_criteria and not product_matches_vegan_preference(product):
        return True

    if "lactose_free" in selected_criteria and product_likely_contains_lactose(product):
        return True

    for allergy in selected_allergies:
        keywords = PREFERENCE_ALLERGEN_KEYWORDS.get(str(allergy).strip().lower(), [])

        if keywords and any(keyword in text for keyword in keywords):
            return True

    for term in split_preference_avoid_terms(preferences.get("avoidIngredients") or ""):
        if term in text:
            return True

    return False


def score_off_alternative(
    products,
    product,
    criteria,
    scanned_product=None,
    normalization_stats=None,
):
    score = float(product.get("score") or 0)
    reasons = []
    candidate_family = get_product_recommendation_family(product)
    candidate_text = product_text_for_recommendation(product)
    criteria = set(criteria or [])
    score += get_catalog_quality_adjustment(product)

    if scanned_product:
        scanned_family = get_product_recommendation_family(scanned_product)
        beverage_families = {
            "still_water",
            "sparkling_water",
            "water",
            "flavoured_water",
            "fruit_juice",
            "apple_juice",
            "orange_juice",
            "multivitamin_juice",
            "smoothie",
            "nectar",
            "lemonade",
            "iced_tea",
            "kombucha",
            "tea_drink",
            "sports_drink",
            "isotonic_drink",
            "orange_soda",
            "lemon_lime_soda",
            "tonic_soda",
            "cola",
            "cola_zero",
            "cola_regular",
            "beverage",
            "zero_energy_drink",
            "energy_shot",
            "energy_drink",
            "cocoa_drink",
            "coffee_drink",
            "caffeinated_beverage",
            "beer",
            "alcohol_free_beer",
            "radler_beer",
            "lager_beer",
            "wheat_beer",
            "dark_beer",
            "alcoholic_drink",
        }

        if candidate_family == scanned_family:
            family_bonus = 18 if scanned_family in {"instant_noodles", "fruit_yogurt", "protein_yogurt", "processed_meat", "salami", "ham", "sausages", "beer", "cheese", "hard_cheese", "soft_cheese", "feta_telemea"} else 10
            score += family_bonus
            reasons.append("aceeași categorie de produs")
        elif candidate_family in get_compatible_recommendation_families(scanned_family):
            score += 4
            reasons.append("alternativă apropiată ca tip")
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
        elif scanned_family == "beer" and candidate_family != "beer":
            score -= 80
        elif scanned_family == "alcoholic_drink" and candidate_family not in {"alcoholic_drink", "beer"}:
            score -= 70
        elif scanned_family == "dairy_dessert" and candidate_family in {"dairy_dessert", "lactate"}:
            score += 5
            reasons.append("alternativă lactată apropiată")

        scanned_sugar = safe_float(scanned_product.get("sugar"))
        candidate_sugar = safe_float(product.get("sugar"))
        scanned_protein = safe_float(scanned_product.get("protein"))
        candidate_protein = safe_float(product.get("protein"))
        scanned_calories = safe_float(scanned_product.get("calories"))
        candidate_calories = safe_float(product.get("calories"))

        if "low_sugar" in criteria and scanned_sugar is not None and candidate_sugar is not None:
            if candidate_sugar < scanned_sugar:
                score += min(8, (scanned_sugar - candidate_sugar) * 0.5)
            elif candidate_sugar > scanned_sugar:
                score -= min(8, (candidate_sugar - scanned_sugar) * 0.35)

        if "protein" in criteria and scanned_protein is not None and candidate_protein is not None:
            if candidate_protein > scanned_protein:
                score += min(7, (candidate_protein - scanned_protein) * 0.45)
            elif candidate_protein < scanned_protein:
                score -= min(5, (scanned_protein - candidate_protein) * 0.25)

        if "low_calorie" in criteria and scanned_calories is not None and candidate_calories is not None:
            if candidate_calories < scanned_calories:
                score += min(7, (scanned_calories - candidate_calories) * 0.04)
            elif candidate_calories > scanned_calories:
                score -= min(6, (candidate_calories - scanned_calories) * 0.025)

        if "different_flavor" in criteria:
            scanned_flavor = extract_product_flavor(scanned_product)
            candidate_flavor = extract_product_flavor(product)

            if scanned_flavor and candidate_flavor and candidate_flavor != scanned_flavor:
                score += 18
                reasons.append("altă aromă din aceeași familie")
            elif scanned_flavor and candidate_flavor == scanned_flavor:
                score -= 14
            elif candidate_family == scanned_family:
                score += 2

    if (
        "cheap" in criteria
        and product.get("price") is not None
        and product.get("priceIsLocal")
    ):
        value = get_alternative_normalized_score(
            products,
            product,
            "price",
            False,
            normalization_stats,
        )
        score += value * 10
        reasons.append("preț observat mai bun")
    elif "cheap" in criteria and product.get("price") is None:
        score -= 2

    if "protein" in criteria:
        value = get_alternative_normalized_score(
            products,
            product,
            "protein",
            True,
            normalization_stats,
        )
        score += value * 10
        reasons.append("mai multă proteină")

        protein_value = safe_float(product.get("protein"))
        if protein_value is not None:
            if protein_value >= 12:
                score += 5
            elif protein_value >= 8:
                score += 3
            elif protein_value < 2 and candidate_family not in {"water", "fruit_juice", "tea_drink", "cola", "energy_drink"}:
                score -= 3

    if "low_sugar" in criteria:
        value = get_alternative_normalized_score(
            products,
            product,
            "sugar",
            False,
            normalization_stats,
        )
        score += value * 10
        reasons.append("mai puțin zahăr")

        sugar_value = safe_float(product.get("sugar"))
        if sugar_value == 0:
            score += 6
            reasons.append("fără zahăr")
        elif sugar_value is not None and sugar_value <= 5:
            score += 3
        elif sugar_value is not None and sugar_value >= 15:
            score -= 5

    if "caffeine" in criteria:
        if candidate_family in {"energy_drink", "zero_energy_drink", "energy_shot"}:
            score += 18
            reasons.append("băutură energizantă")
        elif candidate_family in {"coffee_drink", "cocoa_drink"}:
            score += 14
            reasons.append("băutură cu cafea")
        elif candidate_family == "caffeinated_beverage":
            score += 10
            reasons.append("conține cafeină")
        elif candidate_family in {"cola", "cola_zero", "cola_regular"}:
            score -= 30
        elif candidate_family in {"water", "still_water", "sparkling_water", "beer", "alcoholic_drink"}:
            score -= 60

        if any(token in candidate_text for token in ["taurina", "taurine", "caffeine", "cafeina", "cofeina"]):
            score += 4
            reasons.append("ingrediente cu efect energizant")

    if "low_calorie" in criteria:
        value = get_alternative_normalized_score(
            products,
            product,
            "calories",
            False,
            normalization_stats,
        )
        score += value * 10
        reasons.append("mai puține calorii")

        calories_value = safe_float(product.get("calories"))
        if calories_value is not None:
            if calories_value <= 80:
                score += 3
            elif calories_value >= 300:
                score -= 4

    if "value" in criteria:
        score += float(product.get("score") or 0) * 1.5
        reasons.append("scor nutrițional mai bun")

    if "vegan" in criteria:
        if product_matches_vegan_preference(product):
            score += 14
            reasons.append("potrivit pentru post")
        elif candidate_family in {"meat", "processed_meat", "fresh_meat", "fish", "eggs", "milk", "cheese", "dairy_dessert", "fruit_yogurt", "plain_yogurt", "kefir", "lactate"}:
            score -= 35

    if "lactose_free" in criteria:
        if product.get("lactoseFree") or candidate_family in {"plant_based", "plant_milk", "plant_yogurt"}:
            score += 12
            reasons.append("fără lactoză")
        elif product_likely_contains_lactose(product):
            score -= 22

    if "natural" in criteria:
        if has_clean_ingredient_profile(product):
            score += 12
            reasons.append("ingrediente mai curate")
        else:
            score -= 6

    if not product_has_meaningful_nutrition(product) and candidate_family != "water":
        score -= 8

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
    if not EXTERNAL_CATALOG_ENABLED:
        return []

    distributed = distributed_cache_get("off-search", cache_key)

    if isinstance(distributed, list):
        return distributed

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
    distributed_cache_set(
        "off-search",
        cache_key,
        products,
        OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL,
    )
    set_limited_cache_item(
        OPEN_FOOD_FACTS_ALTERNATIVES_CACHE,
        cache_key,
        {
            "created_at": now,
            "products": products,
        },
        OPEN_FOOD_FACTS_CACHE_MAX_ITEMS,
    )
    return products


def fetch_off_product_by_barcode(barcode):
    if not EXTERNAL_CATALOG_ENABLED:
        return None

    barcode = str(barcode or "").strip()

    if not barcode:
        return None

    cache_key = f"product:{barcode}"
    distributed = distributed_cache_get("off-product", cache_key)

    if isinstance(distributed, dict) and "found" in distributed:
        return distributed.get("product") if distributed.get("found") else None

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
        timeout=8,
    )

    if response.status_code == 404:
        distributed_cache_set(
            "off-product",
            cache_key,
            {"found": False, "product": None},
            OPEN_FOOD_FACTS_PRODUCT_CACHE_TTL,
        )
        set_limited_cache_item(
            OPEN_FOOD_FACTS_PRODUCT_CACHE,
            cache_key,
            {
                "created_at": now,
                "product": None,
            },
            OPEN_FOOD_FACTS_CACHE_MAX_ITEMS,
        )
        return None

    response.raise_for_status()
    data = response.json()

    if data.get("status") != 1:
        product = None
    else:
        product = data.get("product") or {}
        product["code"] = str(data.get("code") or product.get("code") or barcode)

    set_limited_cache_item(
        OPEN_FOOD_FACTS_PRODUCT_CACHE,
        cache_key,
        {
            "created_at": now,
            "product": product,
        },
        OPEN_FOOD_FACTS_CACHE_MAX_ITEMS,
    )
    distributed_cache_set(
        "off-product",
        cache_key,
        {"found": bool(product), "product": product},
        OPEN_FOOD_FACTS_PRODUCT_CACHE_TTL,
    )
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
    if not EXTERNAL_CATALOG_ENABLED:
        return []

    normalized_query = normalize_search_text(query_text)
    primary_terms = get_off_text_search_terms(query_text)
    query_brand = detect_query_brand(query_text)
    search_variants = []

    for terms in [primary_terms, normalized_query, query_brand]:
        terms = str(terms or "").strip()

        if terms and terms not in search_variants:
            search_variants.append(terms)

    search_variants = search_variants[:2]

    if not search_variants:
        return []

    endpoints = ["https://world.openfoodfacts.org/cgi/search.pl"]
    merged_products = []
    seen_barcodes = set()
    last_error = None
    successful_request = False

    for endpoint in endpoints:
        for search_terms in search_variants:
            cache_key = f"legacy-text:{endpoint}:{search_terms}"
            distributed = distributed_cache_get("off-text", cache_key)
            cache_item = OPEN_FOOD_FACTS_ALTERNATIVES_CACHE.get(cache_key)
            now = time.time()

            if isinstance(distributed, list):
                products = distributed
                successful_request = True
            elif (
                cache_item
                and now - cache_item["created_at"]
                < OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL
            ):
                products = cache_item["products"]
                successful_request = True
            else:
                products = None

                for attempt in range(1):
                    try:
                        response = requests.get(
                            endpoint,
                            params={
                                "search_terms": search_terms,
                                "search_simple": 1,
                                "action": "process",
                                "json": 1,
                                "page_size": 20,
                                "fields": OFF_ALTERNATIVE_FIELDS,
                            },
                            headers={
                                "User-Agent": (
                                    "CeAlegApp/1.0 "
                                    "(contact: contact@cealeg.shop)"
                                ),
                                "Accept": "application/json",
                            },
                            timeout=(2.5, 6),
                        )
                        response.raise_for_status()
                        products = response.json().get("products", [])
                        successful_request = True
                        distributed_cache_set(
                            "off-text",
                            cache_key,
                            products,
                            OPEN_FOOD_FACTS_ALTERNATIVES_CACHE_TTL,
                        )
                        set_limited_cache_item(
                            OPEN_FOOD_FACTS_ALTERNATIVES_CACHE,
                            cache_key,
                            {
                                "created_at": now,
                                "products": products,
                            },
                            OPEN_FOOD_FACTS_CACHE_MAX_ITEMS,
                        )
                        break
                    except requests.RequestException as error:
                        last_error = error

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


def get_loose_alternative_identity_key(product_data):
    name = normalize_product_name_for_duplicate(product_data.get("name"))

    if not name:
        return ""

    stopwords = {
        "produs",
        "product",
        "with",
        "and",
        "the",
        "pour",
        "avec",
        "fara",
        "fără",
        "zero",
        "gust",
        "aroma",
        "aromă",
    }
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", name)
        if len(token) > 2 and token not in stopwords
    ]
    brand = normalize_search_text(product_data.get("brand") or "")
    quantity = normalize_search_text(product_data.get("quantity") or "")
    family = get_product_recommendation_family(product_data)

    if not tokens:
        return ""

    return f"{family}:{brand}:{' '.join(tokens[:6])}:{quantity}"


def dedupe_alternatives_by_identity(alternatives):
    deduped = []
    seen_keys = set()
    seen_loose_keys = set()

    for candidate in alternatives:
        identity_key = get_alternative_identity_key(candidate)
        loose_key = get_loose_alternative_identity_key(candidate)

        if identity_key and identity_key in seen_keys:
            continue

        if loose_key and loose_key in seen_loose_keys:
            continue

        if any(is_same_catalog_product(existing, candidate) for existing in deduped):
            continue

        deduped.append(candidate)

        if identity_key:
            seen_keys.add(identity_key)

        if loose_key:
            seen_loose_keys.add(loose_key)

    return deduped


def get_known_catalog_alternatives(scanned_product, criteria):
    alternatives = []
    scanned_family = get_product_recommendation_family(scanned_product)

    if scanned_family not in {
        "coffee_drink",
        "energy_drink",
        "zero_energy_drink",
        "energy_shot",
        "caffeinated_beverage",
        "cola",
        "cola_zero",
        "cola_regular",
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
            "coffee_beans": ["cafea boabe", "cafea macinata", "cafea măcinată", "ground coffee", "coffee beans", "instant coffee", "nescafe", "capsule cafea"],
            "caffeinated_beverage": ["caffeine", "cafeina", "taurina"],
            "fruit_juice": ["suc", "juice", "nectar", "smoothie"],
            "tea_drink": ["ice tea", "iced tea", "ceai rece", "kombucha"],
            "tea_bags": ["ceai plic", "ceai plante", "ceai negru", "ceai verde", "herbal tea", "tea bags", "infuzie"],
            "sports_drink": ["isotonic", "sport drink", "gatorade", "powerade"],
            "carbonated_soft_drink": ["bautura carbogazoasa", "băutură carbogazoasă", "fanta", "sprite", "mirinda", "schweppes", "tonic", "7up", "soft drink"],
            "syrup_concentrate": ["sirop", "syrup", "concentrat", "concentrate"],
            "flavoured_water": ["apa aromata", "apă aromată", "flavoured water", "flavored water", "vitamin water"],
            "beer": ["bere", "beer", "ursus", "timisoreana", "timișoreana", "ciuc", "bergenbier", "heineken", "silva", "tuborg", "carlsberg", "peroni", "stella", "corona", "kozel", "lager", "pilsner", "radler"],
            "alcoholic_drink": ["alcool", "alcohol", "vin", "wine", "vodka", "whisky", "cidru", "cider", "lichior"],
            "instant_noodles": ["buldak", "samyang", "ramen", "noodle", "taitei"],
            "fruit_yogurt": ["iaurt", "yogurt", "zuzu", "fruct"],
            "plain_yogurt": ["iaurt natural", "iaurt grecesc", "plain yogurt", "skyr"],
            "kefir": ["kefir", "chefir", "sana", "lapte batut", "lapte bătut"],
            "butter": ["unt", "butter", "unt gras"],
            "cream": ["smantana", "smântână", "frisca", "frișcă", "sour cream", "whipping cream", "cooking cream"],
            "cottage_cheese": ["branza proaspata", "brânză proaspătă", "branza de vaci", "brânză de vaci", "cottage cheese", "ricotta", "urda"],
            "cheese": ["branza", "brânză", "cascaval", "cașcaval", "telemea", "mozzarella", "feta", "cheddar"],
            "milk": ["lapte", "milk", "uht"],
            "plant_milk": ["lapte vegetal", "bautura vegetala", "băutură vegetală", "oat drink", "almond drink", "soy drink"],
            "plant_yogurt": ["iaurt vegetal", "plant yogurt", "soy yogurt"],
            "lactate": ["iaurt", "yogurt", "lapte", "dairy", "branza", "brânză", "kefir"],
            "dairy_dessert": ["danette", "budinca", "pudding", "desert"],
            "ice_cream": ["inghetata", "ice cream", "gelato", "gelatelli"],
            "ketchup": ["ketchup"],
            "mustard": ["mustar", "muștar", "mustard"],
            "mayonnaise": ["maioneza", "maioneză", "mayonnaise"],
            "sauce": ["sos", "mustar", "muștar", "ketchup", "maioneza", "salsa", "dressing", "pesto"],
            "oil": ["ulei", "olive oil", "sunflower oil"],
            "vinegar": ["otet", "oțet", "vinegar", "balsamic"],
            "spices": ["condiment", "spice", "boia", "piper", "sare", "oregano", "curry"],
            "oil_vinegar_spices": ["ulei", "otet", "oțet", "condiment", "spice"],
            "chips": ["chips", "crisps", "nachos"],
            "crackers": ["crackers", "saratele", "sărățele", "sticks", "covrigei"],
            "popcorn": ["popcorn"],
            "salty_snack": ["chips", "crisps", "snack", "pufule", "crackers", "popcorn"],
            "chocolate": ["ciocolata", "ciocolată", "chocolate", "praline"],
            "biscuits_wafers": ["biscuit", "napolitana", "napolitană", "wafer", "cookies"],
            "candy": ["bomboane", "candy", "jeleuri"],
            "cakes": ["chec", "cake", "tort", "prajitura", "prăjitură", "muffin", "brownie", "cozonac"],
            "sweet_snack": ["ciocolata", "chocolate", "biscuit", "wafer", "bomboane", "prajitura", "prăjitură"],
            "breakfast_cereal": ["cereale", "cereal", "corn flakes", "fulgi"],
            "oats_granola": ["ovaz", "ovăz", "oat", "granola", "muesli"],
            "cereal": ["cereale", "cereal", "granola", "muesli", "ovaz", "ovăz"],
            "water": ["apa", "water", "mineral"],
            "cola": ["cola", "pepsi", "coca"],
            "processed_meat": ["muschi file", "mușchi file", "sunca", "șuncă", "ham", "salam", "carnati", "cârnați", "prosciutto", "bacon", "parizer"],
            "fresh_meat": ["carne", "porc", "pui", "curcan", "vita", "vită", "beef", "chicken"],
            "meat": ["muschi", "file", "filet", "sunca", "ham", "salam", "carne", "porc", "pui", "curcan", "prosciutto"],
            "fish": ["peste", "fish", "ton", "tuna", "somon", "salmon"],
            "eggs": ["oua", "ouă", "egg"],
            "spread": ["spread", "crema", "tartinabila", "nutella", "unt arahide", "peanut butter", "gem"],
            "nuts": ["nuci", "alune", "nuts", "seeds", "seminte"],
            "baby_food": ["baby", "infant", "bebelus", "bebelusi", "piure"],
            "plant_based": ["vegetal", "vegan", "plant based", "lapte vegetal", "bautura vegetala"],
            "bread": ["paine", "bread", "toast", "bagheta", "chifla"],
            "bakery_pastry": ["croissant", "patiserie", "foietaj", "gogoasa", "brioche"],
            "flour_baking": ["faina", "făină", "flour", "malai", "mălai", "drojdie", "praf de copt"],
            "sugar_sweetener": ["zahar", "zahăr", "sugar", "indulcitor", "sweetener", "stevia"],
            "ready_soup": ["supa", "supă", "soup", "ciorba", "ciorbă"],
            "sandwich_salad": ["sandwich", "salata", "salată", "wrap"],
            "ready_meal": ["ready meal", "sandwich", "salata", "supa"],
            "frozen_vegetable": ["legume congelate", "frozen vegetables"],
            "frozen_fish": ["peste congelat", "pește congelat", "frozen fish", "fish fingers", "creveti congelati"],
            "frozen_meat": ["carne congelata", "carne congelată", "frozen meat", "pui congelat"],
            "frozen_meal": ["frozen meal", "mancare congelata", "mâncare congelată"],
            "frozen": ["frozen", "congelat", "congelata"],
            "pizza": ["pizza"],
            "pasta": ["paste", "pasta", "spaghetti", "penne", "fusilli"],
            "rice": ["orez", "rice", "basmati", "jasmine"],
            "legumes": ["fasole", "beans", "linte", "lentils", "naut", "năut", "chickpeas"],
            "pasta_rice_legumes": ["paste", "pasta", "orez", "rice", "fasole", "linte", "naut", "năut"],
            "canned_fish": ["conserva ton", "conservă ton", "canned tuna", "sardine", "macrou conserva"],
            "canned_meat": ["pate", "pateu", "carne conserva", "carne conservă"],
            "canned_vegetables": ["conserva porumb", "conservă porumb", "conserva rosii", "conservă roșii", "conserve legume"],
            "pickles_olives": ["muraturi", "murături", "masline", "măsline", "olives", "pickles"],
            "canned_pickles": ["conserva", "conservă", "muraturi", "murături", "masline", "măsline"],
            "fresh_fruit": ["mere", "banane", "portocale", "lamaie", "lămâie", "struguri", "fructe proaspete"],
            "fresh_vegetable": ["rosii", "roșii", "tomate", "castraveti", "castraveți", "cartofi", "ceapa", "ceapă", "morcovi"],
            "fruit_vegetable": ["fructe", "legume", "fruits", "vegetables"],
            "chocolate_spread": ["nutella", "crema alune", "cremă alune", "hazelnut spread", "chocolate spread"],
            "peanut_butter": ["peanut butter", "unt arahide", "unt de arahide"],
            "jam_honey": ["gem", "dulceata", "dulceață", "marmelada", "miere", "honey"],
            "baby_formula": ["lapte praf bebelusi", "lapte praf bebeluși", "infant formula", "baby formula"],
            "baby_puree": ["piure bebelusi", "piure bebeluși", "baby puree", "borcanel bebelusi"],
        }.get(scanned_family, [])

        detailed_family_keywords = {
            "zero_energy_drink": ["red bull zero", "redbull zero", "monster zero", "monster ultra", "hell zero", "zero sugar energy", "energy zero"],
            "energy_shot": ["energy shot", "shot energizant"],
            "cocoa_drink": ["cacao", "choco drink", "hot chocolate", "ciocolata calda"],
            "lemonade": ["limonada", "limonadă", "lemonade"],
            "iced_tea": ["ice tea", "iced tea", "ceai rece", "fuzetea", "lipton"],
            "kombucha": ["kombucha"],
            "orange_soda": ["fanta", "mirinda", "orange soda", "portocale"],
            "lemon_lime_soda": ["sprite", "7up", "seven up", "lemon lime", "lamaie", "lămâie"],
            "tonic_soda": ["schweppes", "tonic", "bitter lemon"],
            "still_water": ["apa plata", "apă plată", "still water", "spring water"],
            "sparkling_water": ["apa minerala", "apă minerală", "apa carbogazoasa", "apă carbogazoasă", "sparkling water"],
            "cola_zero": ["cola zero", "pepsi max", "pepsi zero", "coca cola zero", "coca-cola zero", "coke zero"],
            "cola_regular": ["coca cola", "coca-cola", "cocacola", "pepsi", "cola original"],
            "drinkable_yogurt": ["iaurt de baut", "iaurt de băut", "drinkable yogurt", "yogurt drink", "actimel"],
            "protein_yogurt": ["iaurt proteic", "protein yogurt", "skyr proteic", "high protein"],
            "greek_yogurt": ["iaurt grecesc", "greek yogurt"],
            "sour_cream": ["smantana", "smântână", "sour cream"],
            "whipped_cream": ["frisca", "frișcă", "whipping cream", "hulala"],
            "cheese_spread": ["crema de branza", "cremă de brânză", "cream cheese", "tartinabila"],
            "processed_cheese": ["branza topita", "brânză topită", "processed cheese"],
            "hard_cheese": ["cascaval", "cașcaval", "cheddar", "gouda", "emmental", "parmesan"],
            "soft_cheese": ["mozzarella", "brie", "camembert", "mascarpone"],
            "feta_telemea": ["telemea", "feta"],
            "potato_chips": ["potato chips", "cartofi chips", "chips cartofi", "lays", "lay's", "pringles"],
            "tortilla_chips": ["tortilla chips", "nachos", "doritos"],
            "puffs": ["pufuleti", "pufuleți", "porumb expandat"],
            "pretzels": ["covrigei", "pretzels", "sticks", "saratele", "sărățele"],
            "milk_chocolate": ["ciocolata cu lapte", "ciocolată cu lapte", "milk chocolate"],
            "dark_chocolate": ["ciocolata neagra", "ciocolată neagră", "dark chocolate"],
            "white_chocolate": ["ciocolata alba", "ciocolată albă", "white chocolate"],
            "filled_chocolate": ["ciocolata umpluta", "ciocolată umplută", "filled chocolate", "praline"],
            "wafers": ["napolitana", "napolitană", "wafer"],
            "cookies": ["cookies", "biscuit", "biscuiti", "biscuiți"],
            "croissant": ["croissant"],
            "sweet_bakery": ["gogoasa", "gogoașă", "brioche", "cozonac", "muffin", "brownie"],
            "cereal_bar": ["cereal bar", "baton cereale", "baton cu cereale"],
            "protein_bar": ["protein bar", "baton proteic"],
            "tomato_sauce": ["sos de rosii", "sos de roșii", "tomato sauce", "passata", "bulion"],
            "hot_sauce": ["sos iute", "hot sauce", "chili sauce", "sriracha", "tabasco"],
            "soy_sauce": ["sos de soia", "soy sauce"],
            "salad_dressing": ["dressing", "salad dressing", "vinegret"],
            "pesto_sauce": ["pesto"],
            "pasta_sauce": ["sos paste", "sos pentru paste", "pasta sauce", "bolognese", "carbonara"],
            "olive_oil": ["ulei de masline", "ulei de măsline", "olive oil"],
            "sunflower_oil": ["ulei floarea soarelui", "ulei de floarea soarelui", "sunflower oil"],
            "spaghetti_pasta": ["spaghetti", "spaghete"],
            "short_pasta": ["penne", "fusilli", "farfalle", "macaroni", "macaroane"],
            "basmati_rice": ["basmati"],
            "round_rice": ["orez bob rotund", "round rice", "risotto"],
            "wheat_flour": ["faina alba", "făină albă", "wheat flour", "faina grau", "făină grâu"],
            "cornmeal": ["malai", "mălai", "cornmeal"],
            "cocoa_powder": ["cacao pudra", "cacao pudră", "cocoa powder"],
            "yeast_baking": ["drojdie", "yeast", "praf de copt", "baking powder"],
            "salami": ["salam", "salami"],
            "ham": ["muschi file", "mușchi file", "sunca", "șuncă", "ham", "jambon", "prosciutto"],
            "sausages": ["carnati", "cârnați", "sausage", "cremvursti", "crenvurști"],
            "chicken_meat": ["pui", "chicken"],
            "pork_meat": ["porc", "pork"],
            "beef_meat": ["vita", "vită", "beef"],
            "turkey_meat": ["curcan", "turkey"],
            "minced_meat": ["carne tocata", "carne tocată", "minced meat"],
            "smoked_fish": ["peste afumat", "pește afumat", "smoked fish", "somon afumat"],
            "roasted_nuts": ["arahide prajite", "arahide prăjite", "alune prajite", "alune prăjite", "migdale", "caju", "fistic"],
            "dried_fruit": ["fructe uscate", "stafide", "curmale", "prune uscate"],
            "frozen_fries": ["cartofi congelati", "cartofi congelați", "frozen fries"],
            "frozen_pizza": ["pizza congelata", "pizza congelată", "frozen pizza"],
            "ready_pasta": ["paste gata", "ready pasta", "pasta salad"],
            "ready_salad": ["salata gata", "salată gata", "ready salad"],
            "hummus": ["hummus", "humus"],
            "tuna_canned": ["conserva ton", "conservă ton", "canned tuna", "ton conserva"],
            "pate": ["pate", "pateu"],
            "tomato_canned": ["conserva rosii", "conservă roșii", "canned tomatoes", "rosii cuburi"],
            "corn_canned": ["conserva porumb", "conservă porumb", "canned corn", "porumb dulce"],
            "bean_canned": ["conserva fasole", "conservă fasole", "canned beans"],
            "olives": ["masline", "măsline", "olives"],
            "pickled_cucumbers": ["castraveti murati", "castraveți murați", "pickled cucumbers"],
            "baby_puree_fruit": ["piure fructe bebelusi", "piure fructe bebeluși", "baby fruit puree"],
            "baby_puree_vegetable": ["piure legume bebelusi", "piure legume bebeluși", "baby vegetable puree"],
            "apple_juice": ["suc de mere", "apple juice"],
            "orange_juice": ["suc de portocale", "orange juice"],
            "multivitamin_juice": ["multivitamin", "multi vitamin", "suc multifruct", "suc tropical"],
            "smoothie": ["smoothie"],
            "nectar": ["nectar"],
            "isotonic_drink": ["isotonic", "izotonic", "gatorade", "powerade", "sport drink"],
            "alcohol_free_beer": ["bere fara alcool", "bere fără alcool", "non alcoholic beer", "alcohol free beer", "0.0"],
            "radler_beer": ["radler"],
            "lager_beer": ["lager", "pilsner", "bere blonda", "bere blondă"],
            "wheat_beer": ["bere nefiltrata", "bere nefiltrată", "weissbier", "weizen"],
            "dark_beer": ["bere bruna", "bere brună", "dark beer", "stout", "porter"],
            "uht_milk": ["lapte uht", "uht milk"],
            "lactose_free_milk": ["lapte fara lactoza", "lapte fără lactoză", "lactose free milk"],
            "oat_milk": ["bautura ovaz", "băutură ovăz", "oat drink", "oat milk"],
            "almond_milk": ["bautura migdale", "băutură migdale", "almond drink", "almond milk"],
            "soy_milk": ["bautura soia", "băutură soia", "soy drink", "soy milk"],
            "protein_pudding": ["budinca proteica", "budincă proteică", "protein pudding"],
            "pudding": ["budinca", "budincă", "pudding", "danette"],
            "rice_pudding": ["orez cu lapte", "rice pudding"],
            "custard_dessert": ["crema desert", "cremă desert", "custard"],
            "ice_cream_bar": ["inghetata baton", "înghețată baton", "ice cream bar", "magnum"],
            "ice_cream_cone": ["inghetata cornet", "înghețată cornet", "ice cream cone", "cornet"],
            "ice_cream_cup": ["inghetata cupa", "înghețată cupă", "ice cream cup", "gelatelli"],
            "sorbet": ["sorbet"],
            "cornflakes": ["corn flakes", "fulgi de porumb"],
            "muesli": ["muesli", "musli"],
            "granola": ["granola"],
            "oats": ["ovaz", "ovăz", "fulgi de ovaz", "fulgi de ovăz", "oat flakes"],
            "rice_cakes": ["rondele orez", "rice cakes"],
            "sunflower_seeds": ["seminte floarea soarelui", "semințe floarea soarelui", "sunflower seeds"],
            "pumpkin_seeds": ["seminte dovleac", "semințe dovleac", "pumpkin seeds"],
            "trail_mix": ["mix fructe uscate", "trail mix", "student mix"],
            "bbq_sauce": ["sos barbeque", "sos barbecue", "bbq sauce"],
            "garlic_sauce": ["sos usturoi", "garlic sauce"],
            "salsa_sauce": ["salsa", "chunky salsa"],
            "sweet_chili_sauce": ["sweet chili", "sos chili dulce"],
            "dijon_mustard": ["dijon"],
            "light_mayonnaise": ["maioneza light", "maioneză light", "light mayonnaise"],
            "salt": ["sare", "salt"],
            "pepper": ["piper", "pepper"],
            "paprika": ["boia", "paprika"],
            "spice_mix": ["mix condimente", "amestec condimente", "seasoning mix"],
            "stock_cube": ["cub supa", "cub supă", "stock cube", "bouillon"],
            "toast_bread": ["paine toast", "pâine toast", "toast bread"],
            "sliced_bread": ["paine feliata", "pâine feliată", "sliced bread"],
            "wholegrain_bread": ["paine integrala", "pâine integrală", "wholegrain bread"],
            "buns": ["chifle", "burger buns", "hot dog buns"],
            "tortilla_wrap": ["tortilla wrap", "lipie", "wrap"],
            "cup_noodles": ["cup noodles", "noodles cup", "taitei la pahar", "tăiței la pahar"],
            "ramen_noodles": ["ramen", "buldak", "samyang", "shin ramyun"],
            "whey_protein": ["whey protein", "proteina zer", "protein powder", "pudra proteica", "pudră proteică"],
            "canned_sardines": ["sardine", "sardines"],
            "canned_mackerel": ["macrou conserva", "macrou conservă", "canned mackerel"],
            "canned_peas": ["mazare conserva", "mazăre conservă", "canned peas"],
            "canned_chickpeas": ["naut conserva", "năut conservă", "canned chickpeas"],
            "canned_lentils": ["linte conserva", "linte conservă", "canned lentils"],
            "vegetable_spread": ["pasta vegetala", "pastă vegetală", "vegetable spread", "zacusca", "zacuscă"],
            "jam": ["gem", "dulceata", "dulceață", "marmelada", "marmeladă"],
            "honey": ["miere", "honey"],
            "frozen_fruit": ["fructe congelate", "frozen fruit"],
            "frozen_vegetable_mix": ["mix legume congelate", "amestec legume congelate", "frozen vegetable mix"],
            "frozen_dessert": ["desert congelat", "frozen dessert"],
            "baby_biscuits": ["biscuiti bebelusi", "biscuiți bebeluși", "baby biscuits"],
            "baby_snack": ["snack bebelusi", "snack bebeluși", "baby snack"],
        }.get(scanned_family, [])

        if detailed_family_keywords:
            family_keywords = list(dict.fromkeys([*family_keywords, *detailed_family_keywords]))

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

        if candidate_family not in get_compatible_recommendation_families(scanned_family):
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
    lock_catalog_key(f"product:{product_data['barcode']}")
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


@route("/barcode/import", methods=["POST"])
def import_barcode_product():
    data = request.get_json(silent=True) or {}
    barcode = str(data.get("barcode") or "").strip()
    barcode_error = validate_barcode(barcode, required=True)

    if barcode_error:
        return jsonify({"error": barcode_error}), 400

    existing_product = Product.query.filter_by(barcode=barcode).first()

    if existing_product:
        return jsonify({
            "message": "Produsul există deja în baza locală.",
            "product": product_to_dict(existing_product),
        })

    try:
        off_product = fetch_off_product_by_barcode(barcode)
    except requests.RequestException as error:
        app.logger.warning("Open Food Facts import failed for %s: %s", barcode, error)
        return jsonify({
            "error": "Catalogul extern nu este disponibil momentan.",
            "code": "external_catalog_unavailable",
        }), 502

    if not off_product:
        return jsonify({
            "error": "Produsul nu există în sursa verificată. Trimite-l ca propunere cu fotografii.",
            "code": "verified_source_product_not_found",
        }), 404

    product_data = build_product_from_open_food_facts(barcode, off_product)
    product = save_product_to_local_database(product_data)

    return jsonify({
        "message": "Produs importat din sursa verificată.",
        "product": product_to_dict(product),
    }), 201


@route("/ai/identify-product-frame", methods=["POST"])
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
    try:
        vision_provider = get_vision_provider()
    except VisionProviderNotConfigured:
        vision_provider = None

    if not vision_enabled or not vision_provider or not vision_provider.configured:
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

    try:
        image = ImageOps.exif_transpose(Image.open(BytesIO(frame_bytes))).convert("RGB")
        image.thumbnail((1280, 1280))
        normalized_frame = BytesIO()
        image.save(normalized_frame, "JPEG", quality=82, optimize=True)
        frame_bytes = normalized_frame.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        return jsonify({"error": "Cadrul video nu conține o imagine validă."}), 400

    mime_type = "image/jpeg"

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
        vision_result = parse_json_object(
            vision_provider.analyze(frame_bytes, mime_type, prompt)
        )
    except (json.JSONDecodeError, ValueError):
        return jsonify({
            "error": "Serviciul vision a returnat un răspuns invalid."
        }), 502
    except VisionProviderError as error:
        app.logger.warning("Vision provider request failed: %s", error)
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

    product_name = str(vision_result.get("product_name") or "").strip()[:150]
    barcode = str(vision_result.get("barcode") or "").strip()

    if validate_barcode(barcode):
        barcode = ""
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


@route("/barcode/lookup/<barcode>", methods=["GET"])
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

register_blueprints(app)

# Schema and release data changes are intentionally absent from application
# startup. Run `python migration.py release` before deploying this process.
if PRODUCTION_MODE:
    from migration import assert_database_at_head

    assert_database_at_head(database_url=RUNTIME_CONFIG.database_url)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        port=int(os.environ.get("PORT", "5001")),
    )
