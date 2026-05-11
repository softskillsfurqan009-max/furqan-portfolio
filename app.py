import os
import json
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
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

# File to store messages (backup)
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
    """Send email using Gmail SMTP"""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("⚠️ Email not configured. Message saved locally only.")
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
        print(f"✅ Email sent to {to_email}")
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

@app.route('/api/contacts', methods=['POST'])
def save_contact():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        message = data.get('message')
        
        # Create message object for local storage
        message_obj = {
            'id': len(load_messages()) + 1,
            'name': name,
            'email': email,
            'message': message,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'unread'
        }
        
        # Save to local JSON file
        save_message(message_obj)
        
        print(f"\n📧 New Message Received!")
        print(f"   ID: {message_obj['id']}")
        print(f"   Name: {name}")
        print(f"   Email: {email}")
        print(f"   Message: {message[:100]}..." if len(message) > 100 else f"   Message: {message}")
        print(f"   Time: {message_obj['date']}")
        print("-" * 50)
        
        # Send email to admin
        if EMAIL_ADDRESS and EMAIL_PASSWORD:
            admin_email_body = f"""
            <!DOCTYPE html>
            <html>
            <head><style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ padding: 20px; background: #f5f5f5; }}
                .content {{ background: white; padding: 20px; border-radius: 10px; }}
                h2 {{ color: #3b82f6; }}
                .label {{ font-weight: bold; color: #333; }}
            </style></head>
            <body>
            <div class="container">
                <div class="content">
                    <h2>✨ New Contact Message from Portfolio</h2>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Message:</strong></p>
                    <p>{message}</p>
                    <hr>
                    <p><small>Sent from Furqan Raza Portfolio</small></p>
                </div>
            </div>
            </body>
            </html>
            """
            send_email(EMAIL_ADDRESS, f"📬 New Contact from {name}", admin_email_body)
            
            # Send auto-reply to user
            auto_reply_body = f"""
            <!DOCTYPE html>
            <html>
            <head><style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ padding: 20px; background: #f5f5f5; }}
                .content {{ background: white; padding: 20px; border-radius: 10px; }}
                h2 {{ color: #3b82f6; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
            </style></head>
            <body>
            <div class="container">
                <div class="content">
                    <h2>🙏 Thank You for Contacting Me!</h2>
                    <p>Dear <strong>{name}</strong>,</p>
                    <p>Thank you for reaching out to me. I have received your message and will get back to you within 24 hours.</p>
                    <p>Here's a copy of your message:</p>
                    <div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <em>"{message}"</em>
                    </div>
                    <p>Best regards,<br><strong>Furqan Raza</strong><br>Full-Stack Developer</p>
                    <hr>
                    <div class="footer">
                        <p>This is an automated response. Please do not reply to this email.</p>
                    </div>
                </div>
            </div>
            </body>
            </html>
            """
            send_email(email, "Thank you for contacting Furqan Raza", auto_reply_body)
        else:
            print("⚠️ Email not configured. Message saved locally only.")
        
        return jsonify({'success': True, 'message': 'Message sent successfully!'}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/messages', methods=['GET'])
@login_required
def get_messages():
    messages = load_messages()
    return jsonify(messages), 200

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
    try:
        data = request.json
        if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return jsonify({'success': True}), 200
        return jsonify({'success': False}), 401
    except:
        return jsonify({'success': False}), 500

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
    print("=" * 60)
    print("📍 Frontend: http://localhost:5000")
    print("🔐 Admin Login: http://localhost:5000/login")
    print("👤 Username: admin")
    print("🔑 Password: furqan123")
    print("=" * 60)
    if EMAIL_ADDRESS:
        print(f"📧 Email configured: {EMAIL_ADDRESS}")
        print("   ✅ Contact form will send emails")
    else:
        print("   ⚠️ Email not configured. Add EMAIL_ADDRESS and EMAIL_PASSWORD in .env file")
    print("📝 Messages will be stored in: messages.json")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
    # Vercel handler
app = app