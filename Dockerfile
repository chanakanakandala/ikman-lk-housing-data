# 1) Use a lightweight Python image
FROM python:3.9-slim-buster

# 2) Create a working directory in the container
WORKDIR /app

# 3) Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy the entire project into the container
COPY . .

# 5) Expose the port Streamlit listens on
EXPOSE 8501

# 6) Default command to launch Streamlit on port 8501
CMD ["streamlit", "run", "ikman_scraper/ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
