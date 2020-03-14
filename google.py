from apiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

import scraper
from scraper import Schedule, Activity  # this is needed for pickled objets

import pickle
import os
from getpass import getpass


def add_event(act_obj, serv_obj, cal_id):
    event = {
        'summary': act_obj.act,
        'location': act_obj.place,
        'start': {
            'dateTime': act_obj.start.strftime('%Y-%m-%dT%H:%M:%S'),
            'timeZone': 'Europe/Stockholm'
        },
        'end': {
            'dateTime': act_obj.stop.strftime('%Y-%m-%dT%H:%M:%S'),
            'timeZone': 'Europe/Stockholm'
        },
    }
    serv_obj.events().insert(calendarId=cal_id, body=event).execute()


def delete_event(serv_obj, cal_id, event_id):
    serv_obj.events().delete(calendarId=cal_id, eventId=event_id).execute()


def make_token():
    scopes = ['https://www.googleapis.com/auth/calendar']
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', scopes=scopes)
    credentials = flow.run_console()
    with open('token.pkl', 'wb') as token:
        pickle.dump(credentials, token)


def get_cal_id(serv_obj, summary):
    calendar_list = serv_obj.calendarList().list().execute()
    for calendar in calendar_list['items']:
        if calendar['summary'] == summary:
            calendar_id = calendar['id']
            break
    return calendar_id


def get_event_ids(serv_obj, calendar_id):
    events = serv_obj.events().list(calendarId=calendar_id).execute()
    return [event['id'] for event in events['items']] if events['items'] else None


if __name__ == '__main__':
    if not os.path.exists('token.pkl'):
        make_token()

    username = input('username: ')
    password = getpass('password: ')
    scraper.main(username, password)

    with open('token.pkl', 'rb') as f:
        credentials = pickle.load(f)
    with open('schedule.pkl', 'rb') as f:
        schedule = pickle.load(f)

    service = build('calendar', 'v3', credentials=credentials)
    calendar_id = get_cal_id(service, 'Skola')
    event_ids = get_event_ids(service, calendar_id)

    if event_ids:
        for event_id in event_ids:
            delete_event(service, calendar_id, event_id)

    for event in schedule.schedule:
        add_event(event, service, calendar_id)
