import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


def authenticate_drive():

    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")

    if gauth.credentials is None:
        gauth.LocalWebserverAuth()

    elif gauth.access_token_expired:
        gauth.Refresh()

    else:
        gauth.Authorize()

    gauth.SaveCredentialsFile("mycreds.txt")

    drive = GoogleDrive(gauth)

    return drive


def download_all_files(folder_id, local_folder):

    drive = authenticate_drive()

    os.makedirs(local_folder, exist_ok=True)

    processed_folder = local_folder.replace(
        "receipts", "processed_receipts"
    ).replace(
        "invoices", "processed_invoices"
    )

    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()
    print("Files found in Drive:", len(file_list))
    for file in file_list:
        print("Drive file detected:", file['title'])
        file_name = file['title']

        file_path = os.path.join(local_folder, file_name)
        processed_path = os.path.join(processed_folder, file_name)
        
        # ----------------------------------
        # SKIP IF FILE ALREADY PROCESSED
        # ----------------------------------

        if os.path.exists(file_path) or os.path.exists(processed_path):

            print("Already processed:", file_name)
            continue

        print("Downloading:", file_name)

        file.GetContentFile(file_path)

        print("Downloaded:", file_name)
