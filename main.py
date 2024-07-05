import os
import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import pytz

API_KEY = '###'
CHANNEL_ID = '###'

# получение запланированных трансляций
def get_upcoming_streams(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    response = youtube.search().list(
        part='id,snippet',
        channelId=channel_id,
        eventType='upcoming',
        type='video',
        maxResults=50
    ).execute()
    
    streams = []
    for item in response['items']:
        video_id = item['id']['videoId']
        video_response = youtube.videos().list(
            part='liveStreamingDetails',
            id=video_id
        ).execute()
        
        if 'liveStreamingDetails' in video_response['items'][0]:
            live_details = video_response['items'][0]['liveStreamingDetails']
            if 'scheduledStartTime' in live_details:
                streams.append({
                    'videoId': video_id,
                    'title': item['snippet']['title'],
                    'scheduledStartTime': live_details['scheduledStartTime']
                })
    
    return streams

# GMT+4
def convert_to_gmt_plus4(iso_time):
    utc_time = datetime.datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
    gmt_plus4 = pytz.timezone('Etc/GMT-4')
    local_time = utc_time.astimezone(gmt_plus4)
    return local_time

# Google Calendar API
def get_calendar_service():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

# события в Google Calendar
def add_event_to_calendar(service, title, start_time):
    event = {
        'summary': title,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Etc/GMT-4',
        },
        'end': {
            'dateTime': (start_time + datetime.timedelta(hours=1)).isoformat(),
            'timeZone': 'Etc/GMT-4',
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")


upcoming_streams = get_upcoming_streams(API_KEY, CHANNEL_ID)

if upcoming_streams:
    latest_stream = max(upcoming_streams, key=lambda x: x['scheduledStartTime'])
    gmt_plus4_time = convert_to_gmt_plus4(latest_stream['scheduledStartTime'])
    print(f"Название последней добавленной трансляции: {latest_stream['title']}")
    print(f"Дата начала последней добавленной трансляции (GMT+4): {gmt_plus4_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    service = get_calendar_service()
    add_event_to_calendar(service, latest_stream['title'], gmt_plus4_time)
else:
    print("Нет запланированных трансляций")
