import streamlit as st
from datetime import datetime
import os

# Import your modules
from ikman_scraper.data import load_locations, load_history, add_record_to_history
from ikman_scraper.scraping import scrape_single_location


def main():
    st.set_page_config(page_title="Ikman Scraper", layout="wide")
    st.title("Ikman Scraper Web UI")

    # TABS
    tab_scrape, tab_process, tab_history = st.tabs(["Scrape", "Start Process", "History"])

    # ----------------------------
    # TAB: Scrape
    # ----------------------------
    with tab_scrape:
        st.header("Scrape Settings")

        # Load possible locations
        all_locations = load_locations()
        if not all_locations:
            st.error("No locations found in the JSON file!")
        else:
            # MULTISELECT: Choose locations
            loc_choices = [loc["name"] for loc in all_locations]
            selected_names = st.multiselect(
                "Select one or more locations",
                options=loc_choices,
                default=None
            )

            if st.button("Start Scrape"):
                # Filter the location objects
                selected_locs = [
                    loc for loc in all_locations if loc["name"] in selected_names
                ]
                if not selected_locs:
                    st.warning("No locations selected.")
                else:
                    # Store in session state
                    st.session_state["selected_locs"] = selected_locs
                    st.session_state["scrape_in_progress"] = True
                    st.success("Locations selected. Go to 'Start Process' tab to see progress.")

    # ----------------------------
    # TAB: Start Process
    # ----------------------------
    with tab_process:
        st.header("Scrape Progress")

        if "scrape_in_progress" not in st.session_state:
            st.session_state["scrape_in_progress"] = False

        if st.session_state.get("scrape_in_progress"):
            selected_locs = st.session_state.get("selected_locs", [])
            total_count = len(selected_locs)

            if not selected_locs:
                st.info("No locations to scrape. Go back to 'Scrape' tab.")
            else:
                # Show a progress bar
                progress_bar = st.progress(0)
                log_area = st.empty()

                summary_data = []
                for i, loc in enumerate(selected_locs, start=1):
                    def st_logger(msg):
                        """Log to the log_area (Streamlit)."""
                        # We can display the log, plus keep previous lines
                        if "log_text" not in st.session_state:
                            st.session_state["log_text"] = ""
                        st.session_state["log_text"] += f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n"
                        log_area.text(st.session_state["log_text"])

                    st_logger(f"Scraping {loc['name']}...")
                    location_summary = scrape_single_location(loc, st_logger=st_logger)
                    if location_summary:
                        summary_data.append(location_summary)

                    # Update progress
                    progress_val = int(i / total_count * 100)
                    progress_bar.progress(progress_val)

                st.session_state["scrape_in_progress"] = False
                progress_bar.progress(100)
                st.success("Scrape process completed.")

                # Summarize results
                if summary_data:
                    total_ads = sum(s["ads_scraped"] for s in summary_data)
                    total_pages = sum(s["pages_scraped"] for s in summary_data)
                    st.subheader("Scrape Summary")
                    st.write(f"**Locations scraped**: {len(summary_data)}")
                    st.write(f"**Total ads scraped**: {total_ads}")
                    st.write(f"**Total pages scraped**: {total_pages}")
                    last_file = summary_data[-1]["excel_file"]
                    if last_file and os.path.exists(last_file):
                        st.markdown(f"**Excel File**: [{last_file}]({last_file})")

                    # Save history log
                    record = {
                        "timestamp": str(datetime.now()),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "locations_scraped": [s["location_name"] for s in summary_data],
                        "total_pages_scraped": total_pages,
                        "total_ads_scraped": total_ads,
                        "excel_file": last_file
                    }
                    add_record_to_history(record)

        else:
            st.info("No scrape in progress. Go to 'Scrape' tab to select and start.")

    # ----------------------------
    # TAB: History
    # ----------------------------
    with tab_history:
        st.header("Scrape History")

        history = load_history()
        if not history:
            st.write("No scrape history recorded yet.")
        else:
            for i, run in enumerate(reversed(history), start=1):
                st.markdown("---")
                st.subheader(f"Run {i}")
                st.write(f"**Timestamp**: {run['timestamp']}")
                st.write(f"**Date**: {run['date']}")
                if "locations_scraped" in run:
                    st.write(f"**Locations**: {', '.join(run['locations_scraped'])}")
                st.write(f"**Total Pages**: {run.get('total_pages_scraped', 0)}")
                st.write(f"**Total Ads**: {run.get('total_ads_scraped', 0)}")

                file_path = run.get("excel_file", "")
                if file_path and os.path.exists(file_path):
                    st.markdown(f"**Excel File**: [{file_path}]({file_path})")
                else:
                    st.write("Excel file not found or no file recorded.")


# If running this file directly, you can do:
#   streamlit run ikman_scraper/ui.py
# or you can call the `main()` function from an external script.
if __name__ == "__main__":
    main()
