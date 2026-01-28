import os
import re
import json
import pytz
import pandas as pd
from datetime import datetime
import config


def load_existing_csv(month, year):
    """
    Load existing CSV data for a given month/year if it exists.
    
    Args:
        month: Month name (e.g., 'January')
        year: Year (e.g., '2026')
    
    Returns:
        DataFrame if file exists, None otherwise
    """
    filepath = f"news/{month}_{year}_news.csv"
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            print(f"[INFO] Loaded existing data from {filepath} ({len(df)} records)")
            return df
        except Exception as e:
            print(f"[WARN] Failed to load existing CSV: {e}")
            return None
    return None


def extract_event_id_from_detail(detail_url):
    """
    Extract event ID from detail URL.
    
    Args:
        detail_url: URL like 'https://www.forexfactory.com/calendar?month=january.2026#detail=147450'
    
    Returns:
        Event ID string or None
    """
    if not detail_url or pd.isna(detail_url):
        return None
    match = re.search(r'#detail=(\d+)', str(detail_url))
    return match.group(1) if match else None


def merge_csv_data(existing_df, new_df):
    """
    Merge new data with existing data, updating existing records and adding new ones.
    
    Args:
        existing_df: Existing DataFrame from CSV
        new_df: New DataFrame from scraper
    
    Returns:
        Merged DataFrame with updates applied
    """
    if existing_df is None or existing_df.empty:
        return new_df
    
    if new_df is None or new_df.empty:
        return existing_df
    
    # Create a unique key for each row based on detail URL (contains event_id)
    # Fallback to date+time+currency+event for events without detail URL
    def create_key(row):
        event_id = extract_event_id_from_detail(row.get('detail', ''))
        if event_id:
            return f"event_{event_id}"
        # Fallback key using multiple fields
        return f"{row.get('date', '')}_{row.get('time', '')}_{row.get('currency', '')}_{row.get('event', '')}"
    
    existing_df = existing_df.copy()
    new_df = new_df.copy()
    
    existing_df['_merge_key'] = existing_df.apply(create_key, axis=1)
    new_df['_merge_key'] = new_df.apply(create_key, axis=1)
    
    # Find new records (in new_df but not in existing_df)
    existing_keys = set(existing_df['_merge_key'])
    new_keys = set(new_df['_merge_key'])
    
    added_keys = new_keys - existing_keys
    updated_keys = new_keys & existing_keys
    
    # Track changes
    added_count = 0
    updated_count = 0
    
    # Create result DataFrame starting with existing data
    result_df = existing_df.copy()
    
    # Update existing records with new data
    for key in updated_keys:
        new_row = new_df[new_df['_merge_key'] == key].iloc[0]
        existing_idx = result_df[result_df['_merge_key'] == key].index[0]
        
        # Check if the record has actually changed (compare time, actual, forecast, previous)
        existing_row = result_df.loc[existing_idx]
        has_changes = False
        
        for col in ['time', 'actual', 'forecast', 'previous']:
            if col in new_row and col in existing_row:
                new_val = str(new_row[col]).strip() if pd.notna(new_row[col]) else ''
                existing_val = str(existing_row[col]).strip() if pd.notna(existing_row[col]) else ''
                if new_val != existing_val:
                    has_changes = True
                    break
        
        if has_changes:
            # Update the row with new data
            for col in new_df.columns:
                if col != '_merge_key':
                    result_df.at[existing_idx, col] = new_row[col]
            updated_count += 1
    
    # Add new records
    for key in added_keys:
        new_row = new_df[new_df['_merge_key'] == key].iloc[0:1].copy()
        result_df = pd.concat([result_df, new_row], ignore_index=True)
        added_count += 1
    
    # Remove the merge key column
    result_df = result_df.drop(columns=['_merge_key'])
    
    # Sort by date and time
    if 'date' in result_df.columns:
        result_df['_sort_date'] = pd.to_datetime(result_df['date'], format='%d/%m/%Y', errors='coerce')
        result_df = result_df.sort_values(by=['_sort_date', 'time']).reset_index(drop=True)
        result_df = result_df.drop(columns=['_sort_date'])
    
    print(f"[INFO] Merge complete: {added_count} new records added, {updated_count} records updated")
    
    return result_df


def read_json(path):
    """
    Read JSON data from a file.
    Args: path (str): The path to the JSON file.
    Returns: dict: The loaded JSON data.
    """
    with open(path, 'r') as f:
        data = json.load(f)
    return data


def extract_date_parts(text, year):
    # Full pattern: Day (e.g., Sun), Month (e.g., Jun), Day number (e.g., 1 or 01)
    pattern = r'\b(?P<day>Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b\s+' \
              r'(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+' \
              r'(?P<date>\d{1,2})\b'

    match = re.search(pattern, text)
    if match:
        month_abbr = match.group("month")
        day = int(match.group("date"))

        # Convert month abbreviation to month number
        month_number = datetime.strptime(month_abbr, "%b").month

        # Format date as dd/mm/yyyy
        formatted_date = f"{day:02d}/{month_number:02d}/{year}"

        return {
            "day": match.group("day"),
            "date": formatted_date
        }
    else:
        return None


def reformat_data(data: list, year: str) -> list:
    current_date = ''
    current_time = ''
    current_day = ''
    structured_rows = []

    for row in data:
        new_row = row.copy()

        if "date" in new_row and new_row['date'] != "empty":
            date_parts = extract_date_parts(new_row["date"], year)
            if date_parts:
                current_date = date_parts["date"]
                current_day = date_parts["day"]

        # Only update current_time if the time cell has an actual value
        # This ensures events with empty time cells inherit the time from the previous event
        if "time" in new_row and new_row["time"] and new_row["time"].strip() and new_row["time"] != "empty":
            current_time = new_row["time"].strip()

        if len(row) == 1:
            continue

        new_row["day"] = current_day
        new_row["date"] = current_date

        if config.SCRAPER_TIMEZONE and config.TARGET_TIMEZONE:
            new_row["time"] = convert_time_zone(
                current_date, current_time, config.SCRAPER_TIMEZONE, config.TARGET_TIMEZONE
            )
            new_row["timezone"] = config.TARGET_TIMEZONE
        else:
            new_row["time"] = current_time
            new_row["timezone"] = config.SCRAPER_TIMEZONE if config.SCRAPER_TIMEZONE else ""

        new_row["currency"] = row.get("currency", "")
        new_row["impact"] = row.get("impact", "")
        new_row["event"] = row.get("event", "")
        new_row["detail"] = row.get("detail", "")
        new_row["actual"] = row.get("actual", "")
        new_row["forecast"] = row.get("forecast", "")
        new_row["previous"] = row.get("previous", "")

        # Replace "empty" with ""
        for key, value in new_row.items():
            if value == "empty":
                new_row[key] = ""

        structured_rows.append(new_row)

    return structured_rows


def save_csv(data, month, year, update_mode=True):
    """
    Save scraped data to CSV, optionally merging with existing data.
    
    Args:
        data: List of scraped row dictionaries
        month: Month name (e.g., 'January')
        year: Year (e.g., '2026')
        update_mode: If True, merge with existing CSV data; if False, overwrite
    
    Returns:
        True on success
    """
    structured_rows = reformat_data(data, year)
    header = list(structured_rows[0].keys())
    new_df = pd.DataFrame(structured_rows, columns=header)
    
    os.makedirs("news", exist_ok=True)
    filepath = f"news/{month}_{year}_news.csv"
    
    if update_mode:
        # Load existing data and merge
        existing_df = load_existing_csv(month, year)
        if existing_df is not None:
            final_df = merge_csv_data(existing_df, new_df)
        else:
            final_df = new_df
            print(f"[INFO] No existing data found, creating new file with {len(final_df)} records")
    else:
        final_df = new_df
        print(f"[INFO] Overwrite mode: saving {len(final_df)} records")
    
    final_df.to_csv(filepath, index=False)
    print(f"[INFO] Saved data to {filepath}")
    return True


def convert_time_zone(date_str, time_str, from_zone_str, to_zone_str):
    """
    Convert time from one timezone to another.
    - date_str: '01/07/2025'
    - time_str: '3:00am'
    """
    if not time_str or not date_str:
        return time_str

    if time_str.lower() in ["all day", "tentative"]:
        return time_str

    try:
        from_zone = pytz.timezone(from_zone_str)
        to_zone = pytz.timezone(to_zone_str)

        naive_dt = datetime.strptime(
            f"{date_str} {time_str}", "%d/%m/%Y %I:%M%p")
        localized_dt = from_zone.localize(naive_dt)
        converted_dt = localized_dt.astimezone(to_zone)

        return converted_dt.strftime("%H:%M")
    except Exception as e:
        print(f"[WARN] Failed to convert '{time_str}' on {date_str}: {e}")
        return time_str
