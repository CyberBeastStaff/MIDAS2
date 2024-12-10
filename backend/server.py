import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS
from backend.chat_routes import chat_routes
from backend.bot_routes import bot_routes
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register blueprints
app.register_blueprint(chat_routes)
app.register_blueprint(bot_routes)

if __name__ == '__main__':
    app.run(port=7860)
