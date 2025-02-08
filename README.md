# Wildfire Risk Tracker with GPU-Accelerated Local LLM

A Flask web application that retrieves wildfire detection data from NASA FIRMS, visualizes it on an interactive map (using Folium), clusters detections to identify risk areas, reverse-geocodes coordinates to human-readable addresses, and uses a GPU-accelerated local summarization model (via Hugging Face Transformers) to produce concise analyses.

> **Note:**  
> This project requires a CUDA-capable GPU and a PyTorch installation with CUDA support to fully leverage GPU acceleration.

## Features

- **Live Data Retrieval:**  
  Fetches wildfire detection data from NASA FIRMS using a configurable API.

- **Interactive Mapping:**  
  Uses [Folium](https://python-visualization.github.io/folium/) to display detections on an interactive map.

- **Reverse Geocoding:**  
  Converts geographic coordinates into human-readable addresses using [Nominatim](https://nominatim.org/).

- **Clustering:**  
  Identifies risk areas by clustering nearby detections with DBSCAN.

- **Local LLM Summarization:**  
  Leverages a local summarization model (e.g., `microsoft/Phi-3-mini-128k-instruct`) on GPU to produce concise summaries.

- **Customizable Inputs:**  
  A user-friendly web form allows you to select the data source, geographic area, day range, and start date.

## Prerequisites

- **Python:** 3.7 or higher.
- **CUDA-enabled GPU:** Required for GPU acceleration.
- **PyTorch:** Installed with CUDA support.
- **Other Python Packages:** Listed in the [Installation](#installation) section.

## Installation


   ```bash
   git clone https://github.com/educationmoment/Sparkhacks-2025.git
   cd Sparkhacks-2025
   pip install -r requirements.txt
   python3 app.py
   Navigate to http://127.0.0.1:5000.
   ```

