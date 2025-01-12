import os
import logging
import argparse
import qrcode
import requests
from lib import epd2in13_V2
from PIL import Image
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def flush_screen(epd):
    logging.info("Flushing screen...")
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)
    epd.sleep()
    logging.info("Screen flushed.")

def download_image(url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            logging.info(f"Downloading image from URL: {url}")
            image_path = '/tmp/temp_image.png'
            with open(image_path, 'wb') as out_file:
                out_file.write(response.content)
            return image_path
        else:
            logging.error(f"Failed to download image. HTTP Status: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error downloading image: {e}")
        return None


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


def render_image(epd, image_source):
    if isinstance(image_source, str) and image_source.startswith('http'):
        image_source = download_image(image_source)
        if not image_source:
            return

    if isinstance(image_source, str):
        if not os.path.exists(image_source):
            logging.error(f"Image file not found: {image_source}")
            return
        logging.info(f"Rendering image from file: {image_source}")
        image = Image.open(image_source)
    else:
        logging.info("Rendering image from object")
        image = image_source

    image = image.convert('1')  # Convert to 1-bit black-and-white
    
    # Maintain aspect ratio
    image.thumbnail((epd.height, epd.width), Image.LANCZOS)
    canvas = Image.new('1', (epd.height, epd.width), 255)  # White background
    x_offset = (epd.height - image.width) // 2
    y_offset = (epd.width - image.height) // 2
    canvas.paste(image, (x_offset, y_offset))
    image = canvas

    epd.init(epd.FULL_UPDATE)
    epd.display(epd.getbuffer(image))
    time.sleep(2)
    epd.sleep()
    logging.info("Image rendered.")


def main():
    parser = argparse.ArgumentParser(description="CLI tool for e-ink display rendering.")
    parser.add_argument('-f', '--flush', action='store_true', help='Flush the screen to clear content')
    parser.add_argument('-i', '--image', type=str, help='Path or URL to the image file to render')
    parser.add_argument('-q', '--qr', type=str, help='Content to render as QR code')

    args = parser.parse_args()

    try:
        logging.info("Initializing e-ink display")
        epd = epd2in13_V2.EPD()

        if args.flush:
            flush_screen(epd)

        if args.image:
            render_image(epd, args.image)
        
        if args.qr:
            qr_code = get_qr_code(args.qr)
            render_image(epd, qr_code)

        if not args.flush and not args.image:
            logging.warning("No actions specified. Use --flush or --image <path>.")

    except IOError as e:
        logging.error(e)

    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
        epd2in13_V2.epdconfig.module_exit(cleanup=True)
    
    exit(0)

if __name__ == '__main__':
    main()