import os
from datetime import datetime
import pandas as pd

from ..data.data_access import load_history, read_excel_file, write_excel_file


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


def cleanup_duplicates(start_date, end_date):
    """
    Merge all excel files in [start_date, end_date], remove duplicates by 'Title',
    keep latest by 'Date', save to cleaned_scrape/...
    Returns a dict with {success, message, file} for the UI to display.
    """

    # 1) Gather Excel files from the range
    excel_files = find_excel_files_for_range(start_date, end_date)
    if not excel_files:
        return {
            "success": False,
            "message": "No Excel files found for the selected date range.",
            "file": ""
        }

    combined_df = pd.DataFrame()

    # 2) Read and combine
    for fpath in excel_files:
        df = read_excel_file(fpath)
        if df is not None:
            # Make sure Date column is datetime
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    if combined_df.empty:
        return {
            "success": False,
            "message": "No data found in the selected files.",
            "file": ""
        }

    # 3) Sort by 'Date' descending so newest is first
    if "Date" in combined_df.columns:
        combined_df.sort_values(by="Date", ascending=False, inplace=True)

    # 4) Remove duplicates by "Title"
    if "Title" not in combined_df.columns:
        return {
            "success": False,
            "message": "No 'Title' column found. Cannot remove duplicates.",
            "file": ""
        }

    combined_df.drop_duplicates(subset=["Title"], keep="first", inplace=True)
    final_count = len(combined_df)

    # 5) Save to 'cleaned_scrape/'
    # Name the file, e.g.: cleaned_YYYY-MM-DD_to_YYYY-MM-DD.xlsx
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    filename = f"cleaned_{start_str}_to_{end_str}.xlsx"
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..",
        "cleaned_scrape",
        filename
    )

    try:
        write_excel_file(combined_df, out_path)
        return {
            "success": True,
            "message": f"Cleanup complete. {final_count} records in final file.",
            "file": out_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error while saving cleaned file: {str(e)}",
            "file": ""
        }
