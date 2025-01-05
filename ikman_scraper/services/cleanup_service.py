import os
import pandas as pd
import re
from datetime import datetime
from thefuzz import fuzz
from ..data.data_access import load_history, read_excel_file, write_excel_file


def normalize_title(title: str) -> str:
    """
    Convert to lowercase, remove punctuation, trim extra spaces, etc.
    Example:
      "   Beautiful House!! " -> "beautiful house"
      "House, For SALE!!!"   -> "house for sale"
    """
    if not isinstance(title, str):
        return ""
    # Lowercase
    title = title.lower()
    # Remove punctuation (keep letters/digits/spaces)
    title = re.sub(r"[^\w\s]", "", title)
    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title)
    # Trim
    title = title.strip()
    return title


def fuzzy_drop_duplicates(df, threshold=80):
    """
    Takes a DataFrame sorted by 'Date' descending (latest first),
    and removes duplicates using fuzzy string matching on 'title_normalized'.

    threshold=80 means 80% similarity => skip as duplicate.

    Returns a new DataFrame with only unique titles by fuzzy match.
    """
    final_rows = []
    final_titles = []  # store 'title_normalized' strings of accepted rows

    for _, row in df.iterrows():
        t_norm = row["title_normalized"]
        # Check if it is "similar enough" to any existing title
        is_duplicate = False
        for existing_t in final_titles:
            ratio = fuzz.ratio(t_norm, existing_t)
            if ratio >= threshold:
                # It's considered the "same" title, so skip
                is_duplicate = True
                break

        if not is_duplicate:
            final_rows.append(row)
            final_titles.append(t_norm)

    # Build a new DataFrame from final_rows
    dedup_df = pd.DataFrame(final_rows)
    return dedup_df


def find_excel_files_for_range(start_date, end_date):
    """
    Looks at scrape_history.json to find all excel files
    that fall between start_date and end_date (inclusive).
    Returns list of file paths (existing on disk).
    """
    history = load_history()
    if not history:
        return []

    valid_paths = []
    for run in history:
        run_date_str = run["date"]  # "YYYY-MM-DD"
        run_file = run.get("excel_file", "")
        if not run_file:
            continue

        run_date = datetime.strptime(run_date_str, "%Y-%m-%d").date()
        if start_date <= run_date <= end_date and os.path.exists(run_file):
            valid_paths.append(run_file)

    return valid_paths


def cleanup_duplicates(start_date, end_date, threshold=80):
    """
    1) Merge Excel files from [start_date, end_date].
    2) Sort by Date (descending).
    3) Normalize title -> "title_normalized".
    4) Fuzzy deduplicate with fuzzy_drop_duplicates(...).
    5) Keep the newest record for each fuzzy-similar Title.
    6) Save to 'cleaned_scrape/' folder as cleaned_<start>_to_<end>.xlsx

    threshold => fuzzy similarity cutoff.
      e.g. 80 means if the ratio is >=80, treat them as duplicates.
    Returns {success, message, file}.
    """
    excel_files = find_excel_files_for_range(start_date, end_date)
    if not excel_files:
        return {
            "success": False,
            "message": "No Excel files found for the selected date range.",
            "file": ""
        }

    combined_df = pd.DataFrame()

    # 1) Read all files
    for fpath in excel_files:
        df = read_excel_file(fpath)
        if df is not None and not df.empty:
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    if combined_df.empty:
        return {
            "success": False,
            "message": "No data found in the selected files.",
            "file": ""
        }

    # 2) Sort descending by date, so the newest records come first
    if "Date" in combined_df.columns:
        combined_df.sort_values(by="Date", ascending=False, inplace=True)

    # 3) If there's no Title column, we can't proceed
    if "Title" not in combined_df.columns:
        return {
            "success": False,
            "message": "No 'Title' column found. Cannot remove duplicates.",
            "file": ""
        }

    # 4) Create a normalized title column
    combined_df["title_normalized"] = combined_df["Title"].apply(normalize_title)

    # 5) Fuzzy deduplicate
    dedup_df = fuzzy_drop_duplicates(combined_df, threshold=threshold)
    final_count = len(dedup_df)

    # 6) Save to cleaned_scrape folder
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    filename = f"cleaned_{start_str}_to_{end_str}.xlsx"

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "cleaned_scrape")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    try:
        write_excel_file(dedup_df, out_path)
        return {
            "success": True,
            "message": f"Fuzzy cleanup done. {final_count} records remain.",
            "file": out_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving file: {str(e)}",
            "file": ""
        }
