import sys
import os
import streamlit.web.cli as stcli


def main():
    # Path to your Streamlit UI script
    ui_path = os.path.join("ikman_scraper", "presentation", "ui.py")

    # Replace the current sys.argv so Streamlit sees: "streamlit run ui.py --server.port=8501"
    sys.argv = ["streamlit", "run", ui_path, "--server.port=8501"]

    # Call the public Streamlit CLI entry point
    stcli.main()


if __name__ == "__main__":
    main()
