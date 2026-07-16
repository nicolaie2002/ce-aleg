from datetime import datetime
from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    email_verified = db.Column(db.Boolean, default=True, nullable=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    invite_code = db.Column(db.String(30), unique=True, nullable=True, index=True)
    referred_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    bonus_unlimited_until = db.Column(db.DateTime, nullable=True)
    bonus_scan_credits = db.Column(db.Integer, default=0, nullable=False)
    auth_version = db.Column(db.Integer, default=0, nullable=False)
    processing_restricted = db.Column(db.Boolean, default=False, nullable=False)
    processing_restricted_at = db.Column(db.DateTime, nullable=True)
    processing_restriction_reason = db.Column(db.String(500), nullable=True)
    terms_version = db.Column(db.String(30), nullable=True)
    terms_accepted_at = db.Column(db.DateTime, nullable=True)
    age_confirmed_at = db.Column(db.DateTime, nullable=True)
    analytics_consent = db.Column(db.Boolean, nullable=True)
    analytics_consent_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)
    store = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(80), nullable=True)

    score = db.Column(db.Float, nullable=False)
    tag = db.Column(db.String(100), nullable=True)

    image = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, nullable=True)
    price_text = db.Column(db.String(100), nullable=True)

    calories = db.Column(db.Float, nullable=True)
    protein = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    fat = db.Column(db.Float, nullable=True)

    vegan = db.Column(db.Boolean, default=False)
    lactose_free = db.Column(db.Boolean, default=False)
    natural = db.Column(db.Boolean, default=False)

    reason = db.Column(db.Text, nullable=True)
    ingredients = db.Column(db.Text, nullable=True)


class ProductSubmission(db.Model):
    __tablename__ = "product_submissions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    product_name = db.Column(db.String(150), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    store = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.String(100), nullable=True)
    barcode = db.Column(db.String(80), nullable=True)
    price = db.Column(db.String(100), nullable=True)

    front_image = db.Column(db.String(255), nullable=True)
    nutrition_image = db.Column(db.String(255), nullable=True)

    calories = db.Column(db.Float, nullable=True)
    protein = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    fat = db.Column(db.Float, nullable=True)

    ingredients = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(30), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="product_submissions")


class ScanHistory(db.Model):
    __tablename__ = "scan_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)

    store = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    score = db.Column(db.Float, nullable=True)
    price = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(255), nullable=True)

    verdict = db.Column(db.Text, nullable=True)
    short_advice = db.Column(db.Text, nullable=True)

    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="scan_history")


class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)

    store = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    score = db.Column(db.Float, nullable=True)
    price = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="favorites")


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    family_profile_id = db.Column(
        db.Integer,
        db.ForeignKey("family_profiles.id"),
        nullable=True,
        index=True,
    )
    product_name = db.Column(db.String(150), nullable=False)

    store = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=True)
    price = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    reason = db.Column(db.Text, nullable=True)

    quantity = db.Column(db.Integer, default=1)
    bought = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="cart_items")
    family_profile = db.relationship("FamilyProfile")


class PriceObservation(db.Model):
    __tablename__ = "price_observations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_barcode = db.Column(db.String(80), nullable=False, index=True)
    store = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="RON")
    observed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="price_observations")


class SearchEvent(db.Model):
    __tablename__ = "search_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    search_text = db.Column("query", db.String(250), nullable=False)
    store = db.Column(db.String(100), nullable=True)
    result_count = db.Column(db.Integer, default=0, nullable=False)
    source = db.Column(db.String(40), nullable=False, default="product_search")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="search_events")


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    plan = db.Column(db.String(30), nullable=False, default="free")
    status = db.Column(db.String(30), nullable=False, default="active")
    provider = db.Column(db.String(50), nullable=True)
    provider_customer_id = db.Column(db.String(120), nullable=True)
    provider_subscription_id = db.Column(db.String(120), nullable=True)
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="subscription")


class FamilyProfile(db.Model):
    __tablename__ = "family_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    color = db.Column(db.String(30), nullable=False, default="teal")
    avatar = db.Column(db.String(20), nullable=True)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="family_profiles")


class UsageEvent(db.Model):
    __tablename__ = "usage_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)
    source = db.Column(db.String(40), nullable=True)
    idempotency_key = db.Column(db.String(180), nullable=True, unique=True, index=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", backref="usage_events")


class StripeWebhookEvent(db.Model):
    __tablename__ = "stripe_webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    provider_event_id = db.Column(db.String(180), nullable=False, unique=True, index=True)
    event_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="processing", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=1)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime, nullable=True)


class ConsentRecord(db.Model):
    __tablename__ = "consent_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    consent_type = db.Column(db.String(80), nullable=False, index=True)
    granted = db.Column(db.Boolean, nullable=False)
    policy_version = db.Column(db.String(40), nullable=False)
    source = db.Column(db.String(80), nullable=False, default="web")
    request_identity_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", backref="consent_records")
