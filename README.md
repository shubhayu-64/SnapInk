
# SnapInk

Turn your Raspberry Pi into a retro photo artist! This project lets you swipe through your favorite memories from Google Photos and display them in black-and-white elegance on an E-Ink screen. Think of it as a hipster slideshow—no flashy animations, just timeless grayscale beauty. Perfect for a desk companion, a thoughtful gift, or just to impress your friends with your DIY tech skills.


## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-repo/e-ink-slideshow.git
   cd e-ink-slideshow
   ```
2. Install the required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```
3. Add the `credentials.json` file from your GCP project (Photos Picker API enabled) to the project directory.

4. Configure ngrok with your authentication token:

    ```bash
    ngrok config add-authtoken <your_auth_token>
    ```

## Usage

1. **Run via SSH**  

   SSH into your Raspberry Pi and start the server manually:
   ```bash
   ssh pi@<your-raspberry-pi-ip>
   cd e-ink-slideshow
   python server.py
   ```
2. **Run on Startup**

    To make the server start automatically on boot, follow these steps:

    a. Open the crontab editor:
    ```bash
    crontab -e
    ```

    b. Add the following line at the end of the file to run `server.py` at boot:

    ```bash
    @reboot python /home/pi/e-ink-slideshow/server.py
    ```

    c. Save and exit the editor.

    d. Reboot your Raspberry Pi to verify the server starts automatically:

    ```bash
    sudo reboot
    ```

## Help

For common issues or errors, consider the following:

- Verify your credentials.json file is properly configured.
- Ensure your E-Ink display is connected and functional.
- Check ngrok logs for URL exposure issues.


## License

This project is licensed under the MIT License - see the LICENSE.md file for details.