# Exponential Retry Implementation

## Overview
The Forex Factory scraper now includes robust retry mechanisms with exponential backoff to handle temporary failures during web scraping operations.

## Features

### 1. Exponential Backoff
- Implements exponential backoff with jitter to avoid thundering herd problems
- Base delay starts at 1 second and doubles with each retry
- Maximum delay capped at 60 seconds
- Adds random jitter (up to 10% of delay) to prevent synchronized retries

### 2. Configurable Retry Settings
Default configuration in `config.py`:
```python
RETRY_CONFIG = {
    'max_retries': 3,           # Maximum number of retry attempts
    'base_delay': 1,            # Base delay in seconds
    'max_delay': 60,            # Maximum delay in seconds
}
```

### 3. Command Line Options
Override retry settings via command line:
```bash
python scraper.py --months this --retries 5 --base-delay 2 --max-delay 120
```

### 4. Retry Operations
The following operations now have retry logic:
- **Page Loading**: Retries if page fails to load or calendar table doesn't appear
- **Element Finding**: Retries if calendar table or other elements are not found
- **Table Parsing**: Retries if data extraction fails
- **Complete Month Scraping**: Top-level retry for entire month scraping operation

### 5. Statistics Tracking
Provides detailed statistics after scraping:
- Total operations attempted
- Successful first attempts
- Operations that required retries
- Final failures
- Overall success rate

## Usage Examples

### Basic usage with default retries
```bash
python scraper.py --months this next
```

### Date range scraping with custom retries
```bash
python scraper.py --start "jan 2007" --end "jun 2007" --retries 5
```

### High-reliability scraping
```bash
python scraper.py --months this --retries 10 --base-delay 3 --max-delay 300
```

## Benefits

1. **Improved Reliability**: Handles temporary network issues, rate limiting, and website unavailability
2. **Reduced Manual Intervention**: Automatically recovers from transient failures
3. **Respectful Scraping**: Implements delays to avoid overwhelming the target server
4. **Visibility**: Provides clear logging of retry attempts and statistics
5. **Flexibility**: Configurable retry parameters for different use cases

## Implementation Details

The retry mechanism uses a decorator pattern where core functions are wrapped with retry logic:

1. `exponential_backoff_retry()` - Core retry function with exponential backoff
2. `load_page_with_retry()` - Wraps page loading with retries
3. `find_element_with_retry()` - Wraps element finding with retries
4. `parse_table()` - Enhanced with retry wrapper
5. `scrape_month()` - Top-level function with comprehensive retry logic

Each retry attempt includes:
- Progressive delay calculation (1s, 2s, 4s, 8s, etc.)
- Random jitter addition
- Detailed logging of failures and retry attempts
- Statistics collection for post-run analysis
