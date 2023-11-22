from datetime import datetime
import requests
import os
import json
from dotenv import load_dotenv
import concurrent.futures
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]

load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
BASE_URL=os.getenv('BASE_URL') # https://api.intra.42.fr
SHEET_ID=os.getenv('SHEET_ID') # from the uuid https://docs.google.com/spreadsheets/d/1p04SkQl8uigZ628tKmdSQ2FlJHcD3EFB41c7LXUzgy0/edit#gid=0
CAMPUS_ID=int(os.getenv('CAMPUS_ID')) # from the uuid https://docs.google.com/spreadsheets/d/1p04SkQl8uigZ628tKmdSQ2FlJHcD3EFB41c7LXUzgy0/edit#gid=0

class AccessToken:
    def __init__(self, token, type, expires_in, scope, created_at, valid_until):
        self.token = token
        self.type = type
        self.expires_in = expires_in
        self.scope = scope
        self.created_at = created_at
        self.valid_until = valid_until

def check_token_validity(access_token):
    if datetime.fromtimestamp(access_token.valid_until) > datetime.now():
        return True
    return False

def gen_token():
    res = requests.post(f'{BASE_URL}/oauth/token', data={
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })
    access_token = AccessToken(
        res.json()['access_token'],
        res.json()['token_type'],
        res.json()['expires_in'],
        res.json()['scope'],
        res.json()['created_at'],
        res.json()['secret_valid_until']
    )
    return access_token

def get_all_users_of_campus(campus_id, access_token):
    page_count = 1
    users = []

    def fetch_users(page_number):
        res = requests.get(f'{BASE_URL}/v2/campus/{campus_id}/users', params={
            'sort': '-updated_at,status',
            'status': 1,
            'page[size]': 100,
            'page[number]': page_number
        },
                           headers={
            'Authorization': f'Bearer {access_token.token}'
        })
        if (res.status_code != 200):
            return []
        users.extend(res.json())

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_users, page_count)]
        page_count += 1
        loop = True
        while loop:
            if len(futures) >= 10:
                completed, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in completed:
                    res = future.result()
                    if len(res) == 0:
                        loop = False
                    users.extend(future.result())
            if not isinstance(futures, list):
                futures = list(futures)
            futures.append(executor.submit(fetch_users, page_count))
            page_count += 1

    with open('users.json', 'w') as f:
        json.dump(users, f)

    return users


def get_users_onsite(access_token):
    if os.path.exists('users.json'):
        if input('Do you want to use the cached users.json? (y/n) ') == 'y':
            with open('users.json', 'r') as f:
                users = json.load(f)
        else:
            users = get_all_users_of_campus(CAMPUS_ID, access_token)
    else:
        users = get_all_users_of_campus(CAMPUS_ID, access_token)
    users_onsite = []

    for user in users:
        if user['location']:
            users_onsite.append(user)

    with open('users_onsite.json', 'w') as f:
        f.write(json.dumps(users_onsite))
    return users_onsite

def google_auth():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def google_sheets():
    creds = google_auth()

    try:
        service = build("sheets", "v4", credentials=creds)
        sheets = service.spreadsheets()

        return sheets

    except HttpError as error:
            print(f"An error occurred: {error}")


def sheetProperties(title, **kwargs):
    defaultProperties = {
        'properties': {
            'title': title,
            'index': 0,
            'sheetType': 'GRID',
            'hidden': False,
        }
    }
    defaultProperties.update(kwargs)
    return (defaultProperties)

def execute_request(users_onsite):
    try:
        sheets = google_sheets()
        time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
        # create sheet
        sheets.batchUpdate(
            spreadsheetId=SHEET_ID,
            body={
                'requests': [
                    {'addSheet': sheetProperties(time)},
                ]
            }
        ).execute()
        lastest_id = sheets.get(spreadsheetId=SHEET_ID).execute()["sheets"][0]["properties"]["sheetId"]
        sheets.batchUpdate(
            spreadsheetId=SHEET_ID,
            body={
                'requests': [
                    {
                        'updateCells': {
                            'start': {
                              "sheetId": lastest_id,
                              "rowIndex": 0,
                              "columnIndex": 0
                            },
                            'rows': [
                                {
                                    'values': [
                                        {
                                            'userEnteredValue': {
                                                'stringValue': 'Login'
                                            }
                                        },
                                        {
                                            'userEnteredValue': {
                                                'stringValue': 'Location'
                                            }
                                        },
                                        {
                                            'userEnteredValue': {
                                                'stringValue': 'Profile URL'
                                            }
                                        },
                                        {
                                            'userEnteredValue': {
                                                'stringValue': 'Profile Picture'
                                            }
                                        }
                                    ]
                                },
                                *[{
                                    'values': [
                                        {
                                            'userEnteredValue': {
                                                'stringValue': user["login"]
                                            }
                                        },
                                        {
                                            'userEnteredValue': {
                                                'stringValue': user["location"]
                                            }
                                        },
                                        {
                                            'userEnteredValue': {
                                                'stringValue': user["url"]
                                            }
                                        },
                                        {
                                            'userEnteredValue': {
                                                'stringValue': user["image"]["link"]
                                            }
                                        }
                                    ]
                                } for user in users_onsite]
                            ],
                            'fields': 'userEnteredValue'
                        }
                    }
                ]
            }
        ).execute()

        return "https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/edit#gid=" + str(lastest_id)

    except HttpError as error:
            print(f"An error occurred: {error}")

def main():
    print('Generating access token...')
    access_token = gen_token()
    print('Done!')
    print('Getting users on site...')
    users_onsite = get_users_onsite(access_token)
    users_onsite.sort(key=lambda x: x['location'])
    print('Done!')
    print('Adding users on site to google sheets...')
    url = execute_request(users_onsite)
    print('Done!')
    print(url)
if __name__ == '__main__':
    main()