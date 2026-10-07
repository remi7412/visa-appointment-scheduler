import os
import json
import threading
import queue
import time
from flask import Flask, render_template, jsonify, request, Response
from main import VisaBot
from logger import log_queue, log

import sys

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

bot_thread = None
bot_instance = None
bot_running = False

CONFIG_PATH = 'config.json'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return jsonify(json.load(f))
        except json.JSONDecodeError as e:
            log.error(f"Failed to load config.json due to syntax error: {e}")
            return jsonify({"error": f"Syntax error in config.json: {e}"}), 500
    return jsonify({})

@app.route('/api/config', methods=['POST'])
def save_config():
    data = request.json
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "success"})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"running": bot_running})

def run_bot_thread(config_overrides):
    global bot_running, bot_instance
    try:
        log.info("Starting bot from Web UI...")
        bot_instance = VisaBot(config_overrides)
        bot_instance.run()
    except Exception as e:
        log.error(f"Bot crashed: {e}")
    finally:
        bot_running = False
        log.info("Bot execution stopped.")

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_thread, bot_running
    if bot_running:
        return jsonify({"status": "error", "message": "Bot is already running"}), 400
    
    bot_running = True
    bot_thread = threading.Thread(target=run_bot_thread, args=({},))
    bot_thread.daemon = True
    bot_thread.start()
    return jsonify({"status": "success"})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_running, bot_instance
    if not bot_running:
        return jsonify({"status": "error", "message": "Bot is not running"}), 400
    
    log.info("Stopping bot...")
    bot_running = False
    if bot_instance:
        if hasattr(bot_instance, 'bm') and bot_instance.bm:
            bot_instance.bm.stop()
        # Force state to exit if needed
        bot_instance.state = "STOPPED"
        
    return jsonify({"status": "success"})

@app.route('/api/logs')
def stream_logs():
    def generate():
        while True:
            try:
                msg = log_queue.get(timeout=0.5)
                # Escape newlines
                msg = msg.replace('\n', '<br>')
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
            except GeneratorExit:
                break
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5000/')).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
