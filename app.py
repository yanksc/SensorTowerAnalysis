"""
Streamlit web application for SensorTower app data scraping and management.
"""

import streamlit as st
import pandas as pd
import json
import time
import re
from datetime import datetime
import database
import scraper


# Page configuration
st.set_page_config(
    page_title="SensorTower App Scraper",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
database.init_db()


def format_iap_display(iap_json: str) -> str:
    """Format in-app purchases JSON for display."""
    if not iap_json:
        return "None"
    try:
        iap_list = json.loads(iap_json) if isinstance(iap_json, str) else iap_json
        if isinstance(iap_list, list) and len(iap_list) > 0:
            formatted = []
            for item in iap_list:
                title = item.get('title', 'N/A')
                duration = item.get('duration', 'N/A')
                price = item.get('price', 'N/A')
                formatted.append(f"{title} ({duration}): {price}")
            return "\n".join(formatted)
        return "None"
    except:
        return str(iap_json) if iap_json else "None"


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


def main():
    st.title("📱 SensorTower App Data Scraper")
    st.markdown("Search for apps by name or ID and save results to your local database.")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Database status - refresh on every render
        try:
            # Ensure database is initialized
            database.init_db()
            history_df = database.get_history()
            db_status = "✅ Connected"
            record_count = len(history_df)
        except Exception as e:
            db_status = f"❌ Error: {str(e)}"
            record_count = 0
            st.error(f"Database error: {str(e)}")
        
        st.metric("Database Status", db_status)
        st.metric("Total Records", record_count)
        
        # Refresh button to manually update record count
        if st.button("🔄 Refresh Database Status", use_container_width=True):
            st.rerun()
        
        st.divider()
        
        # Headless mode toggle
        headless_mode = st.checkbox("Headless Browser Mode", value=True, 
                                    help="Run browser in background (recommended)")
        
        st.divider()
        
        # Export functionality
        st.subheader("📥 Export Data")
        if st.button("Export to Excel", use_container_width=True):
            try:
                history_df = database.get_history()
                if len(history_df) > 0:
                    # Prepare DataFrame for export
                    export_df = history_df.copy()
                    
                    # Format IAP column for better readability
                    if 'in_app_purchases' in export_df.columns:
                        export_df['in_app_purchases'] = export_df['in_app_purchases'].apply(format_iap_display)
                    
                    # Ensure numeric columns exist (they should already be in the database)
                    # But convert them if they don't exist for some reason
                    if 'rating_count_numeric' not in export_df.columns and 'rating_count' in export_df.columns:
                        export_df['rating_count_numeric'] = export_df['rating_count'].apply(convert_text_to_number)
                    
                    if 'downloads_numeric' not in export_df.columns and 'downloads_worldwide' in export_df.columns:
                        export_df['downloads_numeric'] = export_df['downloads_worldwide'].apply(convert_text_to_number)
                        # Apply special handling for "5k" downloads
                        downloads_mask = export_df['downloads_worldwide'].str.strip().str.lower() == '5k'
                        export_df.loc[downloads_mask, 'downloads_numeric'] = 0
                    
                    if 'revenue_numeric' not in export_df.columns and 'revenue_worldwide' in export_df.columns:
                        export_df['revenue_numeric'] = export_df['revenue_worldwide'].apply(convert_text_to_number)
                    
                    if 'average_rating_numeric' not in export_df.columns and 'average_rating' in export_df.columns:
                        export_df['average_rating_numeric'] = export_df['average_rating'].apply(
                            lambda x: float(re.sub(r'[^\d.]', '', str(x))) if pd.notna(x) and str(x).strip() else None
                        )
                    
                    # Exclude text-based columns, keep only numeric versions
                    columns_to_exclude = [
                        'rating_count',           # Exclude text version
                        'average_rating',         # Exclude text version
                        'downloads_worldwide',    # Exclude text version
                        'revenue_worldwide'       # Exclude text version
                    ]
                    
                    # Select columns to keep (all columns except the text-based ones)
                    columns_to_keep = [col for col in export_df.columns if col not in columns_to_exclude]
                    export_df = export_df[columns_to_keep]
                    
                    # Rename numeric columns to cleaner names for Excel
                    column_renames = {
                        'rating_count_numeric': 'Rating Count',
                        'average_rating_numeric': 'Average Rating',
                        'downloads_numeric': 'Downloads',
                        'revenue_numeric': 'Revenue'
                    }
                    export_df = export_df.rename(columns=column_renames)
                    
                    # Calculate Revenue / Download (ARPU - Average Revenue Per User)
                    # Handle division by zero and missing values
                    if 'Revenue' in export_df.columns and 'Downloads' in export_df.columns:
                        export_df['Revenue / Download'] = export_df.apply(
                            lambda row: (
                                row['Revenue'] / row['Downloads'] 
                                if pd.notna(row['Revenue']) and pd.notna(row['Downloads']) and row['Downloads'] > 0
                                else None
                            ),
                            axis=1
                        )
                    
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"sensortower_data_{timestamp}.xlsx"
                    
                    # Export to Excel
                    export_df.to_excel(filename, index=False, engine='openpyxl')
                    st.success(f"✅ Exported {len(export_df)} records to {filename}")
                    st.info("💡 **Tip:** Only numeric columns are included for better Excel calculations and sorting!")
                    
                    # Provide download button
                    with open(filename, 'rb') as f:
                        st.download_button(
                            label="📥 Download Excel File",
                            data=f.read(),
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.warning("No data to export. Please scrape some apps first.")
            except Exception as e:
                st.error(f"Error exporting data: {e}")
    
    # Main content area
    tab1, tab2 = st.tabs(["📊 Database", "🔍 Search & Scrape"])
    
    with tab1:
        st.header("📊 Database")
        
        # Get history
        try:
            history_df = database.get_history()
            
            if len(history_df) > 0:
                # Display statistics
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Total Apps", len(history_df))
                with col2:
                    unique_categories = history_df['categories'].nunique() if 'categories' in history_df.columns else 0
                    st.metric("Unique Categories", unique_categories)
                with col3:
                    free_count = len(history_df[history_df['price'].str.contains('Free', case=False, na=False)]) if 'price' in history_df.columns else 0
                    st.metric("Free Apps", free_count)
                with col4:
                    paid_count = len(history_df[history_df['price'].str.contains('Paid', case=False, na=False)]) if 'price' in history_df.columns else 0
                    st.metric("Paid Apps", paid_count)
                with col5:
                    apps_with_ratings = history_df['average_rating'].notna().sum() if 'average_rating' in history_df.columns else 0
                    st.metric("Apps with Ratings", apps_with_ratings)
                
                st.divider()
                
                # Filters
                st.subheader("🔍 Filters")
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    category_filter = st.selectbox(
                        "Filter by Category",
                        options=["All"] + (history_df['categories'].unique().tolist() if 'categories' in history_df.columns else []),
                        key="category_filter"
                    )
                
                with filter_col2:
                    price_filter = st.selectbox(
                        "Filter by Price",
                        options=["All", "Free", "Paid"],
                        key="price_filter"
                    )
                
                with filter_col3:
                    search_filter = st.text_input(
                        "Search by Name",
                        placeholder="Type to filter...",
                        key="name_filter"
                    )
                
                # Apply filters
                filtered_df = history_df.copy()
                
                if category_filter != "All" and 'categories' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['categories'] == category_filter]
                
                if price_filter != "All" and 'price' in filtered_df.columns:
                    if price_filter == "Free":
                        filtered_df = filtered_df[filtered_df['price'].str.contains('Free', case=False, na=False)]
                    elif price_filter == "Paid":
                        filtered_df = filtered_df[filtered_df['price'].str.contains('Paid', case=False, na=False)]
                
                if search_filter and 'app_name' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['app_name'].str.contains(search_filter, case=False, na=False)]
                
                st.divider()
                
                # Display filtered table with delete options
                st.subheader(f"📋 Apps ({len(filtered_df)} results)")
                
                # Prepare display DataFrame
                display_df = filtered_df.copy()
                
                # Select columns to display (use numeric columns instead of text columns)
                display_columns = ['app_name', 'app_id', 'categories', 'category_ranking', 'price', 'developer_name', 
                                 'content_rating', 
                                 # Use numeric columns instead of text columns
                                 'average_rating_numeric',  # Instead of 'average_rating'
                                 'rating_count_numeric',     # Instead of 'rating_count'
                                 'downloads_numeric',        # Instead of 'downloads_worldwide'
                                 'revenue_numeric',          # Instead of 'revenue_worldwide'
                                 'release_date', 'publisher_country', 'last_updated', 'scraped_at']
                
                # Only show columns that exist in the DataFrame
                available_columns = [col for col in display_columns if col in display_df.columns]
                
                # Debug: Check if numeric columns exist
                missing_numeric = [col for col in ['average_rating_numeric', 'rating_count_numeric', 
                                                   'downloads_numeric', 'revenue_numeric'] 
                                  if col not in display_df.columns]
                if missing_numeric and len(filtered_df) > 0:
                    st.warning(f"⚠️ Some numeric columns are missing: {missing_numeric}. They may not be in the database yet.")
                
                # Select only the columns that exist
                display_df = display_df[available_columns]
                
                # Rename numeric columns for cleaner display (remove "_numeric" suffix)
                column_renames = {}
                if 'average_rating_numeric' in display_df.columns:
                    column_renames['average_rating_numeric'] = 'Rating'
                if 'rating_count_numeric' in display_df.columns:
                    column_renames['rating_count_numeric'] = 'Rating Count'
                if 'downloads_numeric' in display_df.columns:
                    column_renames['downloads_numeric'] = 'Downloads'
                if 'revenue_numeric' in display_df.columns:
                    column_renames['revenue_numeric'] = 'Revenue'
                
                # Only rename if we have columns to rename
                if column_renames:
                    try:
                        display_df = display_df.rename(columns=column_renames)
                        # Update available_columns list to reflect renamed columns
                        for old_name, new_name in column_renames.items():
                            if old_name in available_columns:
                                idx = available_columns.index(old_name)
                                available_columns[idx] = new_name
                    except Exception as e:
                        # If rename fails, just continue without renaming
                        st.warning(f"Could not rename columns: {e}")
                        pass
                
                # Format IAP column if exists
                if 'in_app_purchases' in filtered_df.columns:
                    display_df['in_app_purchases'] = filtered_df['in_app_purchases'].apply(format_iap_display)
                
                # After renaming, ensure we keep all columns (including renamed ones and IAP)
                # Don't filter again - display_df already has the correct columns
                
                # Ensure numeric columns maintain their numeric type for proper sorting
                numeric_cols_to_ensure = ['Rating', 'Rating Count', 'Downloads', 'Revenue',
                                         'rating_count_numeric', 'average_rating_numeric', 
                                         'downloads_numeric', 'revenue_numeric']
                
                for col in numeric_cols_to_ensure:
                    if col in display_df.columns:
                        display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                
                # Calculate Revenue / Download (ARPU - Average Revenue Per User)
                # Handle division by zero and missing values
                if 'Revenue' in display_df.columns and 'Downloads' in display_df.columns:
                    display_df['Revenue / Download'] = display_df.apply(
                        lambda row: (
                            row['Revenue'] / row['Downloads'] 
                            if pd.notna(row['Revenue']) and pd.notna(row['Downloads']) and row['Downloads'] > 0
                            else None
                        ),
                        axis=1
                    )
                
                # Display table with column configuration for proper numeric sorting and formatting
                column_config = {}
                for col in display_df.columns:
                    # Format numeric columns with proper number formatting
                    if col in ['Rating', 'Rating Count', 'Downloads', 'Revenue', 'Revenue / Download']:
                        if col == 'Rating':
                            # Rating: show 1 decimal place
                            column_config[col] = st.column_config.NumberColumn(
                                col,
                                format="%.1f"
                            )
                        elif col == 'Revenue / Download':
                            # Revenue per download: show 2 decimal places (currency-like)
                            column_config[col] = st.column_config.NumberColumn(
                                col,
                                format="%.2f"
                            )
                        elif col in ['Rating Count', 'Downloads', 'Revenue']:
                            # Large numbers: format with commas
                            column_config[col] = st.column_config.NumberColumn(
                                col,
                                format="%d"
                            )
                
                # Display table
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400,
                    hide_index=True,
                    column_config=column_config if column_config else None
                )
                
                # Quick delete section - show delete buttons for each row
                if len(filtered_df) > 0:
                    st.divider()
                    st.subheader("🗑️ Quick Delete")
                    st.caption("Select an app to delete quickly")
                    
                    # Create a selectbox for quick delete
                    delete_options = [f"{row.get('app_name', 'Unknown')} (ID: {row.get('app_id', 'N/A')})" 
                                     for idx, row in filtered_df.iterrows()]
                    selected_delete = st.selectbox(
                        "Select app to delete",
                        options=delete_options,
                        key="quick_delete_select"
                    )
                    
                    if selected_delete:
                        # Extract app_id from selection
                        selected_idx = delete_options.index(selected_delete)
                        selected_row = filtered_df.iloc[selected_idx]
                        delete_app_id = selected_row.get('app_id', '')
                        delete_app_name = selected_row.get('app_name', 'Unknown')
                        
                        delete_btn_col1, delete_btn_col2 = st.columns([3, 1])
                        with delete_btn_col2:
                            if st.button("🗑️ Delete Selected", type="secondary", use_container_width=True, 
                                       key=f"quick_delete_{delete_app_id}"):
                                if delete_app_id:
                                    success = database.delete_app(delete_app_id)
                                    if success:
                                        st.success(f"✅ Deleted '{delete_app_name}' successfully!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete app. It may have already been deleted.")
                                else:
                                    st.error("❌ Cannot delete: No App ID found.")
                
                # Detailed view for selected row
                st.divider()
                st.subheader("🔍 Detailed View")
                
                if len(filtered_df) > 0:
                    selected_index = st.selectbox(
                        "Select an app to view details",
                        options=range(len(filtered_df)),
                        format_func=lambda x: filtered_df.iloc[x]['app_name'] if 'app_name' in filtered_df.columns else f"App {x}"
                    )
                    
                    selected_app = filtered_df.iloc[selected_index]
                    
                    # Delete button at the top
                    delete_col1, delete_col2 = st.columns([3, 1])
                    with delete_col2:
                        app_id_to_delete = selected_app.get('app_id', '')
                        app_name_to_delete = selected_app.get('app_name', 'Unknown')
                        delete_key = f"delete_{app_id_to_delete}_{selected_index}"
                        
                        if st.button("🗑️ Delete", type="secondary", use_container_width=True, key=delete_key):
                            # Confirmation dialog
                            st.warning(f"⚠️ Are you sure you want to delete '{app_name_to_delete}'?")
                            confirm_col1, confirm_col2 = st.columns(2)
                            with confirm_col1:
                                if st.button("✅ Yes, Delete", key=f"confirm_delete_{delete_key}"):
                                    if app_id_to_delete:
                                        success = database.delete_app(app_id_to_delete)
                                        if success:
                                            st.success(f"✅ Deleted '{app_name_to_delete}' successfully!")
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to delete app. Check console for errors.")
                                    else:
                                        st.error("❌ Cannot delete: No App ID found.")
                            with confirm_col2:
                                if st.button("❌ Cancel", key=f"cancel_delete_{delete_key}"):
                                    st.rerun()
                    
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.write("**Basic Information**")
                        for col in ['app_name', 'app_id', 'categories', 'category_ranking', 'price', 'content_rating', 
                                   'average_rating', 'rating_count', 'release_date', 'publisher_country', 'last_updated']:
                            if col in selected_app and selected_app[col]:
                                display_value = selected_app[col]
                                # Format category ranking with # prefix if it's a number
                                if col == 'category_ranking' and display_value and not str(display_value).startswith('#'):
                                    display_value = f"#{display_value}"
                                # Format rating display
                                if col == 'average_rating' and display_value:
                                    rating_count_val = selected_app.get('rating_count', '')
                                    if rating_count_val:
                                        display_value = f"{display_value} ⭐ ({rating_count_val} ratings)"
                                    else:
                                        display_value = f"{display_value} ⭐"
                                elif col == 'rating_count':
                                    # Skip rating_count as it's shown with average_rating
                                    continue
                                st.write(f"- **{col.replace('_', ' ').title()}:** {display_value}")
                    
                    with detail_col2:
                        st.write("**Developer & Metrics**")
                        for col in ['developer_name', 'developer_website', 'support_url', 
                                   'downloads_worldwide', 'revenue_worldwide', 'top_countries']:
                            if col in selected_app:
                                st.write(f"- **{col.replace('_', ' ').title()}:** {selected_app[col]}")
                    
                    # In-App Purchases
                    if 'in_app_purchases' in selected_app and selected_app['in_app_purchases']:
                        st.write("**In-App Purchases:**")
                        try:
                            iap_data = json.loads(selected_app['in_app_purchases']) if isinstance(selected_app['in_app_purchases'], str) else selected_app['in_app_purchases']
                            if isinstance(iap_data, list) and len(iap_data) > 0:
                                iap_df = pd.DataFrame(iap_data)
                                st.dataframe(iap_df, use_container_width=True)
                            else:
                                st.write("None")
                        except:
                            st.write(selected_app['in_app_purchases'])
            else:
                st.info("📭 No apps scraped yet. Use the 'Search & Scrape' tab to get started!")
        
        except Exception as e:
            st.error(f"❌ Error loading history: {str(e)}")
            st.exception(e)
    
    with tab2:
        st.header("Search for iOS App")
        st.info("💡 **How it works:** Enter an app name, and we'll search the Apple App Store to find the App ID, then scrape data from SensorTower.")
        
        # Search input
        search_mode = st.radio(
            "Search Mode",
            ["App Name (Recommended)", "App ID", "Direct SensorTower URL"],
            horizontal=True,
            help="App Name: Searches Apple Store first. App ID: Direct ID lookup. Direct URL: Paste SensorTower URL."
        )
        
        if search_mode == "Direct SensorTower URL":
            search_term = st.text_input(
                "SensorTower Overview URL",
                placeholder="https://app.sensortower.com/overview/1523198397?country=US",
                key="url_input"
            )
            direct_url = search_term if search_term else None
            app_id = None
            search_term_display = ""
            batch_mode = False
        elif search_mode == "App ID":
            search_term = st.text_input(
                "Apple App Store ID (comma-separated for multiple)",
                placeholder="e.g., 1523198397 or 1523198397,6463803046,6737241669",
                key="id_input",
                help="Enter one ID or multiple IDs separated by commas"
            )
            app_id = search_term if search_term and search_term.isdigit() else None
            direct_url = None
            search_term_display = f"App ID: {search_term}" if search_term else ""
            # Check if multiple IDs (comma-separated)
            batch_mode = ',' in search_term if search_term else False
        else:
            search_term = st.text_input(
                "App Name (comma-separated for multiple)",
                placeholder="e.g., 'MamaZen' or 'MamaZen,Facebook,Instagram'",
                key="search_input",
                help="Enter one app name or multiple names separated by commas"
            )
            app_id = None
            direct_url = None
            search_term_display = search_term
            # Check if multiple apps (comma-separated)
            batch_mode = ',' in search_term if search_term else False
        
        col1, col2 = st.columns([3, 1])
        with col1:
            scrape_button = st.button("🔍 Scrape", use_container_width=True, type="primary")
        with col2:
            st.write("")  # Spacing
        
        if scrape_button and (search_term or app_id or direct_url):
            # Check if batch mode (multiple items separated by commas)
            if batch_mode and not direct_url:
                # Parse comma-separated input
                if search_mode == "App ID":
                    items = [item.strip() for item in search_term.split(',') if item.strip()]
                    item_type = "App ID"
                else:
                    items = [item.strip() for item in search_term.split(',') if item.strip()]
                    item_type = "App Name"
                
                if len(items) == 0:
                    st.warning("⚠️ Please enter at least one app name or ID.")
                else:
                    st.info(f"📦 **Batch Mode**: Processing {len(items)} {item_type}(s)")
                    
                    # Process each item
                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, item in enumerate(items):
                        current_num = idx + 1
                        total = len(items)
                        progress_bar.progress(current_num / total)
                        status_text.text(f"Processing {current_num}/{total}: {item}")
                        
                        try:
                            # Get App ID if needed
                            current_app_id = None
                            current_search_term = None
                            
                            if search_mode == "App ID":
                                if item.isdigit():
                                    current_app_id = item
                                    current_search_term = f"App ID: {item}"
                                else:
                                    st.warning(f"⚠️ Skipping '{item}': Not a valid App ID")
                                    continue
                            else:
                                # Search Apple Store for App ID
                                current_search_term = item
                                current_app_id = scraper.get_app_id_from_apple(item, headless=headless_mode)
                                if not current_app_id:
                                    st.warning(f"⚠️ Skipping '{item}': Could not find App ID on Apple Store")
                                    continue
                            
                            # Scrape data
                            app_data = scraper.scrape_app_data(
                                current_search_term,
                                headless=headless_mode,
                                app_id=current_app_id
                            )
                            
                            # Auto-save each result
                            if app_data.get('app_name') or app_data.get('app_id'):
                                try:
                                    database.init_db()
                                    save_success = database.save_result(app_data)
                                    if save_success:
                                        results.append({
                                            'item': item,
                                            'status': 'success',
                                            'app_name': app_data.get('app_name', 'Unknown'),
                                            'app_id': app_data.get('app_id', 'N/A')
                                        })
                                    else:
                                        results.append({
                                            'item': item,
                                            'status': 'save_failed',
                                            'app_name': app_data.get('app_name', 'Unknown'),
                                            'app_id': app_data.get('app_id', 'N/A')
                                        })
                                except Exception as e:
                                    results.append({
                                        'item': item,
                                        'status': 'save_error',
                                        'error': str(e)
                                    })
                            else:
                                results.append({
                                    'item': item,
                                    'status': 'no_data',
                                    'error': app_data.get('error', 'No app data found')
                                })
                        
                        except Exception as e:
                            results.append({
                                'item': item,
                                'status': 'error',
                                'error': str(e)
                            })
                    
                    # Show batch results summary
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.success(f"✅ Batch processing complete! Processed {len(items)} items")
                    
                    # Display results summary
                    success_count = sum(1 for r in results if r['status'] == 'success')
                    failed_count = len(results) - success_count
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("✅ Successfully Saved", success_count)
                    with col2:
                        st.metric("❌ Failed", failed_count)
                    
                    # Show detailed results
                    with st.expander("📊 Batch Results Details", expanded=True):
                        for result in results:
                            if result['status'] == 'success':
                                st.success(f"✅ {result['item']} → {result['app_name']} (ID: {result['app_id']})")
                            else:
                                st.error(f"❌ {result['item']} → {result.get('error', 'Failed')}")
                    
                    # Refresh to show updated history
                    time.sleep(1)
                    st.rerun()
            
            else:
                # Single item mode (existing logic)
                search_display = direct_url if direct_url else (f"App ID: {app_id}" if app_id else search_term)
                
                # Show workflow steps
                progress_container = st.container()
                with progress_container:
                    step1 = st.empty()
                    step2 = st.empty()
                    step3 = st.empty()
                
                with st.spinner(f"Scraping data for '{search_display}'... This may take a moment."):
                    try:
                        # Step 1: Get App ID from Apple Store (if needed)
                        if not app_id and not direct_url and search_term:
                            step1.info("🔍 Step 1: Searching Apple App Store...")
                            app_id = scraper.get_app_id_from_apple(search_term, headless=headless_mode)
                            if app_id:
                                step1.success(f"✅ Step 1: Found App ID: {app_id}")
                                step2.info("🔍 Step 2: Scraping SensorTower data...")
                            else:
                                step1.error("❌ Step 1: Could not find App ID on Apple App Store")
                                st.error(f"Could not find '{search_term}' on Apple App Store. Please check the app name.")
                                st.stop()
                        elif app_id:
                            step1.success(f"✅ Step 1: Using provided App ID: {app_id}")
                            step2.info("🔍 Step 2: Scraping SensorTower data...")
                        elif direct_url:
                            step1.success("✅ Step 1: Using direct URL")
                            step2.info("🔍 Step 2: Scraping SensorTower data...")
                        
                        # Step 2: Scrape app data
                        app_data = scraper.scrape_app_data(
                            search_term if search_term else "direct", 
                            headless=headless_mode,
                            direct_url=direct_url,
                            app_id=app_id
                        )
                        
                        # Check for errors first
                        if app_data.get('error'):
                            step2.error("❌ Step 2: Scraping failed")
                            st.error(f"❌ Error: {app_data['error']}")
                            st.info("💡 **Troubleshooting tips:**\n"
                                   "- Make sure you're logged into SensorTower if required\n"
                                   "- Try using the App ID directly instead of app name\n"
                                   "- Check if the app exists on SensorTower\n"
                                   "- Some data may require a paid SensorTower subscription")
                            with st.expander("🔧 Debug Information"):
                                st.json(app_data)
                        elif not app_data.get('app_name') and not app_data.get('app_id'):
                            step2.warning("⚠️ Step 2: Limited data found")
                            st.warning("⚠️ No app data found. Please check the app name or ID.")
                            st.info("💡 **Tips:**\n"
                                   "- Try the exact app name (e.g., 'MamaZen', 'Facebook')\n"
                                   "- Some data may not be publicly available\n"
                                   "- Try using the App Store ID directly")
                            with st.expander("🔧 See what was found"):
                                st.json(app_data)
                        else:
                            step2.success("✅ Step 2: Data scraped successfully!")
                        
                        # Auto-save to database after successful scraping
                        auto_saved = False
                        save_error = None
                        if app_data.get('app_name') or app_data.get('app_id'):
                            try:
                                database.init_db()
                                with st.spinner("Auto-saving to database..."):
                                    save_success = database.save_result(app_data)
                                if save_success:
                                    # Verify it was saved
                                    history_df = database.get_history()
                                    if len(history_df) > 0:
                                        auto_saved = True
                                        step3.success(f"✅ Step 3: Auto-saved! (Total: {len(history_df)} records)")
                                    else:
                                        step3.warning("⚠️ Step 3: Auto-save verification failed")
                                        save_error = "Save reported success but no records found"
                                else:
                                    step3.error("❌ Step 3: Auto-save failed")
                                    save_error = "Save function returned False"
                            except Exception as e:
                                step3.error(f"❌ Step 3: Auto-save error")
                                save_error = str(e)
                                st.error(f"Auto-save error: {str(e)}")
                        
                        if not auto_saved:
                            step3.info("💾 Step 3: Ready to save manually")
                            if save_error:
                                st.warning(f"⚠️ Auto-save failed: {save_error}. Use manual save button below.")
                        
                        # Display current result
                        if auto_saved:
                            st.success(f"✅ Successfully scraped and saved: {app_data.get('app_name', 'Unknown')}")
                        else:
                            st.success(f"✅ Successfully scraped: {app_data.get('app_name', 'Unknown')}")
                        
                        # Show app data in expandable sections
                        with st.expander("📋 View Scraped Data", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("Basic Information")
                                st.write(f"**App Name:** {app_data.get('app_name', 'N/A')}")
                                st.write(f"**App ID:** {app_data.get('app_id', 'N/A')}")
                                st.write(f"**Categories:** {app_data.get('categories', 'N/A')}")
                                if app_data.get('category_ranking'):
                                    st.write(f"**Category Ranking:** #{app_data.get('category_ranking', 'N/A')}")
                                st.write(f"**Price:** {app_data.get('price', 'N/A')}")
                                st.write(f"**Content Rating:** {app_data.get('content_rating', 'N/A')}")
                                # Display Apple App Store ratings
                                avg_rating = app_data.get('average_rating', '')
                                rating_count = app_data.get('rating_count', '')
                                if avg_rating or rating_count:
                                    rating_display = f"{avg_rating} ⭐" if avg_rating else "N/A"
                                    count_display = f"({rating_count} ratings)" if rating_count else ""
                                    st.write(f"**App Store Rating:** {rating_display} {count_display}")
                                st.write(f"**Publisher Country:** {app_data.get('publisher_country', 'N/A')}")
                                st.write(f"**Last Updated:** {app_data.get('last_updated', 'N/A')}")
                            
                            with col2:
                                st.subheader("Developer & Links")
                                st.write(f"**Developer:** {app_data.get('developer_name', 'N/A')}")
                                st.write(f"**Developer Website:** {app_data.get('developer_website', 'N/A')}")
                                st.write(f"**Support URL:** {app_data.get('support_url', 'N/A')}")
                                st.write(f"**Top Countries:** {app_data.get('top_countries', 'N/A')}")
                                st.write(f"**Advertised Status:** {app_data.get('advertised_status', 'N/A')}")
                            
                            st.subheader("Metrics")
                            col3, col4 = st.columns(2)
                            with col3:
                                st.write(f"**Downloads (Worldwide):** {app_data.get('downloads_worldwide', 'N/A')}")
                            with col4:
                                revenue = app_data.get('revenue_worldwide', 'N/A')
                                st.write(f"**Revenue (Worldwide):** {revenue}")
                                if revenue != 'N/A':
                                    st.caption("⚠️ Estimated by SensorTower (not exact revenue)")
                            
                            # In-App Purchases
                            if app_data.get('in_app_purchases'):
                                st.subheader("In-App Purchases")
                                iap_df = pd.DataFrame(app_data['in_app_purchases'])
                                st.dataframe(iap_df, use_container_width=True)
                            else:
                                st.write("**In-App Purchases:** None")
                            
                            # Raw JSON view
                            with st.expander("🔧 Raw JSON Data"):
                                st.json(app_data)
                        
                        # Manual save button (if auto-save didn't work or user wants to re-save)
                        save_col1, save_col2 = st.columns([2, 1])
                        with save_col1:
                            if auto_saved:
                                if st.button("💾 Re-save to Database", use_container_width=True):
                                    try:
                                        database.init_db()
                                        with st.spinner("Re-saving..."):
                                            success = database.save_result(app_data)
                                        if success:
                                            history_df = database.get_history()
                                            st.success(f"✅ Re-saved! Total records: {len(history_df)}")
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error("❌ Re-save failed")
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                            else:
                                save_button_key = f"save_btn_{app_data.get('app_id', 'unknown')}_{hash(str(app_data))}"
                                if st.button("💾 Save to Database", type="primary", use_container_width=True, key=save_button_key):
                                    # Check if we have at least app name or ID
                                    if app_data.get('app_name') or app_data.get('app_id'):
                                        try:
                                            # Ensure database is initialized
                                            database.init_db()
                                            
                                            with st.spinner("Saving to database..."):
                                                success = database.save_result(app_data)
                                            
                                            if success:
                                                # Verify it was saved
                                                history_df = database.get_history()
                                                record_count = len(history_df)
                                                
                                                if record_count > 0:
                                                    st.success(f"✅ App data saved successfully! Total records: {record_count}")
                                                    time.sleep(0.5)
                                                    st.rerun()
                                                else:
                                                    st.error("⚠️ Save reported success but database shows 0 records.")
                                                    st.info("💡 Check console/terminal for detailed error messages")
                                            else:
                                                st.error("❌ Failed to save to database.")
                                                st.info("💡 Check console/terminal for error details")
                                        except Exception as e:
                                            st.error(f"❌ Exception: {str(e)}")
                                            with st.expander("🔧 Error Details"):
                                                st.exception(e)
                                    else:
                                        st.warning("⚠️ Cannot save: No app name or ID found.")
                        with save_col2:
                            if st.button("🔄 New Search", use_container_width=True):
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
                        st.exception(e)
        
        elif scrape_button and not search_term:
            st.warning("⚠️ Please enter an app name or ID to search.")


if __name__ == "__main__":
    main()

