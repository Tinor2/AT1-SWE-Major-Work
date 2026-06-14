"""WSGI entry point for PythonAnywhere deployment."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pomodoro import create_app

application = create_app()
