# Ikman.lk Housing Data Scrape


## Description
This is a web scraper that scrapes housing data from ikman.lk.
Update the locations list in assets/locations.json to scrape data from different locations.

## Features
- Scrape data from ikman.lk
- Filter data based on location, price, number of bedrooms, and number of bathrooms
- Sort data based on price, number of bedrooms, and number of bathrooms
- Search only for 2 storied houses less than 25M LKR

## Steps to Run
````
docker build -t ikman-scraper:latest .
docker run -it --rm -p 8501:8501 ikman-scraper:latest

Open the browser and go to http://localhost:8501
````