from flask import Flask, render_template, request
import requests
import folium
import csv
import io
import time
from geopy.geocoders import Nominatim
import numpy as np
from sklearn.cluster import DBSCAN
from google import genai

app = Flask(__name__)


# API keys for external service interaction
FIRMS_MAP_KEY = "firmskey"

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
SOURCE_MAP = {
    "US/CANADA, Near/Ultra Real-time (LANDSAT)": "LANDSAT_NRT",
    "WORLD Near/Ultra Real-time (MODIS)": "MODIS_NRT",
    "WORLD Standard (MODIS)": "MODIS_SP",
    "WORLD Near/Ultra Real-time (VIIRS-20)": "VIIRS_NOAA20_NRT",
    "WORLD Near/Ultra Real-time (VIRRS-21)": "VIIRS_NOAA21_NRT",
    "WORLD Near/Ultra Real-time (VIIRS-SUMOI)": "VIIRS_SNPP_NRT",
    "WORLD Standard (VIIRS-SUMOI)": "VIIRS_SNPP_SP"
}

ALLOWED_SOURCES = list(SOURCE_MAP.keys())

gemini_client = genai.Client(api_key="placeholder")

# initialize API clients
geolocator = Nominatim(user_agent="wildfire_tracker_app")

def summarize_with_gemini(text):
    """
    Use Google Gemini AI to generate a summary of wildfire detection data
    Args:
        text (str): Raw detection data to summarize
    Returns:
        str: AI-generated summary of given data
    """
    prompt = (
        f"Please provide a concise summary and analysis, ignoring brightness, and give the exact names of potential risk areas of the following wildfire detection data:\n\n"
        f"{text}\n\nSummary:"
    )
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )
    return response.text

def reverse_geocode(lat, lon):
    """
    Convert coordinates to human-readable address
    Args:
        lat (float): Latitude
        lon (float): Longitude
    Returns:
        str: Address or "Unknown location" if geocoding fails
    """
    try:
        location = geolocator.reverse((lat, lon), language="en", timeout=10)
        if location and location.address:
            return location.address
    except Exception as e:
        print("Reverse geocoding error:", e)
    return "Unknown location"

def cluster_detections(detections):
    """
    Group nearby fire detections into clusters using DBSCAN
    Args:
        detections (list): List of detection dictionaries
    Returns:
        dict: Clustered risk areas with centroids and metadata
    """

    # extract coordinates from detections
    coords = []
    for det in detections:
        try:
            lat = float(det.get("latitude", 0))
            lon = float(det.get("longitude", 0))
            coords.append([lat, lon])
        except Exception:
            continue

    if not coords:
        return {}

    # perform clustering
    X = np.array(coords)
    clustering = DBSCAN(eps=0.5, min_samples=3).fit(X)
    labels = clustering.labels_

    # process clusters into risk areas
    risk_areas = {}
    unique_labels = set(labels)
    for label in unique_labels:
        if label == -1:
            continue
        cluster_points = X[labels == label]
        count = len(cluster_points)
        centroid = cluster_points.mean(axis=0)
        address = reverse_geocode(centroid[0], centroid[1])
        risk_areas[label] = {
            "centroid": (round(centroid[0], 6), round(centroid[1], 6)),
            "count": count,
            "address": address
        }
    return risk_areas

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main route handler for the web application
    Processes form submissions and displays wildfire data
    """
    results = None
    error_message = None
    detections = []  

    if request.method == "POST":
        # get form data
        source = request.form.get("source")
        area_coordinates = request.form.get("area_coordinates")
        day_range = request.form.get("day_range")
        start_date = request.form.get("start_date")

        # validate source
        if source not in ALLOWED_SOURCES:
            error_message = "Invalid source selected."
        else:
            # construct API URL
            source_code = SOURCE_MAP[source]
            if start_date:
                url = f"{BASE_URL}{FIRMS_MAP_KEY}/{source_code}/{area_coordinates}/{day_range}/{start_date}"
            else:
                url = f"{BASE_URL}{FIRMS_MAP_KEY}/{source_code}/{area_coordinates}/{day_range}"
            
            # fetch from FIRMS API
            try:
                response = requests.get(url)
                response.raise_for_status()
                csv_data = response.text
            except Exception as e:
                error_message = f"Error fetching FIRMS data: {e}"
                csv_data = ""

            if csv_data:
                try:
                    csv_reader = csv.DictReader(io.StringIO(csv_data))
                    for i, row in enumerate(csv_reader):
                        if i >= 300:
                            break
                        detections.append(row)
                except Exception as e:
                    error_message = f"Error parsing CSV data: {e}"

            # initialize map and summary
            wildfire_map = folium.Map(location=[40, -100], zoom_start=4)
            detailed_summary = "Detailed Fire Detections:\nTotal Detections: {}\n\n".format(len(detections))
            # process first 10 detections for detailed view
            for idx, detection in enumerate(detections[:10]):
                try:
                    lat = float(detection.get("latitude", 0))
                    lon = float(detection.get("longitude", 0))
                    acq_date = detection.get("acq_date", "N/A")
                    acq_time = detection.get("acq_time", "N/A")
                    brightness = detection.get("brightness", "N/A")
                    # add marker to map
                    popup_text = f"Date: {acq_date} {acq_time}<br>Brightness: {brightness}"
                    folium.Marker(
                        location=[lat, lon],
                        popup=popup_text,
                        icon=folium.Icon(color="red", icon="fire", prefix="fa")
                    ).add_to(wildfire_map)
                    # add to detailed summary
                    address = reverse_geocode(lat, lon)
                    detailed_summary += (
                        f"Detection {idx+1}: Date {acq_date} {acq_time}, Brightness: {brightness}, "
                        f"Coordinates: ({lat}, {lon}), Location: {address}\n"
                    )
                    time.sleep(1)
                except Exception as e:
                    print("Error processing a detection:", e)

            # process risk areas
            risk_areas = cluster_detections(detections)
            risk_summary = "\nIdentified Risk Areas (clusters with ≥ 3 detections):\n"
            if risk_areas:
                for label, info in risk_areas.items():
                    risk_summary += (
                        f"Cluster {label}: {info['count']} detections, "
                        f"Centroid: {info['centroid']}, Location: {info['address']}\n"
                    )
            else:
                risk_summary += "No significant risk areas identified based on clustering.\n"

            # combine summaries and get AI analysis
            full_summary_text = detailed_summary + risk_summary

            gemini_summary = summarize_with_gemini(full_summary_text)
            map_html = wildfire_map._repr_html_()

            # package results
            results = {
                "map_html": map_html,
                "full_summary_text": full_summary_text,
                "gemini_summary": gemini_summary,
                "num_detections": len(detections)
            }
    
    return render_template("index.html",
                           results=results,
                           error_message=error_message,
                           allowed_sources=ALLOWED_SOURCES,
                           active_fires=detections)

if __name__ == "__main__":
    app.run(debug=True)
