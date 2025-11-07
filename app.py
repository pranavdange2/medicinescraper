from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re
import os

app = Flask(__name__)
CORS(app)

def get_driver():
    """Setup Selenium driver with Chrome binary for Render"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-gpu')
    options.add_argument('--single-process')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    chrome_path = os.environ.get('CHROME_BIN', '/usr/bin/chromium-browser')
    options.binary_location = chrome_path
    
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Chrome initialization failed: {e}")
        return None

def clean_price(text):
    """Extract price from text"""
    if not text:
        return None
    text = text.replace(',', '').replace('₹', '').replace('Rs', '').strip()
    match = re.search(r'\d+\.?\d*', text)
    return float(match.group()) if match else None

def scrape_netmeds(medicine):
    """Scrape Netmeds"""
    try:
        driver = get_driver()
        if not driver:
            return None
            
        url = f"https://www.netmeds.com/catalogsearch/result/{medicine.replace(' ', '-')}/all"
        driver.get(url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product = soup.find('div', {'class': lambda x: x and 'product' in str(x).lower()})
        
        if not product:
            driver.quit()
            return None
        
        price_text = product.get_text()
        price_match = re.search(r'₹\s*(\d+\.?\d*)', price_text)
        price = float(price_match.group(1)) if price_match else None
        
        name_elem = product.find(['h2', 'h3', 'a'])
        name = name_elem.text.strip()[:80] if name_elem else medicine
        
        link_elem = product.find('a', href=True)
        link = link_elem['href'] if link_elem else url
        if link and not link.startswith('http'):
            link = f"https://www.netmeds.com{link}"
        
        driver.quit()
        
        if not price:
            return None
        
        return {
            'pharmacy': 'Netmeds',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return None

def scrape_apollo(medicine):
    """Scrape Apollo Pharmacy"""
    try:
        driver = get_driver()
        if not driver:
            return None
            
        url = f"https://www.apollopharmacy.in/search-medicines/{medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(3)
        
        try:
            product = driver.find_element(By.CSS_SELECTOR, "div[class*='product']")
            product_text = product.text
        except:
            driver.quit()
            return None
        
        price_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', product_text)
        price = clean_price(price_match.group(1)) if price_match else None
        
        name = product_text.split('\n')[0][:80] if product_text else medicine
        
        try:
            link_elem = product.find_element(By.TAG_NAME, 'a')
            link = link_elem.get_attribute('href')
        except:
            link = url
        
        driver.quit()
        
        if not price:
            return None
        
        return {
            'pharmacy': 'Apollo Pharmacy',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return None

def scrape_pharmeasy(medicine):
    """Scrape PharmEasy"""
    try:
        driver = get_driver()
        if not driver:
            return None
            
        url = f"https://pharmeasy.in/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(3)
        
        try:
            product = driver.find_element(By.CSS_SELECTOR, "div[class*='product']")
            product_text = product.text
        except:
            driver.quit()
            return None
        
        price_match = re.search(r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)', product_text)
        price = clean_price(price_match.group(1)) if price_match else None
        
        name = product_text.split('\n')[0][:80] if product_text else medicine
        
        try:
            link_elem = product.find_element(By.TAG_NAME, 'a')
            link = link_elem.get_attribute('href')
        except:
            link = url
        
        driver.quit()
        
        if not price:
            return None
        
        return {
            'pharmacy': 'PharmEasy',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return None

def scrape_1mg(medicine):
    """Scrape 1mg"""
    try:
        driver = get_driver()
        if not driver:
            return None
            
        url = f"https://www.1mg.com/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(3)
        
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product = soup.find('div', {'class': lambda x: x and 'product' in str(x).lower()})
        
        if not product:
            driver.quit()
            return None
        
        product_text = product.get_text()
        price_match = re.search(r'₹\s*(\d+\.?\d*)', product_text)
        price = float(price_match.group(1)) if price_match else None
        
        lines = [l.strip() for l in product_text.split('\n') if l.strip()]
        name = lines[0][:80] if lines else medicine
        
        link_elem = product.find('a', href=True)
        link = link_elem['href'] if link_elem else url
        if link and not link.startswith('http'):
            link = f"https://www.1mg.com{link}"
        
        driver.quit()
        
        if not price:
            return None
        
        return {
            'pharmacy': '1mg',
            'medicine': name,
            'price': price,
            'url': link
        }
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return None

@app.route('/api/compare', methods=['POST'])
def compare_prices_api():
    """API endpoint to compare medicine prices"""
    try:
        data = request.get_json()
        medicine = data.get('medicine', '').strip()
        
        if not medicine or len(medicine) < 2:
            return jsonify({'error': 'Please enter a valid medicine name'}), 400
        
        results = []
        scrapers = [
            ('Netmeds', scrape_netmeds),
            ('1mg', scrape_1mg),
            ('Apollo', scrape_apollo),
            ('PharmEasy', scrape_pharmeasy),
        ]
        
        for name, scraper_func in scrapers:
            try:
                result = scraper_func(medicine)
                if result and result['price']:
                    results.append(result)
            except:
                pass
            time.sleep(2)
        
        if not results:
            return jsonify({'error': 'No results found. Try a generic name or check spelling.'}), 404
        
        results.sort(key=lambda x: x['price'] if x['price'] else float('inf'))
        
        # Calculate savings
        savings = None
        savings_percent = None
        if len(results) > 1:
            savings = round(results[-1]['price'] - results[0]['price'], 2)
            savings_percent = round((savings / results[-1]['price']) * 100, 1)
        
        return jsonify({
            'success': True,
            'results': results,
            'best_price': results[0]['price'],
            'pharmacy': results[0]['pharmacy'],
            'savings': savings,
            'savings_percent': savings_percent,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Medicine scraper API is running'})

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({'message': 'Medicine Price Comparison API', 'endpoints': {
        'POST /api/compare': 'Compare medicine prices',
        'GET /api/health': 'Health check'
    }})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
