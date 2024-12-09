import logging
from flask import Flask, send_from_directory, render_template
from threading import Thread
from frontend.interface import create_interface
from backend.chat_routes import chat_bp
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create Flask app
app = Flask(__name__, 
           template_folder='frontend/templates',
           static_folder='assets')

app.register_blueprint(chat_bp, url_prefix='/api')

# Serve favicon.ico
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'assets/gfx'),
                             'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Serve other static files from assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

# Serve main page
@app.route('/')
def index():
    return render_template('index.html')

def run_flask():
    app.run(host="127.0.0.1", port=7860)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Starting LLM Platform...")
    
    # Start Flask server in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Create and launch Gradio interface
    interface = create_interface()
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        favicon_path=os.path.join(os.path.dirname(__file__), "assets", "gfx", "favicon.ico"),
        show_api=False,
        show_error=True,
        quiet=True
    )
