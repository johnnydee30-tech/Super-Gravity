# Super Scraper v2.0

The ultimate product scraper for Amazon, Newegg, BestBuy, B&H, and PCHome.

## Features
- Scrape product details (Name, Price, Rating, URL) from multiple sources.
- Support for Amazon, Newegg, BestBuy, B&H, and PCHome.
- Export results to Excel with organized source grouping.
- Streamlit-based User Interface.
- Headless mode and Proxy support.

## Installation

1. Clone the repository or download the source code.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Usage

### Run with UI (Recommended)
```bash
streamlit run app.py
```
Or use the launcher:
```bash
python run_app.py
```

### Run via CLI
```bash
python main.py --keyword "gaming laptop" --source amazon --pages 1
```

## Requirements
- Python 3.8+
- Chrome/Chromium (installed via Playwright)
