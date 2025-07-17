import sqlite3
import os
from datetime import datetime, timedelta


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
            created_date TEXT NOT NULL  -- Add date tracking
        )
    ''')
    conn.commit()
    conn.close()

def delete_expired_offers():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Get current datetime
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    current_date = now.strftime('%Y-%m-%d')
    
    # Query for potentially expired offers
    c.execute("SELECT id, image_path, start_time, end_time, created_date FROM offers")
    all_offers = c.fetchall()
    
    expired_offers = []
    
    for offer_id, image_path, start_time, end_time, created_date in all_offers:
        # Parse the created date
        try:
            offer_date = datetime.strptime(created_date, '%Y-%m-%d')
        except ValueError:
            # If no date stored, assume it's from today
            offer_date = now.date()
            created_date = current_date
        
        # Check if offer has expired
        if is_offer_expired(start_time, end_time, offer_date, now):
            expired_offers.append((offer_id, image_path))
    
    # Delete expired offers
    for offer_id, image_path in expired_offers:
        # Delete file from disk if it exists
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"Deleted image: {image_path}")
            except OSError as e:
                print(f"Error deleting image {image_path}: {e}")
        else:
            print(f"Image not found: {image_path}")

        # Delete record from database
        c.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
        print(f"Deleted DB entry ID: {offer_id}")

    conn.commit()
    conn.close()
    
    return len(expired_offers)

def is_offer_expired(start_time, end_time, offer_date, current_datetime):
    """
    Check if an offer has expired, handling cases where offers span midnight
    """
    try:
        # Parse times
        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))
        
        # Create datetime objects for start and end times
        start_dt = datetime.combine(offer_date, datetime.min.time().replace(hour=start_hour, minute=start_min))
        end_dt = datetime.combine(offer_date, datetime.min.time().replace(hour=end_hour, minute=end_min))
        
        # If end time is before start time, the offer spans midnight
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        
        # Check if current time is past the end time
        return current_datetime > end_dt
        
    except (ValueError, TypeError) as e:
        print(f"Error parsing time values: {e}")
        return False

def add_offer(shop_name, image_path, start_time, end_time):
    """
    Helper function to add an offer with proper date tracking
    """
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    c.execute('''
        INSERT INTO offers (shop_name, image_path, start_time, end_time, created_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (shop_name, image_path, start_time, end_time, current_date))
    
    conn.commit()
    conn.close()

def get_active_offers():
    """
    Get all currently active offers
    """
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("SELECT id, shop_name, image_path, start_time, end_time, created_date FROM offers")
    all_offers = c.fetchall()
    
    active_offers = []
    now = datetime.now()
    
    for offer in all_offers:
        offer_id, shop_name, image_path, start_time, end_time, created_date = offer
        
        try:
            offer_date = datetime.strptime(created_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            offer_date = now.date()
        
        if not is_offer_expired(start_time, end_time, offer_date, now):
            active_offers.append({
                'id': offer_id,
                'shop_name': shop_name,
                'image_path': image_path,
                'start_time': start_time,
                'end_time': end_time,
                'created_date': created_date
            })
    
    conn.close()
    return active_offers

# Migration function to add created_date to existing records
def migrate_existing_offers():
    """
    Add created_date column to existing offers if it doesn't exist
    """
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Check if created_date column exists
    c.execute("PRAGMA table_info(offers)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'created_date' not in columns:
        c.execute("ALTER TABLE offers ADD COLUMN created_date TEXT")
        
        # Set current date for existing records
        current_date = datetime.now().strftime('%Y-%m-%d')
        c.execute("UPDATE offers SET created_date = ? WHERE created_date IS NULL", (current_date,))
        
        conn.commit()
        print("Added created_date column to existing offers")
    
    conn.close()

# Initialize database with migrations
def setup_database():
    init_db()
    migrate_existing_offers()