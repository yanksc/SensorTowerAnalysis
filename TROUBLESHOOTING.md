# Troubleshooting Guide

## Issue: "No app data found" when searching

If you're getting "⚠️ No app data found" when searching for apps like "Facebook" or "Instagram", here are solutions:

### Solution 1: Use Direct URL (Recommended)

The most reliable way is to use the **Direct URL** option:

1. Go to SensorTower's website in your browser
2. Navigate to the app page you want to scrape (e.g., Facebook)
3. Copy the full URL from your browser's address bar
4. In the web app, select **"Direct URL"** mode
5. Paste the URL and click "Scrape"

Example URLs:
- `https://sensortower.com/ios/app/facebook/id284882215`
- `https://sensortower.com/apps/ios/app/instagram/id389801252`

### Solution 2: Check App Availability

Some apps may:
- Require login/authentication to view
- Not be available in SensorTower's public database
- Have restricted access (paid plans only)

### Solution 3: Try App ID Instead

If you know the SensorTower app ID (numeric), try searching with just the ID instead of the name.

### Solution 4: Verify SensorTower Access

- Make sure you can access the app page directly in your browser
- Check if SensorTower requires login for the data you're trying to access
- Some data fields may only be available with paid subscriptions

## Debugging Tips

1. **Run in non-headless mode**: Uncheck "Headless Browser Mode" in the sidebar to see what the browser is doing
2. **Check the error message**: The error message will provide clues about what went wrong
3. **Try the test script**: Run `python3 test_scraper_debug.py` to see detailed debugging output

## Common Issues

### "Login required or access denied"
- SensorTower may require authentication for this app/data
- Try logging into SensorTower in a regular browser first
- Some data may require a paid subscription

### "Could not navigate to app page"
- The URL structure may have changed
- Try using the Direct URL method instead
- Verify the app exists on SensorTower

### Partial data extracted
- Some fields may not be publicly available
- You can still save partial data to the database
- Try the Direct URL method for more complete data

## Getting Help

If issues persist:
1. Check SensorTower's website structure hasn't changed
2. Verify your internet connection
3. Try with a different app to see if it's app-specific
4. Check if SensorTower has updated their Terms of Service regarding scraping


