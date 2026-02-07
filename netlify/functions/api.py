"""
Netlify serverless function wrapper for FastAPI
"""
import sys
import os

# Add the parent directory to the path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mangum import Mangum
from main import app

# Create the handler for Netlify Functions
handler = Mangum(app, lifespan="off")
