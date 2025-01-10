from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from langdetect import detect
from googletrans import Translator
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize translator and history
translator = Translator()
command_history = []

# Folder paths for uploads and downloads
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    feedback = analyze_file(save_path)
    return jsonify({'message': 'File uploaded successfully', 'feedback': feedback}), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

def analyze_file(filepath):
    try:
        with open(filepath, 'r') as file:
            content = file.read()
            return f"File contains {len(content.split())} words and {len(content)} characters."
    except Exception as e:
        return f"Could not analyze the file: {str(e)}"

@socketio.on('send_message')
def handle_realtime_message(data):
    command = data.get('command', '')
    language = detect_language(command)
    response = process_command(command, language)
    command_history.append({'command': command, 'response': response, 'language': language})
    socketio.emit('receive_message', {"response": response, "history": command_history})

def detect_language(text):
    try:
        return detect(text)
    except Exception:
        return 'unknown'

def process_command(command, language):
    if language != 'en':
        command = translator.translate(command, src=language, dest='en').text

    if command.lower() == 'hello':
        return "Hello! How can I assist you today?"
    elif command.lower() == 'show history':
        return "\n".join([f"Command: {h['command']} | Response: {h['response']}" for h in command_history])
    elif command.lower() == 'what can you do?':
        return "I can communicate, process tasks, analyze data, and more."
    else:
        return f"I'm still learning. Your command '{command}' is noted for improvement."

if __name__ == '__main__':
    socketio.run(app, debug=True)
