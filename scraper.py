import time
import argparse
import random
import time
from datetime import datetime
from config import ALLOWED_ELEMENT_TYPES, ICON_COLOR_MAP, RETRY_CONFIG
from utils import save_csv
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Global retry statistics
retry_stats = {
    'total_attempts': 0,
    'successful_first_attempts': 0,
    'failed_final_attempts': 0
}


def exponential_backoff_retry(func, max_retries=3, base_delay=1, max_delay=60, *args, **kwargs):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        Function result on success
    
    Raises:
        Exception: Last exception if all retries fail
    """ 
    for attempt in range(max_retries + 1):
        retry_stats['total_attempts'] += 1
        try:
            result = func(*args, **kwargs)
            if attempt == 0:
                retry_stats['successful_first_attempts'] += 1
            return result
        except Exception as e:
            
            if attempt == max_retries:
                retry_stats['failed_final_attempts'] += 1
                print(f"[ERROR] All {max_retries + 1} attempts failed. Last error: {e}")
                raise e
            
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # Add up to 10% jitter
            total_delay = delay + jitter
            
            print(f"[WARN] Attempt {attempt + 1} failed: {e}")
            print(f"[INFO] Retrying in {total_delay:.2f} seconds...")
            time.sleep(total_delay)


def init_driver(headless=True) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920x1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    print("Attempting to initialize WebDriver with ChromeDriverManager...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    print("WebDriver initialized successfully using ChromeDriverManager.")
    return driver


def load_page_with_retry(driver, url, max_retries=None):
    """Load a page with retry logic"""
    if max_retries is None:
        max_retries = RETRY_CONFIG['max_retries']
    
    def _load_page():
        driver.get(url)
        # Wait for the calendar table to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "calendar__table")))
        return True
    
    return exponential_backoff_retry(
        _load_page, 
        max_retries=max_retries,
        base_delay=RETRY_CONFIG['base_delay'],
        max_delay=RETRY_CONFIG['max_delay']
    )


def find_element_with_retry(driver, by, value, max_retries=None):
    """Find an element with retry logic"""
    if max_retries is None:
        max_retries = RETRY_CONFIG['max_retries']
    
    def _find_element():
        return driver.find_element(by, value)
    
    return exponential_backoff_retry(
        _find_element, 
        max_retries=max_retries,
        base_delay=RETRY_CONFIG['base_delay'],
        max_delay=RETRY_CONFIG['max_delay']
    )


def scroll_to_end(driver):
    previous_position = None
    while True:
        current_position = driver.execute_script("return window.pageYOffset;")
        driver.execute_script("window.scrollTo(0, window.pageYOffset + 500);")
        time.sleep(2)
        if current_position == previous_position:
            break
        previous_position = current_position


def parse_table(driver, month, year, max_retries=None, update_mode=True):
    """Parse table with retry logic
    
    Args:
        driver: Selenium WebDriver instance
        month: Month name (e.g., 'January')
        year: Year string
        max_retries: Maximum retry attempts
        update_mode: If True, merge with existing CSV; if False, overwrite
    """
    if max_retries is None:
        max_retries = RETRY_CONFIG['max_retries']
    
    def _parse_table():
        data = []
        table = find_element_with_retry(driver, By.CLASS_NAME, "calendar__table", max_retries=2)

        for row in table.find_elements(By.TAG_NAME, "tr"):
            row_data = {}
            event_id = row.get_attribute("data-event-id")

            for element in row.find_elements(By.TAG_NAME, "td"):
                class_name = element.get_attribute('class')

                if class_name in ALLOWED_ELEMENT_TYPES:
                    class_name_key = ALLOWED_ELEMENT_TYPES.get(
                        f"{class_name}", "cell")

                    if "calendar__impact" in class_name:
                        impact_elements = element.find_elements(
                            By.TAG_NAME, "span")
                        color = None
                        for impact in impact_elements:
                            impact_class = impact.get_attribute("class")
                            color = ICON_COLOR_MAP.get(impact_class)
                        row_data[f"{class_name_key}"] = color if color else "impact"

                    elif "calendar__detail" in class_name and event_id:
                        detail_url = f"https://www.forexfactory.com/calendar?month={month.lower()}.{year}#detail={event_id}"
                        row_data[f"{class_name_key}"] = detail_url
                    elif class_name_key in ["forecast", "previous"]:
                        value = element.get_attribute('innerText')
                        value = value.strip() if value else ""
                        row_data[f"{class_name_key}"] = value if value else "empty"
                    elif element.text:
                        row_data[f"{class_name_key}"] = element.text
                    else:
                        row_data[f"{class_name_key}"] = "empty"

            if row_data:
                data.append(row_data)

        save_csv(data, month, year, update_mode=update_mode)
        return data, month
    
    return exponential_backoff_retry(
        _parse_table, 
        max_retries=max_retries,
        base_delay=RETRY_CONFIG['base_delay'],
        max_delay=RETRY_CONFIG['max_delay']
    )


def get_target_month(arg_month=None):
    now = datetime.now()
    month = arg_month if arg_month else now.strftime("%B")
    year = now.strftime("%Y")
    return month, year

def generate_month_range(start_date, end_date):
    """Generate a list of (month, year) tuples between start_date and end_date"""
    months = []
    current = start_date.replace(day=1)  # Start from first day of the month
    
    while current <= end_date:
        months.append((current.strftime("%B"), current.year))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    return months


def parse_month_year_string(date_str):
    """Parse date string in format 'jan 2007', 'january 2007', 'Jan 2007', etc."""
    try:
        # Handle different month formats
        parts = date_str.strip().split()
        if len(parts) != 2:
            raise ValueError("Format should be 'month year' (e.g., 'jan 2007')")
        
        month_str, year_str = parts
        year = int(year_str)
        
        # Try full month name first
        try:
            month_num = datetime.strptime(month_str.capitalize(), "%B").month
        except ValueError:
            # Try abbreviated month name
            try:
                month_num = datetime.strptime(month_str.capitalize(), "%b").month
            except ValueError:
                raise ValueError(f"Invalid month: {month_str}")
        
        return datetime(year, month_num, 1)
        
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid date format: {date_str}. Use format like 'jan 2007' or 'january 2007'")


def scrape_month(month, year, url_param=None, max_retries=None, update_mode=True):
    """Scrape a single month with retry logic
    
    Args:
        month: Month name (e.g., 'January')
        year: Year
        url_param: Optional URL parameter for the month
        max_retries: Maximum retry attempts
        update_mode: If True, merge with existing CSV; if False, overwrite
    """
    if max_retries is None:
        max_retries = RETRY_CONFIG['max_retries']
    
    def _scrape_month_attempt():
        if url_param:
            url = f"https://www.forexfactory.com/calendar?month={url_param}"
        else:
            month_abbr = month[:3].lower()
            url = f"https://www.forexfactory.com/calendar?month={month_abbr}.{year}"
        
        print(f"\n[INFO] Navigating to {url}")

        driver = init_driver()
        try:
            # Load page with retry
            load_page_with_retry(driver, url, max_retries=2)
            
            detected_tz = driver.execute_script("return Intl.DateTimeFormat().resolvedOptions().timeZone")
            print(f"[INFO] Browser timezone: {detected_tz}")
            config.SCRAPER_TIMEZONE = detected_tz
            
            scroll_to_end(driver)

            print(f"[INFO] Scraping data for {month} {year}")
            result = parse_table(driver, month, str(year), max_retries=2, update_mode=update_mode)
            
            return result
            
        finally:
            driver.quit()
            time.sleep(3)
    
    try:
        return exponential_backoff_retry(
            _scrape_month_attempt, 
            max_retries=max_retries,
            base_delay=RETRY_CONFIG['base_delay'],
            max_delay=RETRY_CONFIG['max_delay']
        )
    except Exception as e:
        print(f"[ERROR] Failed to scrape {month} {year} after {max_retries + 1} attempts: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Forex Factory calendar.")
    parser.add_argument("--months", nargs="+",
                        help='Target months: e.g., this next')
    parser.add_argument("--start", 
                        help='Start month for range scraping (e.g., "jan 2007", "january 2007")')
    parser.add_argument("--end", 
                        help='End month for range scraping (e.g., "jun 2007", "june 2007")')
    parser.add_argument("--retries", type=int, default=None,
                        help='Maximum number of retry attempts (default: 3)')
    parser.add_argument("--base-delay", type=float, default=None,
                        help='Base delay in seconds for exponential backoff (default: 1)')
    parser.add_argument("--max-delay", type=float, default=None,
                        help='Maximum delay in seconds for exponential backoff (default: 60)')
    parser.add_argument("--overwrite", action="store_true",
                        help='Overwrite existing CSV files instead of updating them with new data')

    args = parser.parse_args()
    
    # Determine update mode (default is True, --overwrite sets it to False)
    update_mode = not args.overwrite
    
    if update_mode:
        print("[INFO] Update mode: Will merge new data with existing CSV files")
    else:
        print("[INFO] Overwrite mode: Will replace existing CSV files")
    
    # Override retry configuration if provided
    if args.retries is not None:
        RETRY_CONFIG['max_retries'] = args.retries
    if args.base_delay is not None:
        RETRY_CONFIG['base_delay'] = args.base_delay
    if args.max_delay is not None:
        RETRY_CONFIG['max_delay'] = args.max_delay
    
    print(f"[INFO] Using retry configuration: {RETRY_CONFIG}")

    # Handle date range scraping
    if args.start and args.end:
        try:
            start_date = parse_month_year_string(args.start)
            end_date = parse_month_year_string(args.end)
            
            if start_date > end_date:
                print("[ERROR] Start date must be before end date")
                return
            
            print(f"[INFO] Scraping date range: {start_date.strftime('%B %Y')} to {end_date.strftime('%B %Y')}")
            
            months_to_scrape = generate_month_range(start_date, end_date)
            
            for month, year in months_to_scrape:
                scrape_month(month, year, update_mode=update_mode)
                
        except ValueError as e:
            print(f"[ERROR] {e}")
            return
    
    # Handle individual month parameters (existing functionality)
    elif args.months is not None or (not args.start and not args.end):
        month_params = args.months if args.months else ["this"]

        for param in month_params:
            param = param.lower()
            
            # Determine readable month name and year
            if param == "this":
                now = datetime.now()
                month = now.strftime("%B")
                year = now.year
                scrape_month(month, year, param, update_mode=update_mode)
            elif param == "next":
                now = datetime.now()
                next_month = (now.month % 12) + 1
                year = now.year if now.month < 12 else now.year + 1
                month = datetime(year, next_month, 1).strftime("%B")
                scrape_month(month, year, param, update_mode=update_mode)
            else:
                month = param.capitalize()
                year = datetime.now().year
                scrape_month(month, year, param, update_mode=update_mode)
    
    else:
        print("[ERROR] Please provide both --start and --end together for date range scraping. Only one was provided.")
    
    # Print retry statistics
    print_retry_stats()


def print_retry_stats():
    """Print retry statistics summary"""
    print("\n" + "="*50)
    print("RETRY STATISTICS SUMMARY")
    print("="*50)
    print(f"Total operations attempted: {retry_stats['total_attempts']}")
    print(f"Successful on first attempt: {retry_stats['successful_first_attempts']}")
    print(f"Required retries: {retry_stats['total_attempts'] - retry_stats['successful_first_attempts'] - retry_stats['failed_final_attempts']}")
    print(f"Final failures: {retry_stats['failed_final_attempts']}")
    
    if retry_stats['total_attempts'] > 0:
        success_rate = ((retry_stats['total_attempts'] - retry_stats['failed_final_attempts']) / retry_stats['total_attempts']) * 100
        print(f"Overall success rate: {success_rate:.1f}%")
    
    print("="*50)


if __name__ == "__main__":
    main()
