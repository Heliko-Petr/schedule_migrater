from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options as ChromeOptions
from getpass import getpass
import os
import pickle
import csv
from urllib.parse import quote
from string import digits
from JsonDateTime import JsonDateTime
from pprint import pprint
import json


class Coords:
    def __init__(self, element):
        coords = element.location
        self.x = coords['x']
        self.y = coords['y']

    def __gt__(self, other):
        return self.x > other.x and self.y > other.y

    def __lt__(self, other):
        return self.x < other.x and self.y < other.y


class Event:
    def __init__(self, act, place, start_obj, stop_obj):
        self.act = act
        self.place = place
        self.start = start_obj
        self.stop = stop_obj

    def __str__(self):
        return '\n'.join(
            (
                f'start: {self.start.strftime("%Y/%m/%d, %H:%M")}',
                f'  Event: {self.act}',
                f'  location: {self.place}',
                f'stop: {self.stop.strftime("%Y/%m/%d, %H:%M")}'
            )
        )
    
    @property
    def dict_(self):
        return {
            'title': self.act,
            'location': self.place,
            'start': self.start.dict_,
            'stop':self.stop.dict_
        }

    @classmethod
    def from_dict(cls, dict_):
        return cls(
            dict_['title'],
            dict_['location'],
            JsonDateTime.from_dict(dict_['start']),
            JsonDateTime.from_dict(dict_['stop'])
        )

class Schedule:
    def __init__(self, events, date_created):
        self.schedule = events
        self.date_created = date_created

    def __iter__(self):
        for act in self.schedule:
            yield act

    def __str__(self):
        """Return a string representation of the schedule"""

        self_str = ''
        for event in self:
            self_str += str(event) + '\n' * 2
        return self_str

    @classmethod
    def from_selenium(cls, user_name, user_password):
        return cls(get_schedule(user_name, user_password), JsonDateTime.now())

    @classmethod
    def from_dict(cls, dict_):
        return cls([Event.from_dict(dict_) for dict_ in dict_['data']], JsonDateTime.now())

    @property
    def dict_(self):
        return {
            'info': {
                'created': self.date_created.dict_
            },
            'data': [event.dict_ for event in self]
        } 

    def save_csv(self):
        """
        Save schedule to csv
        used for importing schedule into google calendar, instead of using api
        """

        if os.path.exists('schedule.csv'):
            os.remove('schedule.csv')
        with open('schedule.csv', 'w', newline='') as schedule:
            writer = csv.writer(schedule)
            writer.writerow(['Subject', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Location'])
            for act in self.schedule:
                start_date = act.start.strftime('%m/%d/%Y')

                start_time = act.start.strftime('%I:%M %p')
                start_time = start_time.upper()
                if start_time[0] == '0':
                    start_time = start_time[1:]

                end_date = act.stop.strftime('%m/%d/%Y')

                end_time = act.stop.strftime('%I:%M %p')
                end_time = end_time.upper()
                if end_time[0] == '0':
                    end_time = end_time[1:]

                writer.writerow(
                    [
                        act.act,
                        start_date,
                        start_time,
                        end_date,
                        end_time,
                        act.place
                    ]
                )

    def save_pickle(self):
        """Save self to schedule.pkl"""

        if os.path.exists('schedule.pkl'):
            os.remove('schedule.pkl')
        with open('schedule.pkl', 'wb') as f:
            pickle.dump(self, f)

    def get_schedule(self, user_name, user_password):
        options = ChromeOptions()
        options_args = (
            '--headless',
            '--no - sandbox',
            '--disable-gpu',  # nescessary on windows systems if '--headless' is option
            '--window-size=1920x1080'  # TextBoxes get weird without this
        )
        # for option in options_args:
        #     options.add_argument(option)
        browser = webdriver.Chrome('chromedriver.exe', options=options)

        # initial url is for login site
        # base_url is for joining with school
        url = 'https://login001.stockholm.se/siteminderagent/forms/loginForm.jsp?SMAGENTNAME=login001-ext.stockholm' \
              '.se&POSTTARGET=https://login001.stockholm.se/NECSedu/form/b64startpage.jsp?startpage' \
              '=aHR0cHM6Ly9mbnMuc3RvY2tob2xtLnNlL25nL3RpbWV0YWJsZS90aW1ldGFibGUtdmlld2VyL2Zucy5zdG9ja2hvbG0uc2Uv' \
              '&TARGET=-SM-https://fns.stockholm.se/ng/timetable/timetable-viewer/fns.stockholm.se/ '
        base_url = 'https://fns.stockholm.se/ng/timetable/timetable-viewer/fns.stockholm.se/'
        browser.get(url)

        # Login
        browser.find_element_by_name('user').send_keys(user_name)
        browser.find_element_by_name('password').send_keys(user_password)
        browser.find_element_by_name('submit').click()
        WebDriverWait(browser, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'k-input')))
        school_names = self.get_dropdown_options(browser.find_element_by_id('school'))
        chosen_school = self.choose_dropdown_option(school_names)
        url = base_url + chosen_school + '/'
        quote(url)
        browser.get(url)

        # Wait until site is loaded
        WebDriverWait(browser, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'k-input')))

        sche_types = (
            'class',
            'personal id',
            'room',
            'teacher',
            'subject'
        )
        while True:
            sche_type = input('choose sche_type: ')
            if sche_type in sche_types:
                break

        if sche_type == 'personal id':
            user_id = input('personal id: ')
            id_input = browser.find_element_by_id('signatures')
            id_input.send_keys(user_id)
            browser.find_element_by_id('signatures-button').click()
        else:
            drop_down_id = {
                'class': 'classDropDown',
                'room': 'roomDropDown',
                'teacher': 'teacherDropDown',
                'subject': 'subjectDropDown'
            }

            schedule_choices = self.get_dropdown_options(browser.find_element_by_id(drop_down_id[sche_type]))
            chosen_schedule = self.choose_dropdown_option(schedule_choices)
            url += sche_type + '/' + chosen_schedule
            quote(url)
            browser.get(url)

        input('choose week in browser and press enter to resume: ')

        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'textBox')))
        schedule = self.parse(browser)
        browser.close()
        return schedule

    def parse(self, selenium):
        year = self.date_created.year
        allowed_timestamp_characters = digits + ':'

        # textBox element 0-36 are peripheral time stamps, for visual reference
        textboxes = [element for element in selenium.find_elements_by_class_name('textBox')[36:] if element.text]
        day_textboxes = textboxes[:5]

        time_stamps = []
        all_attributes = []
        for element in textboxes:
            text = element.text
            if ':' in text and all(char in allowed_timestamp_characters for char in text):
                time_stamps.append(element)
            else:
                all_attributes.append(element)

        # group time_stamps in pairs
        time_stamp_pairs = [(time_stamps[idx], time_stamps[idx+1]) for idx in range(0, len(time_stamps), +2)]

        events = []

        for pair in time_stamp_pairs:
            start, stop = pair
            attributes = []

            coords_start = Coords(start)
            coords_stop = Coords(stop)

            for element in day_textboxes:
                coords = Coords(element)
                if coords.x >= coords_start.x:
                    day_element = element

            for element in all_attributes:  # can be optimized
                coords = Coords(element)
                if coords_start < coords < coords_stop:
                    attributes.append(element)

            if len(attributes) == 3:
                event, teacher, location = [attribute.text for attribute in attributes]
            elif attributes:
                event = attributes[0].text
                teacher = ''
                location = ''
            else:
                event = ''
                teacher = ''
                location = ''

            month, day = self.make_date(day_element)
            hours_start, minutes_start = self.make_time(start)
            hours_stop, minutes_stop = self.make_time(stop)

            datetime_start = JsonDateTime(year, month, day, hours_start, minutes_start)
            datetime_stop = JsonDateTime(year, month, day, hours_stop, minutes_stop)

            event = Event(event, location, datetime_start, datetime_stop)
            events.append(event)

        return events

    @staticmethod
    def make_date(element):
        text = element.text
        idx = text.index('/')
        month = int(text[idx + 1:])
        day = int(text[idx - 2:idx])
        return month, day

    @staticmethod
    def make_time(element):
        text = element.text
        idx = text.index(':')
        hours = int(text[:idx])
        minutes = int(text[idx + 1:])
        return hours, minutes

    @staticmethod
    def choose_dropdown_option(options):
        """
        :param options: list, textcontent of element's options, from get_dropdown_options
        :return: chosen option
        """

        for i, name in enumerate(options):
            i += 1
            print(f'{i}: {name}')
        idx = int(input('choose: ')) - 1
        option = options[idx]
        return option

    @staticmethod
    def get_dropdown_options(element):
        """
        :param element: selenium WebElement object, dropdown menu
        :return: list, textcontent of element's options
        """

        element = Select(element)
        schools = element.options
        options = [school.get_property('textContent') for school in schools[1:]]  # [0] is the placeholder value
        return options


if __name__ == '__main__':
    # username = input('skolplattformen username: ')
    # password = getpass('password: ')

    # MySche = Schedule(username, password)
    with open('test.json', 'r') as file:
        mysche = Schedule.from_dict(json.load(file))
        print(mysche)

# TODO handle if user chooses schedule_type that isn't avalible
# TODO handle events without location or simular: could be made by bundling elements by coordinates
# TODO add multiple week functionality
# TODO if two lessons are besides each other, one might end when the other one starts !!!
# TODO logging
# TODO maybe make __init__ generator
# TODO comment and document