import httpx
import json
from google_apis import create_service


def create_photos_picker_service(client_file):
    api_name = 'photospicker'
    version = 'v1'
    scopes = ['https://www.googleapis.com/auth/photospicker.mediaitems.readonly']
    return create_service(client_file, api_name, version, scopes)


def create_session(service):
    response = service.sessions().create().execute()
    return response["id"], response["expireTime"], response["pickerUri"]


def get_session(service, session_id):
    return service.sessions().get(sessionId=session_id).execute()


def list_all_media_items(service, session_id, page_size=100):
    media_items = []
    next_page_token = None
    
    
    while True:
        response = service.mediaItems().list(sessionId=session_id, pageSize=page_size, pageToken=next_page_token).execute()
        media_items.extend(response.get("mediaItems", []))
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    
    
    return media_items



def get_auth_token(token_file):
    with open(token_file, 'r') as token:
        return json.load(token)["token"]


def download_media_item(media_item, token):
    base_url = media_item["mediaFile"]["baseUrl"]
    file_name = media_item["mediaFile"]["filename"]
    download_url = f"{base_url}=d"
    
    
    media_response = httpx.get(download_url, headers={"Authorization": f"Bearer {token}"})
    
    
    with open("a" + file_name, "wb") as file:
        file.write(media_response.content)
    
    return file_name



client_file = 'creds.json'
service = create_photos_picker_service(client_file)


session_id, expire_time, picker_uri = create_session(service)
print(f"Session Created: {session_id}, Expires: {expire_time}, Picker URI: {picker_uri}")


session_info = get_session(service, session_id)
print(f"Session Info: {session_info}")


import time
time.sleep(30)


media_items = list_all_media_items(service, session_id)
print(f"Total Media Items: {len(media_items)}") 



token = get_auth_token('./token_files/token_photospicker_v1.json')


for media_item in media_items:
    file_name = download_media_item(media_item, token)
    print(f"Downloaded: {file_name}")