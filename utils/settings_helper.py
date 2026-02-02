"""
Settings helper: read app settings from DB for use in app context and routes.
"""
from models.settings import Settings


def get_setting(key, default=''):
    """Get setting value by key. Safe to call from any request context."""
    try:
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting and setting.value is not None else default
    except Exception:
        return default
