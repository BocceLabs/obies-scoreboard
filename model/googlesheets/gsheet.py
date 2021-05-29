# imports
import os
import pickle

# Google Sheets imports
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


############################
# Google sheet constants   #
############################
# todo move these constants to a config file (YAML or JSON)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
# the spreadsheet ID comes from the URL in your browser (after the /d/ and before the next /
SAMPLE_SPREADSHEET_ID = '1FoPvsKECQE-jigz6fM3W8uvwQolrqHgiwRznkcnIeDQ'
SAMPLE_RANGE_NAME = '2020-02-11!A1:E50'

class GSheet:
    def __init__(self):
        self.sheet = None
        self.connect()

    def connect(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        self.sheet = service.spreadsheets()

    def get_values(self, range_str, spreadsheetId=SAMPLE_SPREADSHEET_ID):
        """Shows basic usage of the Sheets API.
        Prints values from a sample spreadsheet.
        """
        
        result = self.sheet.values().get(spreadsheetId=spreadsheetId,
                                    range=range_str).execute()
        values = result.get('values', [])

        return values
        
    def next_available_row(self, worksheet, spreadsheet_id=SAMPLE_SPREADSHEET_ID):
        result = self.sheet.values().get(spreadsheetId=spreadsheetId,
            range="{}!A1:B1000".format(worksheet)).execute()
        values = result.get('values', [])
        return str(len(values)+1)
        
    def set_values(self, cellRange, values, spreadsheet_id=SAMPLE_SPREADSHEET_ID):
        body = {"values": values}
        result = self.sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID,
            range=cellRange, valueInputOption='USER_ENTERED',
            body=body).execute()
        print("{} cells updated".format(str(result.get("updatedCells"))))
