"""
Main Application Entry Point
Run this file to start the API server
"""

from app.api.app import create_app

# Create app
app = create_app()