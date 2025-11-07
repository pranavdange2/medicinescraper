"""
Simple Medicine Price Scraper with HTML Frontend
Just adds a web UI to the working scraper logic
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re

app = Flask(__name__)
CORS(app)

# Simple HTML Frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medicine Price Scraper</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .search-box {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 25px;
        }
        .search-form { display: flex; gap: 10px; }
        .search-input {
            flex: 1;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
        }
        .search-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .search-btn {
            padding: 12px 30px;
            font-size: 16px;
            font-weight: 600;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .search-btn:hover { background: #5568d3; }
        .search-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .loading {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 15px;
            color: #666;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .results { display: grid; gap: 15px; }
        .result-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .result-card.best {
            border: 3px solid #28a745;
            background: #f0fff4;
        }
        .pharmacy { font-size: 20px; font-weight: bold; color: #333; }
        .medicine { color: #666; font-size: 14px; margin-top: 5px; }
        .price { font-size: 28px; font-weight: bold; color: #667eea; }
        .best-badge {
            background: #28a745;
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        .visit-btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }
        .visit-btn:hover { background: #5568d3; }
        .no-results {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 15px;
        }
        .savings {
            background: #28a745;
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 15px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💊 Medicine Price Scraper</h1>
            <p>Compare prices from top Indian pharmacies</p>
        </div>

        <div class="search-box">
            <div class="search-form">
                <input 
                    type="text" 
                    id="medicineInput" 
                    class="search-input" 
                    placeholder="Enter medicine name (e.g., paracetamol 500mg)"
                    onkeypress="if(event.key==='Enter') searchMedicine()"
                >
                <button class="search-btn" onclick="searchMedicine()" id="searchBtn">
                    Search
                </button>
            </div>
        </div>

        <div id="resultsContainer"></div>
    </div>

    <script>
        async function searchMedicine() {
            const input = document.getElementById('medicineInput');
            const medicine = input.value.trim();
            
            if (!medicine) {
                alert('Please enter a medicine name');
                return;
            }

            const searchBtn = document.getElementById('searchBtn');
            const resultsContainer = document.getElementById('resultsContainer');

            searchBtn.disabled = true;
            searchBtn.textContent = 'Searching...';
            
            resultsContainer.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Scraping pharmacies... This may take a few seconds</p>
                </div>
            `;

            try {
                const response = await fetch('/api/search?medicine=' + encodeURIComponent(medicine));
                const data = await response.json();

                if (data.error) {
                    resultsContainer.innerHTML = `
                        <div class="no-results">
                            <h2>❌ Error</h2>
                            <p>${data.error}</p>
                        </div>
                    `;
                } else {
                    // Show all results including not found ones
                    const allSites = ['Netmeds', '1mg', 'Apollo Pharmacy', 'PharmEasy'];
                    const foundPrices = data.results.map(r => r.price).filter(p => p);
                    const minPrice = foundPrices.length > 0 ? Math.min(...foundPrices) : 0;
                    const maxPrice = foundPrices.length > 0 ? Math.max(...foundPrices) : 0;
                    const savings = maxPrice - minPrice;

                    let html = '';
                    
                    if (savings > 0) {
                        html += `
                            <div class="savings">
                                💰 Save ₹${savings.toFixed(2)} by choosing the best price!
                            </div>
                        `;
                    }

                    html += '<div class="results">';
                    
                    // First show all found results
                    data.results.forEach((result, index) => {
                        const isBest = result.price === minPrice;
                        html += `
                            <div class="result-card ${isBest ? 'best' : ''}">
                                <div>
                                    <div class="pharmacy">
                                        ${result.pharmacy}
                                        ${isBest ? '<span class="best-badge">⭐ BEST</span>' : ''}
                                    </div>
                                    <div class="medicine">${result.medicine}</div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 20px;">
                                    <div class="price">₹${result.price.toFixed(2)}</div>
                                    <a href="${result.url}" target="_blank" class="visit-btn">Visit</a>
                                </div>
                            </div>
                        `;
                    });
                    
                    // Then show sites that didn't return results
                    const foundSites = data.results.map(r => r.pharmacy);
                    const notFoundSites = allSites.filter(site => !foundSites.includes(site));
                    
                    notFoundSites.forEach(site => {
                        html += `
                            <div class="result-card" style="opacity: 0.6;">
                                <div>
                                    <div class="pharmacy">${site}</div>
                                    <div class="medicine" style="color: #999;">Not found or unavailable</div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 20px;">
                                    <div class="price" style="color: #999;">-</div>
                                    <button class="visit-btn" disabled style="opacity: 0.5; cursor: not-allowed;">N/A</button>
                                </div>
                            </div>
                        `;
                    });
                    
                    html += '</div>';

                    resultsContainer.innerHTML = html;
                }
            } catch (error) {
                resultsContainer.innerHTML = `
                    <div class="no-results">
                        <h2>❌ Connection Error</h2>
                        <p>Could not connect to server. Make sure Flask is running.</p>
                    </div>
                `;
            } finally {
                searchBtn.disabled = false;
                searchBtn.textContent = 'Search';
            }
        }
    </script>
</body>
</html>
"""

# Original working scraper functions
def get_driver():
    """Setup Selenium driver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def clean_price(text):
    """Extract price from text"""
    if not text:
        return None
    text = text.replace(',', '').replace('₹', '').replace('Rs', '').strip()
    match = re.search(r'\d+\.?\d*', text)
    return float(match.group()) if match else None

def scrape_netmeds(medicine):
    """Scrape Netmeds"""
    driver = None
    try:
        driver = get_driver()
        url = f"https://www.netmeds.com/catalogsearch/result/{medicine.replace(' ', '-')}/all"
        driver.get(url)
        time.sleep(4)
        
        # Try multiple methods
        # Method 1: BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Look for price pattern in entire page
        price_matches = re.findall(r'₹\s*(\d+\.?\d*)', page_text)
        if price_matches:
            # Get first reasonable price (between 1 and 10000)
            for price_str in price_matches:
                price = float(price_str)
                if 1 <= price <= 10000:
                    # Try to find medicine name
                    name_elem = soup.find(['h2', 'h3', 'a', 'span'], string=re.compile(medicine, re.I))
                    name = name_elem.text.strip()[:80] if name_elem else medicine
                    
                    driver.quit()
                    return {
                        'pharmacy': 'Netmeds',
                        'medicine': name,
                        'price': price,
                        'url': url
                    }
        
        # Method 2: Try Selenium elements
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '₹')]")
            for elem in elements[:10]:
                text = elem.text
                price_match = re.search(r'₹\s*(\d+\.?\d*)', text)
                if price_match:
                    price = float(price_match.group(1))
                    if 1 <= price <= 10000:
                        driver.quit()
                        return {
                            'pharmacy': 'Netmeds',
                            'medicine': medicine,
                            'price': price,
                            'url': url
                        }
        except:
            pass
        
        driver.quit()
        return None
    except Exception as e:
        if driver:
            driver.quit()
        print(f"Netmeds error: {str(e)[:100]}")
        return None

def scrape_apollo(medicine):
    """Scrape Apollo Pharmacy"""
    driver = None
    try:
        driver = get_driver()
        url = f"https://www.apollopharmacy.in/search-medicines/{medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(4)
        
        # Method 1: Find any element with rupee symbol
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '₹')]")
            for elem in elements[:15]:
                text = elem.text
                if len(text) > 5 and '₹' in text:
                    price_match = re.search(r'₹\s*(\d+\.?\d*)', text)
                    if price_match:
                        price = float(price_match.group(1))
                        if 1 <= price <= 10000:
                            name = text.split('\n')[0][:80] if '\n' in text else medicine
                            driver.quit()
                            return {
                                'pharmacy': 'Apollo Pharmacy',
                                'medicine': name,
                                'price': price,
                                'url': url
                            }
        except:
            pass
        
        # Method 2: Parse entire page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text()
        price_matches = re.findall(r'₹\s*(\d+\.?\d*)', page_text)
        
        if price_matches:
            for price_str in price_matches:
                price = float(price_str)
                if 1 <= price <= 10000:
                    driver.quit()
                    return {
                        'pharmacy': 'Apollo Pharmacy',
                        'medicine': medicine,
                        'price': price,
                        'url': url
                    }
        
        driver.quit()
        return None
    except Exception as e:
        if driver:
            driver.quit()
        print(f"Apollo error: {str(e)[:100]}")
        return None

def scrape_pharmeasy(medicine):
    """Scrape PharmEasy"""
    driver = None
    try:
        driver = get_driver()
        url = f"https://pharmeasy.in/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        # Scroll to load content
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        # Method 1: Look for any element with price
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '₹')]")
            for elem in elements[:15]:
                text = elem.text
                if len(text) > 5 and '₹' in text:
                    price_match = re.search(r'₹\s*(\d+\.?\d*)', text)
                    if price_match:
                        price = float(price_match.group(1))
                        if 1 <= price <= 10000:
                            name = text.split('\n')[0][:80] if '\n' in text else medicine
                            driver.quit()
                            return {
                                'pharmacy': 'PharmEasy',
                                'medicine': name,
                                'price': price,
                                'url': url
                            }
        except:
            pass
        
        # Method 2: Parse entire page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text()
        price_matches = re.findall(r'₹\s*(\d+\.?\d*)', page_text)
        
        if price_matches:
            for price_str in price_matches:
                price = float(price_str)
                if 1 <= price <= 10000:
                    driver.quit()
                    return {
                        'pharmacy': 'PharmEasy',
                        'medicine': medicine,
                        'price': price,
                        'url': url
                    }
        
        driver.quit()
        return None
    except Exception as e:
        if driver:
            driver.quit()
        print(f"PharmEasy error: {str(e)[:100]}")
        return None

def scrape_1mg(medicine):
    """Scrape 1mg"""
    driver = None
    try:
        driver = get_driver()
        url = f"https://www.1mg.com/search/all?name={medicine.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(5)
        
        # Scroll to load content
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)
        
        # Method 1: Find elements with price
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '₹')]")
            for elem in elements[:20]:
                text = elem.text
                if len(text) > 5 and '₹' in text:
                    price_match = re.search(r'₹\s*(\d+\.?\d*)', text)
                    if price_match:
                        price = float(price_match.group(1))
                        if 1 <= price <= 10000:
                            # Try to get medicine name
                            name_lines = text.split('\n')
                            name = name_lines[0][:80] if name_lines else medicine
                            
                            # Try to get URL
                            try:
                                parent = elem.find_element(By.XPATH, './ancestor::a')
                                link = parent.get_attribute('href')
                            except:
                                link = url
                            
                            driver.quit()
                            return {
                                'pharmacy': '1mg',
                                'medicine': name,
                                'price': price,
                                'url': link
                            }
        except:
            pass
        
        # Method 2: Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text()
        price_matches = re.findall(r'₹\s*(\d+\.?\d*)', page_text)
        
        if price_matches:
            for price_str in price_matches:
                price = float(price_str)
                if 1 <= price <= 10000:
                    driver.quit()
                    return {
                        'pharmacy': '1mg',
                        'medicine': medicine,
                        'price': price,
                        'url': url
                    }
        
        driver.quit()
        return None
    except Exception as e:
        if driver:
            driver.quit()
        print(f"1mg error: {str(e)[:100]}")
        return None

# Flask routes
@app.route('/')
def index():
    """Serve the main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search')
def search():
    """API endpoint for searching medicines"""
    medicine = request.args.get('medicine', '')
    
    if not medicine:
        return jsonify({'error': 'Medicine name is required'}), 400
    
    print(f"\n{'='*60}")
    print(f"Searching for: {medicine}")
    print(f"{'='*60}\n")
    
    results = []
    
    scrapers = [
        ('Netmeds', scrape_netmeds),
        ('1mg', scrape_1mg),
        ('Apollo', scrape_apollo),
        ('PharmEasy', scrape_pharmeasy),
    ]
    
    # Run in parallel for speed
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_scraper = {
            executor.submit(scraper_func, medicine): name 
            for name, scraper_func in scrapers
        }
        
        for future in as_completed(future_to_scraper):
            name = future_to_scraper[future]
            try:
                result = future.result(timeout=30)  # Increased timeout
                if result and result['price']:
                    results.append(result)
                    print(f"✓ {name}: ₹{result['price']:.2f}")
                else:
                    print(f"✗ {name}: Not found")
            except Exception as e:
                print(f"✗ {name}: Error - {str(e)[:50]}")
    
    results.sort(key=lambda x: x['price'])
    
    print(f"\nFound {len(results)} results\n")
    
    return jsonify({
        'medicine': medicine,
        'results': results
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🏥 MEDICINE PRICE SCRAPER - WEB VERSION")
    print("="*70)
    print("\n✅ Server starting...")
    print("📱 Open: http://localhost:5000")
    print("⏸️  Press Ctrl+C to stop\n")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
