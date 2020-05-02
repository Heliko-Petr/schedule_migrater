from apiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

import scraper
from scraper import Schedule, Event  # this is needed for pickled objects

import pickle
import os
from getpass import getpass
import json

from rich.progress import track

def add_event(act_obj, serv_obj, cal_id):
    event = {
        'summary': act_obj.act,
        'location': act_obj.place,
        'description': act_obj.info,
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


def get_event_ids_by_dts(serv_obj, calendar_id, dts):
    dttuples = []
    for dt in dts:
        year = dt.year
        month = dt.month
        day = dt.day
        dttuples.append((year, month, day))

    events = serv_obj.events().list(calendarId=calendar_id).execute()
    ids = []
    for event in events['items']:
        start = parse_caltime(event['start']['dateTime'])
        if start in dttuples:
            ids.append(event['id'])
    return ids

def parse_caltime(str_):
    str_ = str_[:str_.index('T')]
    date = [int(a) for a in str_.split('-')]
    return tuple(date)

if __name__ == '__main__':
    if not os.path.exists('token.pkl'):
        make_token()

    username = input('username: ')
    password = getpass('password: ')
    scraper.main(username, password)

    with open('token.pkl', 'rb') as file:
        credentials = pickle.load(file)
    with open('schedule.json', 'r') as file:
        mydict = json.load(file)
        schedule = Schedule.from_dict(mydict)
    days_to_clear = schedule.days_updated

    service = build('calendar', 'v3', credentials=credentials)
    calendar_id = get_cal_id(service, 'schedule_migrater')
    event_ids = get_event_ids_by_dts(service, calendar_id, days_to_clear)

    if event_ids:  # TODO don't delete entire calendar, only days that have changed
        for event_id in track(event_ids, description='deleting events in google calendar'):
            delete_event(service, calendar_id, event_id)

    for event in track(schedule.schedule, description='adding events to gogle calendar'):
        add_event(event, service, calendar_id)
