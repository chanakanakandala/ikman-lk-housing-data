import requests
from datetime import datetime
from .data import append_to_excel, clean_price, ensure_excel_file


def construct_api_url(location_id, location_slug, page):
    """
    Build the API URL for a given location/page with the filter_json from prompt.
    """
    base_url = (
        "https://ikman.lk/data/serp?top_ads=2&spotlights=5&sort=date&order=desc&buy_now=0&urgent=0"
        "&categorySlug=houses-for-sale"
        f"&locationSlug={location_slug}"
        "&category=415"
        f"&location={location_id}"
        f"&page={page}"
        "&filter_json=[%7B%22type%22:%22money%22,%22key%22:%22price%22,%22maximum%22:25000000%7D,"
        "%7B%22type%22:%22enum%22,%22key%22:%22bedrooms%22,%22values%22:[%223%22,%224%22,%225%22]%7D,"
        "%7B%22type%22:%22enum%22,%22key%22:%22bathrooms%22,%22values%22:[%222%22]%7D]"
    )
    return base_url


def get_pagination_info(json_response):
    """
    Return total pages from "paginationData" => floor(total / pageSize)
    """
    pagination = json_response.get("paginationData", {})
    total = pagination.get("total", 0)
    page_size = pagination.get("pageSize", 1)
    if page_size == 0:
        return 0
    return total // page_size


def parse_ads(json_data, area_slug):
    ads = json_data.get("ads", [])
    results = []

    # Keywords to skip if found in 'title'
    skip_keywords = ["Single", "තනි තට්ටු", "තනිමහල්"]

    # Current date (e.g. "2025-01-05")
    today_str = datetime.now().strftime("%Y-%m-%d")

    for ad in ads:
        title = ad.get("title", "")

        # --- 1) Check if we should skip this ad ---
        # Convert both the title and skip keywords to lowercase for case-insensitive match
        title_lower = title.lower()
        if any(k.lower() in title_lower for k in skip_keywords):
            # If any forbidden keyword appears, skip this record
            continue

        location_ = ad.get("location", "")
        description = ad.get("description", "")
        details = ad.get("details", "")
        price_str = ad.get("price", "")
        price_num = clean_price(price_str)  # Or however you clean the price
        shop_name = ad.get("shopName", "")
        slug = ad.get("slug", "")
        url = "https://ikman.lk/en/ad/" + slug

        row = [
            area_slug,
            today_str,
            location_,
            title,
            description,
            details,
            price_num,
            shop_name,
            url,
            ""
        ]
        results.append(row)

    return results


def scrape_single_location(loc, st_logger=None):
    """
    Scrapes a single location dict like: {"id":10, "name":"Ampara", "slug":"ampara"}.
    st_logger is optional (a function that logs to the Streamlit UI).
    Returns a dict with summary:
      {
        "location_name": str,
        "pages_scraped": int,
        "ads_scraped": int,
        "excel_file": path_to_excel
      }
    """
    location_id = loc["id"]
    location_slug = loc["slug"]

    if st_logger:
        st_logger(f"Starting {loc['name']} (slug={location_slug})")

    # 1) Fetch page=1 to get pagination info
    url1 = construct_api_url(location_id, location_slug, 1)
    resp = requests.get(url1)
    if resp.status_code != 200:
        if st_logger:
            st_logger(f"Failed to fetch page=1 for {location_slug}, status: {resp.status_code}")
        # Return partial summary or None
        return None

    data_page1 = resp.json()
    total_pages = get_pagination_info(data_page1)
    if st_logger:
        st_logger(f"Total pages for {location_slug}: {total_pages}")

    # 2) Parse page 1 ads, append to excel
    ads_page1 = parse_ads(data_page1, location_slug)
    append_to_excel(ads_page1)
    ads_scraped = len(ads_page1)

    # 3) Iterate pages 2..total_pages
    for page_num in range(2, total_pages + 1):
        url_n = construct_api_url(location_id, location_slug, page_num)
        resp_n = requests.get(url_n)
        if resp_n.status_code == 200:
            data_n = resp_n.json()
            page_records = parse_ads(data_n, location_slug)
            append_to_excel(page_records)
            ads_scraped += len(page_records)
            if st_logger:
                st_logger(f"  Page {page_num} done ({len(page_records)} ads).")
        else:
            if st_logger:
                st_logger(f"  Failed on page {page_num} (status {resp_n.status_code}). Stopping.")
            break

    # 4) Return final summary
    _, _, excel_file = ensure_excel_file()
    summary = {
        "location_name": loc["name"],
        "pages_scraped": total_pages if total_pages else 1,
        "ads_scraped": ads_scraped,
        "excel_file": excel_file,
    }
    if st_logger:
        st_logger(f"Finished {loc['name']} (slug={location_slug}) - {ads_scraped} ads total.")
    return summary
