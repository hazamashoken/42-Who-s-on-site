# Who's on site ?
## Description
This is a simple python script that will get the list of users currently on site and add it to google sheets.

## Requirements
- python3
- poetry
- google client keys in `credentials.json`


## links
- https://console.cloud.google.com/apis/api/sheets.googleapis.com/

## Installation
```bash
poetry install
```

## Usage
```bash
poetry run main.py
```

### .env
```
# 42 api credentials
CLIENT_ID=
CLIENT_SECRET=22a

BASE_URL=https://api.intra.42.fr

# google spreadsheets uuid
SHEET_ID=

# 42 campus id
CAMPUS_ID=
```

### Author
- [Thanapol Liangsoonthornsit](https://github.com/hazamashoken)
