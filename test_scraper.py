"""
Debug script to test the scraper and see what's happening.
"""

import scraper
import json

# Test with headless=False to see what's happening
print("Testing scraper with 'Facebook'...")
result = scraper.scrape_app_data("Facebook", headless=False)

print("\n" + "="*50)
print("RESULT:")
print("="*50)
print(json.dumps(result, indent=2))
print("="*50)

if result.get('app_name'):
    print("\n✅ SUCCESS: Found app name!")
else:
    print("\n❌ FAILED: No app name found")
    print(f"Error: {result.get('error', 'No error message')}")


