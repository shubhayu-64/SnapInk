import os
import time
import logging
import sqlite3
import yaml
from lib import epd2in13_V2
from PIL import Image

# Load Configuration
CONFIG_FILE = 'config.yaml'
with open(CONFIG_FILE, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Config Parameters
DB_NAME = config['app']['db_name']
IMAGE_FOLDER = config['app']['image_folder']
REFRESH_RATE = config['display']['refresh_rate']
PLAYBACK_MODE = config['display']['playback_mode']

# Logging Configuration
logging.basicConfig(level=config['log_level'])

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


if __name__ == '__main__':
    start_display_driver()
