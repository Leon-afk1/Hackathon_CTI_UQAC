FROM python:3.12-slim

WORKDIR /app

# Install Chromium for Kaleido (needed for Plotly image export)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ . 

EXPOSE 8502

# Run Streamlit with live reload
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0", "--server.headless=true"]
