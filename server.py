import logging
import socket
import time
from flask import Flask, request, redirect, render_template
import os
import sqlite3
from pyngrok import ngrok
from PIL import Image
import httpx
import json

import qrcode
import yaml
from lib import epd2in13_V2
from google_apis import create_service

app = Flask(__name__)
service = None

# Load Configuration
CONFIG_FILE = 'config.yaml'
with open(CONFIG_FILE, 'r') as config_file:
    config = yaml.safe_load(config_file)
    config = config["app"]

# Config Parameters
DB_NAME = config.get('db_name', 'photos.db')
IMAGE_FOLDER = config.get('image_folder', 'images')
REFRESH_RATE = config['refresh_rate']
PLAYBACK_MODE = config['playback_mode']

os.makedirs(IMAGE_FOLDER, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT,
                        sequence INTEGER,
                        last_shown BOOLEAN DEFAULT 0)"""
    )
    conn.commit()
    conn.close()


init_db()


# Utils Functions
def get_qr_code(content: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


# Google Photos Picker API setup
def create_photos_picker_service(client_file, host_ip=None):
    api_name = "photospicker"
    version = "v1"
    scopes = ["https://www.googleapis.com/auth/photospicker.mediaitems.readonly"]
    return create_service(client_file, api_name, version, scopes, host_ip=host_ip)


# API and Session Configuration
client_file = "creds.json"
service = None
session_id, expire_time, picker_uri = None, None, None


@app.route("/")
def home():
    # Redirect to /picker as the default route
    return redirect("/picker")


@app.route("/picker", methods=["GET"])
def get_picker_uri():
    global session_id, expire_time, picker_uri
    try:
        session_id, expire_time, picker_uri = create_session(service)
        # Render a page with Picker URL and Confirm Button
        return render_template("picker.html", picker_uri=picker_uri)
    except Exception as e:
        print(f"Error during picker URI creation: {e}")
        return render_template("error.html", error_message="Failed to load Picker URI.")


@app.route("/confirm", methods=["POST"])
def confirm_selection():
    global session_id
    try:
        token = get_auth_token("./token_files/token_photospicker_v1.json")

        media_items = list_all_media_items(service, session_id)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        sequence = 0

        for media_item in media_items:
            file_name = media_item["mediaFile"]["filename"]
            file_path = os.path.join(IMAGE_FOLDER, file_name)

            # Check if the file already exists in the database
            cursor.execute("SELECT COUNT(*) FROM images WHERE path = ?", (file_path,))
            if cursor.fetchone()[0] > 0:
                # If the file exists, skip downloading it
                print(f"File {file_name} already exists in the database. Skipping download.")
                continue
            
            # If the file doesn't exist, download and store it
            download_media_item(media_item, token)

            cursor.execute(
                "INSERT INTO images (path, sequence) VALUES (?, ?)",
                (file_path, sequence),
            )
            sequence += 1

        conn.commit()
        conn.close()
        
        return redirect("/picker")
    except Exception as e:
        print(f"Error during image processing: {e}")
        return render_template(
            "error.html", error_message="Failed to download or store images."
        )


@app.route("/kill", methods=["GET"])
def kill():
    os.system("pkill -f ngrok")

    os.remove(DB_NAME)
    for file in os.listdir("images"):
        os.remove(os.path.join("images", file))
    os.rmdir("images")
    
    return "Server killed."


@app.errorhandler(500)
def internal_error(error):
    return (
        render_template("error.html", error_message="An unexpected error occurred."),
        500,
    )


# Google Photos Session Handlers
def create_session(service):
    response = service.sessions().create().execute()
    return response["id"], response["expireTime"], response["pickerUri"]


def get_auth_token(token_file):
    with open(token_file, "r") as token:
        return json.load(token)["token"]


def list_all_media_items(service, session_id, page_size=100):
    media_items = []
    next_page_token = None
    while True:
        response = (
            service.mediaItems()
            .list(sessionId=session_id, pageSize=page_size, pageToken=next_page_token)
            .execute()
        )
        media_items.extend(response.get("mediaItems", []))
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return media_items


def download_media_item(media_item, token):
    base_url = media_item["mediaFile"]["baseUrl"]
    file_name = media_item["mediaFile"]["filename"]
    download_url = f"{base_url}=d"

    media_response = httpx.get(
        download_url, headers={"Authorization": f"Bearer {token}"}
    )
    file_path = os.path.join(IMAGE_FOLDER, file_name)

    with open(file_path, "wb") as file:
        file.write(media_response.content)

    return file_name

def fetch_next_image():
    """
    Fetch the next image based on playback mode.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if PLAYBACK_MODE == 'sequential':
            # Get the last shown image
            cursor.execute("SELECT id, path FROM images WHERE last_shown = 1 ORDER BY sequence LIMIT 1")
            last_shown = cursor.fetchone()

            # Select the next image in sequence
            if last_shown:
                cursor.execute("UPDATE images SET last_shown = 0 WHERE id = ?", (last_shown[0],))
                cursor.execute(
                    """
                    SELECT id, path FROM images 
                    WHERE sequence > (SELECT sequence FROM images WHERE id = ?) 
                    ORDER BY sequence LIMIT 1
                    """,
                    (last_shown[0],)
                )
            else:
                cursor.execute("SELECT id, path FROM images ORDER BY sequence LIMIT 1")

        elif PLAYBACK_MODE == 'random':
            # Random playback mode
            cursor.execute("SELECT id, path FROM images ORDER BY RANDOM() LIMIT 1")
        else:
            logging.warning("Invalid playback mode. Defaulting to sequential.")
            cursor.execute("SELECT id, path FROM images ORDER BY sequence LIMIT 1")

        image = cursor.fetchone()

        # Update the last_shown flag
        if image:
            cursor.execute("UPDATE images SET last_shown = 1 WHERE id = ?", (image[0],))
            return image[1]  # Return full path to the image
        return None


def render_image(epd, image_path):
    """
    Render the given image on the e-paper display.
    """
    if not os.path.exists(image_path):
        logging.error(f"Image not found: {image_path}")
        return

    # Prepare the image for display
    image = Image.open(image_path).convert('1')
    image.thumbnail((epd.height, epd.width), Image.LANCZOS)

    # Center the image on the display
    canvas = Image.new('1', (epd.height, epd.width), 255)
    x_offset = (epd.height - image.width) // 2
    y_offset = (epd.width - image.height) // 2
    canvas.paste(image, (x_offset, y_offset))

    # Display the image
    epd.init(epd.FULL_UPDATE)
    epd.display(epd.getbuffer(canvas))
    time.sleep(2)  # Hold the image for stability
    epd.sleep()
    logging.info(f"Image rendered: {image_path}")


def display_QR(image: Image):
    logging.info("Displaying QR code...")
    epd = epd2in13_V2.EPD()
    render_image(epd, image)
    
    

def start_display_driver():
    """
    Main function to start the display driver.
    """
    try:
        logging.info("Initializing E-Paper display driver...")
        epd = epd2in13_V2.EPD()
        while True:
            image_path = fetch_next_image()
            if image_path:
                render_image(epd, image_path)
            else:
                logging.warning("No images available.")
            time.sleep(REFRESH_RATE)
    except KeyboardInterrupt:
        logging.info("Display driver interrupted.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        logging.info("Shutting down the display driver.")

service = None

def init_service(host_ip=None):
    global service
    service = create_photos_picker_service(client_file, host_ip=host_ip)

if __name__ == "__main__":
    os.system("pkill -f ngrok")

    public_url = ngrok.connect(5000)
    url = public_url.public_url
    qr_code = get_qr_code(url)
    display_QR(qr_code)
    hostname = url.split("//")[1].split(":")[0]
    ip_address = socket.gethostbyname(hostname)
    init_service(host_ip=ip_address)
    
    app.run(host="0.0.0.0", port=5000, debug=True)
