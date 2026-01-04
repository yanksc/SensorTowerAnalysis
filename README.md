# SensorTower App Data Scraper

A web application built with Streamlit to systematically scrape and store app data from SensorTower. Search for apps by name or ID, view detailed information, and maintain a local database with export capabilities.

## Features

- 🔍 **Search by App Name or ID**: Search SensorTower for any iOS/Android app
- 📊 **Data Extraction**: Captures comprehensive app information including:
  - Basic info (name, ID, categories, price)
  - Developer information and links
  - Content rating and publisher country
  - Download and revenue metrics
  - In-app purchases
  - Top countries/regions
- 💾 **Local Database**: SQLite database stores all scraped data with timestamps
- 📥 **Export to Excel**: Export your entire history to Excel format
- 🔍 **Filtering & Search**: Filter and search through your scraped app history
- 📱 **Modern UI**: Clean, intuitive Streamlit interface

## Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd SensorTowerAnalysis
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

## Usage

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Search for apps**:
   - Navigate to the "Search & Scrape" tab
   - Enter an app name or SensorTower app ID
   - Click "Scrape" to fetch data
   - Review the results and click "Save to Database" to store

3. **View history**:
   - Go to the "History" tab
   - Filter by category, price, or search by name
   - View detailed information for any app
   - Export all data to Excel

## Project Structure

```
SensorTowerAnalysis/
├── app.py              # Main Streamlit application
├── scraper.py          # Web scraping logic using Playwright
├── database.py         # SQLite database management
├── requirements.txt    # Python dependencies
├── history.db          # SQLite database (created automatically)
└── README.md           # This file
```

## Data Fields Captured

- App Name & ID
- Categories
- Price (Free/Paid)
- Top Countries/Regions
- Advertised Status
- Support URL
- Developer Website & Name
- Content Rating
- Downloads (Worldwide, Last Month)
- Revenue (Worldwide, Last Month)
- Last Updated Date
- Publisher Country
- In-App Purchases (Title, Duration, Price)

## Notes

- The scraper uses Playwright for browser automation
- Data is stored locally in SQLite database (`history.db`)
- The application runs in headless mode by default (can be toggled in sidebar)
- Some data fields may not be available depending on SensorTower's public access restrictions

## Requirements

- Python 3.8+
- Chromium browser (installed via Playwright)

## License

This project is for personal/educational use. Please respect SensorTower's Terms of Service when using this tool.


