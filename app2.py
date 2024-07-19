import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Define your API keys and endpoints
openai_api_key = "sk-proj-KOqKbiVjxAkyOROyLqmqT3BlbkFJDQNXliHvV17jlCcfNjDH"
elevenlabs_api_key = "sk_e5647cac24f572f55023fe8dc0b971f044387a87bfeab080"
whisper_api_key = "sk-proj-KOqKbiVjxAkyOROyLqmqT3BlbkFJDQNXliHvV17jlCcfNjDH"

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Define the OpenAI endpoint
openai_url = "https://api.openai.com/v1/chat/completions"

# Define the Eleven Labs endpoint for text-to-speech
elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/"

# Define the Whisper AI endpoint for transcription
whisper_url = "https://api.openai.ai/v1/transcriptions"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Function to get chatbot response from OpenAI
def get_chatbot_response(prompt, voice_id):
    try:
        prompt_prefix = ""
        if voice_id == "0UmLVoOMMM6fxQsAVmyY":  # Andrew's voice ID
            prompt_prefix = "You are a black man from the hood. Speak as a black man from the hood would."
        if voice_id == "xq7t2qeOp7R2rw1noISp":  # Brenna's voice ID
            prompt_prefix = "You are an American white girl. Speak as an American white girl would."
        if voice_id == "Gqe8GJJLg3haJkTwYj2L":  # Santa's voice ID
            prompt_prefix = "You are Santa Claus. Speak as Santa would."
        if voice_id == "aOcS60CY8CoaVaZfqqb5":  # Cowboy's voice ID
            prompt_prefix = "You are a Cowboy. Speak as a Cowboy would."
        if voice_id == "tVkOo4DLgZb89qB0x4qP":  # Pirate's voice ID
            prompt_prefix = "You are a Pirate. Speak as a Pirate would."

        full_prompt = f"{prompt_prefix} {prompt}"

        openai_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
        }
        openai_payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 1000
        }
        response = requests.post(openai_url, headers=openai_headers, json=openai_payload)
        
        if response.status_code != 200:
            logging.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return "Sorry, I couldn't generate a response."

        response_json = response.json()
        
        if 'choices' not in response_json or len(response_json['choices']) == 0:
            logging.error(f"OpenAI API response format error: {response_json}")
            return "Sorry, I couldn't generate a response."

        return response_json['choices'][0]['message']['content'].strip()

    except Exception as e:
        logging.exception("Error in get_chatbot_response")
        return "Sorry, there was an error processing your request."

# Function to convert text to speech using Eleven Labs
def text_to_speech_elevenlabs(text, voice_id):
    try:
        elevenlabs_headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": elevenlabs_api_key
        }
        elevenlabs_payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        response = requests.post(f"{elevenlabs_url}{voice_id}", json=elevenlabs_payload, headers=elevenlabs_headers)
        
        if response.status_code != 200:
            logging.error(f"Eleven Labs API error: {response.status_code} - {response.text}")
            return None

        output_file = "static/media/audio/output.mp3"
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return output_file
    except Exception as e:
        logging.exception("Error in text_to_speech_elevenlabs")
        return None

# Function to transcribe audio using Whisper AI
def transcribe_audio_whisper(file_path):
    try:
        whisper_headers = {
            "Authorization": f"Bearer {whisper_api_key}"
        }
        files = {'file': open(file_path, 'rb')}
        data = {'model': 'whisper-1'}
        
        response = requests.post(whisper_url, headers=whisper_headers, files=files, data=data)
        
        if response.status_code != 200:
            logging.error(f"Whisper AI API error: {response.status_code} - {response.text}")
            return None

        response_json = response.json()
        return response_json.get("text")
    except Exception as e:
        logging.exception("Error in transcribe_audio_whisper")
        return None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.get_json()
        user_input = data.get('user_input')
        voice_id = data.get('voice_id', '0UmLVoOMMM6fxQsAVmyY')
        chatbot_response = get_chatbot_response(user_input, voice_id)
        audio_file = text_to_speech_elevenlabs(chatbot_response, voice_id)
        if audio_file:
            return jsonify({"response": chatbot_response, "audio_url": audio_file})
        else:
            return jsonify({"error": "Sorry, I couldn't convert the response to audio."}), 500
    except Exception as e:
        logging.exception("Error in /chat endpoint")
        return jsonify({"error": "Internal server error"}), 500
    
@app.route('/process_audio', methods=['POST'])
@login_required
def process_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided."}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No selected file."}), 400

        filename = secure_filename(audio_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(file_path)

        transcribed_text = transcribe_audio_whisper(file_path)
        if not transcribed_text:
            return jsonify({"error": "Failed to transcribe audio."}), 500

        chatbot_response = get_chatbot_response(transcribed_text, '0UmLVoOMMM6fxQsAVmyY')
        audio_file = text_to_speech_elevenlabs(chatbot_response, '0UmLVoOMMM6fxQsAVmyY')
        if audio_file:
            return jsonify({"response": chatbot_response, "audio_url": audio_file})
        else:
            return jsonify({"error": "Sorry, I couldn't convert the response to audio."}), 500
    except Exception as e:
        logging.exception("Error in /process_audio endpoint")
        return jsonify({"error": "Internal server error"}), 500

# User Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')

# User Logout Route
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
