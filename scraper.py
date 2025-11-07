"""
Robust Medicine Price Scraper
Works with current website structures
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

def get_driver():
    """Setup Selenium driver with auto-managed ChromeDriver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def clean_price(text):
    """Extract price from text"""
    if not text:
        return None
    # Remove currency symbols and commas, but keep decimal point
    text = text.replace(',', '').replace('₹', '').replace('Rs', '').strip()
    # Match number with optional decimal
    match = re.search(r'\d+\.?\d*', text)
    return float(match.group()) if match else None

def scrape_netmeds(medicine):
    """Scrape Netmeds using Selenium for better reliability"""
    try:
        driver = get_driver()
        url = f"https://www.netmeds.com/catalogsearch/result/{medicine.replace(' ', '-')}/all"
        driver.get(url)
        time.sleep(4)
        
        # Get page source
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Try to find any product container
        product = None
        selectors = [
            {'class': 'cat-product'},
            {'class': 'ais-InfiniteHits-item'},
            {'class': 'product-box'},
            {'data-sku': True}
        ]
        
        for selector in selectors:
            product = soup.find('div', selector)
            if product:
                break
        
        if not product:
            # Try with Selenium
            try:
                product_elem = driver.find_element(By.CSS_SELECTOR, "div[class*='product'], div[class*='cat-'], div[class*='item']")
                product_text = product_elem.text
                
                # Extract price from text
                price_match = re.search(r'₹\s*(\d+\.?\d*)', product_text)
                if price_match:
                    price = float(price_match.group(1))
                    name = product_text.split('\n')[0][:80]
                    
                    driver.quit()
                    return {
                        'pharmacy': 'Netmeds',
                        'medicine': name,
                        'price': price,
                        'url': url
                    }
            except:
                pass
            
            driver.quit()
            print("   No product found")
            return None
        
        # Find price in HTML
        price_elem = product.find('span', {'class': lambda x: x and 'price' in str(x).lower()})
        if not price_elem:
            # Search for any text with rupee symbol
            price_text = product.get_text()
            price_match = re.search(r'₹\s*(\d+\.?\d*)', price_text)
            price = float(price_match.group(1)) if price_match else None
        else:
            price = clean_price(price_elem.text)
        
        # Find name
        name_elem = product.find(['h2', 'h3', 'a'])
        name = name_elem.text.strip()[:80] if name_elem else medicine
        
        # Find link
        link_elem = product.find('a', href=True)
        link = link_elem['href']
        if not link.startswith('http'):
            link = f"https://www.netmeds.com{link}"
        
        driver.quit()
        
        if not price:
            print("   Could not find price")
            return None
        
        return {
            'pharmacy': 'Netmeds',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        print(f"   Error: {str(e)[:100]}")
        return None

def scrape_apollo(medicine):
    """Scrape Apollo Pharmacy"""
    try:
        driver = get_driver()
        url = f"https://www.apollopharmacy.in/search-medicines/{medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(4)
        
        # Save page source for debugging
        page_source = driver.page_source
        
        # Try to find products with multiple selectors
        selectors = [
            "div[class*='ProductCard']",
            "div[class*='product']",
            "div[class*='medicine']",
            "a[href*='/otc/']",
            "div[data-qa='product']"
        ]
        
        product = None
        for selector in selectors:
            try:
                product = driver.find_element(By.CSS_SELECTOR, selector)
                if product:
                    break
            except:
                continue
        
        if not product:
            driver.quit()
            print("   No products found")
            return None
        
        # Get all text from product element
        product_text = product.text
        
        # Find price with regex
        price_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', product_text)
        price = clean_price(price_match.group(1)) if price_match else None
        
        # Get name (first line usually)
        name = product_text.split('\n')[0][:80] if product_text else medicine
        
        # Get URL
        try:
            link_elem = product.find_element(By.TAG_NAME, 'a')
            link = link_elem.get_attribute('href')
        except:
            link = url
        
        driver.quit()
        
        if not price:
            print("   Could not extract price")
            return None
        
        return {
            'pharmacy': 'Apollo Pharmacy',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        print(f"   Error: {str(e)[:100]}")
        return None

def scrape_pharmeasy(medicine):
    """Scrape PharmEasy"""
    try:
        driver = get_driver()
        url = f"https://pharmeasy.in/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        # Try multiple approaches
        selectors = [
            "div[class*='ProductCard']",
            "div[class*='Search_medicineLists']",
            "div[class*='product']",
            "a[href*='/medicine/']"
        ]
        
        product = None
        for selector in selectors:
            try:
                products = driver.find_elements(By.CSS_SELECTOR, selector)
                if products:
                    product = products[0]
                    break
            except:
                continue
        
        if not product:
            driver.quit()
            print("   No products found")
            return None
        
        # Extract all text
        product_text = product.text
        
        # Find price
        price_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', product_text)
        price = clean_price(price_match.group(1)) if price_match else None
        
        # Get name
        name = product_text.split('\n')[0][:80] if product_text else medicine
        
        # Get URL
        try:
            link_elem = product.find_element(By.TAG_NAME, 'a')
            link = link_elem.get_attribute('href')
        except:
            link = url
        
        driver.quit()
        
        if not price:
            print("   Could not extract price")
            return None
        
        return {
            'pharmacy': 'PharmEasy',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        print(f"   Error: {str(e)[:100]}")
        return None

def scrape_1mg(medicine):
    """Scrape 1mg (more reliable than Flipkart)"""
    try:
        driver = get_driver()
        url = f"https://www.1mg.com/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        # Wait for content to load and scroll
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        # Get page HTML
        page_html = driver.page_source
        
        # Try with BeautifulSoup first
        soup = BeautifulSoup(page_html, 'html.parser')
        
        # Find any div that might be a product
        products = soup.find_all('div', {'class': lambda x: x and ('product' in str(x).lower() or 'card' in str(x).lower())})
        
        if not products:
            # Try direct Selenium approach
            try:
                # Look for any link with price
                all_links = driver.find_elements(By.TAG_NAME, 'a')
                for link in all_links[:20]:  # Check first 20 links
                    link_text = link.text
                    if '₹' in link_text and len(link_text) > 10:
                        price_match = re.search(r'₹\s*(\d+\.?\d*)', link_text)
                        if price_match:
                            price = float(price_match.group(1))
                            name = link_text.split('\n')[0][:80]
                            link_url = link.get_attribute('href')
                            
                            driver.quit()
                            return {
                                'pharmacy': '1mg',
                                'medicine': name,
                                'price': price,
                                'url': link_url if link_url else url
                            }
            except:
                pass
            
            driver.quit()
            print("   No products found")
            return None
        
        # Parse first product
        product = products[0]
        product_text = product.get_text()
        
        # Find price
        price_match = re.search(r'₹\s*(\d+\.?\d*)', product_text)
        price = float(price_match.group(1)) if price_match else None
        
        # Get name (first line)
        lines = [l.strip() for l in product_text.split('\n') if l.strip()]
        name = lines[0][:80] if lines else medicine
        
        # Get URL
        link_elem = product.find('a', href=True)
        if link_elem:
            link = link_elem['href']
            if not link.startswith('http'):
                link = f"https://www.1mg.com{link}"
        else:
            link = url
        
        driver.quit()
        
        if not price:
            print("   Could not extract price")
            return None
        
        return {
            'pharmacy': '1mg',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        print(f"   Error: {str(e)[:100]}")
        return None

def compare_prices(medicine_name):
    """Main function to compare prices"""
    print(f"\n{'='*70}")
    print(f"Searching for: {medicine_name}")
    print(f"{'='*70}\n")
    
    results = []
    
    # List of scrapers to try
    scrapers = [
        ('Netmeds', scrape_netmeds),
        ('1mg', scrape_1mg),
        ('Apollo', scrape_apollo),
        ('PharmEasy', scrape_pharmeasy),
    ]
    
    for name, scraper_func in scrapers:
        print(f"Checking {name}...", end=' ')
        try:
            result = scraper_func(medicine_name)
            if result and result['price']:
                results.append(result)
                print(f"✓ Found: ₹{result['price']:.2f}")
            else:
                print("✗ Not found")
        except Exception as e:
            print(f"✗ Failed")
        
        time.sleep(3)  # Delay between requests
    
    # Sort by price
    results.sort(key=lambda x: x['price'] if x['price'] else float('inf'))
    
    # Display results
    print(f"\n{'='*70}")
    print(f"RESULTS ({len(results)} found)")
    print(f"{'='*70}\n")
    
    if not results:
        print("❌ No results found.")
        print("\nTips:")
        print("- Try the generic name (e.g., 'paracetamol' instead of brand)")
        print("- Include dosage (e.g., 'paracetamol 500mg')")
        print("- Check spelling")
        return
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['pharmacy']}")
        print(f"   Medicine: {result['medicine']}")
        print(f"   Price: ₹{result['price']:.2f}")
        print(f"   URL: {result['url']}")
        if i == 1:
            print(f"   ⭐ BEST PRICE")
        print()
    
    # Calculate savings
    if len(results) > 1:
        savings = results[-1]['price'] - results[0]['price']
        savings_pct = (savings / results[-1]['price']) * 100
        print(f"💰 Save ₹{savings:.2f} ({savings_pct:.1f}%) by choosing {results[0]['pharmacy']}!")

if __name__ == "__main__":
    print("\n🏥 Medicine Price Comparison Tool")
    print("="*70)
    
    medicine = input("\nEnter medicine name: ").strip()
    
    if medicine:
        compare_prices(medicine)
    else:
        print("❌ Please enter a valid medicine name!")
    
    input("\nPress Enter to exit...")