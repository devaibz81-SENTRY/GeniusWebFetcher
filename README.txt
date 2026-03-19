# NEBL Fetch Server

Python Flask app to fetch and extract player statistics from Genius Sports.

## Setup

1. Run `setup.bat` to install dependencies
2. Run `python fetch_server.py` to start server
3. Open browser to http://localhost:5000

## Endpoints

- `/` - HTML interface
- `/fetch` - Fetch data from Genius Sports
- `/data` - Get cached JSON data
- `/health` - Health check

## Deploy to Render

1. Push to GitHub
2. Connect repo to Render.com
3. Deploy!

## Requirements

- Python 3.8+
- Chrome/Chromium (for Selenium if needed)
