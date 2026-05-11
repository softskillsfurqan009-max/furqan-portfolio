import os
import json
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = Flask(__name__)
CORS(app)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'furqan123')

# Gmail Configuration
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# File to store messages
MESSAGES_FILE = 'messages.json'

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_message(message):
    messages = load_messages()
    messages.append(message)
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    return True

def send_email(to_email, subject, body):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("⚠️ Email not configured.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== API ROUTES ====================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files like images"""
    return send_from_directory('static', filename)

@app.route('/api/contacts', methods=['POST'])
def save_contact():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        message = data.get('message')
        
        message_obj = {
            'id': len(load_messages()) + 1,
            'name': name,
            'email': email,
            'message': message,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'unread'
        }
        
        save_message(message_obj)
        
        print(f"\n📧 New Message from {name} ({email})")
        
        # Send email if configured
        if EMAIL_ADDRESS and EMAIL_PASSWORD:
            admin_email_body = f"<h2>New Contact</h2><p><strong>Name:</strong> {name}</p><p><strong>Email:</strong> {email}</p><p><strong>Message:</strong><br>{message}</p>"
            send_email(EMAIL_ADDRESS, f"New Contact from {name}", admin_email_body)
            auto_reply = f"<h2>Thank you!</h2><p>Dear {name},</p><p>I received your message and will get back to you soon.</p>"
            send_email(email, "Thank you for contacting Furqan Raza", auto_reply)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    return jsonify(load_messages()), 200

@app.route('/api/messages/<int:msg_id>', methods=['DELETE'])
@login_required
def delete_message(msg_id):
    messages = load_messages()
    messages = [m for m in messages if m['id'] != msg_id]
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    return jsonify({'success': True}), 200

@app.route('/api/messages/<int:msg_id>/read', methods=['PUT'])
@login_required
def mark_as_read(msg_id):
    messages = load_messages()
    for m in messages:
        if m['id'] == msg_id:
            m['status'] = 'read'
            break
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    return jsonify({'success': True}), 200

@app.route('/api/admin/login', methods=['POST'])
def admin_login_api():
    data = request.json
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True}), 200
    return jsonify({'success': False}), 401

@app.route('/api/admin/check', methods=['GET'])
def check_admin():
    return jsonify({'logged_in': session.get('logged_in', False)}), 200

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout_api():
    session.pop('logged_in', None)
    return jsonify({'success': True}), 200

# ==================== RENDER PAGES ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
@login_required
def admin_panel():
    return render_template('admin.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 SERVER STARTED")
    print("📍 http://localhost:5000")
    print("🔐 http://localhost:5000/login (admin/furqan123)")
    print("=" * 60)
    app.run(debug=True, port=5000)
