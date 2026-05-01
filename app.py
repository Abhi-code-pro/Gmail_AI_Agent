from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from agent_logic import sync_emails_to_db
import threading
import time

app = Flask(__name__)

# 1. Database Configuration (SQLite)
# This creates a 'database.db' file in your project folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. Database Model (Table structure)
class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gmail_id = db.Column(db.String(100), unique=True)
    subject = db.Column(db.String(200))
    sender = db.Column(db.String(200))
    snippet = db.Column(db.Text)
    category = db.Column(db.String(50)) # URGENT, LEGAL, NORMAL
    is_unread = db.Column(db.Boolean)

# 3. Background Thread Logic
def background_monitor():
    """This runs 24/7 in the background to handle AI processing and WhatsApp alerts."""
    with app.app_context():
        while True:
            try:
                print("\n[Background Agent] Syncing with Gmail and AI...")
                sync_emails_to_db(db, Email)
                print("[Background Agent] Sync Complete. Sleeping for 5 mins.")
            except Exception as e:
                print(f"[Background Agent] Error: {e}")
            
            time.sleep(300) # Wait 5 minutes before next check

# 4. Web Routes
@app.route('/')
def index():
    """Main Dashboard: Displays all emails from the database."""
    # Fetch all emails, newest first
    emails = Email.query.order_by(Email.id.desc()).all()
    
    # Calculate counts for the sidebar badges
    urgent_count = Email.query.filter_by(category='URGENT', is_unread=True).count()
    legal_count = Email.query.filter_by(category='LEGAL', is_unread=True).count()
    
    return render_template('index.html', 
                           emails=emails, 
                           urgent_count=urgent_count, 
                           legal_count=legal_count)

@app.route('/category/<cat_name>')
def show_category(cat_name):
    """Filter route: Displays specific categories and maintains sidebar counts."""
    # 1. Fetch filtered emails
    emails = Email.query.filter_by(category=cat_name.upper()).order_by(Email.id.desc()).all()
    
    # 2. Fetch counts so the sidebar badges don't cause an UndefinedError
    urgent_count = Email.query.filter_by(category='URGENT', is_unread=True).count()
    legal_count = Email.query.filter_by(category='LEGAL', is_unread=True).count()
    
    # 3. Pass everything to the template
    return render_template('index.html', 
                           emails=emails, 
                           current_filter=cat_name.upper(),
                           urgent_count=urgent_count,
                           legal_count=legal_count)

# 5. Application Launch
if __name__ == '__main__':
    with app.app_context():
        # This creates the database file and tables if they don't exist
        db.create_all() 
        print("Database initialized successfully.")
        
    # Start the background monitor in a separate thread
    monitor_thread = threading.Thread(target=background_monitor, daemon=True)
    monitor_thread.start()
    
    # Run the Flask Web Server
    # Access it at http://127.0.0.1:5000
    app.run(debug=True, use_reloader=False)