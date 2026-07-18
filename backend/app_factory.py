from flask import Flask

from config import RuntimeConfig


def create_app(
    import_name,
    runtime_config=None,
    config_overrides=None,
    app_class=Flask,
    extension_initializers=(),
    before_request_handlers=(),
    after_request_handlers=(),
    error_handlers=None,
    blueprint_registrar=None,
):
    """Create an isolated Flask application and attach explicit collaborators."""
    resolved_config = runtime_config or RuntimeConfig.from_env()
    flask_app = app_class(import_name)
    resolved_config.apply_to(flask_app)

    if config_overrides:
        flask_app.config.update(config_overrides)

    flask_app.extensions["cealeg_runtime_config"] = resolved_config

    for initializer in extension_initializers:
        initializer(flask_app)

    for handler in before_request_handlers:
        flask_app.before_request(handler)

    for handler in after_request_handlers:
        flask_app.after_request(handler)

    for status_code, handler in (error_handlers or {}).items():
        flask_app.register_error_handler(status_code, handler)

    if blueprint_registrar:
        blueprint_registrar(flask_app)

    return flask_app
