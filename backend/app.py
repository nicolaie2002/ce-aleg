from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
from PIL import Image, ImageOps
from sqlalchemy import text
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
OPEN_PRICES_CACHE = {}
OPEN_PRICES_CACHE_TTL = 30 * 60
AI_STATUS_CACHE = {"created_at": 0, "data": None}
AI_STATUS_CACHE_TTL = 30
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
    if database_url
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
FREE_WEEKLY_SCAN_LIMIT = int(os.environ.get("FREE_WEEKLY_SCAN_LIMIT", "5"))
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
ACCOUNT_DELETE_MAX_AGE = int(os.environ.get("ACCOUNT_DELETE_MAX_AGE", str(24 * 60 * 60)))

PLAN_CATALOG = {
    "free": {
        "id": "free",
        "name": "Free",
        "monthlyPrice": 0,
        "yearlyPrice": 0,
        "weeklyScanLimit": FREE_WEEKLY_SCAN_LIMIT,
        "features": [
            "5 scanari pe saptamana",
            "2 alternative pentru fiecare produs",
            "verdict rapid si istoric de baza",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "monthlyPrice": 19.99,
        "yearlyPrice": 149,
        "weeklyScanLimit": None,
        "features": [
            "scanari nelimitate",
            "asistent live la raft",
            "3 alternative imediat + afiseaza mai multe",
            "cautare dupa preferintele tale",
            "istoric complet",
        ],
    },
    "family": {
        "id": "family",
        "name": "Family",
        "monthlyPrice": 29.99,
        "yearlyPrice": 249,
        "weeklyScanLimit": None,
        "features": [
            "scanari nelimitate",
            "profiluri pentru familie",
            "preferinte separate",
            "liste comune de cumparaturi",
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


def get_auth_serializer():
    return URLSafeTimedSerializer(app.config["AUTH_SECRET"], salt="cealeg-auth")


def get_password_reset_serializer():
    return URLSafeTimedSerializer(
        app.config["AUTH_SECRET"],
        salt="cealeg-password-reset",
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
            return True

        app.logger.warning(
            "Brevo email failed with status %s: %s",
            response.status_code,
            response.text[:300],
        )
        return False
    except Exception as error:
        app.logger.warning("Brevo email failed: %s", error)
        return False


def send_resend_email(to_email, subject, text_body, html_body=None):
    payload = {
        "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": get_email_html_body(text_body, html_body),
    }

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
            return True

        app.logger.warning(
            "Resend email failed with status %s: %s",
            response.status_code,
            response.text[:300],
        )
        return False
    except Exception as error:
        app.logger.warning("Resend email failed: %s", error)
        return False


def send_smtp_email(to_email, subject, text_body, html_body=None):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    message["To"] = to_email
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

        return True
    except Exception as error:
        app.logger.warning("SMTP email failed: %s", error)
        return False


def send_transactional_email(to_email, subject, text_body, html_body=None):
    if not is_email_configured():
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


def send_welcome_email(user):
    dashboard_url = f"{FRONTEND_PUBLIC_URL}/dashboard"
    text_body = (
        f"Salut, {user.name}!\n\n"
        "Contul tau Ce aleg? este pregatit.\n"
        "Poti scana produse, salva cosul si primi alternative mai bune.\n\n"
        f"Intra aici: {dashboard_url}\n"
    )
    html_body = f"""
    <p>Salut, {user.name}!</p>
    <p>Contul tau <strong>Ce aleg?</strong> este pregatit.</p>
    <p>Poti scana produse, salva cosul si primi alternative mai bune.</p>
    <p><a href="{dashboard_url}">Deschide dashboardul</a></p>
    """
    return send_transactional_email(
        user.email,
        "Bine ai venit in Ce aleg?",
        text_body,
        html_body,
    )


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
        f"Schimba parola aici: {reset_url}\n\n"
        "Linkul expira in 60 de minute. Daca nu ai cerut resetarea, ignora acest email.\n"
    )
    html_body = f"""
    <p>Salut, {user.name}!</p>
    <p>Ai cerut resetarea parolei pentru contul <strong>Ce aleg?</strong>.</p>
    <p><a href="{reset_url}">Schimba parola</a></p>
    <p>Linkul expira in 60 de minute. Daca nu ai cerut resetarea, ignora acest email.</p>
    """
    sent = send_transactional_email(
        user.email,
        "Resetare parola Ce aleg?",
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
        "Ai cerut stergerea contului Ce aleg?.\n"
        "Daca tu ai facut cererea, confirma stergerea aici:\n"
        f"{deletion_url}\n\n"
        "Linkul expira in 24 de ore. Daca nu ai cerut stergerea, ignora acest email "
        "si contul tau ramane activ.\n"
    )
    html_body = f"""
    <p>Salut, {user.name}!</p>
    <p>Ai cerut stergerea contului <strong>Ce aleg?</strong>.</p>
    <p>Daca tu ai facut cererea, confirma stergerea aici:</p>
    <p><a href="{deletion_url}">Sterge contul meu</a></p>
    <p>Linkul expira in 24 de ore. Daca nu ai cerut stergerea, ignora acest email si contul tau ramane activ.</p>
    """
    sent = send_transactional_email(
        user.email,
        "Confirmare stergere cont Ce aleg?",
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
        return False, "Abonamentul Stripe nu a putut fi anulat momentan. Incearca din nou sau contacteaza suportul."

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


def user_to_dict(user):
    subscription = get_or_create_subscription(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "isAdmin": bool(user.is_admin),
        "plan": subscription.plan,
        "subscriptionStatus": subscription.status,
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
        blockers.append("DATABASE_URL lipseste. Pentru publicare foloseste Supabase/Postgres, nu SQLite local.")

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
    elif payment_provider in {"", "manual", "mock", "none"}:
        warnings.append("Platile reale nu sunt conectate. Pro/Family se pot activa doar manual din admin.")

    if not env_flag("ENABLE_OPENAI_VISION", False):
        warnings.append("Vision cloud este oprit. Produsul ramane functional prin barcode, OCR local si Open Food Facts.")

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        warnings.append("Storage Supabase nu este complet configurat; imaginile contribuite pot ramane locale.")

    if not is_email_configured():
        warnings.append(
            "Emailurile tranzactionale nu sunt configurate; welcome/reset vor merge doar in mod local de test."
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


def update_existing_stripe_subscription_price(
    local_subscription,
    plan,
    billing_interval,
    price_id,
    metadata,
):
    if (
        local_subscription.provider != "stripe"
        or not local_subscription.provider_subscription_id
        or not configure_stripe()
    ):
        return None

    try:
        stripe_subscription = stripe.Subscription.retrieve(
            local_subscription.provider_subscription_id
        )
        line_item_id = get_subscription_line_item_id(stripe_subscription)

        if not line_item_id:
            return None

        updated_subscription = stripe.Subscription.modify(
            local_subscription.provider_subscription_id,
            cancel_at_period_end=False,
            items=[{"id": line_item_id, "price": price_id}],
            metadata=metadata,
            proration_behavior=os.environ.get(
                "STRIPE_PRORATION_BEHAVIOR",
                "create_prorations",
            ).strip()
            or "create_prorations",
        )
    except Exception as error:
        app.logger.warning("Stripe subscription update failed: %s", error)
        return None

    synced_subscription = sync_stripe_subscription(updated_subscription)

    if synced_subscription:
        return {
            "mode": "stripe",
            "plan": plan,
            "billingInterval": billing_interval,
            "updated": True,
            "message": "Abonamentul a fost actualizat.",
        }

    return None


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


def handle_stripe_checkout_completed(session):
    metadata = session.get("metadata") or {}
    plan = metadata.get("plan")
    user_id = metadata.get("user_id")
    subscription_id = session.get("subscription")

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

    return update_local_subscription_from_stripe(
        user=user,
        plan=plan,
        status="active",
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


def get_weekly_scan_count(user_id):
    week_start = get_week_start()
    return UsageEvent.query.filter(
        UsageEvent.user_id == user_id,
        UsageEvent.event_type == "scan",
        UsageEvent.created_at >= week_start,
    ).count()


def get_usage_summary(user):
    subscription = get_or_create_subscription(user)
    limit = None if is_paid_subscription(subscription) else FREE_WEEKLY_SCAN_LIMIT
    used = get_weekly_scan_count(user.id)
    week_start = get_week_start()
    reset_at = week_start + timedelta(days=7)

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "weeklyScanLimit": limit,
        "weeklyScansUsed": used,
        "weeklyScansRemaining": None if limit is None else max(limit - used, 0),
        "resetsAt": reset_at.isoformat() + "Z",
        "isUnlimited": limit is None,
    }


def reserve_scan_usage(user, source, metadata=None):
    if user.is_admin:
        return {"allowed": True, "usage": get_usage_summary(user)}

    subscription = get_or_create_subscription(user)

    if is_paid_subscription(subscription):
        db.session.add(
            UsageEvent(
                user_id=user.id,
                event_type="scan",
                source=source,
                metadata_json=json.dumps(metadata or {}),
            )
        )
        db.session.commit()
        return {"allowed": True, "usage": get_usage_summary(user)}

    used = get_weekly_scan_count(user.id)

    if used >= FREE_WEEKLY_SCAN_LIMIT:
        return {
            "allowed": False,
            "usage": get_usage_summary(user),
            "error": {
                "code": "scan_limit_reached",
                "message": "Ai folosit cele 5 scanari gratuite din aceasta saptamana. Treci la Pro pentru scanari nelimitate.",
            },
        }

    db.session.add(
        UsageEvent(
            user_id=user.id,
            event_type="scan",
            source=source,
            metadata_json=json.dumps(metadata or {}),
        )
    )
    db.session.commit()
    return {"allowed": True, "usage": get_usage_summary(user)}


def respond_scan_limit(scan_gate):
    return jsonify({
        "error": scan_gate["error"]["message"],
        "code": scan_gate["error"]["code"],
        "usage": scan_gate["usage"],
        "plans": PLAN_CATALOG,
    }), 402


ADMIN_ENDPOINTS = {
    "init_db",
    "get_users",
    "seed_products",
    "cleanup_duplicate_products",
    "ai_review_product_submission",
    "approve_product_submission",
    "get_admin_overview",
    "get_admin_submissions",
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

    if not rate_limit("global", GLOBAL_RATE_LIMIT, GLOBAL_RATE_LIMIT_WINDOW):
        return jsonify({"error": "Prea multe cereri. Reincearca in cateva secunde."}), 429

    payload_error = validate_request_payload()

    if payload_error:
        return payload_error

    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        if not request_origin_is_trusted() or not request_fetch_metadata_is_trusted():
            return jsonify({"error": "Cererea a fost blocata din motive de securitate."}), 403

    if endpoint in {
        "login",
        "register",
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
        return jsonify({"error": "Prea multe traduceri. Reincearca in cateva secunde."}), 429

    if endpoint in {"ai_extract_product_info", "get_open_food_facts_alternatives"} and not rate_limit(
        endpoint, 30, 60
    ):
        return jsonify({"error": "Prea multe cereri. Reincearca in cateva secunde."}), 429

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
            return jsonify({"error": "Nu poti modifica datele altui cont."}), 403

    if endpoint == "add_product_submission" and not user.is_admin:
        user_id = request.form.get("user_id")

        if user_id and not require_same_user(user_id):
            return jsonify({"error": "Nu poti trimite produse pentru alt cont."}), 403

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
        "error": "A aparut o eroare interna. Reincearca in cateva momente.",
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
    "Informatiile nutritionale sunt limitate. Verifica zaharul, caloriile si "
    "ingredientele de pe eticheta, apoi compara produsul cu variante similare."
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
        "ice_cream": "Înghețată",
        "spread": "Creme tartinabile",
        "yogurt": "Lactate",
        "cheese": "Lactate și brânzeturi",
        "energy_drink": "Băuturi energizante",
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
    }

    for brand, aliases in brand_aliases.items():
        if any(alias in words or alias in text for alias in aliases):
            return brand

    return None


def detect_product_type(search_text):
    text = normalize_search_text(search_text)

    product_types = [
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
                "skyr",
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
    ]

    for product_type, tokens in product_types:
        if any(token in text for token in tokens):
            return product_type

    return None


def product_matches_query_type(product_text, product_type):
    if not product_type:
        return True

    type_tokens = {
        "ice_cream": {"inghetata", "gelato", "ice cream", "icecream", "sorbet"},
        "spread": {"crema tartinabila", "spread", "nutella"},
        "yogurt": {"iaurt", "yogurt", "skyr"},
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
    products_query = Product.query

    all_products = products_query.all()

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
            "Produsul are informatii nutritionale limitate. Verifica zaharul, "
            "caloriile si ingredientele de pe eticheta, apoi compara-l cu produse "
            "din aceeasi categorie."
        )

    sentence = "Produsul " + ", ".join(reasons) + "."

    if ingredients_text:
        sentence += f" Observații: {ingredients_text}"

    return sentence

def normalize_product_name_for_duplicate(text):
    if not text:
        return ""

    text = normalize_search_text(text)

    generic_words = {
        "energy",
        "energizant",
        "energizanta",
        "bautura",
        "băutură",
        "drink",
        "doza",
        "can",
        "produs",
        "cu",
        "fara",
        "fără",
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
        db.session.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        db.session.commit()
        return

    add_column_if_missing("users", "is_admin", "BOOLEAN NOT NULL DEFAULT 0")
    add_column_if_missing("products", "barcode", "VARCHAR(80)")
    add_column_if_missing("products", "ingredients", "TEXT")
    add_column_if_missing("product_submissions", "barcode", "VARCHAR(80)")


def ensure_configured_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()

    if not admin_email:
        return

    user = User.query.filter_by(email=admin_email).first()

    if user and not user.is_admin:
        user.is_admin = True
        db.session.commit()

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
    to_email = (data.get("to") or g.current_user.email).strip().lower()

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to_email):
        return jsonify({"error": "Adresa de email nu este valida."}), 400

    if not is_email_configured():
        return jsonify({
            "sent": False,
            "error": "Emailul nu este configurat. Completeaza EMAIL_PROVIDER si cheia providerului ales.",
        }), 400

    sent = send_transactional_email(
        to_email,
        "Test email Ce aleg?",
        (
            "Salut!\n\n"
            "Emailurile tranzactionale Ce aleg? functioneaza. "
            "Resetarea parolei si mesajele de cont pot fi trimise din cloud.\n"
        ),
        """
        <p>Salut!</p>
        <p>Emailurile tranzactionale <strong>Ce aleg?</strong> functioneaza.</p>
        <p>Resetarea parolei si mesajele de cont pot fi trimise din cloud.</p>
        """,
    )

    if not sent:
        return jsonify({
            "sent": False,
            "error": "Emailul de test nu a putut fi trimis. Verifica datele SMTP.",
        }), 502

    return jsonify({
        "sent": True,
        "message": "Email de test trimis cu succes.",
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

    if not name or not email or not password:
        return jsonify({"error": "Numele, emailul si parola sunt obligatorii."}), 400

    if not age_confirmed:
        return jsonify({
            "error": "Pentru cont trebuie sa confirmi ca ai cel putin 16 ani sau acordul parintelui/tutorelui."
        }), 400

    if not accepted_terms:
        return jsonify({
            "error": "Trebuie sa accepti Termenii si Politica de confidentialitate."
        }), 400

    password_strength = validate_password_strength(password)

    if not password_strength["isValid"]:
        return jsonify({
            "error": f"Parola trebuie sa aiba minimum {PASSWORD_MIN_LENGTH} caractere.",
            "passwordStrength": password_strength,
        }), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({"error": "Exista deja un cont cu acest email."}), 409

    new_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
    )

    db.session.add(new_user)
    db.session.commit()
    welcome_email_sent = send_welcome_email(new_user)
    email_status = {
        "welcomeSent": welcome_email_sent,
        "configured": is_email_configured(),
        "provider": EMAIL_PROVIDER,
    }

    if not welcome_email_sent:
        app.logger.warning("Welcome email was not sent for user %s", new_user.id)

    response = jsonify({
        "message": "Cont creat cu succes.",
        "user": user_to_dict(new_user),
        "emailStatus": email_status,
    })
    return set_auth_cookie(response, new_user), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Emailul si parola sunt obligatorii."}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Email sau parola gresita."}), 401

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
        "message": "Daca exista un cont cu acest email, vei primi un link pentru resetarea parolei.",
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
        return jsonify({"error": "Tokenul si parola noua sunt obligatorii."}), 400

    user = verify_password_reset_token(token)

    if not user:
        return jsonify({"error": "Linkul de resetare este invalid sau a expirat."}), 400

    password_strength = validate_password_strength(password)

    if not password_strength["isValid"]:
        return jsonify({
            "error": f"Parola trebuie sa aiba minimum {PASSWORD_MIN_LENGTH} caractere.",
            "passwordStrength": password_strength,
        }), 400

    user.password_hash = generate_password_hash(password)
    db.session.commit()

    response = jsonify({
        "message": "Parola a fost schimbata. Te-am autentificat automat.",
        "user": user_to_dict(user),
    })
    return set_auth_cookie(response, user)


@app.route("/account/delete/request", methods=["POST"])
def request_account_deletion():
    user = g.current_user
    sent, deletion_url = send_account_deletion_email(user)

    if not sent and PRODUCTION_MODE:
        return jsonify({
            "error": "Emailul de confirmare nu a putut fi trimis momentan. Incearca din nou mai tarziu.",
            "emailConfigured": is_email_configured(),
        }), 502

    response = {
        "message": "Ti-am trimis un email cu linkul de confirmare pentru stergerea contului.",
        "sent": sent,
        "email": user.email,
        "emailConfigured": is_email_configured(),
    }

    if not sent and not PRODUCTION_MODE:
        response["devDeletionLink"] = deletion_url
        response["message"] = (
            "Emailul nu a putut fi trimis in mediul local. Foloseste linkul de test pentru confirmare."
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
        return jsonify({"error": "Linkul de stergere este invalid sau a expirat."}), 400

    canceled, cancel_error = cancel_subscription_before_account_deletion(user)

    if not canceled:
        return jsonify({"error": cancel_error}), 502

    try:
        delete_account_data(user)
    except Exception as error:
        db.session.rollback()
        app.logger.exception("Account deletion failed: %s", error)
        return jsonify({
            "error": "Contul nu a putut fi sters momentan. Incearca din nou mai tarziu.",
        }), 500

    response = jsonify({
        "message": "Contul tau si datele personale asociate au fost sterse.",
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
        metadata = {
            "user_id": str(user.id),
            "plan": plan,
            "billing_interval": billing_interval,
            "price_id": price_id,
            "price_env": price_env_name,
            "app": "ce-aleg",
        }
        existing_subscription_update = update_existing_stripe_subscription_price(
            subscription,
            plan,
            billing_interval,
            price_id,
            metadata,
        )

        if existing_subscription_update:
            return jsonify(existing_subscription_update)

        automatic_tax_enabled = env_flag("STRIPE_AUTOMATIC_TAX", False)
        checkout_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{FRONTEND_PUBLIC_URL}/pricing?checkout=success",
            "cancel_url": f"{FRONTEND_PUBLIC_URL}/pricing?checkout=cancelled",
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

        if (
            subscription.provider == "stripe"
            and subscription.provider_customer_id
        ):
            checkout_params["customer"] = subscription.provider_customer_id
            checkout_params["customer_update"] = {
                "address": "auto",
                "name": "auto",
            }
        else:
            checkout_params["customer_email"] = user.email

        try:
            checkout_session = stripe.checkout.Session.create(**checkout_params)
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
        "message": "Am notat alegerea ta. Verifica datele de plata sau activeaza planul din administrare.",
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

    return jsonify({"received": True})


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


@app.route("/admin/products/<int:product_id>", methods=["DELETE"])
def delete_admin_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        return jsonify({"error": "Produsul nu exista."}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Produs sters din catalog."})


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

    if len(query_text) >= 3:
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

    db.session.add(SearchEvent(
        user_id=user_id if user_id and User.query.get(user_id) else None,
        search_text=query_text[:250],
        store=store_name,
        result_count=len(results),
        source="openfoodfacts",
    ))
    db.session.commit()

    response = jsonify(results)
    response.headers["X-Product-Source"] = "openfoodfacts"
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
    category_tag = get_off_alternative_category(scanned_product)

    off_products = []
    lookup_errors = []

    if category_tag:
        try:
            off_products.extend(fetch_off_category_products(category_tag))
        except requests.RequestException as error:
            lookup_errors.append(str(error))
            app.logger.warning(
                "Open Food Facts category alternatives failed for %s: %s",
                category_tag,
                error,
            )

    if len(off_products) < 8:
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

    if not off_products and category_tag:
        try:
            search_products = fetch_off_search_products(scanned_product, None)
            off_products.extend(search_products)
        except requests.RequestException as error:
            lookup_errors.append(str(error))
            app.logger.warning(
                "Open Food Facts broad alternatives failed: %s",
                error,
            )

    if len(off_products) < 6:
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

        if "caffeine" in criteria and not is_high_caffeine_candidate(candidate):
            continue

        alternatives.append(candidate)

    existing_alternative_keys = {
        normalize_search_text(f"{item.get('barcode') or ''} {item.get('name') or ''}")
        for item in alternatives
    }

    for candidate in get_known_catalog_alternatives(scanned_product, criteria):
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
    photographed_alternatives = [
        product for product in alternatives if product.get("image")
    ]
    alternatives_without_photos = [
        product for product in alternatives if not product.get("image")
    ]

    return jsonify({
        "source": "openfoodfacts",
        "category": category_tag,
        "products": (photographed_alternatives + alternatives_without_photos)[:6],
        "message": (
            "Alternative calculate din catalogul Open Food Facts."
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

    items = CartItem.query.filter_by(user_id=user_id).order_by(
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

    existing_item = CartItem.query.filter_by(
        user_id=user_id,
        product_name=product_name,
        store=store
    ).first()

    if existing_item:
        existing_item.quantity += 1
        db.session.commit()

        return jsonify({
            "message": "Cantitatea produsului a fost actualizată.",
            "item": cart_item_to_dict(existing_item)
        })

    new_item = CartItem(
        user_id=user_id,
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

    CartItem.query.filter_by(user_id=user_id).delete()
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
        return jsonify({"error": "Nu poti accesa aceasta imagine."}), 403

    return send_from_directory(SUBMISSIONS_FOLDER, filename)


@app.route("/uploads/scans/<path:filename>", methods=["GET"])
@require_auth
def get_scan_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/uploads/supabase-submissions/<path:object_path>", methods=["GET"])
def get_supabase_submission_image(object_path):
    image_path = f"/uploads/supabase-submissions/{object_path}"

    if not user_can_access_submission_image(image_path):
        return jsonify({"error": "Nu poti accesa aceasta imagine."}), 403

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
        db.session.commit()

        return jsonify({
            "message": "Produsul pare să existe deja în baza oficială. Propunerea a fost marcată ca aprobată, fără să se creeze duplicat.",
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
    db.session.commit()

    return jsonify({
        "message": "Produsul a fost publicat în baza oficială cu scor și verdict generate automat.",
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
    product_text = normalize_search_text(
        " ".join([product_name, brands, categories, ingredients or ""])
    )

    if any(word in product_text for word in ["ice cream", "icecream", "gelato", "sorbet", "inghetata"]):
        category = "Înghețată"
    elif any(word in product_text for word in ["coffee", "cafea", "cappuccino", "capuccino", "latte", "mocha", "espresso", "ice coffee", "iced coffee", "cold brew", "frappe"]):
        category = "Băuturi cu cafea"
    elif "energy drink" in categories_lower or "energ" in categories_lower:
        category = "Băuturi energizante"
    elif (
        "dairy dessert" in categories_lower
        or "dessert" in categories_lower
        or "pudding" in categories_lower
        or "custard" in categories_lower
        or "cream dessert" in categories_lower
        or any(word in product_text for word in ["danette", "budinca", "desert lactat"])
    ):
        category = "Deserturi lactate"
    elif "yogurt" in categories_lower or "dairy" in categories_lower:
        category = "Lactate"
    elif "beverage" in categories_lower or "drink" in categories_lower:
        category = "Băuturi"
    elif "snack" in categories_lower:
        category = "Snacks"
    elif "sweet" in categories_lower or "candy" in categories_lower or "chocolate" in categories_lower:
        category = "Dulciuri"
    elif "cereal" in categories_lower:
        category = "Cereale"
    elif "meat" in categories_lower:
        category = "Carne"
    elif "bread" in categories_lower or "bakery" in categories_lower:
        category = "Panificație"
    elif "fruit" in categories_lower or "vegetable" in categories_lower:
        category = "Fructe și legume"
    elif "sauce" in categories_lower or "mustard" in categories_lower or "condiment" in categories_lower:
        category = "Sosuri și condimente"

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
                "User-Agent": "CeAlegApp/1.0 (contact: local-dev)",
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

    if any(word in text_value for word in water_words) and not any(
        word in text_value
        for word in energy_words + coffee_words + caffeine_words + cola_words
    ):
        return "water"

    if any(word in text_value for word in coffee_words):
        return "coffee_drink"

    if any(word in text_value for word in energy_words):
        return "energy_drink"

    if any(word in text_value for word in caffeine_words):
        return "caffeinated_beverage"

    if any(word in text_value for word in cola_words):
        return "cola"

    if any(word in text_value for word in dairy_dessert_words):
        return "dairy_dessert"

    if any(word in text_value for word in ["lactate", "dairy", "iaurt", "yogurt", "skyr", "lapte", "milk"]):
        return "lactate"

    if "bauturi" in text_value or "beverage" in text_value or "drink" in text_value:
        return "beverage"

    return "general"


def is_compatible_alternative(scanned_product, candidate):
    scanned_family = get_product_recommendation_family(scanned_product)
    candidate_family = get_product_recommendation_family(candidate)

    if candidate_family == "water" and scanned_family != "water":
        return False

    if scanned_family in {
        "coffee_drink",
        "energy_drink",
        "caffeinated_beverage",
        "cola",
    }:
        return candidate_family in {
            "coffee_drink",
            "energy_drink",
            "caffeinated_beverage",
            "cola",
        }

    if scanned_family == "dairy_dessert":
        return candidate_family in {"dairy_dessert", "lactate", "general"} or (
            normalize_search_text(candidate.get("category")) in {"lactate", "deserturi lactate"}
        )

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
        "bauturi energizante": "en:energy-drinks",
        "bauturi cu cafea": "en:iced-coffees",
        "bauturi": "en:beverages",
        "lactate": "en:dairies",
        "deserturi lactate": "en:dairy-desserts",
        "snacks": "en:snacks",
        "dulciuri": "en:sweet-snacks",
        "cereale": "en:breakfast-cereals",
        "carne": "en:meats",
        "panificatie": "en:breads",
        "fructe si legume": "en:fruits-and-vegetables",
        "sosuri si condimente": "en:condiments",
    }

    if category in category_map:
        return category_map[category]

    if any(word in product_text for word in ["hell", "red bull", "redbull", "monster", "energiz", "energy", "taurina", "taurine"]):
        return "en:energy-drinks"

    if any(word in product_text for word in ["coffee", "cafea", "cafe", "cappuccino", "capuccino", "latte", "mocha", "espresso", "iced coffee", "ice coffee", "cold brew", "frappe", "cafeina", "cofeina", "caffeine"]):
        return "en:iced-coffees"

    if any(word in product_text for word in ["danette", "budinca", "pudding", "custard", "desert lactat"]):
        return "en:dairy-desserts"

    if any(word in product_text for word in ["iaurt", "yogurt", "skyr", "lapte", "milk"]):
        return "en:dairies"

    if any(word in product_text for word in ["sos", "mustar", "ketchup", "salsa"]):
        return "en:condiments"

    if any(word in product_text for word in ["ciocolata", "napolitana", "biscuit", "dulce"]):
        return "en:sweet-snacks"

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


def score_off_alternative(products, product, criteria, scanned_product=None):
    score = float(product.get("score") or 0)
    reasons = []
    candidate_family = get_product_recommendation_family(product)
    candidate_text = product_text_for_recommendation(product)

    if scanned_product:
        scanned_family = get_product_recommendation_family(scanned_product)

        if candidate_family == scanned_family:
            score += 8
            reasons.append("aceeași categorie de produs")
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
            score -= 8

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
            "User-Agent": "CeAlegApp/1.0 (contact: local-dev)",
            "Accept": "application/json",
        },
        timeout=15,
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
            "User-Agent": "CeAlegApp/1.0 (contact: local-dev)",
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
                                    "(contact: cealegshop@gmail.com)"
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

    return SequenceMatcher(None, scanned_name, candidate_name).ratio() >= 0.88


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

        if "caffeine" in criteria and not is_high_caffeine_candidate(product_data):
            continue

        alternatives.append(product_data)

    return alternatives


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
        score=product_data["score"],
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

    scan_gate = reserve_scan_usage(
        g.current_user,
        "live_vision",
        {"endpoint": "ai_identify_product_frame"},
    )

    if not scan_gate["allowed"]:
        return respond_scan_limit(scan_gate)

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

    return jsonify({
        "identified": True,
        "source": "local" if local_product else "vision",
        "product": product_to_dict(local_product) if local_product else None,
        "candidate": {
            "name": product_name or None,
            "brand": vision_result.get("brand"),
            "variant": vision_result.get("variant"),
            "barcode": barcode or None,
            "confidence": vision_result.get("confidence", 0),
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

    scan_gate = reserve_scan_usage(
        g.current_user,
        "barcode",
        {"barcode": barcode},
    )

    if not scan_gate["allowed"]:
        return respond_scan_limit(scan_gate)

    local_product = Product.query.filter_by(barcode=barcode).first()

    if local_product:
        return jsonify({
            "found": True,
            "source": "local",
            "product": product_to_dict_with_open_price(local_product),
            "usage": scan_gate["usage"],
        })

    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}"

        headers = {
            "User-Agent": "CeAlegApp/1.0 (contact: local-dev)",
            "Accept": "application/json",
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 404:
            return jsonify({
                "found": False,
                "source": "openfoodfacts",
                "message": "Produsul nu a fost găsit după codul de bare.",
                "barcode": barcode,
            }), 404

        if response.status_code != 200:
            app.logger.warning(
                "Open Food Facts barcode lookup returned status %s: %s",
                response.status_code,
                response.text[:300],
            )
            return jsonify({
                "found": False,
                "source": "openfoodfacts",
                "message": "Open Food Facts a răspuns cu eroare.",
                "status_code": response.status_code,
            }), 502

        data = response.json()

    except Exception as error:
        app.logger.warning("Open Food Facts barcode lookup failed: %s", error)
        return jsonify({
            "found": False,
            "source": "openfoodfacts",
            "code": "openfoodfacts_unavailable",
            "message": "Open Food Facts nu este disponibil momentan. Poți încerca din nou sau contribui produsul manual.",
        }), 503

    if data.get("status") != 1 or not data.get("product"):
        return jsonify({
            "found": False,
            "source": "openfoodfacts",
            "message": "Produsul nu a fost găsit după codul de bare.",
            "barcode": barcode,
        }), 404

    product_data = build_product_from_open_food_facts(barcode, data["product"])
    price_summary = get_open_prices_summary(barcode)

    if price_summary:
        product_data.update(price_summary)

    local_product = save_product_to_local_database(product_data)

    return jsonify({
        "found": True,
        "source": "openfoodfacts",
        "cached": True,
        "product": product_to_dict_with_open_price(local_product),
        "usage": scan_gate["usage"],
    })                                    

with app.app_context():
    db.create_all()
    ensure_database_columns()
    ensure_configured_admin()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        port=int(os.environ.get("PORT", "5001")),
    )


