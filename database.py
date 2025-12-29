"""
Database module for managing SensorTower app data history.
Uses SQLite to store scraped app information.
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List


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
    
    # Migrate existing tables to add category_ranking column if it doesn't exist
    try:
        cursor.execute("PRAGMA table_info(apps)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'category_ranking' not in columns:
            cursor.execute("ALTER TABLE apps ADD COLUMN category_ranking TEXT")
            conn.commit()
            print("Added category_ranking column to existing database")
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
        
        # Debug: Print what we're trying to save
        print(f"Attempting to save: app_name={app_name}, app_id={app_id}")
        
        cursor.execute("""
            INSERT OR REPLACE INTO apps (
                app_name, app_id, categories, price, top_countries,
                advertised_status, support_url, developer_website,
                developer_name, content_rating, downloads_worldwide,
                revenue_worldwide, last_updated, publisher_country,
                category_ranking, in_app_purchases, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    
    Returns:
        DataFrame containing all app records
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM apps ORDER BY scraped_at DESC", conn)
        conn.close()
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

