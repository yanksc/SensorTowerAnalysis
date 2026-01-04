#!/usr/bin/env python3
"""
Script to update database records where "< 5k" values were incorrectly converted to 5000.
Updates them to 0 instead.
"""

import database
from database import get_history, convert_text_to_number
import sqlite3
import pandas as pd

def update_less_than_5k_values():
    """Update records where < 5k values should be 0."""
    print("=" * 80)
    print("Updating '< 5k' Values to 0")
    print("=" * 80)
    
    # Initialize database
    database.init_db()
    
    # Get all records
    df = get_history()
    
    if len(df) == 0:
        print("No records to update.")
        return
    
    print(f"\nFound {len(df)} records to check")
    print("-" * 80)
    
    conn = sqlite3.connect(database.DB_NAME)
    cursor = conn.cursor()
    
    updated_count = 0
    
    for idx, row in df.iterrows():
        app_id = row.get('app_id', '')
        app_name = row.get('app_name', 'Unknown')
        
        updates_needed = {}
        
        # Check downloads_worldwide - if it's "< $5k" or "< 5k", numeric should be 0
        downloads_text = str(row.get('downloads_worldwide', '')).strip()
        downloads_numeric = row.get('downloads_numeric')
        
        # Check if text contains < 5k pattern
        if downloads_text and ('< 5' in downloads_text.lower() or '< $5' in downloads_text.lower()):
            if downloads_numeric == 5000 or downloads_numeric == 5000.0:
                updates_needed['downloads_numeric'] = 0
                print(f"  Downloads: '{downloads_text}' -> 0 (was {downloads_numeric})")
        
        # Also check if numeric is 5000 but text might indicate < 5k
        # Re-convert using the updated function to see if it should be 0
        if downloads_text and downloads_numeric == 5000:
            converted_value = convert_text_to_number(downloads_text)
            if converted_value == 0 and downloads_numeric != 0:
                updates_needed['downloads_numeric'] = 0
                print(f"  Downloads: '{downloads_text}' -> 0 (was {downloads_numeric}, re-converted)")
        
        # Check revenue_worldwide - if it's "< $5k" or "< 5k", numeric should be 0
        revenue_text = str(row.get('revenue_worldwide', '')).strip()
        revenue_numeric = row.get('revenue_numeric')
        
        if revenue_text and ('< 5' in revenue_text.lower() or '< $5' in revenue_text.lower()):
            if revenue_numeric == 5000:
                updates_needed['revenue_numeric'] = 0
                print(f"  Revenue: '{revenue_text}' -> 0 (was {revenue_numeric})")
        
        # Update if needed
        if updates_needed:
            try:
                update_fields = []
                update_values = []
                
                if 'downloads_numeric' in updates_needed:
                    update_fields.append('downloads_numeric = ?')
                    update_values.append(updates_needed['downloads_numeric'])
                
                if 'revenue_numeric' in updates_needed:
                    update_fields.append('revenue_numeric = ?')
                    update_values.append(updates_needed['revenue_numeric'])
                
                update_values.append(app_id)
                
                cursor.execute(f"""
                    UPDATE apps SET {', '.join(update_fields)}
                    WHERE app_id = ?
                """, update_values)
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    print(f"[{updated_count}] ✅ {app_name[:40]:40} | App ID: {app_id}")
            except Exception as e:
                print(f"❌ Error updating {app_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"✅ Successfully updated {updated_count} records")
    print("=" * 80)

if __name__ == "__main__":
    update_less_than_5k_values()

