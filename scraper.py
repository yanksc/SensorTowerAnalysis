"""
Scraper module for extracting app data from SensorTower.
Uses Playwright for browser automation.
"""

import json
import re
import time
from typing import Dict, Optional, List
from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup


SENSORTOWER_BASE_URL = "https://sensortower.com"
SENSORTOWER_APP_BASE_URL = "https://app.sensortower.com"
APPLE_STORE_SEARCH_URL = "https://apps.apple.com/us/iphone/search"
APPLE_STORE_BASE_URL = "https://apps.apple.com"


def scrape_apple_app_store(url: str, headless: bool = True, timeout: int = 30000) -> Dict:
    """
    Scrape app data directly from Apple App Store page.
    
    Extracts:
    - Rating count (e.g., "8.1K Ratings")
    - Average rating (e.g., "4.6")
    - Age rating (e.g., "Ages 4+")
    - Category
    - Developer name
    - Language
    - App size
    - In-app purchases
    - Price
    - Description
    - Release date
    - Version
    
    Args:
        url: Apple App Store URL (e.g., https://apps.apple.com/us/app/vocal-image-ai-speaking-coach/id1535324205)
        headless: Whether to run browser in headless mode
        timeout: Page load timeout in milliseconds
        
    Returns:
        Dictionary containing extracted app data
    """
    result = {
        'app_name': '',
        'app_id': '',
        'rating_count': '',
        'average_rating': '',
        'age_rating': '',
        'category': '',
        'developer_name': '',
        'languages': '',
        'app_size': '',
        'price': '',
        'in_app_purchases': [],
        'description': '',
        'release_date': '',
        'version': '',
        'compatibility': '',
        'copyright': '',
        'support_url': '',
        'developer_website': ''
    }
    
    browser = None
    try:
        with sync_playwright() as p:
            # Configure browser launch args
            launch_args = []
            if headless:
                launch_args.extend([
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ])
            
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args if launch_args else None
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                java_script_enabled=True,
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            page = context.new_page()
            page.set_default_timeout(timeout)
            
            # Navigate to Apple App Store page
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            time.sleep(3)  # Wait for page to fully load
            
            # Wait for main content to load
            try:
                page.wait_for_selector('body', state='visible', timeout=10000)
                time.sleep(2)  # Additional wait for dynamic content
            except:
                pass
            
            # Get page HTML
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract App ID from URL
            id_match = re.search(r'/id(\d+)', url)
            if id_match:
                result['app_id'] = id_match.group(1)
            
            # Extract app name from page title or h1
            try:
                page_title = page.title()
                if page_title:
                    # Format: "App Name - Apple App Store - US - ..."
                    title_parts = page_title.split(' - ')
                    if title_parts:
                        result['app_name'] = title_parts[0].strip()
            except:
                pass
            
            # Try to get app name from h1
            if not result['app_name']:
                try:
                    h1 = soup.find('h1')
                    if h1:
                        result['app_name'] = h1.get_text(strip=True)
                except:
                    pass
            
            # Extract rating information using JavaScript
            try:
                rating_data = page.evaluate("""
                    () => {
                        const result = { rating_count: null, average_rating: null };
                        
                        // Look for rating text patterns in the entire page
                        const bodyText = document.body.innerText;
                        
                        // More comprehensive patterns
                        // Pattern 1: "8.1K Ratings 4.6" or "8.1K Ratings\\n4.6"
                        const pattern1 = /(\\d+\\.?\\d*[KMB]?)\\s*Ratings?[\\s\\n]+(\\d+\\.?\\d*)/i;
                        const match1 = bodyText.match(pattern1);
                        if (match1) {
                            result.rating_count = match1[1];
                            result.average_rating = match1[2];
                        }
                        
                        // Pattern 2: "4.6 out of 5  8.1K Ratings"
                        if (!result.rating_count || !result.average_rating) {
                            const pattern2 = /(\\d+\\.?\\d*)\\s+out of 5[\\s\\n]+(\\d+\\.?\\d*[KMB]?)\\s*Ratings?/i;
                            const match2 = bodyText.match(pattern2);
                            if (match2) {
                                result.average_rating = match2[1];
                                result.rating_count = match2[2];
                            }
                        }
                        
                        // Pattern 3: Look for rating and count separately
                        if (!result.average_rating) {
                            const ratingMatch = bodyText.match(/(\\d+\\.?\\d*)\\s+out of 5/i);
                            if (ratingMatch) {
                                result.average_rating = ratingMatch[1];
                            }
                        }
                        
                        if (!result.rating_count) {
                            // Look for rating count with decimal (e.g., "8.1K")
                            const countMatch = bodyText.match(/(\\d+\\.?\\d*[KMB]?)\\s*Ratings?/i);
                            if (countMatch) {
                                result.rating_count = countMatch[1];
                            }
                        }
                        
                        // Try finding rating elements directly in the DOM
                        const allElements = document.querySelectorAll('*');
                        for (const elem of allElements) {
                            const text = elem.textContent || elem.innerText || '';
                            if (text.includes('Ratings') || text.includes('out of 5')) {
                                // Check for rating count with decimal
                                const countMatch = text.match(/(\\d+\\.?\\d*[KMB]?)\\s*Ratings?/i);
                                if (countMatch && !result.rating_count) {
                                    result.rating_count = countMatch[1];
                                }
                                
                                // Check for average rating
                                const ratingMatch = text.match(/(\\d+\\.?\\d*)\\s+out of 5/i);
                                if (ratingMatch && !result.average_rating) {
                                    result.average_rating = ratingMatch[1];
                                }
                                
                                // Also try pattern: "4.6" near "Ratings"
                                if (!result.average_rating && text.includes('Ratings')) {
                                    const nearRating = text.match(/(\\d+\\.?\\d*)\\s*[\\s\\n]*Ratings?/i);
                                    if (nearRating) {
                                        // Check if there's a number before "Ratings"
                                        const beforeRatings = text.substring(0, text.indexOf('Ratings'));
                                        const numMatch = beforeRatings.match(/(\\d+\\.?\\d*)\\s*$/);
                                        if (numMatch) {
                                            result.average_rating = numMatch[1];
                                        }
                                    }
                                }
                                
                                if (result.average_rating && result.rating_count) {
                                    break;
                                }
                            }
                        }
                        
                        return result;
                    }
                """)
                
                if rating_data.get('rating_count'):
                    result['rating_count'] = str(rating_data['rating_count']).strip()
                if rating_data.get('average_rating'):
                    result['average_rating'] = str(rating_data['average_rating']).strip()
            except Exception as e:
                print(f"Warning: Error extracting ratings via JavaScript: {str(e)}")
                pass
            
            # Fallback: Extract from page text using regex
            page_text = page.inner_text('body')
            
            # Only use fallback if we didn't get both values from JavaScript
            if not result['rating_count'] or not result['average_rating']:
                # Pattern: "8.1K Ratings 4.6" or "4.6 out of 5  8.1K Ratings"
                rating_match = re.search(r'(\d+\.?\d*[KMB]?)\s*Ratings?\s+(\d+\.?\d*)', page_text, re.I)
                if rating_match:
                    if not result['rating_count']:
                        result['rating_count'] = rating_match.group(1).strip()
                    if not result['average_rating']:
                        result['average_rating'] = rating_match.group(2).strip()
                else:
                    # Try alternative pattern: "4.6 out of 5"
                    if not result['average_rating']:
                        rating_alt = re.search(r'(\d+\.?\d*)\s+out of 5', page_text, re.I)
                        if rating_alt:
                            result['average_rating'] = rating_alt.group(1).strip()
                    # Try to find rating count separately
                    if not result['rating_count']:
                        count_match = re.search(r'(\d+\.?\d*[KMB]?)\s*Ratings?', page_text, re.I)
                        if count_match:
                            result['rating_count'] = count_match.group(1).strip()
            
            # Debug: Print what we extracted
            if result['rating_count'] or result['average_rating']:
                print(f"Apple Store ratings extracted: {result.get('average_rating', 'N/A')} ⭐ ({result.get('rating_count', 'N/A')} ratings)")
            else:
                print(f"Warning: No ratings found on Apple App Store page")
            
            # Extract age rating (e.g., "Ages 4+")
            age_match = re.search(r'Ages\s+(\d+\+)', page_text, re.I)
            if age_match:
                result['age_rating'] = age_match.group(1)
            else:
                # Try alternative pattern
                age_alt = re.search(r'(\d+\+)\s+Years?', page_text, re.I)
                if age_alt:
                    result['age_rating'] = age_alt.group(1)
            
            # Extract category
            category_match = re.search(r'Category\s+([^\n\r]+)', page_text, re.I)
            if category_match:
                result['category'] = category_match.group(1).strip()
            
            # Extract developer name
            dev_match = re.search(r'Developer\s+([^\n\r]+)', page_text, re.I)
            if dev_match:
                result['developer_name'] = dev_match.group(1).strip()
            
            # Extract language (capture full text including "+ 5 More")
            # Try JavaScript first for better accuracy
            try:
                lang_data = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        // Look for "Language" followed by text
                        const langMatch = bodyText.match(/Language[\\s:]+([^\\n\\r]+?)(?:\\n|Information|Supports|$)/i);
                        if (langMatch) {
                            return langMatch[1].trim();
                        }
                        return null;
                    }
                """)
                if lang_data:
                    result['languages'] = lang_data
            except:
                pass
            
            # Fallback to regex
            if not result['languages']:
                lang_match = re.search(r'Language\s+([^\n\r]+?)(?:\n|Information|Supports|$)', page_text, re.I)
                if lang_match:
                    lang_text = lang_match.group(1).strip()
                    # Clean up common patterns
                    lang_text = re.sub(r'\s+', ' ', lang_text)
                    result['languages'] = lang_text
            
            # Extract app size
            size_match = re.search(r'Size\s+([^\n\r]+)', page_text, re.I)
            if size_match:
                result['app_size'] = size_match.group(1).strip()
            
            # Extract price (Free or Paid)
            if re.search(r'\bFree\b', page_text, re.I):
                result['price'] = 'Free'
            else:
                # Look for price in text
                price_match = re.search(r'\$(\d+\.?\d*)', page_text)
                if price_match:
                    result['price'] = f"${price_match.group(1)}"
                else:
                    result['price'] = 'Free'  # Default if no price found
            
            # Extract in-app purchases
            try:
                iap_section = page.evaluate("""
                    () => {
                        const iapItems = [];
                        const bodyText = document.body.innerText;
                        const htmlContent = document.body.innerHTML;
                        
                        // Look for "In-App Purchases" section
                        const iapIndex = bodyText.toLowerCase().indexOf('in-app purchases');
                        if (iapIndex === -1) {
                            // Try alternative text
                            const altIndex = bodyText.toLowerCase().indexOf('in‑app purchases');
                            if (altIndex === -1) return [];
                            var sectionStart = altIndex;
                        } else {
                            var sectionStart = iapIndex;
                        }
                        
                        // Extract larger section to get all IAPs
                        const section = bodyText.substring(sectionStart, sectionStart + 5000);
                        
                        // Look for IAP items - they usually appear as lines with prices
                        const lines = section.split('\\n');
                        let inIapSection = false;
                        
                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i].trim();
                            
                            // Check if we're in the IAP section
                            if (line.toLowerCase().includes('in-app purchase') || 
                                line.toLowerCase().includes('in‑app purchase')) {
                                inIapSection = true;
                                continue;
                            }
                            
                            // Stop if we hit another major section
                            if (inIapSection && (line.toLowerCase().includes('information') || 
                                line.toLowerCase().includes('supports') ||
                                line.toLowerCase().includes('privacy'))) {
                                break;
                            }
                            
                            if (inIapSection && line) {
                                // Look for price pattern
                                const priceMatch = line.match(/\\$([\\d,]+(?:\\.\\d{2})?)/);
                                if (priceMatch) {
                                    const price = '$' + priceMatch[1];
                                    // Get product name (everything before the price)
                                    const name = line.replace(/\\$[\\d,]+(?:\\.\\d{2})?.*$/, '').trim();
                                    
                                    if (name && name.length > 0 && name.length < 200) {
                                        iapItems.push({
                                            name: name,
                                            price: price
                                        });
                                    } else {
                                        iapItems.push({
                                            name: 'In-App Purchase',
                                            price: price
                                        });
                                    }
                                }
                            }
                        }
                        
                        // Also try to find IAP in HTML structure
                        if (iapItems.length === 0) {
                            // Look for list items or divs containing prices
                            const priceElements = document.querySelectorAll('*');
                            for (const elem of priceElements) {
                                const text = elem.textContent || '';
                                const priceMatch = text.match(/\\$([\\d,]+(?:\\.\\d{2})?)/);
                                if (priceMatch && text.toLowerCase().includes('subscription') || 
                                    text.toLowerCase().includes('purchase')) {
                                    const price = '$' + priceMatch[1];
                                    const name = text.replace(/\\$[\\d,]+(?:\\.\\d{2})?.*$/, '').trim();
                                    if (name && name.length < 200) {
                                        iapItems.push({ name: name, price: price });
                                    }
                                }
                            }
                        }
                        
                        // Remove duplicates
                        const uniqueIaps = [];
                        const seen = new Set();
                        for (const iap of iapItems) {
                            const key = iap.name + '|' + iap.price;
                            if (!seen.has(key)) {
                                seen.add(key);
                                uniqueIaps.push(iap);
                            }
                        }
                        
                        return uniqueIaps.slice(0, 20); // Limit to 20 items
                    }
                """)
                
                if iap_section and len(iap_section) > 0:
                    result['in_app_purchases'] = iap_section
            except Exception as e:
                pass
            
            # Extract description (first paragraph)
            try:
                # Try multiple strategies to find description
                desc_text = None
                
                # Strategy 1: Look for description in specific elements
                desc_selectors = [
                    'div[class*="description"]',
                    'div[class*="product-review"]',
                    'div[class*="app-description"]',
                    'section[class*="description"]',
                    'p[class*="description"]'
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_elem = soup.select_one(selector)
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if desc_text and len(desc_text) > 50:
                                break
                    except:
                        continue
                
                # Strategy 2: Look for text after app name/title
                if not desc_text or len(desc_text) < 50:
                    try:
                        # Find h1 or title, then get next paragraph
                        h1 = soup.find('h1')
                        if h1:
                            next_p = h1.find_next('p')
                            if next_p:
                                desc_text = next_p.get_text(strip=True)
                    except:
                        pass
                
                # Strategy 3: Extract from page text (look for longer paragraphs)
                if not desc_text or len(desc_text) < 50:
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if len(line) > 100 and len(line) < 1000:
                            # Skip if it looks like navigation or metadata
                            if not any(x in line.lower() for x in ['download', 'app store', 'copyright', 'developer']):
                                desc_text = line
                                break
                
                if desc_text:
                    # Clean up and limit length
                    desc_text = ' '.join(desc_text.split())  # Normalize whitespace
                    result['description'] = desc_text[:500] + ('...' if len(desc_text) > 500 else '')
            except:
                pass
            
            # Extract compatibility
            compat_match = re.search(r'Requires\s+([^\n\r]+)', page_text, re.I)
            if compat_match:
                result['compatibility'] = compat_match.group(1).strip()
            
            # Extract copyright
            copyright_match = re.search(r'©\s+([^\n\r]+)', page_text)
            if copyright_match:
                result['copyright'] = copyright_match.group(1).strip()
            
            # Extract release date / first launch date
            # Try multiple patterns for release date
            try:
                # JavaScript extraction for release date (more reliable)
                release_js = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        // Look for "Released" followed by date in various formats
                        const patterns = [
                            /Released[\\s:]+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/i,
                            /Release\\s+Date[\\s:]+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/i,
                            /First\\s+Available[\\s:]+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/i,
                            /Released[\\s:]+(\\d{1,2}[/-]\\d{1,2}[/-]\\d{4})/i,
                        ];
                        
                        for (const pattern of patterns) {
                            const match = bodyText.match(pattern);
                            if (match && match[1]) {
                                return match[1].trim();
                            }
                        }
                        
                        // Also check HTML for structured data
                        const metaTags = document.querySelectorAll('meta');
                        for (const tag of metaTags) {
                            const property = tag.getAttribute('property') || tag.getAttribute('name') || '';
                            const content = tag.getAttribute('content') || '';
                            if ((property.includes('release') || property.includes('date')) && content) {
                                const dateMatch = content.match(/(\\d{4}[\\/-]\\d{1,2}[\\/-]\\d{1,2}|[A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})/);
                                if (dateMatch) {
                                    return dateMatch[1].trim();
                                }
                            }
                        }
                        
                        return null;
                    }
                """)
                if release_js:
                    result['release_date'] = release_js
                else:
                    # Fallback: Pattern matching in page text
                    # Pattern 1: "Released: Dec 15, 2023" or "Released Dec 15, 2023"
                    release_match = re.search(r'Released[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', page_text, re.I)
                    if release_match:
                        result['release_date'] = release_match.group(1).strip()
                    else:
                        # Pattern 2: Look for date patterns near "Release" or "First" keywords
                        release_patterns = [
                            r'(?:First\s+)?Released[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
                            r'(?:First\s+)?Released[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                            r'Release\s+Date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                            r'First\s+Available[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                        ]
                        for pattern in release_patterns:
                            match = re.search(pattern, page_text, re.I)
                            if match:
                                result['release_date'] = match.group(1).strip()
                                break
            except Exception as e:
                print(f"Warning: Error extracting release date: {str(e)}")
                pass
            
            # Extract version
            try:
                # Try JavaScript extraction first
                version_js = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        const match = bodyText.match(/Version[\\s:]+([\\d.]+)/i);
                        return match ? match[1].trim() : null;
                    }
                """)
                if version_js:
                    result['version'] = version_js
                else:
                    # Fallback: Pattern matching
                    version_match = re.search(r'Version[:\s]+([\d.]+)', page_text, re.I)
                    if version_match:
                        result['version'] = version_match.group(1).strip()
            except Exception as e:
                pass
            
            # Extract support URL
            try:
                support_links = soup.find_all('a', href=re.compile(r'support|help'))
                if support_links:
                    href = support_links[0].get('href', '')
                    if href:
                        result['support_url'] = href if href.startswith('http') else f"https://apps.apple.com{href}"
            except:
                pass
            
            # Extract developer website
            try:
                dev_links = soup.find_all('a', href=re.compile(r'developer|publisher'))
                if dev_links:
                    href = dev_links[0].get('href', '')
                    if href:
                        result['developer_website'] = href if href.startswith('http') else f"https://apps.apple.com{href}"
            except:
                pass
            
            browser.close()
            return result
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error scraping Apple App Store: {error_msg}")
        result['error'] = error_msg
        if browser:
            try:
                browser.close()
            except:
                pass
        return result


def get_app_id_from_apple(search_term: str, headless: bool = True, timeout: int = 30000) -> Optional[str]:
    """
    Search Apple App Store and extract the App ID from the first result.
    
    Args:
        search_term: App name to search for
        headless: Whether to run browser in headless mode
        timeout: Page load timeout in milliseconds
        
    Returns:
        App ID (numeric string) or None if not found
    """
    browser = None
    try:
        with sync_playwright() as p:
            # Configure browser launch args for better headless compatibility
            launch_args = []
            if headless:
                # Add args to improve headless mode compatibility
                launch_args.extend([
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--disable-features=IsolateOrigins,site-per-process',
                ])
            
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args if launch_args else None
            )
            
            # Configure context with permissions and settings
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                # Grant permissions for network access
                permissions=['geolocation'],
                # Allow local network access
                ignore_https_errors=False,
                # Set locale and timezone
                locale='en-US',
                timezone_id='America/New_York',
                # Additional settings for better compatibility
                java_script_enabled=True,
                bypass_csp=True,
                # Set extra HTTP headers
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            page = context.new_page()
            page.set_default_timeout(timeout)
            
            # Navigate to Apple App Store search
            search_url = f"{APPLE_STORE_SEARCH_URL}?term={search_term.replace(' ', '+')}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=timeout)
            time.sleep(3)  # Wait for search results to load
            
            # Look for the first app result link
            # Apple Store search results have links like: /us/app/app-name/id123456789
            result_selectors = [
                'a[href*="/app/"]',
                'a[href*="/id"]',
                'li[class*="app"] a',
                'div[class*="result"] a',
                'a[data-testid*="app"]'
            ]
            
            app_url = None
            for selector in result_selectors:
                try:
                    # Wait for results to appear
                    page.wait_for_selector(selector, timeout=10000)
                    links = page.query_selector_all(selector)
                    
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '/app/' in href and '/id' in href:
                            # Extract the full URL
                            if href.startswith('http'):
                                app_url = href
                            else:
                                app_url = f"https://apps.apple.com{href}"
                            break
                    
                    if app_url:
                        break
                except Exception as e:
                    continue
            
            browser.close()
            
            if app_url:
                # Extract App ID from URL pattern: .../id123456789 or .../id/123456789
                id_match = re.search(r'/id(\d+)', app_url)
                if id_match:
                    return id_match.group(1)
                # Try alternative pattern
                id_match2 = re.search(r'/id/(\d+)', app_url)
                if id_match2:
                    return id_match2.group(1)
            
            return None
            
    except Exception as e:
        print(f"Error getting App ID from Apple Store: {e}")
        if browser:
            try:
                browser.close()
            except:
                pass
        return None


def scrape_app_data(search_term: str, headless: bool = True, timeout: int = 60000, direct_url: str = None, app_id: str = None) -> Dict:
    """
    Scrape app data from SensorTower using the new workflow:
    1. Search Apple App Store to get App ID (if not provided)
    2. Construct SensorTower URL: app.sensortower.com/overview/{app_id}?country=US
    3. Scrape data from SensorTower overview page
    
    Args:
        search_term: App name to search (used to find App ID via Apple Store)
        headless: Whether to run browser in headless mode
        timeout: Page load timeout in milliseconds
        direct_url: Optional direct SensorTower URL to scrape (legacy support)
        app_id: Optional App ID to skip Apple Store search
        
    Returns:
        Dictionary containing extracted app data
    """
    result = {
        'app_name': '',
        'app_id': '',
        'categories': '',
        'price': '',
        'top_countries': '',
        'advertised_status': '',
        'support_url': '',
        'developer_website': '',
        'developer_name': '',
        'content_rating': '',
        'downloads_worldwide': '',
        'revenue_worldwide': '',
        'last_updated': '',
        'publisher_country': '',
        'category_ranking': '',
        'in_app_purchases': [],
        'average_rating': '',
        'rating_count': ''
    }
    
    browser = None
    try:
        with sync_playwright() as p:
            # Configure browser launch args for better headless compatibility
            launch_args = []
            if headless:
                # Add args to improve headless mode compatibility and local network access
                launch_args.extend([
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--disable-features=IsolateOrigins,site-per-process',
                ])
            
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args if launch_args else None
            )
            
            # Configure context with permissions and settings for local network access
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                # Grant permissions for network access
                permissions=['geolocation'],
                # Allow local network access
                ignore_https_errors=False,
                # Set locale and timezone
                locale='en-US',
                timezone_id='America/New_York',
                # Additional settings for better compatibility
                java_script_enabled=True,
                bypass_csp=True,
                # Set extra HTTP headers
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            page = context.new_page()
            page.set_default_timeout(timeout)
            
            # Step 1: Get App ID (if not provided)
            if not app_id and not direct_url:
                if search_term.isdigit():
                    # If search term is already a numeric ID, use it
                    app_id = search_term
                else:
                    # Search Apple App Store to get App ID
                    app_id = get_app_id_from_apple(search_term, headless=headless, timeout=30000)
                    if not app_id:
                        result['error'] = f"Could not find App ID for '{search_term}' on Apple App Store. Please check the app name."
                        browser.close()
                        return result
            
            # Step 2: Construct SensorTower URL
            if direct_url:
                sensortower_url = direct_url
            elif app_id:
                sensortower_url = f"{SENSORTOWER_APP_BASE_URL}/overview/{app_id}?country=US"
            else:
                result['error'] = "No App ID or direct URL provided"
                browser.close()
                return result
            
            # Step 3: Navigate to SensorTower overview page
            try:
                response = page.goto(sensortower_url, wait_until="domcontentloaded", timeout=timeout)
                
                # Check if we're redirected to login
                current_url = page.url
                page_content = page.content().lower()
                
                if 'login' in current_url.lower() or 'sign-in' in current_url.lower() or 'login' in page_content[:5000]:
                    result['error'] = f"Login required to access SensorTower. The URL {sensortower_url} requires authentication."
                    browser.close()
                    return result
                
                if response and response.status >= 400:
                    result['error'] = f"Failed to load SensorTower page: {sensortower_url} (Status: {response.status})"
                    browser.close()
                    return result
                
                # Try to fetch API data directly (more reliable than scraping rendered page)
                api_url = f"{SENSORTOWER_APP_BASE_URL}/api/ios/apps/{app_id}?country=US"
                api_data = None
                try:
                    api_response = page.request.get(api_url, timeout=10000)
                    if api_response.status == 200:
                        api_data = api_response.json()
                except:
                    pass  # API might require auth, fall back to scraping
                
                # Wait for React app to fully render
                time.sleep(3)
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(5)  # Additional wait for React hydration
                
                # Wait for react-root to have content
                try:
                    page.wait_for_selector('#react-root', state='attached', timeout=10000)
                    # Wait for content to appear in react-root
                    for i in range(15):  # Wait up to 15 seconds
                        react_content = page.query_selector('#react-root')
                        if react_content:
                            inner_text = react_content.inner_text()
                            if len(inner_text) > 100:  # Meaningful content
                                break
                        time.sleep(1)
                except:
                    pass
                
                page_loaded = True
                final_url = page.url
                
            except Exception as e:
                result['error'] = f"Error loading SensorTower URL {sensortower_url}: {str(e)}"
                browser.close()
                return result
            
            # Store the app_id in result
            if app_id:
                result['app_id'] = app_id
            
            # First, try to extract from API data if available (most reliable)
            if api_data:
                try:
                    # Extract from API response structure
                    if 'name' in api_data:
                        result['app_name'] = api_data['name']
                    if 'category' in api_data:
                        result['categories'] = api_data.get('category', {}).get('name', '')
                    if 'price' in api_data:
                        price_val = api_data.get('price', 0)
                        result['price'] = 'Free' if price_val == 0 or price_val == '0' else 'Paid'
                    if 'developer' in api_data:
                        result['developer_name'] = api_data['developer'].get('name', '')
                    if 'content_rating' in api_data:
                        result['content_rating'] = api_data['content_rating']
                    if 'last_updated' in api_data or 'updated_at' in api_data:
                        result['last_updated'] = api_data.get('last_updated') or api_data.get('updated_at', '')
                    if 'publisher_country' in api_data:
                        result['publisher_country'] = api_data['publisher_country']
                    # Downloads and revenue might be in nested structures
                    if 'estimates' in api_data:
                        estimates = api_data['estimates']
                        if 'downloads' in estimates:
                            result['downloads_worldwide'] = str(estimates['downloads'])
                        if 'revenue' in estimates:
                            result['revenue_worldwide'] = str(estimates['revenue'])
                except Exception as e:
                    pass  # Fall back to HTML scraping
            
            # Extract from HTML meta tags and JSON-LD (reliable, available immediately)
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract from JSON-LD schema (most reliable)
            json_ld_script = soup.find('script', type='application/ld+json')
            if json_ld_script:
                try:
                    json_ld_data = json.loads(json_ld_script.string)
                    if not result['app_name'] and 'name' in json_ld_data:
                        result['app_name'] = json_ld_data['name']
                    if not result['categories'] and 'applicationCategory' in json_ld_data:
                        result['categories'] = json_ld_data['applicationCategory']
                    if not result['price']:
                        if 'offers' in json_ld_data and 'price' in json_ld_data['offers']:
                            price_val = json_ld_data['offers']['price']
                            result['price'] = 'Free' if price_val == '0' or price_val == 0 else 'Paid'
                    if not result['last_updated'] and 'dateModified' in json_ld_data:
                        date_str = json_ld_data['dateModified']
                        # Convert ISO format to YYYY/MM/DD
                        if 'T' in date_str:
                            date_str = date_str.split('T')[0].replace('-', '/')
                        result['last_updated'] = date_str
                except:
                    pass
            
            # Extract from meta tags
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content') and not result['app_name']:
                title = og_title['content']
                # Extract app name from title (format: "App Name - Apple App Store - US - ...")
                title_parts = title.split(' - ')
                if title_parts:
                    result['app_name'] = title_parts[0].strip()
            
            # Extract from meta description
            meta_desc = soup.find('meta', property='og:description') or soup.find('meta', name='description')
            if meta_desc and meta_desc.get('content'):
                desc = meta_desc['content']
                # Extract downloads from description if available
                if not result['downloads_worldwide']:
                    download_match = re.search(r'(\d+[KMB]?)\s*downloads?', desc, re.I)
                    if download_match:
                        result['downloads_worldwide'] = download_match.group(1)
            
            # Wait for React content to fully load (for additional data)
            try:
                # Wait for network to be idle
                page.wait_for_load_state("networkidle", timeout=15000)
                # Additional wait for React hydration
                time.sleep(3)
                
                # Try to wait for content to appear - look for common SensorTower page elements
                try:
                    # Wait for body to be visible
                    page.wait_for_selector('body', state='visible', timeout=10000)
                    
                    # Try waiting for any text content (indicates React has rendered)
                    max_wait = 10
                    for i in range(max_wait):
                        page_text_check = page.inner_text('body')
                        if len(page_text_check) > 500:  # Meaningful content loaded
                            break
                        time.sleep(1)
                    
                    # Final wait for any remaining async content
                    time.sleep(2)
                except:
                    pass
            except:
                pass
            
            # Extract data from the SensorTower overview page
            # Use JavaScript evaluation to get text content (works better with React)
            try:
                # Get all visible text using JavaScript (bypasses React rendering issues)
                page_text_js = page.evaluate("""
                    () => {
                        // Get all text nodes recursively
                        function getTextNodes(node) {
                            let textNodes = [];
                            if (node.nodeType === 3) { // Text node
                                textNodes.push(node.textContent.trim());
                            } else {
                                for (let child of node.childNodes) {
                                    textNodes = textNodes.concat(getTextNodes(child));
                                }
                            }
                            return textNodes;
                        }
                        return getTextNodes(document.body).filter(t => t.length > 0).join('\\n');
                    }
                """)
                page_text = page_text_js if page_text_js else page.inner_text('body')
            except:
                page_text = page.inner_text('body')
            
            # Also get HTML for fallback parsing
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Debug: Check if we have meaningful content
            if len(page_text) < 100:
                # Page might not have loaded properly, wait more and retry
                time.sleep(5)
                try:
                    page_text = page.evaluate("""
                        () => {
                            function getTextNodes(node) {
                                let textNodes = [];
                                if (node.nodeType === 3) {
                                    textNodes.push(node.textContent.trim());
                                } else {
                                    for (let child of node.childNodes) {
                                        textNodes = textNodes.concat(getTextNodes(child));
                                    }
                                }
                                return textNodes;
                            }
                            return getTextNodes(document.body).filter(t => t.length > 0).join('\\n');
                        }
                    """)
                    if not page_text or len(page_text) < 100:
                        page_text = page.inner_text('body')
                except:
                    page_text = page.inner_text('body')
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
            
            # Store page text length for debugging (if needed)
            if len(page_text) < 50:
                result['debug_info'] = f"Page text too short ({len(page_text)} chars). Page may not have loaded correctly."
            
            # Extract app name from React-rendered content (only if not already found)
            name_found = bool(result.get('app_name'))
            
            if not name_found:
                # Strategy: Look specifically in react-root, avoiding navigation/header
                try:
                    app_name_js = page.evaluate("""
                        () => {
                            // Focus on react-root content, avoid header/navigation
                            const reactRoot = document.getElementById('react-root');
                            if (!reactRoot) return null;
                            
                            // Look for h1 or main title within react-root
                            const h1 = reactRoot.querySelector('h1');
                            if (h1) {
                                const text = h1.textContent.trim();
                                if (text && text.length < 200 && !text.toLowerCase().includes('sensortower') 
                                    && !text.toLowerCase().includes('track performance')) {
                                    return text;
                                }
                            }
                            
                            // Look for app name in specific data attributes or classes
                            const nameSelectors = [
                                '[data-testid*="app-name"]',
                                '[class*="AppName"]',
                                '[class*="app-name"]',
                                'h1[class*="title"]',
                                '[aria-label*="app"]'
                            ];
                            
                            for (const selector of nameSelectors) {
                                const elem = reactRoot.querySelector(selector);
                                if (elem) {
                                    const text = elem.textContent.trim();
                                    if (text && text.length < 200 && !text.toLowerCase().includes('sensortower')) {
                                        return text;
                                    }
                                }
                            }
                            
                            // Get first meaningful text from react-root (skip navigation)
                            const allText = reactRoot.innerText;
                            const lines = allText.split('\\n').filter(l => {
                                const trimmed = l.trim();
                                return trimmed.length > 2 && trimmed.length < 200 
                                    && !trimmed.toLowerCase().includes('sensortower')
                                    && !trimmed.toLowerCase().includes('track performance')
                                    && !trimmed.toLowerCase().includes('sign up')
                                    && !trimmed.toLowerCase().includes('help');
                            });
                            
                            return lines.length > 0 ? lines[0] : null;
                        }
                    """)
                    if app_name_js:
                        result['app_name'] = app_name_js
                        name_found = True
                except Exception as e:
                    pass
            
            # Strategy 2: Try Playwright selectors
            if not name_found:
                try:
                    name_selectors_playwright = [
                        'h1',
                        'h2',
                        '[class*="app-name"]',
                        '[class*="app-title"]',
                        '[data-testid*="name"]',
                        '[data-testid*="title"]'
                    ]
                    
                    for selector in name_selectors_playwright:
                        try:
                            element = page.query_selector(selector)
                            if element:
                                name_text = element.inner_text().strip()
                                if name_text and len(name_text) > 0 and len(name_text) < 200 and 'sensortower' not in name_text.lower():
                                    result['app_name'] = name_text
                                    name_found = True
                                    break
                        except:
                            continue
                except:
                    pass
            
            # Strategy 3: Look in page title
            if not name_found:
                page_title = page.title()
                if page_title:
                    # Remove SensorTower branding
                    title_clean = page_title.replace('SensorTower', '').replace('|', '-').replace('Overview', '').strip()
                    title_parts = [p.strip() for p in title_clean.split('-') if p.strip() and p.strip().lower() != 'overview']
                    if title_parts and title_parts[0]:
                        result['app_name'] = title_parts[0]
                        name_found = True
            
            # Strategy 4: Extract from visible text (first significant text)
            if not name_found and page_text:
                lines = [l.strip() for l in page_text.split('\n') if l.strip() and len(l.strip()) > 2]
                for line in lines[:10]:
                    if len(line) < 200 and 'sensortower' not in line.lower() and not line.lower().startswith('http'):
                        result['app_name'] = line
                        name_found = True
                        break
            
            # Strategy 5: Look for meta tags
            if not name_found:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    result['app_name'] = og_title['content'].strip()
                    name_found = True
            
            # Extract app ID from URL (should already be set, but verify)
            current_url = page.url
            overview_id_match = re.search(r'/overview/(\d+)', current_url)
            if overview_id_match:
                result['app_id'] = overview_id_match.group(1)
            
            # Extract categories - only if not already found from API/JSON-LD
            category_found = bool(result.get('categories'))
            
            if not category_found:
                try:
                    category_js = page.evaluate("""
                        () => {
                            const reactRoot = document.getElementById('react-root');
                            if (!reactRoot) return null;
                            
                            // Look for category in react-root only
                            const categoryKeywords = ['Category', 'Categories', 'Genre'];
                            const reactText = reactRoot.innerText;
                            
                            for (const keyword of categoryKeywords) {
                                const regex = new RegExp(keyword + '[\\s:]+([^\\n\\r]+)', 'i');
                                const match = reactText.match(regex);
                                if (match && match[1]) {
                                    const cat = match[1].trim().split('\\n')[0].split('|')[0].trim();
                                    if (cat && cat.length < 100 && !cat.toLowerCase().includes('ranking')) {
                                        return cat;
                                    }
                                }
                            }
                            
                            // Try finding category elements in react-root
                            const catSelectors = [
                                '[data-testid*="category"]',
                                '[class*="Category"]',
                                '[class*="category"]',
                                '[data-category]'
                            ];
                            
                            for (const selector of catSelectors) {
                                const elem = reactRoot.querySelector(selector);
                                if (elem) {
                                    const text = elem.textContent.trim();
                                    if (text && text.length < 100 && !text.toLowerCase().includes('ranking')) {
                                        return text;
                                    }
                                }
                            }
                            
                            return null;
                        }
                    """)
                    if category_js:
                        result['categories'] = category_js
                        category_found = True
                except:
                    pass
            
            # Fallback: search in page text
            if not category_found and page_text:
                for keyword in ['Category', 'Categories', 'Genre']:
                    pattern = re.compile(rf'{keyword}[:\s]+([^\n\r]+)', re.I)
                    match = pattern.search(page_text)
                    if match:
                        result['categories'] = match.group(1).strip()
                        category_found = True
                        break
            
            # Fallback: look for common category names
            if not category_found and page_text:
                common_categories = ['Productivity', 'Education', 'Games', 'Social', 'Entertainment', 
                                   'Photo', 'Video', 'Health & Fitness', 'Business', 'Lifestyle', 'Utilities']
                for cat in common_categories:
                    if cat.lower() in page_text.lower():
                        result['categories'] = cat
                        break
            
            # Extract price (Free/Paid) - use JavaScript
            price_found = False
            
            try:
                price_js = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        
                        // Check for Free
                        if (/\\bFree\\b/i.test(bodyText) || bodyText.includes('$0')) {
                            return 'Free';
                        }
                        
                        // Check for Paid (has price)
                        if (/\\$\\d+/.test(bodyText)) {
                            return 'Paid';
                        }
                        
                        // Try finding price elements
                        const priceSelectors = [
                            '[class*="price"]',
                            '[class*="Price"]',
                            '[data-price]',
                            '[data-testid*="price"]'
                        ];
                        
                        for (const selector of priceSelectors) {
                            const elem = document.querySelector(selector);
                            if (elem) {
                                const text = elem.textContent.trim().toLowerCase();
                                if (text.includes('free') || text.includes('$0')) {
                                    return 'Free';
                                } else if (text.includes('$')) {
                                    return 'Paid';
                                }
                            }
                        }
                        
                        return null;
                    }
                """)
                if price_js:
                    result['price'] = price_js
                    price_found = True
            except:
                pass
            
            # Fallback: search in text
            if not price_found and page_text:
                if re.search(r'\bFree\b', page_text, re.I) or '$0' in page_text:
                    result['price'] = 'Free'
                elif re.search(r'\$\d+', page_text):
                    result['price'] = 'Paid'
            
            # Extract top countries - search in text
            country_pattern = re.compile(r'Top Countries[:\s]+([^\n\r]+)', re.I)
            country_match = country_pattern.search(page_text)
            if country_match:
                result['top_countries'] = country_match.group(1).strip()
            else:
                # Look for country flags or names
                common_countries = ['Taiwan', 'Philippines', 'Pakistan', 'United States', 'China', 'Japan']
                found_countries = []
                for country in common_countries:
                    if country.lower() in page_text.lower():
                        found_countries.append(country)
                if found_countries:
                    result['top_countries'] = ', '.join(found_countries[:5])
            
            # Extract developer information - only if not from API
            if not result.get('developer_name'):
                try:
                    dev_info_js = page.evaluate("""
                        () => {
                            const reactRoot = document.getElementById('react-root');
                            if (!reactRoot) return null;
                            
                            const reactText = reactRoot.innerText;
                            
                            // Look for developer pattern in react-root
                            const devPatterns = [
                                /(?:Developer|Publisher|By|Made by)[\\s:]+([^\\n\\r]+)/i,
                                /Developer[\\s:]+([^\\n\\r]+)/i,
                                /Publisher[\\s:]+([^\\n\\r]+)/i
                            ];
                            
                            for (const pattern of devPatterns) {
                                const match = reactText.match(pattern);
                                if (match && match[1]) {
                                    const dev = match[1].trim().split('\\n')[0].split('|')[0].trim();
                                    if (dev && dev.length < 200 && dev.toLowerCase() !== 'website') {
                                        return dev;
                                    }
                                }
                            }
                            
                            // Try finding developer links in react-root
                            const devLinks = reactRoot.querySelectorAll('a[href*="developer"], a[href*="publisher"]');
                            for (const link of devLinks) {
                                const text = link.textContent.trim();
                                if (text && text.length < 200 && text.toLowerCase() !== 'website') {
                                    return text;
                                }
                            }
                            
                            return null;
                        }
                    """)
                    if dev_info_js:
                        result['developer_name'] = dev_info_js
                except:
                    pass
            
            # Fallback: regex search
            if not result['developer_name'] and page_text:
                dev_pattern = re.compile(r'(?:Developer|Publisher|By|Made by)[:\s]+([^\n\r]+)', re.I)
                dev_match = dev_pattern.search(page_text)
                if dev_match:
                    result['developer_name'] = dev_match.group(1).strip().split('\n')[0].split('|')[0].strip()
            
            # Try finding developer link for website
            try:
                dev_links = page.query_selector_all('a[href*="developer"], a[href*="publisher"]')
                if dev_links:
                    dev_link = dev_links[0]
                    href = dev_link.get_attribute('href')
                    if href:
                        result['developer_website'] = href if href.startswith('http') else f"{SENSORTOWER_BASE_URL}{href}"
            except:
                pass
            
            # Extract support URL
            try:
                support_links = page.query_selector_all('a[href*="support"], a[href*="help"]')
                if support_links:
                    href = support_links[0].get_attribute('href')
                    if href:
                        result['support_url'] = href if href.startswith('http') else f"https://{href}"
            except:
                pass
            
            # Extract content rating - use JavaScript
            try:
                rating_js = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        
                        // Look for content rating patterns
                        const ratingPatterns = [
                            /(?:Content Rating|Age Rating|Rating)[\\s:]*?(\\d+\\+)/i,
                            /\\b(\\d{1,2})\\+\\b/
                        ];
                        
                        for (const pattern of ratingPatterns) {
                            const match = bodyText.match(pattern);
                            if (match && match[1]) {
                                return match[1] + '+';
                            }
                        }
                        
                        return null;
                    }
                """)
                if rating_js:
                    result['content_rating'] = rating_js
            except:
                pass
            
            # Fallback: regex search
            if not result['content_rating'] and page_text:
                rating_pattern = re.compile(r'(?:Content Rating|Age Rating|Rating)[:\s]*(\d+\+)', re.I)
                rating_match = rating_pattern.search(page_text)
                if rating_match:
                    result['content_rating'] = rating_match.group(1)
                else:
                    age_match = re.search(r'\b(\d{1,2})\+\b', page_text)
                    if age_match:
                        result['content_rating'] = age_match.group(0)
            
            # Extract downloads and revenue - use specific element IDs
            try:
                metrics_js = page.evaluate("""
                    () => {
                        const results = { downloads: null, revenue: null };
                        
                        // Extract Downloads using specific ID
                        const downloadsElem = document.getElementById('app-overview-unified-kpi-downloads');
                        if (downloadsElem) {
                            // Find the span with the value (sibling or parent's child)
                            const downloadsCard = downloadsElem.closest('[data-test="app-overview-kpi-block"]');
                            if (downloadsCard) {
                                const valueSpan = downloadsCard.querySelector('span[aria-labelledby="app-overview-unified-kpi-downloads"]');
                                if (valueSpan) {
                                    results.downloads = valueSpan.textContent.trim();
                                }
                            }
                        }
                        
                        // Extract Revenue using specific ID
                        const revenueElem = document.getElementById('app-overview-unified-kpi-revenue');
                        if (revenueElem) {
                            const revenueCard = revenueElem.closest('[data-test="app-overview-kpi-block"]');
                            if (revenueCard) {
                                const valueSpan = revenueCard.querySelector('span[aria-labelledby="app-overview-unified-kpi-revenue"]');
                                if (valueSpan) {
                                    // Remove $ sign if present, keep the value
                                    const revenueText = valueSpan.textContent.trim();
                                    results.revenue = revenueText.replace(/^\\$/, '');
                                }
                            }
                        }
                        
                        return results;
                    }
                """)
                if metrics_js:
                    if metrics_js.get('downloads') and not result.get('downloads_worldwide'):
                        result['downloads_worldwide'] = metrics_js['downloads']
                    if metrics_js.get('revenue') and not result.get('revenue_worldwide'):
                        result['revenue_worldwide'] = metrics_js['revenue']
            except:
                pass
            
            # Fallback: regex search in text
            if not result['downloads_worldwide'] and page_text:
                downloads_pattern = re.compile(r'Downloads[:\s]+([^\n\r]+?)(?:\n|Worldwide|Last Month|$)', re.I)
                downloads_match = downloads_pattern.search(page_text)
                if downloads_match:
                    result['downloads_worldwide'] = downloads_match.group(1).strip()
                else:
                    download_num_pattern = re.compile(r'(\d+[KMB]?)\s*(?:downloads?|installs?)', re.I)
                    download_num_match = download_num_pattern.search(page_text)
                    if download_num_match:
                        result['downloads_worldwide'] = download_num_match.group(1)
            
            if not result['revenue_worldwide'] and page_text:
                revenue_pattern = re.compile(r'Revenue[:\s]+([^\n\r]+?)(?:\n|Worldwide|Last Month|$)', re.I)
                revenue_match = revenue_pattern.search(page_text)
                if revenue_match:
                    result['revenue_worldwide'] = revenue_match.group(1).strip()
                else:
                    revenue_num_pattern = re.compile(r'(\$?\d+[KMB]?)\s*(?:revenue|earnings)', re.I)
                    revenue_num_match = revenue_num_pattern.search(page_text)
                    if revenue_num_match:
                        result['revenue_worldwide'] = revenue_num_match.group(1)
            
            # Extract last updated - use JavaScript
            try:
                updated_js = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        
                        // Look for date patterns
                        const datePatterns = [
                            /(?:Last Updated|Updated|Release Date)[\\s:]+(\\d{4}[\\/-]\\d{1,2}[\\/-]\\d{1,2})/i,
                            /(\\d{4}[\\/-]\\d{1,2}[\\/-]\\d{1,2})/
                        ];
                        
                        for (const pattern of datePatterns) {
                            const match = bodyText.match(pattern);
                            if (match && match[1]) {
                                return match[1];
                            }
                        }
                        
                        return null;
                    }
                """)
                if updated_js:
                    result['last_updated'] = updated_js
            except:
                pass
            
            # Fallback: regex search
            if not result['last_updated'] and page_text:
                updated_pattern = re.compile(r'(?:Last Updated|Updated|Release Date)[:\s]+(\d{4}[/-]\d{1,2}[/-]\d{1,2})', re.I)
                updated_match = updated_pattern.search(page_text)
                if updated_match:
                    result['last_updated'] = updated_match.group(1)
                else:
                    date_pattern = re.compile(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}')
                    date_matches = date_pattern.findall(page_text)
                    if date_matches:
                        result['last_updated'] = date_matches[0]
            
            # Extract publisher country - use JavaScript
            try:
                pub_country_js = page.evaluate("""
                    () => {
                        const bodyText = document.body.innerText;
                        
                        // Look for publisher country pattern
                        const pattern = /Publisher Country[\\s:]+([^\\n\\r]+)/i;
                        const match = bodyText.match(pattern);
                        if (match && match[1]) {
                            return match[1].trim().split('\\n')[0].split('|')[0].trim();
                        }
                        
                        // Look for common countries near "publisher"
                        const countries = ['Taiwan', 'Philippines', 'Pakistan', 'United States', 'China', 'Japan', 'South Korea'];
                        for (const country of countries) {
                            const countryIndex = bodyText.toLowerCase().indexOf(country.toLowerCase());
                            const publisherIndex = bodyText.toLowerCase().indexOf('publisher');
                            if (countryIndex !== -1 && publisherIndex !== -1 && Math.abs(countryIndex - publisherIndex) < 200) {
                                return country;
                            }
                        }
                        
                        return null;
                    }
                """)
                if pub_country_js:
                    result['publisher_country'] = pub_country_js
            except:
                pass
            
            # Fallback: regex search
            if not result['publisher_country'] and page_text:
                pub_country_pattern = re.compile(r'Publisher Country[:\s]+([^\n\r]+)', re.I)
                pub_country_match = pub_country_pattern.search(page_text)
                if pub_country_match:
                    result['publisher_country'] = pub_country_match.group(1).strip().split('\n')[0].split('|')[0].strip()
                else:
                    for country in ['Taiwan', 'Philippines', 'Pakistan', 'United States', 'China']:
                        if country.lower() in page_text.lower() and 'publisher' in page_text.lower():
                            result['publisher_country'] = country
                            break
            
            # Extract in-app purchases - improved table extraction
            try:
                iap_data_js = page.evaluate("""
                    () => {
                        const reactRoot = document.getElementById('react-root');
                        if (!reactRoot) return [];
                        
                        const iapItems = [];
                        
                        // Find IAP table
                        const tables = reactRoot.querySelectorAll('table');
                        for (const table of tables) {
                            const tableText = table.innerText.toLowerCase();
                            if (tableText.includes('in-app purchase') || tableText.includes('iap') || 
                                tableText.includes('title') && tableText.includes('price')) {
                                
                                const rows = table.querySelectorAll('tr');
                                for (let i = 1; i < rows.length; i++) { // Skip header
                                    const cells = rows[i].querySelectorAll('td, th');
                                    if (cells.length >= 2) {
                                        const title = cells[0] ? cells[0].textContent.trim() : '';
                                        const duration = cells[1] ? cells[1].textContent.trim() : '';
                                        const price = cells[2] ? cells[2].textContent.trim() : '';
                                        
                                        if (title && title.toLowerCase() !== 'title' && 
                                            !title.toLowerCase().includes('duration') &&
                                            !title.toLowerCase().includes('price')) {
                                            iapItems.push({
                                                title: title,
                                                duration: duration || '',
                                                price: price || ''
                                            });
                                        }
                                    }
                                }
                                break;
                            }
                        }
                        
                        return iapItems;
                    }
                """)
                if iap_data_js and len(iap_data_js) > 0:
                    result['in_app_purchases'] = iap_data_js
            except:
                pass
            
            # Fallback: Try Playwright table extraction
            if not result['in_app_purchases']:
                try:
                    iap_tables = page.query_selector_all('table')
                    for table in iap_tables:
                        table_text = table.inner_text()
                        if 'purchase' in table_text.lower() or ('title' in table_text.lower() and 'price' in table_text.lower()):
                            rows = table.query_selector_all('tr')
                            for row in rows[1:]:  # Skip header
                                cells = row.query_selector_all('td, th')
                                if len(cells) >= 2:
                                    title = cells[0].inner_text().strip() if len(cells) > 0 else ''
                                    duration = cells[1].inner_text().strip() if len(cells) > 1 else ''
                                    price = cells[2].inner_text().strip() if len(cells) > 2 else ''
                                    
                                    # Skip header rows
                                    if title and title.lower() not in ['title', 'duration', 'price']:
                                        result['in_app_purchases'].append({
                                            'title': title,
                                            'duration': duration,
                                            'price': price
                                        })
                            if result['in_app_purchases']:
                                break
                except:
                    pass
            
            # Extract category ranking - use specific element ID
            try:
                ranking_js = page.evaluate("""
                    () => {
                        // Extract Category Ranking using specific ID
                        const rankingElem = document.getElementById('app-overview-unified-kpi-category-ranking');
                        if (rankingElem) {
                            const rankingCard = rankingElem.closest('[data-test="app-overview-kpi-block"]');
                            if (rankingCard) {
                                const valueSpan = rankingCard.querySelector('span[aria-labelledby="app-overview-unified-kpi-category-ranking"]');
                                if (valueSpan) {
                                    // Extract the ranking number (e.g., "#249")
                                    const rankingText = valueSpan.textContent.trim();
                                    const match = rankingText.match(/#(\\d+)/);
                                    if (match && match[1]) {
                                        return match[1];
                                    }
                                    // Also try to get the category info
                                    const categoryP = valueSpan.querySelector('p');
                                    if (categoryP) {
                                        const categoryInfo = categoryP.textContent.trim();
                                        // Return ranking with category if available
                                        if (match && match[1]) {
                                            return match[1] + ' (' + categoryInfo + ')';
                                        }
                                    }
                                }
                            }
                        }
                        
                        return null;
                    }
                """)
                if ranking_js:
                    result['category_ranking'] = ranking_js
            except:
                pass
            
            # Fix developer name extraction - avoid "Country:" text
            if result.get('developer_name') and ('country' in result['developer_name'].lower() or result['developer_name'].lower() == 'website'):
                result['developer_name'] = ''  # Clear incorrect value
                
            if not result.get('developer_name'):
                try:
                    dev_name_js = page.evaluate("""
                        () => {
                            const reactRoot = document.getElementById('react-root');
                            if (!reactRoot) return null;
                            
                            // Look for developer link text (not "Website" or "Country")
                            const devLinks = reactRoot.querySelectorAll('a[href*="publisher"], a[href*="developer"]');
                            for (const link of devLinks) {
                                const text = link.textContent.trim();
                                if (text && text.length < 200 && 
                                    text.toLowerCase() !== 'website' && 
                                    !text.toLowerCase().includes('country') &&
                                    !text.toLowerCase().includes('sensortower')) {
                                    return text;
                                }
                            }
                            
                            // Look for developer pattern in text
                            const reactText = reactRoot.innerText;
                            const devPattern = /(?:Developer|Publisher|By)[\\s:]+([^\\n\\r]+?)(?:\\n|Country|Website|$)/i;
                            const match = reactText.match(devPattern);
                            if (match && match[1]) {
                                const dev = match[1].trim().split('\\n')[0].split('|')[0].trim();
                                if (dev && !dev.toLowerCase().includes('country') && dev.toLowerCase() !== 'website') {
                                    return dev;
                                }
                            }
                            
                            return null;
                        }
                    """)
                    if dev_name_js:
                        result['developer_name'] = dev_name_js
                except:
                    pass
            
            # Fix top countries - avoid "/ Regions" label
            if result.get('top_countries') and ('/ regions' in result['top_countries'].lower() or result['top_countries'].strip() == '/ Regions'):
                result['top_countries'] = ''  # Clear incorrect value
                
            if not result.get('top_countries'):
                try:
                    countries_js = page.evaluate("""
                        () => {
                            const reactRoot = document.getElementById('react-root');
                            if (!reactRoot) return null;
                            
                            const reactText = reactRoot.innerText;
                            
                            // Look for "Top Countries" section
                            const topCountriesMatch = reactText.match(/Top Countries[\\s:]+([^\\n\\r]+?)(?:\\n|Regions|$)/i);
                            if (topCountriesMatch && topCountriesMatch[1]) {
                                const countries = topCountriesMatch[1].trim();
                                if (countries && !countries.includes('/ Regions') && countries.length < 200) {
                                    return countries;
                                }
                            }
                            
                            // Look for country flags/names after "Top Countries"
                            const countries = ['Taiwan', 'Philippines', 'Pakistan', 'United States', 'China', 'Japan', 'US'];
                            const found = [];
                            const topCountriesIndex = reactText.toLowerCase().indexOf('top countries');
                            if (topCountriesIndex !== -1) {
                                const section = reactText.substring(topCountriesIndex, topCountriesIndex + 500);
                                for (const country of countries) {
                                    if (section.toLowerCase().includes(country.toLowerCase())) {
                                        found.push(country);
                                    }
                                }
                                if (found.length > 0) {
                                    return found.join(', ');
                                }
                            }
                            
                            return null;
                        }
                    """)
                    if countries_js:
                        result['top_countries'] = countries_js
                except:
                    pass
            
            browser.close()
            
            # Automatically fetch Apple App Store ratings if we have an app_id
            # Fetch ratings even if SensorTower scraping had errors (ratings are independent)
            if result.get('app_id'):
                try:
                    apple_url = f"{APPLE_STORE_BASE_URL}/us/app/id{result['app_id']}"
                    print(f"Fetching Apple App Store ratings from: {apple_url}")
                    apple_data = scrape_apple_app_store(apple_url, headless=headless, timeout=30000)
                    
                    # Always try to add rating data if it exists, regardless of error status
                    # (Some apps might have ratings even if other data extraction failed)
                    rating_added = False
                    if apple_data.get('average_rating'):
                        result['average_rating'] = apple_data['average_rating']
                        rating_added = True
                    if apple_data.get('rating_count'):
                        result['rating_count'] = apple_data['rating_count']
                        rating_added = True
                    
                    # Add release date if available
                    if apple_data.get('release_date'):
                        result['release_date'] = apple_data['release_date']
                    
                    if rating_added:
                        release_info = f" | Released: {apple_data.get('release_date', 'N/A')}" if apple_data.get('release_date') else ""
                        print(f"✅ Added ratings: {result.get('average_rating', 'N/A')} ⭐ ({result.get('rating_count', 'N/A')} ratings){release_info}")
                    elif apple_data.get('error'):
                        print(f"⚠️ Could not fetch Apple Store ratings: {apple_data.get('error', 'Unknown error')}")
                    else:
                        print(f"⚠️ No rating data found on Apple App Store page")
                except Exception as e:
                    print(f"⚠️ Error fetching Apple Store ratings: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the whole scrape if rating fetch fails
            
            return result
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error during scraping: {error_msg}")
        result['error'] = error_msg
        if browser:
            try:
                browser.close()
            except:
                pass
        return result


def search_apps_by_category(category: str, headless: bool = True) -> List[Dict]:
    """
    Search for apps by category (if this functionality is available on SensorTower).
    
    Args:
        category: Category name (e.g., "Productivity", "Education")
        headless: Whether to run browser in headless mode
        
    Returns:
        List of app data dictionaries
    """
    results = []
    
    with sync_playwright() as p:
        try:
            launch_args = []
            if headless:
                launch_args.extend([
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ])
            
            browser = p.chromium.launch(
                headless=headless,
                args=launch_args if launch_args else None
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080},
                permissions=['geolocation'],
                java_script_enabled=True
            )
            page = context.new_page()
            
            # Navigate to category page
            category_url = f"{SENSORTOWER_BASE_URL}/apps/ios/category/{category.lower()}"
            page.goto(category_url, wait_until="networkidle")
            time.sleep(3)
            
            # Extract app links from the category page
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            app_links = soup.find_all('a', href=re.compile(r'/apps/ios/app/'))
            
            # Limit to first 10 results to avoid overwhelming
            for link in app_links[:10]:
                app_path = link.get('href', '')
                if app_path:
                    app_url = f"{SENSORTOWER_BASE_URL}{app_path}" if not app_path.startswith('http') else app_path
                    # Extract app name from link text or URL
                    app_name = link.get_text(strip=True) or app_path.split('/')[-1]
                    # Scrape individual app data
                    app_data = scrape_app_data(app_name, headless=headless)
                    if app_data.get('app_name'):
                        results.append(app_data)
            
            browser.close()
        except Exception as e:
            print(f"Error searching by category: {e}")
            if 'browser' in locals():
                browser.close()
    
    return results

