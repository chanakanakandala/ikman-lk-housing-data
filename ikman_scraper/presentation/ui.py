import streamlit as st
from datetime import datetime
import os

# Domain or data layer references
from ikman_scraper.data.data_access import load_history, load_locations
from ikman_scraper.services.scrape_service import scrape_location, record_scrape_summary
from ikman_scraper.services.cleanup_service import cleanup_duplicates


def main():
    st.set_page_config(page_title="Ikman Scraper", layout="wide")
    st.title("Ikman Scraper Web UI")

    tab_scrape, tab_process, tab_history, tab_cleanup = st.tabs(
        ["Scrape", "Start Process", "History", "Cleanup"]
    )

    # ----------------------------------
    # TAB: SCRAPE
    # ----------------------------------
    with tab_scrape:
        st.header("Scrape Settings")
        all_locs = load_locations()
        if not all_locs:
            st.error("No locations found.")
        else:
            names = [l["name"] for l in all_locs]
            selection = st.multiselect("Select locations", options=names)

            if st.button("Start Scrape"):
                if not selection:
                    st.warning("No locations selected.")
                else:
                    st.session_state["selected_locs"] = [
                        loc for loc in all_locs if loc["name"] in selection
                    ]
                    st.session_state["scrape_in_progress"] = True
                    st.success("Locations selected. Go to 'Start Process' tab.")

    # ----------------------------------
    # TAB: START PROCESS (example)
    # ----------------------------------
    with tab_process:
        st.header("Scrape Progress")
        if "scrape_in_progress" not in st.session_state:
            st.session_state["scrape_in_progress"] = False

        if st.session_state["scrape_in_progress"]:
            selected_locs = st.session_state.get("selected_locs", [])
            if not selected_locs:
                st.info("No locations to scrape.")
            else:
                progress_bar = st.progress(0)
                log_area = st.empty()
                summary_list = []

                for i, loc in enumerate(selected_locs, start=1):
                    log_area.text(f"Scraping Started for {loc['name']}...This will take few minutes to complete.")
                    res = scrape_location(loc, log_area)
                    if res:
                        summary_list.append(res)
                    progress_bar.progress(int(i / len(selected_locs) * 100))

                st.session_state["scrape_in_progress"] = False
                st.success("Scrape process complete.")
                record_scrape_summary(summary_list)

        else:
            st.info("No scrape in progress.")

    # ----------------------------------
    # TAB: HISTORY
    # ----------------------------------
    with tab_history:
        st.header("Scrape History")
        history = load_history()
        if not history:
            st.write("No history found.")
        else:
            for idx, run in enumerate(reversed(history), start=1):
                st.subheader(f"Run {idx}")
                st.write(f"**Date**: {run['date']}")
                st.write(f"**Ads**: {run['total_ads_scraped']}")
                st.write(f"**Pages**: {run['total_pages_scraped']}")
                file_ = run.get("excel_file", "")
                if file_ and os.path.exists(file_):
                    st.markdown(f"[Open Excel File]({file_})")

    # ----------------------------------
    # TAB: CLEANUP
    # ----------------------------------
    with tab_cleanup:
        st.header("Cleanup Duplicate Records")

        # Build a list of dates from history
        history = load_history()
        if not history:
            st.info("No scrape history. Nothing to clean up.")
            return

        all_dates = sorted(list({h["date"] for h in history}))
        if not all_dates:
            st.info("No valid dates in history.")
            return

        start_date_str = st.selectbox("Start Date", all_dates, index=0)
        end_date_str = st.selectbox("End Date", all_dates, index=len(all_dates) - 1)

        if st.button("Cleanup"):
            dt_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            dt_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            result = cleanup_duplicates(dt_start, dt_end)
            if result["success"]:
                st.success(result["message"])
                if os.path.exists(result["file"]):
                    st.markdown(f"[Open Cleaned File]({result['file']})")
            else:
                st.error(result["message"])


if __name__ == "__main__":
    main()
