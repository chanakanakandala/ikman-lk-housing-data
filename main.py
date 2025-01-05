# main.py
import streamlit.web.cli as stcli
import sys
import os


def main():
    ui_path = os.path.join("ikman_scraper", "ui.py")
    sys.argv = ["streamlit", "run", ui_path]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
