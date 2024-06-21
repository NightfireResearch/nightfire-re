#!/usr/bin/env python3
# Upload Nightfire translations to a spreadsheet

from __future__ import print_function

import io
import os
import os.path
import string
import unicodedata
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from lxml import etree

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '1bh8Zm1wmgGCLkIQn8KefkLLlugNEp6pzzTofWoivx5U'


#
# Authentication with Google APIs
#

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

gsheets = build('sheets', 'v4', credentials=creds)


#
# Sheets
#

languages = ["DU", "FR", "GR", "IT", "JAP", "SP", "SW", "UK", "USA"]

import common.extraction.extract_dat as extract_dat

translations = extract_dat.extract_all("platform_ps2/ps2_archives_extracted")


# Prepare the data for the request
data_to_insert = []

# Header row
header = ["Index", "Hashcode", "Enum Name"]
header.extend(languages)

data_to_insert.append({
        'range': f'Data!A1:L1',
        'values': [header]
    })

for idx in range(len(translations['UK'])):  # All are the same length

    rowData = [str(idx), f"{extract_dat.idx_to_hashcode(idx):08x}", ""]
    rowData.extend(translations[x][idx] for x in languages)

    data_to_insert.append({
        'range': f'Data!A{idx+2}:L{idx+2}',
        'values': [rowData]
    })

# Create a request to update the spreadsheet with the data
request = {
    'valueInputOption': 'RAW',
    'data': data_to_insert
}

# Execute the request to update the spreadsheet
response = gsheets.spreadsheets().values().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
    body={
        'data': data_to_insert,
        'valueInputOption': 'RAW'
    }
).execute()

# Print the response (optional)
print(response)
