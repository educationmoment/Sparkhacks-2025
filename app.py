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


FIRMS_MAP_KEY = "6f645ed435dbe07885371d90c76f39a7"
BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
ALLOWED_SOURCES = [
    "LANDSAT_NRT",       # US/Canada only LANDSAT Near Real-Time, Real-Time and Ultra Real-Time
    "MODIS_NRT",         # MODIS Near Real-Time, Real-Time and Ultra Real-Time
    "MODIS_SP",          # MODIS Standard Processing
    "VIIRS_NOAA20_NRT",  # VIIRS NOAA-20 Near Real-Time, Real-Time and Ultra Real-Time
    "VIIRS_NOAA21_NRT",  # VIIRS NOAA-21 Near Real-Time, Real-Time and Ultra Real-Time
    "VIIRS_SNPP_NRT",    # VIIRS Suomi-NPP Near Real-Time, Real-Time and Ultra Real-Time
    "VIIRS_SNPP_SP"      # VIIRS Suomi-NPP Standard Processing
]

gemini_client = genai.Client(api_key="AIzaSyDipXpuqsvnDVmPqxYgHnRPCDRIp59rPXY")

geolocator = Nominatim(user_agent="wildfire_tracker_app")


def summarize_with_gemini(text):
    """
    Uses the Gemini API to generate a summary for the given text.
    The function builds a prompt and calls the Gemini model "gemini-2.0-flash".
    """
    prompt = (
        f"Please provide a concise summary and analysis of the following wildfire detection data:\n\n"
        f"{text}\n\nSummary:"
    )
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )
    return response.text


def reverse_geocode(lat, lon):
    """Return a resolved address (or 'Unknown location') for given latitude and longitude."""
    try:
        location = geolocator.reverse((lat, lon), language="en", timeout=10)
        if location and location.address:
            return location.address
    except Exception as e:
        print("Reverse geocoding error:", e)
    return "Unknown location"

def cluster_detections(detections):

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

    X = np.array(coords)
    clustering = DBSCAN(eps=0.5, min_samples=3).fit(X)
    labels = clustering.labels_

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
    results = None
    error_message = None
    detections = []  

    if request.method == "POST":
        source = request.form.get("source")
        area_coordinates = request.form.get("area_coordinates")
        day_range = request.form.get("day_range")
        start_date = request.form.get("start_date")

        if source not in ALLOWED_SOURCES:
            error_message = "Invalid source selected."
        else:
            if start_date:
                url = f"{BASE_URL}{FIRMS_MAP_KEY}/{source}/{area_coordinates}/{day_range}/{start_date}"
            else:
                url = f"{BASE_URL}{FIRMS_MAP_KEY}/{source}/{area_coordinates}/{day_range}"
            
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

            wildfire_map = folium.Map(location=[40, -100], zoom_start=4)
            detailed_summary = "Detailed Fire Detections:\nTotal Detections: {}\n\n".format(len(detections))
            
            for idx, detection in enumerate(detections[:10]):
                try:
                    lat = float(detection.get("latitude", 0))
                    lon = float(detection.get("longitude", 0))
                    acq_date = detection.get("acq_date", "N/A")
                    acq_time = detection.get("acq_time", "N/A")
                    brightness = detection.get("brightness", "N/A")
                    popup_text = f"Date: {acq_date} {acq_time}<br>Brightness: {brightness}"
                    folium.Marker(
                        location=[lat, lon],
                        popup=popup_text,
                        icon=folium.Icon(color="red", icon="fire", prefix="fa")
                    ).add_to(wildfire_map)
                    address = reverse_geocode(lat, lon)
                    detailed_summary += (
                        f"Detection {idx+1}: Date {acq_date} {acq_time}, Brightness: {brightness}, "
                        f"Coordinates: ({lat}, {lon}), Location: {address}\n"
                    )
                    time.sleep(1)
                except Exception as e:
                    print("Error processing a detection:", e)
            
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

            full_summary_text = detailed_summary + risk_summary

            gemini_summary = summarize_with_gemini(full_summary_text)
            map_html = wildfire_map._repr_html_()

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
