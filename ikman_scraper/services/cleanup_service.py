import os
import pandas as pd
import re
from datetime import datetime
from thefuzz import fuzz
from ..data.data_access import load_history, read_excel_file, write_excel_file, CLEANED_SCRAPE_DIR


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


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation/extra spaces, etc."""
    if not isinstance(title, str):
        return ""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    title = title.strip()
    return title


def fuzzy_drop_duplicates(df, threshold=80):
    """
    Remove duplicates based on fuzzy string matching of 'title_normalized'.
    Assumes DataFrame is sorted by 'Date' descending.
    """
    final_rows = []
    seen_titles = []

    for _, row in df.iterrows():
        t_norm = row["title_normalized"]
        is_duplicate = False
        for existing_t in seen_titles:
            ratio = fuzz.ratio(t_norm, existing_t)
            if ratio >= threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            final_rows.append(row)
            seen_titles.append(t_norm)

    return pd.DataFrame(final_rows)


def cleanup_duplicates(start_date, end_date, threshold=80):
    """
    1) Collect all Excel files in [start_date, end_date].
    2) Merge them, sort by Date DESC.
    3) Fuzzy deduplicate by 'Title'.
    4) Keep only these columns (in order):
         [Location, Date, Title, Price, Link].
    5) Save to 'cleaned_scrape/cleaned_YYYY-MM-DD_to_YYYY-MM-DD.xlsx'
    """
    excel_files = find_excel_files_for_range(start_date, end_date)
    if not excel_files:
        return {
            "success": False,
            "message": "No Excel files found in the selected date range.",
            "file": ""
        }

    combined_df = pd.DataFrame()

    # Load & combine
    for fpath in excel_files:
        df = read_excel_file(fpath)  # your own function
        if df is not None and not df.empty:
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    if combined_df.empty:
        return {
            "success": False,
            "message": "No data in the selected files.",
            "file": ""
        }

    # Sort by newest
    if "Date" in combined_df.columns:
        combined_df.sort_values(by="Date", ascending=False, inplace=True)

    # Must have Title for dedup
    if "Title" not in combined_df.columns:
        return {
            "success": False,
            "message": "No 'Title' column found. Cannot remove duplicates.",
            "file": ""
        }

    # Create a normalized col for fuzzy matching
    combined_df["title_normalized"] = combined_df["Title"].apply(normalize_title)

    # Fuzzy deduplicate
    dedup_df = fuzzy_drop_duplicates(combined_df, threshold=threshold)

    # Now select and rename columns as desired
    # Assume your DF has "Location", "Date", "Title", "Price (numeric)", "URL"
    # We'll rename "Price (numeric)" -> "Price", "URL" -> "Link" if you want
    column_mapping = {
        "Price (numeric)": "Price",
        "URL": "Link"
    }
    for old_col, new_col in column_mapping.items():
        if old_col in dedup_df.columns:
            dedup_df.rename(columns={old_col: new_col}, inplace=True)

    # Keep only these columns, in this order:
    final_columns = ["Location", "Date", "Title", "Price", "Link"]
    # If any are missing, you may need to handle that gracefully
    missing_cols = [c for c in final_columns if c not in dedup_df.columns]
    if missing_cols:
        return {
            "success": False,
            "message": f"Missing columns in data: {missing_cols}",
            "file": ""
        }

    dedup_df = dedup_df[final_columns]

    final_count = len(dedup_df)

    # Write file
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    filename = f"cleaned_{start_str}_to_{end_str}.xlsx"
    out_dir = CLEANED_SCRAPE_DIR
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    try:
        write_excel_file(dedup_df, out_path)  # your own function
        return {
            "success": True,
            "message": f"Fuzzy cleanup done. {final_count} records remain.",
            "file": out_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving file: {e}",
            "file": ""
        }
