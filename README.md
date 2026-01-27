# Forex Factory News Event Scraper
This project is a Python-based web scraper designed to retrieve news events for the current month from Forex Factory. It utilizes the Selenium library to automate the process of collecting data from the Forex Factory page. Here, I provide a brief overview of the project's structure and how to use it.

## Project Structure
The project consists of several Python files and a configuration file:

***scraper.py***: This is the main script responsible for scraping data from the Forex Factory calendar page. It uses Selenium to interact with the website, scroll through the page to load all events, and extract relevant data.

***utils.py***: This file contains utility functions for reading JSON data and processing text to extract relevant information from the scraped data.

***config.py***: Here, you can configure constants related to allowed HTML element types, excluded element types, impact color mapping, allowed currency codes, and allowed impact colors. These configurations help filter and categorize the scraped data.

## How to Use
Follow these steps to use the Forex Factory News Event Scraper:
Ensure you have Python installed on your system.

## Virtual Environment Setup
It is recommended to use a Python virtual environment for this project. To set up and activate a virtual environment, run the following commands in your project directory:

```
python3 -m venv venv
source venv/bin/activate
```

Once the environment is activated, install the necessary Python libraries by running:

```
pip install -r requirements.txt
```

## Webdriver Installation:
The script uses the Chrome WebDriver to interact with the website. Make sure you have Google Chrome installed.
If you don't have the Chrome WebDriver installed, the script will attempt to install it using webdriver_manager. However, it's recommended to install it manually for better control.

## Running the Scraper:
The scraper supports multiple usage modes for flexible data collection and includes robust retry mechanisms for improved reliability:

### Default Behavior (Current Month)
Execute the scraper without any arguments to scrape the current month:
```bash
python3 scraper.py
```

### Scraping Specific Months
Use the `--months` parameter to specify particular months:
```bash
# Scrape current month
python3 scraper.py --months this

# Scrape next month
python3 scraper.py --months next

# Scrape multiple specific months
python3 scraper.py --months this next
```

### Scraping Date Ranges
Use the `--start` and `--end` parameters to scrape data across multiple months:
```bash
# Scrape from January 2007 to June 2007
python3 scraper.py --start "jan 2007" --end "jun 2007"

# Also works with full month names
python3 scraper.py --start "january 2007" --end "december 2007"

# Mixed case formatting is supported
python3 scraper.py --start "Jan 2007" --end "Dec 2007"
```

### Retry Configuration
The scraper includes exponential backoff retry mechanisms. You can customize retry behavior:
```bash
# Use custom retry settings
python3 scraper.py --months this --retries 5 --base-delay 2 --max-delay 120

# High-reliability scraping for important data
python3 scraper.py --start "jan 2007" --end "jun 2007" --retries 10 --base-delay 3
```

#### Retry Parameters:
- `--retries`: Maximum number of retry attempts (default: 3)
- `--base-delay`: Base delay in seconds for exponential backoff (default: 1)
- `--max-delay`: Maximum delay in seconds (default: 60)

### Supported Date Formats
The scraper accepts flexible month/year formats:
- Abbreviated months: `jan`, `feb`, `mar`, etc.
- Full month names: `january`, `february`, `march`, etc.
- Case insensitive: `Jan`, `JAN`, `january`, `JANUARY` all work
- Format: `"month year"` (e.g., `"jan 2007"`, `"January 2025"`)

## Features

### Exponential Retry Mechanism
- **Automatic Recovery**: Handles temporary network issues, rate limiting, and website unavailability
- **Exponential Backoff**: Progressive delay increases (1s, 2s, 4s, 8s, etc.) with random jitter
- **Comprehensive Coverage**: Retries page loading, element finding, and data extraction
- **Statistics Tracking**: Provides detailed success/failure statistics after completion
- **Configurable**: Customize retry behavior via command line or configuration file

### Incremental Update Mode
By default, the scraper operates in **update mode**, which intelligently merges new data with existing CSV files:

- **Smart Merging**: Detects new events and updated records based on unique event IDs
- **No Duplicates**: Existing records are preserved; only new or changed data is added
- **Change Detection**: Compares `actual`, `forecast`, and `previous` values to detect updates
- **Automatic Sorting**: Results are sorted by date and time after merging

```bash
# Default behavior: Update existing CSV with new data
python3 scraper.py --months this

# Force overwrite mode: Replace existing CSV completely
python3 scraper.py --months this --overwrite
```

#### Update Mode vs Overwrite Mode

| Mode | Behavior |
|------|----------|
| **Update (default)** | Loads existing CSV, adds new events, updates changed records, preserves everything else |
| **Overwrite (`--overwrite`)** | Completely replaces the existing CSV with freshly scraped data |

#### Recommended Mode by Scenario

| Scenario | Recommended Mode |
|----------|-----------------|
| Daily/weekly updates to capture new data releases | Update (default) |
| Suspect corrupted or incorrect data | `--overwrite` |
| First-time scrape of a month | Either (no difference) |
| Re-scraping historical months | `--overwrite` |

For detailed retry mechanism documentation, see `RETRY_DOCUMENTATION.md`.

The scraped data will be reformatted and saved as CSV files in the "news" directory with filenames in the format "MONTH_YEAR_news.csv" for each month processed.


### Notes
This scraper is designed for educational and informational purposes. Ensure you comply with the terms of use and policies of Forex Factory when using this tool. Keep in mind that web scraping may be subject to legal and ethical considerations. 
Always respect the website's terms of service and robots.txt file.
It's a good practice to schedule the scraper to run periodically if you need updated data regularly.

**Disclaimer**: The accuracy and functionality of this scraper may change over time due to updates on the Forex Factory website. Be prepared to make adjustments if necessary.

**Please use this tool responsibly and in accordance with applicable laws and regulations.**
