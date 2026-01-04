"""
Database module for managing SensorTower app data history.
Uses SQLite to store scraped app information.
"""

import sqlite3
import json
import re
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List


def convert_text_to_number(text_value):
    """
    Convert text values like '8.2K', '134K', '13M', '200k', '< $5k' to plain numbers.
    
    Examples:
    - '8.2K' -> 8200
    - '134K' -> 134000
    - '13M' -> 13000000
    - '200k' -> 200000
    - '< $5k' -> 0 (less than 5000, so treat as 0)
    - '< 5k' -> 0 (less than 5000, so treat as 0)
    - '40K' -> 40000
    """
    if pd.isna(text_value) or text_value == '' or text_value is None:
        return None
    
    # Convert to string and strip whitespace
    text = str(text_value).strip()
    
    # Handle empty strings
    if not text or text.lower() in ['n/a', 'none', '']:
        return None
    
    # Check for "< 5k" or "< $5k" patterns - these mean less than 5000, so return 0
    if re.match(r'^[<]\s*\$?\s*5\s*[kK]', text, re.IGNORECASE):
        return 0
    
    # Check for "< 5k" in downloads/revenue context
    if re.match(r'^[<]\s*\$?\s*5', text, re.IGNORECASE):
        return 0
    
    # Remove common prefixes like '< $', '$', etc. (but we already handled < 5k above)
    text = re.sub(r'^[<>=]?\s*\$?\s*', '', text, flags=re.IGNORECASE)
    
    # Extract number and unit
    # Match patterns like: "8.2K", "134K", "13M", "200k", "5k", etc.
    match = re.match(r'([\d.]+)\s*([KMBkmb]?)', text, re.IGNORECASE)
    
    if not match:
        # Try to extract just a number if no unit
        try:
            return float(text.replace(',', ''))
        except:
            return None
    
    number_str = match.group(1)
    unit = match.group(2).upper() if match.group(2) else ''
    
    try:
        number = float(number_str)
        
        # Multiply based on unit
        if unit == 'K':
            return int(number * 1000)
        elif unit == 'M':
            return int(number * 1000000)
        elif unit == 'B':
            return int(number * 1000000000)
        else:
            # No unit, return as-is
            return int(number) if number.is_integer() else number
    except:
        return None


DB_NAME = "history.db"


def init_db():
    """Initialize the database and create the apps table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            app_id TEXT,
            categories TEXT,
            price TEXT,
            top_countries TEXT,
            advertised_status TEXT,
            support_url TEXT,
            developer_website TEXT,
            developer_name TEXT,
            content_rating TEXT,
            downloads_worldwide TEXT,
            revenue_worldwide TEXT,
            last_updated TEXT,
            publisher_country TEXT,
            category_ranking TEXT,
            in_app_purchases TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(app_id, app_name)
        )
    """)
    
    # Migrate existing tables to add new columns if they don't exist
    try:
        cursor.execute("PRAGMA table_info(apps)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'category_ranking' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN category_ranking TEXT")
            conn.commit()
            print("Added category_ranking column to existing database")
        
        if 'average_rating' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN average_rating TEXT")
            conn.commit()
            print("Added average_rating column to existing database")
        
        if 'rating_count' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN rating_count TEXT")
            conn.commit()
            print("Added rating_count column to existing database")
        
        # Add numeric columns for sorting and calculations
        if 'rating_count_numeric' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN rating_count_numeric INTEGER")
            conn.commit()
            print("Added rating_count_numeric column to existing database")
        
        if 'average_rating_numeric' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN average_rating_numeric REAL")
            conn.commit()
            print("Added average_rating_numeric column to existing database")
        
        if 'downloads_numeric' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN downloads_numeric INTEGER")
            conn.commit()
            print("Added downloads_numeric column to existing database")
        
        if 'revenue_numeric' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN revenue_numeric INTEGER")
            conn.commit()
            print("Added revenue_numeric column to existing database")
        
        if 'release_date' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN release_date TEXT")
            conn.commit()
            print("Added release_date column to existing database")
            
    except Exception as e:
        print(f"Migration check error (may be OK if table is new): {e}")
    
    conn.commit()
    conn.close()


def save_result(data: Dict) -> bool:
    """
    Save or update app data in the database.
    
    Args:
        data: Dictionary containing app information
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure database is initialized
        init_db()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Convert in-app purchases list to JSON string if present
        iap_json = None
        if 'in_app_purchases' in data and data['in_app_purchases']:
            if isinstance(data['in_app_purchases'], list):
                iap_json = json.dumps(data['in_app_purchases'])
            else:
                iap_json = str(data['in_app_purchases'])
        
        # Prepare data for insertion
        app_name = data.get('app_name', 'Unknown')
        app_id = data.get('app_id', '')
        
        # Convert text values to numbers for sorting/calculations
        rating_count_numeric = convert_text_to_number(data.get('rating_count', ''))
        downloads_numeric = convert_text_to_number(data.get('downloads_worldwide', ''))
        revenue_numeric = convert_text_to_number(data.get('revenue_worldwide', ''))
        
        # Special handling: SensorTower uses "5k" to mean "< 5k" for downloads
        # If downloads text is exactly "5k" (without "<"), treat it as 0
        downloads_text = str(data.get('downloads_worldwide', '')).strip().lower()
        if downloads_text == '5k' and downloads_numeric == 5000:
            downloads_numeric = 0
        
        # Convert average_rating to numeric (remove star emoji if present)
        avg_rating_text = data.get('average_rating', '')
        average_rating_numeric = None
        if avg_rating_text:
            try:
                # Remove non-numeric characters except decimal point
                avg_rating_clean = re.sub(r'[^\d.]', '', str(avg_rating_text))
                if avg_rating_clean:
                    average_rating_numeric = float(avg_rating_clean)
            except:
                pass
        
        # Debug: Print what we're trying to save
        print(f"Attempting to save: app_name={app_name}, app_id={app_id}")
        
        cursor.execute("""
            INSERT OR REPLACE INTO apps (
                app_name, app_id, categories, price, top_countries,
                advertised_status, support_url, developer_website,
                developer_name, content_rating, downloads_worldwide,
                revenue_worldwide, last_updated, publisher_country,
                category_ranking, in_app_purchases, average_rating,
                rating_count, rating_count_numeric, average_rating_numeric,
                downloads_numeric, revenue_numeric, release_date, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_name,
            app_id,
            data.get('categories', ''),
            data.get('price', ''),
            data.get('top_countries', ''),
            data.get('advertised_status', ''),
            data.get('support_url', ''),
            data.get('developer_website', ''),
            data.get('developer_name', ''),
            data.get('content_rating', ''),
            data.get('downloads_worldwide', ''),
            data.get('revenue_worldwide', ''),
            data.get('last_updated', ''),
            data.get('publisher_country', ''),
            data.get('category_ranking', ''),
            iap_json,
            data.get('average_rating', ''),
            data.get('rating_count', ''),
            rating_count_numeric,
            average_rating_numeric,
            downloads_numeric,
            revenue_numeric,
            data.get('release_date', ''),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        rows_affected = cursor.rowcount
        
        # Verify the save by querying
        cursor.execute("SELECT COUNT(*) FROM apps WHERE app_id = ? OR app_name = ?", (app_id, app_name))
        verify_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"Save completed. Rows affected: {rows_affected}, Verified count: {verify_count}")
        
        # Return True only if we can verify the record exists
        return verify_count > 0
    except Exception as e:
        import traceback
        error_msg = f"Error saving to database: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return False


def get_history() -> pd.DataFrame:
    """
    Retrieve all app records from the database as a pandas DataFrame.
    Converts numeric columns to proper numeric types for sorting.
    
    Returns:
        DataFrame containing all app records with numeric columns properly typed
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM apps ORDER BY scraped_at DESC", conn)
        conn.close()
        
        # Convert numeric columns to proper numeric types for sorting
        numeric_columns = ['rating_count_numeric', 'average_rating_numeric', 
                          'downloads_numeric', 'revenue_numeric']
        
        for col in numeric_columns:
            if col in df.columns:
                # Convert to numeric, coercing errors to NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error retrieving history: {e}")
        return pd.DataFrame()


def get_app_by_id(app_id: str) -> Optional[Dict]:
    """
    Retrieve a specific app by its ID.
    
    Args:
        app_id: The app ID to search for
        
    Returns:
        Dictionary with app data or None if not found
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM apps WHERE app_id = ?", (app_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None
    except Exception as e:
        print(f"Error retrieving app: {e}")
        return None


def delete_app(app_id: str) -> bool:
    """
    Delete an app record from the database.
    
    Args:
        app_id: The app ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apps WHERE app_id = ?", (app_id,))
        rows_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Deleted app with ID {app_id}. Rows affected: {rows_deleted}")
        return rows_deleted > 0
    except Exception as e:
        print(f"Error deleting app: {e}")
        return False


def delete_app_by_name(app_name: str) -> bool:
    """
    Delete an app record by app name.
    
    Args:
        app_name: The app name to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apps WHERE app_name = ?", (app_name,))
        rows_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Deleted app '{app_name}'. Rows affected: {rows_deleted}")
        return rows_deleted > 0
    except Exception as e:
        print(f"Error deleting app by name: {e}")
        return False


def delete_apps_by_ids(app_ids: List[str]) -> int:
    """
    Delete multiple app records by their IDs.
    
    Args:
        app_ids: List of app IDs to delete
        
    Returns:
        Number of apps successfully deleted
    """
    if not app_ids:
        return 0
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(app_ids))
        cursor.execute(f"DELETE FROM apps WHERE app_id IN ({placeholders})", app_ids)
        rows_deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Bulk deleted {rows_deleted} apps")
        return rows_deleted
    except Exception as e:
        print(f"Error bulk deleting apps: {e}")
        return 0

