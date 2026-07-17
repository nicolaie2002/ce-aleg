from routes.admin import blueprint as admin_blueprint
from routes.ai import blueprint as ai_blueprint
from routes.auth import blueprint as auth_blueprint
from routes.billing import blueprint as billing_blueprint
from routes.cart import blueprint as cart_blueprint
from routes.family import blueprint as family_blueprint
from routes.favorites import blueprint as favorites_blueprint
from routes.feedback import blueprint as feedback_blueprint
from routes.gamification import blueprint as gamification_blueprint
from routes.history import blueprint as history_blueprint
from routes.products import blueprint as products_blueprint
from routes.submissions import blueprint as submissions_blueprint
from routes.system import blueprint as system_blueprint


BLUEPRINTS = (
    system_blueprint,
    auth_blueprint,
    products_blueprint,
    cart_blueprint,
    favorites_blueprint,
    history_blueprint,
    submissions_blueprint,
    billing_blueprint,
    gamification_blueprint,
    family_blueprint,
    admin_blueprint,
    feedback_blueprint,
    ai_blueprint,
)


def blueprint_for_rule(rule):
    if rule.startswith("/admin/") or rule in {"/users", "/init-db"}:
        return admin_blueprint
    if rule.startswith("/internal/") or rule in {
        "/products/seed",
        "/products/cleanup-duplicates",
    }:
        return admin_blueprint
    if rule.startswith(("/auth/", "/account/", "/privacy/")) or rule in {
        "/register",
        "/login",
        "/logout",
        "/forgot-password",
        "/reset-password",
        "/dashboard/summary",
    }:
        return auth_blueprint
    if rule.startswith(("/products", "/catalog/", "/barcode/", "/prices/")):
        return products_blueprint
    if rule.startswith("/cart"):
        return cart_blueprint
    if rule.startswith("/favorites"):
        return favorites_blueprint
    if rule.startswith("/history"):
        return history_blueprint
    if rule.startswith(("/submissions", "/uploads/")):
        return submissions_blueprint
    if rule.startswith("/billing"):
        return billing_blueprint
    if rule.startswith("/gamification"):
        return gamification_blueprint
    if rule.startswith("/family"):
        return family_blueprint
    if rule.startswith(("/feedback/", "/support/", "/analytics/")):
        return feedback_blueprint
    if rule.startswith("/ai/") or rule in {"/analyze", "/translate"}:
        return ai_blueprint
    return system_blueprint


def route(rule, **options):
    return blueprint_for_rule(rule).route(rule, **options)


def register_blueprints(flask_app):
    for blueprint in BLUEPRINTS:
        flask_app.register_blueprint(blueprint)
