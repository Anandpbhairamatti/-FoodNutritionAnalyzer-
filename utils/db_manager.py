import sqlite3
import json
import os
import datetime
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Tuple

DB_PATH = "nutrition_tracker.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str, salt: str) -> str:
    """Hash password using PBKDF2 with SHA-256."""
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()

def send_otp_email(recipient_email: str, otp: str) -> Tuple[bool, str]:
    """Send verification OTP code to the recipient's Gmail address using SMTP."""
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")
    if not sender_email or not sender_password:
        return False, "SMTP credentials not configured in .env. Please set SMTP_EMAIL and SMTP_PASSWORD."
        
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "Verification Code for Food Nutrition Analyzer"
        
        body = f"""Hello,

Thank you for signing up for the Food Nutrition Analyzer.
Your 6-digit verification code is:

{otp}

Please enter this code on the registration page to verify your account.

Regards,
Food Nutrition Analyzer Team
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP (TLS port 587)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True, "Verification email sent successfully."
    except Exception as e:
        return False, str(e)

def create_user(username: str, password: str, email: str) -> Tuple[bool, str, str]:
    """Create an unverified user in the database. Generates OTP and attempts to send it."""
    username = username.strip().lower()
    email = email.strip().lower()
    if not username or not password or not email:
        return False, "", "All fields are required."
        
    if not email.endswith("@gmail.com"):
        return False, "", "Registration must be with a valid Gmail address (@gmail.com)."
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if username exists and is verified
    cursor.execute("SELECT is_verified FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row is not None and row[0] == 1:
        conn.close()
        return False, "", "Username already exists."
        
    # Check if email exists and is verified
    cursor.execute("SELECT is_verified FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row is not None and row[0] == 1:
        conn.close()
        return False, "", "Gmail address is already registered."
        
    # Generate OTP
    otp = "".join(secrets.choice("0123456789") for _ in range(6))
    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)
    
    try:
        # Delete if unverified exists to avoid duplicate rows
        cursor.execute("DELETE FROM users WHERE username = ? OR email = ?", (username, email))
        cursor.execute(
            """INSERT INTO users (username, password_hash, salt, email, is_verified, verification_otp)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (username, password_hash, salt, email, otp)
        )
        conn.commit()
        
        # Send SMTP OTP email
        sent, msg = send_otp_email(email, otp)
        print(f"[TESTING] Verification OTP for '{username}': {otp} (SMTP Status: {msg})")
        
        # We also initialize profile target defaults (marked under 'Default' profile name)
        cursor.execute(
            """INSERT OR IGNORE INTO profile_targets (username, profile_name, target_calories, target_protein, target_fat, target_carbs)
               VALUES (?, 'Default', 2000.0, 130.0, 65.0, 220.0)""",
            (username,)
        )
        conn.commit()
        
        success = True
    except sqlite3.Error as e:
        success = False
        msg = f"Database error: {str(e)}"
    finally:
        conn.close()
        
    if success:
        return True, otp, msg
    else:
        return False, "", msg

def verify_user_otp(username: str, otp: str) -> Tuple[bool, str]:
    """Verify the 6-digit OTP code for a user and activate their account."""
    username = username.strip().lower()
    otp = otp.strip()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT verification_otp, is_verified FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        return False, "User not found."
        
    stored_otp, is_verified = row
    if is_verified == 1:
        conn.close()
        return True, "Account is already verified."
        
    if stored_otp == otp:
        try:
            cursor.execute("UPDATE users SET is_verified = 1, verification_otp = NULL WHERE username = ?", (username,))
            conn.commit()
            success = True
            msg = "Verification successful. You can now log in!"
        except sqlite3.Error as e:
            success = False
            msg = f"Database error: {str(e)}"
        finally:
            conn.close()
        return success, msg
    else:
        conn.close()
        return False, "Invalid verification code. Please try again."

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user against the stored password hash, ensuring they are verified."""
    username = username.strip().lower()
    if not username or not password:
        return False
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, is_verified FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return False
        
    stored_hash, salt, is_verified = row
    if is_verified != 1:
        return False
        
    computed_hash = hash_password(password, salt)
    return computed_hash == stored_hash

def seed_guest_user():
    """Seed a default guest/guest user for instant logging/demo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = 'guest'")
    if cursor.fetchone() is None:
        salt = secrets.token_hex(16)
        password_hash = hash_password("guest", salt)
        cursor.execute(
            """INSERT INTO users (username, password_hash, salt, email, is_verified, verification_otp) 
               VALUES ('guest', ?, ?, 'guest@gmail.com', 1, NULL)""",
            (password_hash, salt)
        )
        # Also seed Default profile targets for guest
        cursor.execute(
            """INSERT OR IGNORE INTO profile_targets (username, profile_name, target_calories, target_protein, target_fat, target_carbs)
               VALUES ('guest', 'Default', 2000.0, 130.0, 65.0, 220.0)"""
        )
        conn.commit()
    else:
        # Update existing guest user to be verified and have guest@gmail.com
        cursor.execute(
            "UPDATE users SET email = 'guest@gmail.com', is_verified = 1 WHERE username = 'guest'"
        )
        conn.commit()
    conn.close()

def init_db():
    """Initialize database tables if they do not exist, and migrate schema if needed."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create users table first
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            email TEXT,
            is_verified INTEGER DEFAULT 0,
            verification_otp TEXT
        )
    """)

    # Migrate users if it was created previously without email/is_verified columns
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [c[1] for c in cursor.fetchall()]
    if 'email' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if 'is_verified' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
    if 'verification_otp' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN verification_otp TEXT")

    # Check existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meals'")
    meals_exists = cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profile_targets'")
    targets_exists = cursor.fetchone() is not None

    # Determine if they have foreign keys defined
    has_fks_meals = False
    if meals_exists:
        cursor.execute("PRAGMA foreign_key_list(meals)")
        has_fks_meals = len(cursor.fetchall()) > 0

    has_fks_targets = False
    if targets_exists:
        cursor.execute("PRAGMA foreign_key_list(profile_targets)")
        has_fks_targets = len(cursor.fetchall()) > 0

    # Migrate/Create meals table
    if meals_exists and not has_fks_meals:
        cursor.execute("ALTER TABLE meals RENAME TO meals_old")
        cursor.execute("""
            CREATE TABLE meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                meal_name TEXT NOT NULL,
                calories REAL NOT NULL,
                protein_g REAL NOT NULL,
                fat_g REAL NOT NULL,
                carbs_g REAL NOT NULL,
                items_json TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
            )
        """)
        # Only copy rows where the username actually exists in users table (to avoid FK violation)
        cursor.execute("""
            INSERT INTO meals (id, timestamp, username, profile_name, meal_name, calories, protein_g, fat_g, carbs_g, items_json)
            SELECT id, timestamp, username, profile_name, meal_name, calories, protein_g, fat_g, carbs_g, items_json 
            FROM meals_old WHERE username IN (SELECT username FROM users)
        """)
        cursor.execute("DROP TABLE meals_old")
    elif not meals_exists:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                meal_name TEXT NOT NULL,
                calories REAL NOT NULL,
                protein_g REAL NOT NULL,
                fat_g REAL NOT NULL,
                carbs_g REAL NOT NULL,
                items_json TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
            )
        """)

    # Migrate/Create profile_targets table
    if targets_exists and not has_fks_targets:
        cursor.execute("ALTER TABLE profile_targets RENAME TO profile_targets_old")
        cursor.execute("""
            CREATE TABLE profile_targets (
                username TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                target_calories REAL NOT NULL,
                target_protein REAL NOT NULL,
                target_fat REAL NOT NULL,
                target_carbs REAL NOT NULL,
                PRIMARY KEY (username, profile_name),
                FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO profile_targets (username, profile_name, target_calories, target_protein, target_fat, target_carbs)
            SELECT username, profile_name, target_calories, target_protein, target_fat, target_carbs 
            FROM profile_targets_old WHERE username IN (SELECT username FROM users)
        """)
        cursor.execute("DROP TABLE profile_targets_old")
    elif not targets_exists:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile_targets (
                username TEXT NOT NULL,
                profile_name TEXT NOT NULL,
                target_calories REAL NOT NULL,
                target_protein REAL NOT NULL,
                target_fat REAL NOT NULL,
                target_carbs REAL NOT NULL,
                PRIMARY KEY (username, profile_name),
                FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
            )
        """)
        
    conn.commit()
    conn.close()
    
    # Seed default users
    seed_guest_user()

def get_profiles(username: str) -> List[str]:
    """Retrieve all unique profile names for a specific user. Includes 'Default' by default."""
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT profile_name FROM profile_targets WHERE username = ?", (username,))
    rows = cursor.fetchall()
    conn.close()
    
    profiles = [r[0] for r in rows]
    if "Default" not in profiles:
        profiles.insert(0, "Default")
    return profiles

def get_targets(username: str, profile_name: str) -> Dict[str, float]:
    """Get daily targets for a profile of a specific user. Creates default targets if profile doesn't exist."""
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT target_calories, target_protein, target_fat, target_carbs FROM profile_targets WHERE username = ? AND profile_name = ?", 
        (username, profile_name)
    )
    row = cursor.fetchone()
    
    if row is None:
        # Default targets
        defaults = {
            "calories": 2000.0,
            "protein": 130.0,
            "fat": 65.0,
            "carbs": 220.0
        }
        cursor.execute(
            """INSERT OR IGNORE INTO profile_targets (username, profile_name, target_calories, target_protein, target_fat, target_carbs)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, profile_name, defaults["calories"], defaults["protein"], defaults["fat"], defaults["carbs"])
        )
        conn.commit()
        conn.close()
        return defaults
        
    conn.close()
    return {
        "calories": row[0],
        "protein": row[1],
        "fat": row[2],
        "carbs": row[3]
    }

def save_targets(username: str, profile_name: str, calories: float, protein: float, fat: float, carbs: float):
    """Insert or update daily goals for a specific profile and user."""
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO profile_targets (username, profile_name, target_calories, target_protein, target_fat, target_carbs)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(username, profile_name) DO UPDATE SET
             target_calories = excluded.target_calories,
             target_protein = excluded.target_protein,
             target_fat = excluded.target_fat,
             target_carbs = excluded.target_carbs""",
        (username, profile_name, calories, protein, fat, carbs)
    )
    conn.commit()
    conn.close()

def log_meal(username: str, profile_name: str, meal_name: str, calories: float, protein: float, fat: float, carbs: float, items: List[Dict]):
    """Insert a logged meal into the database associated with a specific user."""
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items_json = json.dumps(items)
    
    cursor.execute(
        """INSERT INTO meals (timestamp, username, profile_name, meal_name, calories, protein_g, fat_g, carbs_g, items_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (now_str, username, profile_name, meal_name, calories, protein, fat, carbs, items_json)
    )
    conn.commit()
    conn.close()

def get_today_totals(username: str, profile_name: str) -> Dict[str, float]:
    """Calculate the total nutritional intake for today for a given profile of a specific user."""
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    today_end = datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        """SELECT SUM(calories), SUM(protein_g), SUM(fat_g), SUM(carbs_g)
           FROM meals 
           WHERE username = ? AND profile_name = ? AND timestamp BETWEEN ? AND ?""",
        (username, profile_name, today_start, today_end)
    )
    row = cursor.fetchone()
    conn.close()
    
    return {
        "calories": float(row[0] or 0.0),
        "protein": float(row[1] or 0.0),
        "fat": float(row[2] or 0.0),
        "carbs": float(row[3] or 0.0)
    }

def get_meal_history(username: str, profile_name: str, limit: int = 50) -> List[Dict]:
    """Retrieve historical meals logged for a profile of a specific user."""
    username = username.strip().lower()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, timestamp, meal_name, calories, protein_g, fat_g, carbs_g, items_json
           FROM meals 
           WHERE username = ? AND profile_name = ? 
           ORDER BY timestamp DESC 
           LIMIT ?""",
        (username, profile_name, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "meal_name": r["meal_name"],
            "calories": r["calories"],
            "protein": r["protein_g"],
            "fat": r["fat_g"],
            "carbs": r["carbs_g"],
            "items": json.loads(r["items_json"])
        })
    return history

def delete_meal(username: str, meal_id: int):
    """Delete a logged meal by its ID, ensuring it belongs to the authenticated user."""
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meals WHERE id = ? AND username = ?", (meal_id, username))
    conn.commit()
    conn.close()

# Initialize tables when imported
init_db()
