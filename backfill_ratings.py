#!/usr/bin/env python3
"""
Script to backfill missing rating data from Apple App Store for all apps in the database.
"""

import database
from database import get_history, save_result
import scraper
import pandas as pd
import time
from typing import Dict

def backfill_ratings():
    """Backfill rating data for all apps missing ratings."""
    print("=" * 80)
    print("Backfilling Rating Data from Apple App Store")
    print("=" * 80)
    
    # Initialize database
    database.init_db()
    
    # Get all records
    df = get_history()
    
    if len(df) == 0:
        print("No records found in database.")
        return
    
    print(f"\nFound {len(df)} total records")
    
    # Find records with missing ratings
    missing_ratings = df[
        (df['average_rating'].isna()) | 
        (df['average_rating'] == '') | 
        (df['rating_count'].isna()) | 
        (df['rating_count'] == '')
    ]
    
    print(f"Records with missing ratings: {len(missing_ratings)}")
    
    if len(missing_ratings) == 0:
        print("\n✅ All records already have rating data!")
        return
    
    print("\n" + "-" * 80)
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for idx, row in missing_ratings.iterrows():
        app_name = row['app_name']
        app_id = row.get('app_id', '')
        
        print(f"\n[{idx + 1}/{len(missing_ratings)}] {app_name}")
        print(f"  App ID: {app_id}")
        
        if not app_id or pd.isna(app_id) or app_id == '':
            print(f"  ⚠️ Skipping: No App ID")
            skipped_count += 1
            continue
        
        # Construct Apple App Store URL
        apple_url = f"https://apps.apple.com/us/app/id{app_id}"
        
        try:
            # Scrape Apple App Store data
            print(f"  Scraping: {apple_url}")
            apple_data = scraper.scrape_apple_app_store(apple_url, headless=True, timeout=30000)
            
            if apple_data.get('error'):
                print(f"  ❌ Error: {apple_data.get('error')}")
                error_count += 1
                continue
            
            # Get existing app data
            existing_data = {}
            for col in df.columns:
                existing_data[col] = row.get(col)
            
            # Update with rating data
            rating_added = False
            if apple_data.get('average_rating'):
                existing_data['average_rating'] = apple_data['average_rating']
                rating_added = True
            if apple_data.get('rating_count'):
                existing_data['rating_count'] = apple_data['rating_count']
                rating_added = True
            
            if rating_added:
                # Save updated data
                success = save_result(existing_data)
                
                if success:
                    rating_display = apple_data.get('average_rating', 'N/A')
                    count_display = apple_data.get('rating_count', 'N/A')
                    print(f"  ✅ Updated: {rating_display} ⭐ ({count_display} ratings)")
                    success_count += 1
                else:
                    print(f"  ❌ Failed to save rating data")
                    error_count += 1
            else:
                print(f"  ⚠️ No rating data found on Apple App Store")
                error_count += 1
            
            # Be nice to Apple's servers - add a small delay
            time.sleep(2)
            
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            error_count += 1
            time.sleep(1)
    
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  ✅ Successfully updated: {success_count}")
    print(f"  ⚠️ Skipped (no App ID): {skipped_count}")
    print(f"  ❌ Errors/Failed: {error_count}")
    print("=" * 80)

if __name__ == "__main__":
    backfill_ratings()


