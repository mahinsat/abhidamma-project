import json
import time
import boto3
import jwt
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# Define your AWS DynamoDB table name
DYNAMODB_TABLE_NAME = "ZoomMembers"

# Environment variables expected:
# - GCP_CREDS: JSON string of Google service account
# - SHEET_ID: Google Sheet ID (from URL)
# - ZOOM_CLIENT_ID
# - ZOOM_CLIENT_SECRET
# - ZOOM_MEETING_ID

def lambda_handler(event, context):
    # 1. Load Google Credentials
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.environ['GCP_CREDS']),
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )

    # 2. Access Google Sheet
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=os.environ['SHEET_ID'],
        range="Form Responses 1!A2:B"
    ).execute()
    rows = result.get('values', [])

    if not rows:
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No new submissions'})
        }

    # 3. Set up DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)

    results = []

    for row in rows:
        name = row[0]
        email = row[1]
        member_id = f"MEM{int(time.time())}"

        join_link = register_zoom_user(name, email)
        if join_link:
            store_member(table, member_id, name, email, join_link)

            results.append({
                "member_id": member_id,
                "email": email,
                "zoom_link": join_link
            })

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_zoom_access_token():
    url = "https://zoom.us/oauth/token"
    client_id = os.environ["ZOOM_CLIENT_ID"]
    client_secret = os.environ["ZOOM_CLIENT_SECRET"]

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(
        url,
        headers=headers,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret)
    )

    response.raise_for_status()
    return response.json()["access_token"]

def register_zoom_user(name, email):
    try:
        access_token = get_zoom_access_token()
        meeting_id = os.environ["ZOOM_MEETING_ID"]

        url = f"https://api.zoom.us/v2/meetings/{meeting_id}/registrants"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "email": email,
            "first_name": name
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("join_url")

    except Exception as e:
        print(f"Error registering Zoom user: {e}")
        return None

def store_member(table, member_id, name, email, zoom_url):
    table.put_item(
        Item={
            'member_id': member_id,
            'name': name,
            'email': email,
            'zoom_url': zoom_url
        }
    )
