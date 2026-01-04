"""
Enhanced debug script to test the scraper with detailed output.
"""

import scraper
import json

def test_scraper(search_term, headless=False):
    print(f"\n{'='*60}")
    print(f"Testing scraper with: '{search_term}'")
    print(f"Headless mode: {headless}")
    print(f"{'='*60}\n")
    
    result = scraper.scrape_app_data(search_term, headless=headless)
    
    print("\n" + "="*60)
    print("SCRAPER RESULT:")
    print("="*60)
    print(json.dumps(result, indent=2))
    print("="*60)
    
    # Analysis
    print("\n" + "="*60)
    print("ANALYSIS:")
    print("="*60)
    
    if result.get('error'):
        print(f"❌ ERROR: {result['error']}")
    elif result.get('app_name'):
        print(f"✅ SUCCESS: Found app '{result['app_name']}'")
        print(f"   App ID: {result.get('app_id', 'N/A')}")
        print(f"   Categories: {result.get('categories', 'N/A')}")
        print(f"   Price: {result.get('price', 'N/A')}")
        fields_found = sum(1 for k, v in result.items() if v and k != 'in_app_purchases')
        print(f"   Fields populated: {fields_found}/{len(result)}")
    else:
        print("⚠️  PARTIAL: No app name found, but no error reported")
        print("   This might indicate:")
        print("   - Page loaded but data extraction failed")
        print("   - Wrong page structure")
        print("   - Login/authentication required")
    
    print("="*60 + "\n")
    
    return result

if __name__ == "__main__":
    # Test with common apps
    test_cases = ["Facebook", "Instagram"]
    
    for app_name in test_cases:
        test_scraper(app_name, headless=False)
        input("Press Enter to continue to next test...")


