from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json, os
from datetime import datetime
import sqlite3
from werkzeug.utils import secure_filename
import sys


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# --- Config ---
SHOP_DATA_DIR = 'shop_data'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(SHOP_DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DB Setup ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_date TEXT NOT NULL DEFAULT (date('now'))
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_links(shop_name):
    path = os.path.join(SHOP_DATA_DIR, f"{shop_name}.json")
    default_data = {
        "facebook": "",
        "instagram": "",
        "whatsapp": "",
        "display_name": shop_name.capitalize(),
        "header_text": "Welcome to our store!",
        "address": "Not provided yet",
        "map_url": "https://maps.google.com"
    }

    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default_data, f, indent=2)
        return default_data

    with open(path, 'r') as f:
        existing_data = json.load(f)

    for key, value in default_data.items():
        if key not in existing_data:
            existing_data[key] = value

    with open(path, 'w') as f:
        json.dump(existing_data, f, indent=2)

    return existing_data

def save_links(shop_name, data):
    path = os.path.join(SHOP_DATA_DIR, f"{shop_name}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_credentials():
    path = 'shop_credentials.json'
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump({}, f)
    with open(path, 'r') as f:
        return json.load(f)

def save_credentials(credentials):
    with open('shop_credentials.json', 'w') as f:
        json.dump(credentials, f, indent=2)

def get_time_banner(shop_name):
    from datetime import datetime
    import sqlite3

    now = datetime.now().strftime('%H:%M')
    today = datetime.now().strftime('%Y-%m-%d')

    print(f"[DEBUG] Checking banner for shop: {shop_name} at {now} on {today}")

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('''
            SELECT image_path, start_time, end_time, created_date
            FROM offers
            WHERE shop_name = ?
            ORDER BY id DESC
        ''', (shop_name,))
        
        results = c.fetchall()
        conn.close()

        for row in results:
            image_path, start_time, end_time, created_date = row
            print(f"[DEBUG] Found in DB: path={image_path}, start={start_time}, end={end_time}, date={created_date}")

            if created_date == today and start_time <= now <= end_time:
                print("[DEBUG] Banner MATCHED. Returning:", image_path)
                return '/' + image_path  # Include slash so it loads correctly in browser

        print("[DEBUG] No banner matched. Returning default.")
        return '/static/images/default.jpg'

    except Exception as e:
        print(f"[ERROR] get_time_banner failed: {e}")
        return '/static/images/default.jpg'


# --- Routes ---
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['POST'])
def handle_login():
    shop_name = request.form.get('shop_name').lower()
    password = request.form.get('password')
    creds = load_credentials()

    if shop_name not in creds:
        creds[shop_name] = 'default123'
        save_credentials(creds)
        flash(f"Shop '{shop_name}' registered. Default password: default123", "info")
        session[f"{shop_name}_logged_in"] = True
        return redirect(url_for('dashboard', shop_name=shop_name))

    if creds.get(shop_name) == password:
        session[f"{shop_name}_logged_in"] = True
        return redirect(url_for('dashboard', shop_name=shop_name))
    else:
        flash("Incorrect shop name or password", "error")
        return redirect(url_for('landing'))

@app.route('/<shop_name>/dashboard')
def dashboard(shop_name):
    if not session.get(f"{shop_name}_logged_in"):
        return redirect(url_for('landing'))
    return render_template('dashboard.html', shop=shop_name)

@app.route('/<shop_name>/admin', methods=['GET', 'POST'])
def admin(shop_name):
    if not session.get(f"{shop_name}_logged_in"):
        return redirect(url_for('landing'))

    if request.method == 'POST':
        data = load_links(shop_name)
        data.update({
            "facebook": request.form.get('facebook'),
            "instagram": request.form.get('instagram'),
            "whatsapp": request.form.get('whatsapp'),
            "display_name": request.form.get('display_name'),
            "header_text": request.form.get('header_text'),
            "address": request.form.get('address'),
            "map_url": request.form.get('map_url')
        })
        save_links(shop_name, data)
        flash("Links updated successfully", "success")
        return redirect(url_for('dashboard', shop_name=shop_name))

    links = load_links(shop_name)
    return render_template('admin.html', links=links, shop=shop_name)

@app.route('/<shop_name>/update_offer', methods=['GET', 'POST'])
def update_offer(shop_name):
    shop_name = shop_name.lower()
    if not session.get(f"{shop_name}_logged_in"):
        return redirect(url_for('landing'))

    if request.method == 'POST':
        file = request.files.get('offer_image')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if file and allowed_file(file.filename):
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = secure_filename(f"{shop_name}_{timestamp}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            print("Saving file to:", filepath)
            try:
                # Save file
                file.save(filepath)
                
                # Set proper permissions (important for AWS)
                os.chmod(filepath, 0o644)
                
                # Store relative path for database
                relative_path = f"static/uploads/{filename}"
                
                # Get current date
                current_date = datetime.now().strftime('%Y-%m-%d')
                
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute('''
                    INSERT INTO offers (shop_name, image_path, start_time, end_time, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (shop_name, relative_path, start_time, end_time, current_date))
                conn.commit()
                conn.close()

                flash("Offer updated successfully!", "success")
                return redirect(url_for('dashboard', shop_name=shop_name))
                
            except Exception as e:
                flash(f"Error uploading file: {str(e)}", "danger")
                return redirect(url_for('update_offer', shop_name=shop_name))
        else:
            flash("Invalid file or format. Please upload PNG, JPG, JPEG, or GIF files.", "danger")

    return render_template('update_offer.html', shop=shop_name)

@app.route('/<shop_name>')
def home(shop_name):
    links = load_links(shop_name)
    banner = get_time_banner(shop_name)
    return render_template('index.html', links=links, shop=shop_name, banner_image=banner)

@app.route('/<shop_name>/logout')
def logout(shop_name):
    session.pop(f"{shop_name}_logged_in", None)
    return redirect(url_for('landing'))

@app.route('/<shop_name>/current_banner')
def current_banner(shop_name):
    banner = get_time_banner(shop_name)
    return jsonify({'banner_image': banner})

# Add a route to serve uploaded files (important for AWS)
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Main ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)