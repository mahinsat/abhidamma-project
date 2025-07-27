
# Updated Lambda Function 1 for Free Zoom Account
# This version assigns a member ID and stores the common Zoom link in DynamoDB

import json
import time
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# Define DynamoDB table name
DYNAMODB_TABLE_NAME = "ZoomMembers"

def lambda_handler(event, context):
    # Load Google credentials from environment variable
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.environ['GCP_CREDS']),
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )

    # Read data from Google Sheet
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=os.environ['SHEET_ID'],
        range="Form_Responses!B2:D"
    ).execute()
    rows = result.get('values', [])

    if not rows:
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No new form responses found.'})
        }

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    results = []

    # Use common Zoom link
    common_zoom_link = os.environ.get("ZOOM_COMMON_LINK")

    for row in rows:
        if len(row) < 2:
            continue  # Skip incomplete rows
        name, email = row[0], row[1]
        member_id = f"MEM{int(time.time())}"

        table.put_item(Item={
            'member_id': member_id,
            'name': name,
            'whatsapp': whatsapp,
            'address': address,
            'zoom_url': common_zoom_link
        })

        results.append({
            'member_id': member_id,
            'name': name,
            'whatsapp': whatsapp,
            'address': address,
            'zoom_url': common_zoom_link
        })

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
