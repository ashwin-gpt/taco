from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, os
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # required for session

SHOP_DATA_DIR = 'shop_data'

if not os.path.exists(SHOP_DATA_DIR):
    os.makedirs(SHOP_DATA_DIR)

# ------------------------------
# Utility Functions
# ------------------------------

def init_offer_table():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            start_time TEXT NOT NULL,   -- format: HH:MM
            end_time TEXT NOT NULL      -- format: HH:MM
        )
    ''')
    conn.commit()
    conn.close()

# Call once on app startup
init_offer_table()

def load_links(shop_name):
    path = os.path.join(SHOP_DATA_DIR, f"{shop_name}.json")
    
    # Default data template for any new shop
    default_data = {
        "facebook": "",
        "instagram": "",
        "whatsapp": "",
        "display_name": shop_name.capitalize(),
        "header_text": "Welcome to our store!",
        "address": "Not provided yet",
        "map_url": "https://maps.google.com"
    }

    # Create file if it doesn't exist
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default_data, f, indent=2)
        return default_data  # Return immediately to avoid double-read

    # If exists, load and merge with defaults (in case of missing fields)
    with open(path, 'r') as f:
        existing_data = json.load(f)
    
    # Merge missing fields into the file (if you later add new keys)
    for key, value in default_data.items():
        if key not in existing_data:
            existing_data[key] = value
    
    # Save updated fields (optional, if you want to persist)
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
    now = datetime.now().strftime('%H:%M')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT image_path FROM offers WHERE shop_name = ? AND start_time <= ? AND end_time >= ? ORDER BY id DESC LIMIT 1",
              (shop_name, now, now))
    result = c.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        return 'static/default.jpg'  # fallback



# ------------------------------
# Routes
# ------------------------------

@app.route('/')
def landing():
    return render_template('landing.html')  # Login form

@app.route('/login', methods=['POST'])
def handle_login():
    shop_name = request.form.get('shop_name').lower()
    password = request.form.get('password')
    creds = load_credentials()

    # Auto-register logic
    if shop_name not in creds:
        creds[shop_name] = 'default123'
        save_credentials(creds)
        flash(f"Shop '{shop_name}' auto-registered. Default password: default123", "info")
        session[f"{shop_name}_logged_in"] = True
        return redirect(url_for('dashboard', shop_name=shop_name))

    # If shop exists, check password
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
    if request.method == 'POST':
        # Load existing data first
        existing_data = load_links(shop_name)
        
        # Update with form data
        existing_data.update({
            "facebook": request.form.get('facebook'),
            "instagram": request.form.get('instagram'),
            "whatsapp": request.form.get('whatsapp'),
            "display_name": request.form.get('display_name'),
            "header_text": request.form.get('header_text'),
            "address": request.form.get('address'),
            "map_url": request.form.get('map_url')
        })
        
        save_links(shop_name, existing_data)
        flash("Links updated successfully", "success")
        return redirect(url_for('dashboard', shop_name=shop_name))  # ← redirect to dashboard

    links = load_links(shop_name)
    return render_template('admin.html', links=links, shop=shop_name)


@app.route('/<shop_name>/update_offer', methods=['GET', 'POST'])
def update_offer(shop_name):
    shop_name = shop_name.lower()
    if not session.get(f"{shop_name}_logged_in"):
        return redirect(url_for('landing'))


    if request.method == 'POST':
        file = request.files['offer_image']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        if file:
            filename = f"{shop_name}_{file.filename}"
            filepath = os.path.join('static/uploads', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)



            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT INTO offers (shop_name, image_path, start_time, end_time) VALUES (?, ?, ?, ?)",
                      (shop_name, filepath, start_time, end_time))
            conn.commit()
            conn.close()

            flash("Offer updated successfully!", "success")
            return redirect(url_for('dashboard', shop_name=shop_name))

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

@app.route('/current_banner')
def current_banner():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT image_path FROM offers ORDER BY id DESC LIMIT 1')
    result = c.fetchone()
    conn.close()
    if result:
        image_path = result[0]
        banner_url = url_for('static', filename='uploads/' + image_path)
        return jsonify({'banner_image': banner_url})
    else:
        return jsonify({'banner_image': ''})



if __name__ == '__main__':
    app.run(debug=True)
