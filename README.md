# <img src="static/logo.png" alt="Logo" style="width: 100px; height: 100px; vertical-align: middle;">
# Wildfire Risk Tracker

Wildfire Risk Tracker is a Flask-based web application that retrieves real-time wildfire detection data from NASA FIRMS, visualizes the data using interactive maps (Folium for detailed markers and Leaflet for a heatmap), clusters and reverse-geocodes detections to identify high-risk areas, and generates a concise summary of the wildfire data using the Google Gemini API via the `google-genai` client.

## Features

- **Real-time Data Retrieval:**  
  Fetches wildfire detection data from NASA FIRMS (limited to 300 entries) based on user-specified parameters.
  
- **Interactive Mapping:**  
  Displays detailed markers on a Folium-generated map and a dynamic heatmap (using Leaflet and the Leaflet.heat plugin) based on active fire data.
  
- **Risk Clustering:**  
  Uses DBSCAN clustering to identify high-risk areas from the detection data, with reverse geocoding for human-readable addresses.
  
- **Gemini Summarization:**  
  Generates a concise summary of the wildfire detection data by sending a prompt to the Gemini API using the `google-genai` client.
  
- **Customizable Inputs:**  
  Offers a web form for selecting data source, area coordinates, day range, and start date.

## Prerequisites

- **Python:** 3.7 or higher.
- **NASA FIRMS MAP_KEY:** A valid API key for accessing FIRMS data.
- **Gemini API Key:** Your API key for the Google Gemini API.
- **Google OAuth2 Credentials:** A `client_secret.json` file (placed in the project root) to generate and cache the access token in `token.json`.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/educationmoment/Sparkhacks-2025.git
   cd Sparkhacks-2025
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
```
  
