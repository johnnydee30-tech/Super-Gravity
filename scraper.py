import re
from proxy_manager import ProxyManager
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    from playwright_stealth.stealth import stealth_sync
import time
import random
import logging

def extract_model(title, brand):
    if not brand or brand == "N/A":
        return "N/A"
    
    # Find brand in title (case-insensitive)
    brand_match = re.search(re.escape(brand), title, re.IGNORECASE)
    if not brand_match:
        return "N/A"
    
    # Get text after brand
    after_brand = title[brand_match.end():].strip()
    
    # List of keywords that likely start the specs section
    spec_keywords = [
        r"DDR\d", r"\d+\s*GB", r"\d+\s*MHz", r"\d+\s*MT/s", r"CL\d+", 
        r"PC\d", r"DIMM", r"SODIMM", r"UDIMM", r"RDIMM", r"ECC", 
        r"Kit", r"288-Pin", r"262-Pin", r"x\d", r"\("
    ]
    
    # Create a regex to find the first occurrence of any spec keyword
    spec_regex = "|".join(spec_keywords)
    spec_match = re.search(spec_regex, after_brand, re.IGNORECASE)
    
    if spec_match:
        model = after_brand[:spec_match.start()].strip()
    else:
        # If no specs found, take the first 3-4 words as a fallback
        words = after_brand.split()
        model = " ".join(words[:4])
        
    # Clean up trailing punctuation
    model = model.strip(" -,.|")
    
    return model if model else "N/A"

class AmazonScraper:
    def __init__(self, headless=True, use_proxy=True):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def parse_specs(self, title):
        specs = {
            "Brand": "N/A",
            "Model": "N/A",
            "Capacity": "N/A",
            "Speed": "N/A",
            "CL_Timing": "N/A",
            "Voltage": "N/A",
            "XMP_Support": "No",
            "EXPO_Support": "No",
            "RGB": "No"
        }
        
        if not title or title == "N/A":
            return specs

        # Brand (Common RAM brands)
        brands = ["Corsair", "G.Skill", "Kingston", "Crucial", "TeamGroup", "Patriot", "ADATA", "Samsung", "Hynix", "Micron", "GeIL", "Mushkin", "KLEVV", "Lexar", "Silicon Power", "V-Color", "Acer", "HP", "Dell", "Lenovo", "Asus", "MSI", "Gigabyte"]
        for brand in brands:
            if brand.lower() in title.lower():
                specs["Brand"] = brand
                break
        
        # Model
        specs["Model"] = extract_model(title, specs["Brand"])
        
        # Capacity
        cap_match = re.search(r'(\d+\s*GB\s*x\s*\d+|\d+\s*GB)', title, re.IGNORECASE)
        if cap_match:
            specs["Capacity"] = cap_match.group(0)

        # Speed
        speed_match = re.search(r'(\d+\s*MHz|\d+\s*MT/s)', title, re.IGNORECASE)
        if speed_match:
            specs["Speed"] = speed_match.group(0)

        # CL Timing
        cl_match = re.search(r'(CL\s*\d+|C\d+)', title, re.IGNORECASE)
        if cl_match:
            specs["CL_Timing"] = cl_match.group(0).replace(" ", "")

        # Voltage
        volt_match = re.search(r'(\d+\.\d+\s*V)', title, re.IGNORECASE)
        if volt_match:
            specs["Voltage"] = volt_match.group(0)

        # Features
        if "XMP" in title.upper():
            specs["XMP_Support"] = "Yes"
        if "EXPO" in title.upper():
            specs["EXPO_Support"] = "Yes"
        if "RGB" in title.upper():
            specs["RGB"] = "Yes"
            
        return specs

    def validate_item(self, item, keyword):
        """
        Validates if the item matches the search keyword strictly.
        Returns True if the item is valid, False otherwise.
        """
        title = item.get("Title", "").upper()
        keyword_upper = keyword.upper()
        
        # Strict DDR generation filtering
        if "DDR5" in keyword_upper and "DDR4" in title:
            return False
        if "DDR4" in keyword_upper and "DDR5" in title:
            return False
            
        return True

    def scrape_search_results(self, keyword, max_pages=1):
        results = []
        
        with sync_playwright() as p:
            proxy = None
            if self.use_proxy:
                proxy = self.proxy_manager.get_random_proxy()
            
            browser_args = {}
            if proxy:
                self.logger.info(f"Using proxy: {proxy}")
                browser_args['proxy'] = {"server": proxy}
            
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US'
            )
            
            # Force USD currency via cookies
            context.add_cookies([
                {'name': 'lc-main', 'value': 'en_US', 'domain': '.amazon.com', 'path': '/'},
                {'name': 'i18n-prefs', 'value': 'USD', 'domain': '.amazon.com', 'path': '/'}
            ])
            
            stealth_sync(context)
            
            page = context.new_page()
            
            try:
                self.logger.info("Navigating to Amazon...")
                # Reduced timeout to 30 seconds to fail fast on bad proxies
                page.goto("https://www.amazon.com/?currency=USD", timeout=30000)
                time.sleep(random.uniform(2, 5))
                
                # ... (search logic)
                self.logger.info(f"Searching for: {keyword}")
                search_box = page.locator("input[id='twotabsearchtextbox']")
                search_box.fill(keyword)
                time.sleep(random.uniform(1, 2))
                search_box.press("Enter")
                time.sleep(random.uniform(3, 6))
                
                for current_page in range(1, max_pages + 1):
                    self.logger.info(f"Scraping page {current_page}...")
                    
                    # Wait for results to load
                    try:
                        page.wait_for_selector("div[data-component-type='s-search-result']", timeout=15000)
                    except:
                        self.logger.warning("Timeout waiting for search results. Maybe no more results or blocked.")
                        break

                    product_cards = page.locator("div[data-component-type='s-search-result']").all()
                    self.logger.info(f"Found {len(product_cards)} cards on page {current_page}")
                    
                    page_results = 0
                    for card in product_cards:
                        try:
                            # Improved Title Selector
                            title_el = card.locator("h2 a span")
                            link_el = card.locator("h2 a").first
                            
                            if title_el.count() == 0:
                                title_el = card.locator("h2 a")
                            if title_el.count() == 0:
                                title_el = card.locator("h2")
                            
                            # Price
                            price_el = card.locator(".a-price .a-offscreen").first
                            rating_el = card.locator("span[aria-label*='out of 5 stars']")
                            
                            title = title_el.inner_text().strip() if title_el.count() > 0 else "N/A"
                            price = price_el.inner_text().strip() if price_el.count() > 0 else "N/A"
                            rating = rating_el.get_attribute("aria-label") if rating_el.count() > 0 else "N/A"
                            
                            link = "N/A"
                            try:
                                if link_el.count() > 0:
                                    href = link_el.get_attribute("href")
                                    if href:
                                        if href.startswith("http"):
                                            link = href
                                        else:
                                            link = f"https://www.amazon.com{href}"
                                else:
                                    # Try finding any link in the card
                                    any_link = card.locator("a.a-link-normal").first
                                    if any_link.count() > 0:
                                        href = any_link.get_attribute("href")
                                        if href:
                                            if href.startswith("http"):
                                                link = href
                                            else:
                                                link = f"https://www.amazon.com{href}"
                            except Exception:
                                pass
                            
                            # Parse detailed specs
                            specs = self.parse_specs(title)
                            
                            item = {
                                **specs,
                                "Title": title,
                                "Price": price,
                                "Rating": rating,
                                "Product Link": link
                            }
                            
                            # Validate Item
                            if self.validate_item(item, keyword):
                                results.append(item)
                                page_results += 1
                            else:
                                # self.logger.info(f"Filtered out irrelevant item: {title}")
                                pass

                        except Exception as e:
                            continue
                    
                    self.logger.info(f"Added {page_results} valid items from page {current_page}. Total: {len(results)}")

                    if current_page < max_pages:
                        self.logger.info("Checking for next page button...")
                        next_button = page.locator("a.s-pagination-next")
                        
                        if next_button.count() > 0:
                            classes = next_button.get_attribute("class") or ""
                            if "s-pagination-disabled" not in classes:
                                self.logger.info("Clicking next page...")
                                
                                # Get current URL to verify navigation later
                                old_url = page.url
                                
                                next_button.click()
                                
                                # Robust wait for navigation
                                try:
                                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                                    # Wait for URL to change or a short sleep if URL parameters change
                                    time.sleep(random.uniform(4, 8))
                                    
                                    # Check if we actually moved
                                    if page.url == old_url:
                                        self.logger.warning("URL did not change after clicking next. Retrying or stopping.")
                                        # Optional: Try clicking again or break
                                        break
                                        
                                except Exception as e:
                                    self.logger.warning(f"Error waiting for next page: {e}")
                                    break
                            else:
                                self.logger.info("Next button is disabled. Stopping.")
                                break
                        else:
                            self.logger.info("Next button not found. Stopping.")
                            break
                            
            except Exception as e:
                self.logger.error(f"An error occurred: {e}")
                try:
                    page.screenshot(path="error_screenshot.png")
                    self.logger.info("Screenshot saved to error_screenshot.png")
                except:
                    pass
            finally:
                browser.close()
                
        return results

class NeweggScraper:
    def __init__(self, headless=True, use_proxy=True):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def parse_specs(self, title):
        specs = {
            "Brand": "N/A",
            "Model": "N/A",
            "Capacity": "N/A",
            "Speed": "N/A",
            "CL_Timing": "N/A",
            "Voltage": "N/A",
            "XMP_Support": "No",
            "EXPO_Support": "No",
            "RGB": "No"
        }
        
        if not title or title == "N/A":
            return specs

        # Brand (Common RAM brands - same list)
        brands = ["Corsair", "G.Skill", "Kingston", "Crucial", "TeamGroup", "Patriot", "ADATA", "Samsung", "Hynix", "Micron", "GeIL", "Mushkin", "KLEVV", "Lexar", "Silicon Power", "V-Color", "Acer", "HP", "Dell", "Lenovo", "Asus", "MSI", "Gigabyte"]
        for brand in brands:
            if brand.lower() in title.lower():
                specs["Brand"] = brand
                break
        
        # Model
        specs["Model"] = extract_model(title, specs["Brand"])
        
        # Capacity
        cap_match = re.search(r'(\d+\s*GB\s*x\s*\d+|\d+\s*GB)', title, re.IGNORECASE)
        if cap_match:
            specs["Capacity"] = cap_match.group(0)

        # Speed
        speed_match = re.search(r'(\d+\s*MHz|\d+\s*MT/s)', title, re.IGNORECASE)
        if speed_match:
            specs["Speed"] = speed_match.group(0)

        # CL Timing
        cl_match = re.search(r'(CL\s*\d+|C\d+)', title, re.IGNORECASE)
        if cl_match:
            specs["CL_Timing"] = cl_match.group(0).replace(" ", "")

        # Voltage
        volt_match = re.search(r'(\d+\.\d+\s*V)', title, re.IGNORECASE)
        if volt_match:
            specs["Voltage"] = volt_match.group(0)

        # Features
        if "XMP" in title.upper():
            specs["XMP_Support"] = "Yes"
        if "EXPO" in title.upper():
            specs["EXPO_Support"] = "Yes"
        if "RGB" in title.upper():
            specs["RGB"] = "Yes"
            
        return specs

    def validate_item(self, item, keyword):
        """
        Validates if the item matches the search keyword strictly.
        Returns True if the item is valid, False otherwise.
        """
        title = item.get("Title", "").upper()
        keyword_upper = keyword.upper()
        
        # Strict DDR generation filtering
        if "DDR5" in keyword_upper and "DDR4" in title:
            return False
        if "DDR4" in keyword_upper and "DDR5" in title:
            return False
            
        return True

    def scrape_search_results(self, keyword, max_pages=1):
        results = []
        
        with sync_playwright() as p:
            proxy = None
            if self.use_proxy:
                proxy = self.proxy_manager.get_random_proxy()
            
            browser_args = {}
            if proxy:
                self.logger.info(f"Using proxy: {proxy}")
                browser_args['proxy'] = {"server": proxy}
            
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US'
            )
            
            stealth_sync(context)
            
            page = context.new_page()
            
            try:
                self.logger.info("Navigating to Newegg...")
                # Newegg search URL structure
                search_url = f"https://www.newegg.com/p/pl?d={keyword.replace(' ', '+')}"
                page.goto(search_url, timeout=60000)
                time.sleep(random.uniform(2, 5))
                
                for current_page in range(1, max_pages + 1):
                    self.logger.info(f"Scraping page {current_page}...")
                    
                    # Wait for results
                    try:
                        page.wait_for_selector("div.item-cell", timeout=15000)
                    except:
                        self.logger.warning("Timeout waiting for search results.")
                        break

                    # Scroll down to load lazy images/content
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)

                    product_cards = page.locator("div.item-cell").all()
                    self.logger.info(f"Found {len(product_cards)} cards on page {current_page}")
                    
                    page_results = 0
                    for card in product_cards:
                        try:
                            # Selectors based on inspection
                            title_el = card.locator("a.item-title")
                            price_strong_el = card.locator("li.price-current strong")
                            price_sup_el = card.locator("li.price-current sup")
                            rating_el = card.locator("a.item-rating")
                            
                            title = title_el.inner_text().strip() if title_el.count() > 0 else "N/A"
                            
                            price = "N/A"
                            if price_strong_el.count() > 0 and price_sup_el.count() > 0:
                                price = f"${price_strong_el.inner_text().strip()}{price_sup_el.inner_text().strip()}"
                            
                            rating = rating_el.get_attribute("title") if rating_el.count() > 0 else "N/A"
                            
                            link = "N/A"
                            if title_el.count() > 0:
                                href = title_el.get_attribute("href")
                                if href:
                                    link = href
                            
                            # Parse specs
                            specs = self.parse_specs(title)
                            
                            item = {
                                **specs,
                                "Title": title,
                                "Price": price,
                                "Rating": rating,
                                "Product Link": link
                            }
                            
                            # Validate Item
                            if self.validate_item(item, keyword):
                                results.append(item)
                                page_results += 1
                            else:
                                pass

                        except Exception as e:
                            continue
                    
                    self.logger.info(f"Added {page_results} items from page {current_page}. Total: {len(results)}")

                    if current_page < max_pages:
                        # Pagination logic for Newegg
                        next_button = page.locator("button[title='Next']") # Check this selector if needed, usually it's a button or link
                        if next_button.count() == 0:
                             next_button = page.locator("a[title='Next']")

                        if next_button.count() > 0 and next_button.is_enabled():
                            self.logger.info("Clicking next page...")
                            next_button.click()
                            time.sleep(random.uniform(3, 6))
                        else:
                            self.logger.info("Next button not found or disabled. Stopping.")
                            break
                            
            except Exception as e:
                self.logger.error(f"An error occurred: {e}")
                try:
                    page.screenshot(path="newegg_error_screenshot.png")
                except:
                    pass
            finally:
                browser.close()
                
        return results

class BestBuyScraper:
    def __init__(self, headless=True, use_proxy=True):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def parse_specs(self, title):
        specs = {
            "Brand": "N/A",
            "Model": "N/A",
            "Capacity": "N/A",
            "Speed": "N/A",
            "CL_Timing": "N/A",
            "Voltage": "N/A",
            "XMP_Support": "No",
            "EXPO_Support": "No",
            "RGB": "No"
        }
        if not title: return specs
        
        # Brand
        brands = ["Corsair", "G.Skill", "Kingston", "Crucial", "TeamGroup", "Patriot", "ADATA", "Samsung", "Hynix", "Micron", "GeIL", "Mushkin", "KLEVV", "Lexar", "Silicon Power", "V-Color", "Acer", "HP", "Dell", "Lenovo", "Asus", "MSI", "Gigabyte"]
        for brand in brands:
            if brand.lower() in title.lower():
                specs["Brand"] = brand
                break
        
        # Model
        specs["Model"] = extract_model(title, specs["Brand"])
        
        # Basic extraction similar to others
        cap_match = re.search(r'(\d+\s*GB\s*x\s*\d+|\d+\s*GB)', title, re.IGNORECASE)
        if cap_match: specs["Capacity"] = cap_match.group(0)
        
        speed_match = re.search(r'(\d+\s*MHz|\d+\s*MT/s)', title, re.IGNORECASE)
        if speed_match: specs["Speed"] = speed_match.group(0)
        
        return specs

    def validate_item(self, item, keyword):
        title = item.get("Title", "").upper()
        keyword_upper = keyword.upper()
        if "DDR5" in keyword_upper and "DDR4" in title: return False
        if "DDR4" in keyword_upper and "DDR5" in title: return False
        return True

    def scrape_search_results(self, keyword, max_pages=1):
        results = []
        with sync_playwright() as p:
            proxy = None
            if self.use_proxy: proxy = self.proxy_manager.get_random_proxy()
            
            browser_args = {}
            if proxy: browser_args['proxy'] = {"server": proxy}
            
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            stealth_sync(context)
            page = context.new_page()
            
            try:
                self.logger.info("Navigating to Best Buy...")
                page.goto(f"https://www.bestbuy.com/site/searchpage.jsp?st={keyword.replace(' ', '+')}", timeout=60000)
                
                for current_page in range(1, max_pages + 1):
                    try:
                        page.wait_for_selector("li.sku-item", timeout=15000)
                    except:
                        self.logger.warning("Timeout waiting for Best Buy results.")
                        break
                        
                    product_cards = page.locator("li.sku-item").all()
                    self.logger.info(f"Found {len(product_cards)} cards on page {current_page}")
                    
                    for card in product_cards:
                        try:
                            title_el = card.locator("h4.sku-header a")
                            price_el = card.locator("div.priceView-hero-price span[aria-hidden='true']").first
                            
                            title = title_el.inner_text().strip() if title_el.count() > 0 else "N/A"
                            price = price_el.inner_text().strip() if price_el.count() > 0 else "N/A"
                            link = f"https://www.bestbuy.com{title_el.get_attribute('href')}" if title_el.count() > 0 else "N/A"
                            
                            specs = self.parse_specs(title)
                            item = {**specs, "Title": title, "Price": price, "Rating": "N/A", "Product Link": link}
                            
                            if self.validate_item(item, keyword):
                                results.append(item)
                        except: continue
                        
                    if current_page < max_pages:
                        next_btn = page.locator("a.sku-list-page-next")
                        if next_btn.count() > 0 and "disabled" not in next_btn.get_attribute("class"):
                            next_btn.click()
                            time.sleep(5)
                        else: break
            except Exception as e:
                self.logger.error(f"Best Buy Error: {e}")
            finally:
                browser.close()
        return results

class BHScraper:
    def __init__(self, headless=True, use_proxy=True):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def parse_specs(self, title):
        specs = {
            "Brand": "N/A", "Model": "N/A", "Capacity": "N/A", "Speed": "N/A",
            "CL_Timing": "N/A", "Voltage": "N/A", "XMP_Support": "No", "EXPO_Support": "No", "RGB": "No"
        }
        if not title: return specs
        
        # Brand
        brands = ["Corsair", "G.Skill", "Kingston", "Crucial", "TeamGroup", "Patriot", "ADATA", "Samsung", "Hynix", "Micron", "GeIL", "Mushkin", "KLEVV", "Lexar", "Silicon Power", "V-Color", "Acer", "HP", "Dell", "Lenovo", "Asus", "MSI", "Gigabyte"]
        for brand in brands:
            if brand.lower() in title.lower():
                specs["Brand"] = brand
                break
        
        # Model
        specs["Model"] = extract_model(title, specs["Brand"])
        
        cap_match = re.search(r'(\d+\s*GB\s*x\s*\d+|\d+\s*GB)', title, re.IGNORECASE)
        if cap_match: specs["Capacity"] = cap_match.group(0)
        speed_match = re.search(r'(\d+\s*MHz|\d+\s*MT/s)', title, re.IGNORECASE)
        if speed_match: specs["Speed"] = speed_match.group(0)
        return specs

    def validate_item(self, item, keyword):
        title = item.get("Title", "").upper()
        keyword_upper = keyword.upper()
        if "DDR5" in keyword_upper and "DDR4" in title: return False
        if "DDR4" in keyword_upper and "DDR5" in title: return False
        return True

    def scrape_search_results(self, keyword, max_pages=1):
        results = []
        with sync_playwright() as p:
            proxy = None
            if self.use_proxy: proxy = self.proxy_manager.get_random_proxy()
            
            browser_args = {}
            if proxy: browser_args['proxy'] = {"server": proxy}
            
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            stealth_sync(context)
            page = context.new_page()
            
            try:
                self.logger.info("Navigating to B&H...")
                page.goto(f"https://www.bhphotovideo.com/c/search?Ntt={keyword.replace(' ', '+')}", timeout=60000)
                
                for current_page in range(1, max_pages + 1):
                    try:
                        page.wait_for_selector("div[data-selenium='miniProductPage']", timeout=15000)
                    except:
                        # Fallback to observed class if data-selenium fails
                        try:
                            page.wait_for_selector("div[class*='product_']", timeout=5000)
                        except:
                            self.logger.warning("Timeout waiting for B&H results.")
                            break
                        
                    product_cards = page.locator("div[data-selenium='miniProductPage']").all()
                    if not product_cards:
                         # Fallback selector
                         product_cards = page.locator("div[class*='product_']").all() # Generic fallback

                    self.logger.info(f"Found {len(product_cards)} cards on page {current_page}")
                    
                    for card in product_cards:
                        try:
                            # Try data-selenium first
                            title_el = card.locator("span[data-selenium='miniProductPageProductName']")
                            if title_el.count() == 0:
                                title_el = card.locator("a[class*='title_']") # Fallback

                            price_el = card.locator("span[data-selenium='uppedDecimalPrice']")
                            
                            title = title_el.inner_text().strip() if title_el.count() > 0 else "N/A"
                            price = price_el.inner_text().strip() if price_el.count() > 0 else "N/A"
                            
                            link_el = card.locator("a[data-selenium='miniProductPageProductNameLink']")
                            if link_el.count() == 0:
                                link_el = card.locator("a[class*='title_']")
                                
                            link = f"https://www.bhphotovideo.com{link_el.get_attribute('href')}" if link_el.count() > 0 else "N/A"
                            
                            specs = self.parse_specs(title)
                            item = {**specs, "Title": title, "Price": price, "Rating": "N/A", "Product Link": link}
                            
                            if self.validate_item(item, keyword):
                                results.append(item)
                        except: continue
                        
                    if current_page < max_pages:
                        next_btn = page.locator("a[data-selenium='listingPagingNextLink']")
                        if next_btn.count() > 0:
                            next_btn.click()
                            time.sleep(5)
                        else: break
            except Exception as e:
                self.logger.error(f"B&H Error: {e}")
            finally:
                browser.close()
        return results

class PCHomeScraper:
    def __init__(self, headless=True, use_proxy=True):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy_manager = ProxyManager()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.exchange_rate = 32.5 # 1 USD = 32.5 TWD

    def parse_specs(self, title):
        specs = {
            "Brand": "N/A", "Model": "N/A", "Capacity": "N/A", "Speed": "N/A",
            "CL_Timing": "N/A", "Voltage": "N/A", "XMP_Support": "No", "EXPO_Support": "No", "RGB": "No"
        }
        if not title: return specs
        
        # Brand
        brands = ["Corsair", "G.Skill", "Kingston", "Crucial", "TeamGroup", "Patriot", "ADATA", "Samsung", "Hynix", "Micron", "GeIL", "Mushkin", "KLEVV", "Lexar", "Silicon Power", "V-Color", "Acer", "HP", "Dell", "Lenovo", "Asus", "MSI", "Gigabyte", "Transcend", "Apacer"]
        for brand in brands:
            if brand.lower() in title.lower():
                specs["Brand"] = brand
                break
        
        # Model
        specs["Model"] = extract_model(title, specs["Brand"])
        
        cap_match = re.search(r'(\d+\s*GB\s*x\s*\d+|\d+\s*GB)', title, re.IGNORECASE)
        if cap_match: specs["Capacity"] = cap_match.group(0)
        
        # Speed extraction
        speed_match = re.search(r'(\d+\s*MHz|\d+\s*MT/s)', title, re.IGNORECASE)
        if speed_match: 
            specs["Speed"] = speed_match.group(0)
        else:
            # Fallback: Look for 4-digit number after DDR5 (e.g., DDR5 6000, DDR5-6000)
            ddr_speed_match = re.search(r'DDR5[\s-]?(\d{4})', title, re.IGNORECASE)
            if ddr_speed_match:
                specs["Speed"] = f"{ddr_speed_match.group(1)} MHz"
        
        return specs

    def validate_item(self, item, keyword):
        title = item.get("Title", "").upper()
        keyword_upper = keyword.upper()
        if "DDR5" in keyword_upper and "DDR4" in title: return False
        if "DDR4" in keyword_upper and "DDR5" in title: return False
        return True

    def convert_price(self, price_str):
        try:
            # Remove non-numeric characters except dot
            clean_price = re.sub(r'[^\d.]', '', price_str)
            price_twd = float(clean_price)
            price_usd = price_twd / self.exchange_rate
            return f"${price_usd:.2f}"
        except:
            return "N/A"

    def scrape_search_results(self, keyword, max_pages=1):
        results = []
        with sync_playwright() as p:
            proxy = None
            if self.use_proxy: proxy = self.proxy_manager.get_random_proxy()
            
            browser_args = {}
            if proxy: browser_args['proxy'] = {"server": proxy}
            
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            stealth_sync(context)
            page = context.new_page()
            
            try:
                self.logger.info("Navigating to PCHome...")
                page.goto(f"https://24h.pchome.com.tw/search/?q={keyword.replace(' ', '%20')}", timeout=60000)
                
                for current_page in range(1, max_pages + 1):
                    try:
                        page.wait_for_selector("div.c-prodInfoV2--gridCard", timeout=15000)
                    except:
                        self.logger.warning("Timeout waiting for PCHome results.")
                        break
                        
                    # Scroll to load more items (PCHome often uses infinite scroll or lazy load)
                    for _ in range(5):
                        page.evaluate("window.scrollBy(0, 1000)")
                        time.sleep(1)
                        
                    product_cards = page.locator("div.c-prodInfoV2--gridCard").all()
                    self.logger.info(f"Found {len(product_cards)} cards on page {current_page}")
                    
                    for card in product_cards:
                        try:
                            # Selectors based on inspection
                            # Title is often in a specific div structure or has a class like c-prodInfoV2__title if available
                            # Based on inspection: "div with no specific class... one after the div with text..."
                            # Let's try to find the title by text content or structure
                            
                            # Try finding the link first, it usually wraps the title or is near it
                            link_el = card.locator("a.c-prodInfoV2__link").first
                            
                            title = "N/A"
                            link = "N/A"
                            
                            if link_el.count() > 0:
                                link = link_el.get_attribute("href")
                                if link and not link.startswith("http"):
                                    link = f"https://24h.pchome.com.tw{link}"
                                
                                # Title is often inside the link or a sibling div
                                # Inspection said: a.c-prodInfoV2__link > div > div > div > div > div:nth-child(2)
                                # Let's try getting all text from the link and splitting/cleaning
                                all_text = link_el.inner_text()
                                lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                                # Heuristic: The longest line is likely the title, or the one with the keyword
                                for line in lines:
                                    if len(line) > 10: # Titles are usually long
                                        title = line
                                        break
                            
                            # Price
                            # Inspection: div.c-prodInfoV2--gridCard div[style*='align-items: flex-end'] > div > div
                            # Or look for '$' sign
                            price_el = card.locator("div").filter(has_text="$").last
                            price_text = price_el.inner_text() if price_el.count() > 0 else "N/A"
                            
                            # Extract just the price number
                            price_match = re.search(r'\$([\d,]+)', price_text)
                            if price_match:
                                price_twd = price_match.group(1)
                                price = self.convert_price(price_twd)
                            else:
                                price = "N/A"
                            
                            specs = self.parse_specs(title)
                            item = {"Title": title, "Price": price, "Rating": "N/A", **specs, "Product Link": link}
                            
                            if self.validate_item(item, keyword):
                                results.append(item)
                        except: continue
                        
                    # PCHome pagination is often infinite scroll or "Next" button. 
                    # For V1, we might just stick to the first loaded batch or try to find a next button if it exists.
                    # PCHome search usually has pages. URL parameter &page=2
                    if current_page < max_pages:
                        # Construct next page URL
                        next_page_url = f"https://24h.pchome.com.tw/search/?q={keyword.replace(' ', '%20')}&page={current_page + 1}"
                        page.goto(next_page_url)
                        time.sleep(3)
                        
            except Exception as e:
                self.logger.error(f"PCHome Error: {e}")
            finally:
                browser.close()
        return results
