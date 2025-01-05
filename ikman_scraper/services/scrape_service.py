import requests
from datetime import datetime
from ..data.data_access import append_to_excel, add_history_record


# If you have these helpers in a different module, adjust imports accordingly.
# e.g. from ..services.helpers import clean_price, construct_api_url, get_pagination_info

def clean_price(price_str: str) -> int:
    """
    Remove 'Rs', commas, extra spaces, then convert to integer.
    e.g. "Rs 19,500,000" -> 19500000
    """
    if not price_str:
        return 0
    p = price_str.replace("Rs", "").replace(",", "").strip()
    try:
        return int(p)
    except ValueError:
        return 0


def construct_api_url(location_id, location_slug, page):
    """
    Build the API URL for the given location and page number.
    Adjust the filter_json as needed based on your requirements.
    """
    return (
        "https://ikman.lk/data/serp?top_ads=2&spotlights=5&sort=date&order=desc"
        "&buy_now=0&urgent=0"
        "&categorySlug=houses-for-sale"
        f"&locationSlug={location_slug}"
        "&category=415"
        f"&location={location_id}"
        f"&page={page}"
        "&filter_json=[%7B%22type%22:%22money%22,%22key%22:%22price%22,"
        "%22maximum%22:25000000%7D,%7B%22type%22:%22enum%22,%22key%22:%22bedrooms%22,"
        "%22values%22:[%223%22,%224%22,%225%22]%7D,%7B%22type%22:%22enum%22,"
        "%22key%22:%22bathrooms%22,%22values%22:[%222%22]%7D]"
    )


def get_pagination_info(json_data) -> int:
    """
    Return the number of pages from 'paginationData':
      "paginationData": {
         "total": 838,
         "pageSize": 25,
         ...
      }
    If total=838, pageSize=25 => 838 // 25 = 33 pages
    """
    pagination = json_data.get("paginationData", {})
    total = pagination.get("total", 0)
    page_size = pagination.get("pageSize", 1)
    if page_size == 0:
        return 0
    return total // page_size


def scrape_location(location_dict, log_area):
    """
    Actual scraping logic:
      - Construct URL for page=1
      - Get total_pages
      - For each page, fetch ads
      - Skip ads whose title has "Single", "තනි තට්ටු", or "තනිමහල්"
      - Clean up price
      - Append valid ads to Excel
      - Return a summary dict
    """
    location_name = location_dict["name"]
    location_slug = location_dict["slug"]
    location_id = location_dict["id"]

    skip_keywords = ["Single", "තනි තට්ටු", "තනිමහල්", "තනිමහළේ"]
    ads_scraped = 0
    pages_scraped = 0

    # 1) Fetch page=1 to get pagination info
    url_page1 = construct_api_url(location_id, location_slug, page=1)
    resp1 = requests.get(url_page1)
    if resp1.status_code != 200:
        # If failed to fetch first page, we can return partial or zero
        return {
            "location_name": location_name,
            "excel_file": None,
            "ads_scraped": 0,
            "pages_scraped": 0
        }

    data_page1 = resp1.json()
    total_pages = get_pagination_info(data_page1)
    if total_pages == 0:
        total_pages = 1  # fallback if pagination data is missing

    # 2) For each page, parse ads
    # We'll store all records for each page in a temporary list, then append them
    # to Excel at once. Alternatively, you can append per page or at the end only.
    excel_file = None

    for page_num in range(1, total_pages + 1):
        url = construct_api_url(location_id, location_slug, page=page_num)
        resp = requests.get(url)
        if resp.status_code != 200:
            # If a page fails, you can break or skip it
            break

        data = resp.json()
        ads = data.get("ads", [])
        records_this_page = []
        for ad in ads:
            title = ad.get("title", "")
            # Skip if title has any forbidden keyword
            # Compare in lowercase for case-insensitive match
            t_lower = title.lower()
            if any(k.lower() in t_lower for k in skip_keywords):
                continue

            # Build a row matching your Excel columns
            description = ad.get("description", "")
            details = ad.get("details", "")
            price_str = ad.get("price", "")
            price_val = clean_price(price_str)
            shop_name = ad.get("shopName", "")
            slug = ad.get("slug", "")
            url_ = "https://ikman.lk/en/ad/" + slug
            location_ = ad.get("location", "")

            # "Date" column is today's date so you can identify the scrape day
            today_str = datetime.now().strftime("%Y-%m-%d")

            row = [
                location_slug,  # "Area Slug"
                location_,  # "Location"
                title,  # "Title"
                description,  # "Description"
                details,  # "Details"
                price_val,  # "Price (numeric)"
                shop_name,  # "Shop Name"
                slug,  # "Slug"
                url_,  # "URL"
                today_str  # "Date"
            ]
            records_this_page.append(row)

        # Append if we have any
        if records_this_page:
            excel_file = append_to_excel(records_this_page)
            ads_scraped += len(records_this_page)
            log_area.text(f"Scraped : {ads_scraped} ads. Page : {page_num} of {total_pages} pages for {location_name}")

    pages_scraped = page_num  # track the last successful page

    # Return a summary
    return {
        "location_name": location_name,
        "excel_file": excel_file,
        "ads_scraped": ads_scraped,
        "pages_scraped": pages_scraped
    }


def record_scrape_summary(summary_data):
    """
    After scraping multiple locations, combine the summary data,
    build a record, store in scrape_history.json via `add_history_record`.
    """
    total_ads = sum(item["ads_scraped"] for item in summary_data)
    total_pages = sum(item["pages_scraped"] for item in summary_data)
    last_file = summary_data[-1]["excel_file"] if summary_data else None

    record = {
        "timestamp": str(datetime.now()),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "locations_scraped": [s["location_name"] for s in summary_data],
        "total_pages_scraped": total_pages,
        "total_ads_scraped": total_ads,
        "excel_file": last_file
    }
    add_history_record(record)
