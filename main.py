import argparse
from scraper import AmazonScraper
from exporter import save_to_excel
import logging

def main():
    parser = argparse.ArgumentParser(description="Amazon Scraper with Proxy Rotation")
    parser.add_argument("--keyword", type=str, required=True, help="Search keyword")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy usage")
    parser.add_argument("--source", type=str, default="amazon", choices=["amazon", "newegg", "bestbuy", "bh", "pchome", "all"], help="Source to scrape")
    parser.add_argument("--output", type=str, default="products.xlsx", help="Output file name")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting scraper for keyword: {args.keyword} from {args.source}")
    
    all_results = []
    
    sources_to_scrape = []
    if args.source == "all":
        sources_to_scrape = ["amazon", "newegg", "bestbuy", "bh", "pchome"]
    else:
        sources_to_scrape = [args.source]
        
    for source in sources_to_scrape:
        logger.info(f"Scraping source: {source}")
        scraper = None
        if source == "newegg":
            from scraper import NeweggScraper
            scraper = NeweggScraper(headless=args.headless, use_proxy=not args.no_proxy)
        elif source == "bestbuy":
            from scraper import BestBuyScraper
            scraper = BestBuyScraper(headless=args.headless, use_proxy=not args.no_proxy)
        elif source == "bh":
            from scraper import BHScraper
            scraper = BHScraper(headless=args.headless, use_proxy=not args.no_proxy)
        elif source == "pchome":
            from scraper import PCHomeScraper
            scraper = PCHomeScraper(headless=args.headless, use_proxy=not args.no_proxy)
        elif source == "amazon":
            from scraper import AmazonScraper
            scraper = AmazonScraper(headless=args.headless, use_proxy=not args.no_proxy)
            
        if scraper:
            try:
                data = scraper.scrape_search_results(args.keyword, max_pages=args.pages)
                # Add Source field
                for item in data:
                    item["Source"] = source.capitalize()
                    if source == "bh": item["Source"] = "B&H"
                    if source == "pchome": item["Source"] = "PCHome"
                
                all_results.extend(data)
                logger.info(f"Found {len(data)} items from {source}")
            except Exception as e:
                logger.error(f"Error scraping {source}: {e}")

    if all_results:
        logger.info(f"Scraping complete. Total found {len(all_results)} items.")
        save_to_excel(all_results, args.output)
    else:
        logger.warning("No data found.")

if __name__ == "__main__":
    main()
