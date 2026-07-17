from flask import Flask

from config import RuntimeConfig


def create_app(import_name, runtime_config=None, config_overrides=None, app_class=Flask):
    """Create the Flask shell before routes and extensions are registered."""
    resolved_config = runtime_config or RuntimeConfig.from_env()
    flask_app = app_class(import_name)
    resolved_config.apply_to(flask_app)

    if config_overrides:
        flask_app.config.update(config_overrides)

    flask_app.extensions["cealeg_runtime_config"] = resolved_config
    return flask_app
