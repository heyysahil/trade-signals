"""
Gunicorn config: bind to 0.0.0.0 and PORT for Railway/Render.
"""
import os

bind = "0.0.0.0:{}".format(os.environ.get("PORT", "8080"))
workers = 1
threads = 2
timeout = 120
