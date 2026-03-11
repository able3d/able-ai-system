from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
import os


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = "service_account.json"


def authenticate_drive():

    creds = None

    # -----------------------------
    # RUNNING ON RENDER
    # -----------------------------
    if os.getenv("SERVICE_ACCOUNT_JSON"):

        service_account_info = json.loads(
            os.environ["SERVICE_ACCOUNT_JSON"]
        )

        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        print("Using service account from environment")

    # -----------------------------
    # RUNNING LOCALLY
    # -----------------------------
    elif os.path.exists(SERVICE_ACCOUNT_FILE):

        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        print("Using local service_account.json")

    else:

        raise Exception(
            "No Google credentials found. "
            "Add SERVICE_ACCOUNT_JSON to environment or provide service_account.json"
        )

    service = build(
        "drive",
        "v3",
        credentials=creds
    )

    return service


def download_all_files(folder_id, local_folder):

    service = authenticate_drive()

    os.makedirs(local_folder, exist_ok=True)

    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    print("Files found:", len(files))

    for file in files:

        file_id = file["id"]
        file_name = file["name"]

        file_path = os.path.join(local_folder, file_name)

        if os.path.exists(file_path):

            print("Already downloaded:", file_name)
            continue

        print("Downloading:", file_name)

        request = service.files().get_media(fileId=file_id)

        with open(file_path, "wb") as f:
            f.write(request.execute())

        print("Downloaded:", file_name)
