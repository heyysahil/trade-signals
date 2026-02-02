"""
cPanel / Passenger WSGI entry point.
Place your project in the directory this file lives in; Passenger will use 'application'.
"""
import sys
import os

# Add project directory to path so 'app' can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import application
