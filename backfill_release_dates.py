#!/usr/bin/env python3
"""
Script to backfill missing release date data from Apple App Store for all apps in the database.
"""

import database
from database import get_history, save_result
import scraper
import pandas as pd
import time

def backfill_release_dates():
    """Backfill release date data for all apps missing release dates."""
    print("=" * 80)
    print("Backfilling Release Date Data from Apple App Store")
    print("=" * 80)
    
    # Initialize database
    database.init_db()
    
    # Get all records
    df = get_history()
    
    if len(df) == 0:
        print("No records found in database.")
        return
    
    print(f"\nFound {len(df)} total records")
    
    # Find records with missing release dates
    missing_dates = df[
        (df['release_date'].isna()) | 
        (df['release_date'] == '')
    ]
    
    print(f"Records with missing release dates: {len(missing_dates)}")
    
    if len(missing_dates) == 0:
        print("\n✅ All records already have release date data!")
        return
    
    print("\n" + "-" * 80)
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for idx, row in missing_dates.iterrows():
        app_name = row['app_name']
        app_id = row.get('app_id', '')
        
        print(f"\n[{idx + 1}/{len(missing_dates)}] {app_name}")
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
            
            # Update with release date
            if apple_data.get('release_date'):
                existing_data['release_date'] = apple_data['release_date']
                
                # Save updated data
                success = save_result(existing_data)
                
                if success:
                    print(f"  ✅ Updated: Release Date = {apple_data.get('release_date', 'N/A')}")
                    success_count += 1
                else:
                    print(f"  ❌ Failed to save release date data")
                    error_count += 1
            else:
                print(f"  ⚠️ No release date found on Apple App Store")
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
    backfill_release_dates()


