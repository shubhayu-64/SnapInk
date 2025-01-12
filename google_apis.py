import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow

def create_service(client_secret_file, api_name, api_version, *scopes, prefix="", host_ip=None):
    # Constants
    CLIENT_SECRET_FILE = client_secret_file
    API_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    # Directory for storing tokens
    working_dir = os.getcwd()
    token_dir = 'token_files'
    token_file = f"token_{API_NAME}_{API_VERSION}{prefix}.json"
    token_path = os.path.join(working_dir, token_dir, token_file)

    # Ensure the token directory exists
    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    # Load existing credentials
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh or obtain new credentials
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if host_ip:  # Device flow for SSH (No browser support)
                    print("Using device flow authentication...")
                    flow = Flow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES)
                    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f"Go to the following URL in a browser on any device:\n{auth_url}")
                    code = input("Enter the authorization code: ")
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                else:  # Local server flow (supports browser)
                    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                    creds = flow.run_local_server(port=0, success_message="Authentication complete. You may close this window.")
            
            # Save the credentials
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Authentication error: {e}")
            return None

    # Build and return the service
    try:
        service = build(API_NAME, API_VERSION, credentials=creds, static_discovery=False)
        print(f"{API_NAME} {API_VERSION} service created successfully.")
        return service
    except Exception as e:
        print(f"Unable to connect. Error: {e}")
        print(f"Failed to create service instance for {API_NAME}. Deleting invalid token file.")
        if os.path.exists(token_path):
            os.remove(token_path)
        return None
