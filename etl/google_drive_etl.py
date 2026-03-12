from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import json
import os
import io


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = "service_account.json"


def authenticate_drive():

    if os.getenv("SERVICE_ACCOUNT_JSON"):

        service_account_info = json.loads(
            os.environ["SERVICE_ACCOUNT_JSON"]
        )

        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        print("Using service account from environment")

    elif os.path.exists(SERVICE_ACCOUNT_FILE):

        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        print("Using local service_account.json")

    else:

        raise Exception(
            "No Google credentials found."
        )

    service = build("drive", "v3", credentials=creds)

    return service


def download_all_files(folder_id, local_folder):

    service = authenticate_drive()

    os.makedirs(local_folder, exist_ok=True)

    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get("files", [])

    print("Files found:", len(files))

    for f in files:
        print("Drive file:", f["name"])

    for file in files:

        file_id = file["id"]
        file_name = file["name"]

        file_path = os.path.join(local_folder, file_name)

        if os.path.exists(file_path):

            print("Already downloaded:", file_name)
            continue

        print("Downloading:", file_name)

        request = service.files().get_media(fileId=file_id)

        fh = io.FileIO(file_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()

        print("Downloaded:", file_name)