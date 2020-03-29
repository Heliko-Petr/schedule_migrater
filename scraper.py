from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options as ChromeOptions
import datetime
import pickle
from getpass import getpass
import os
import csv


class Event:
    def __init__(self, act, place, start_obj, stop_obj):
        self.act = act
        self.place = place
        self.start = start_obj
        self.stop = stop_obj

    def __str__(self):
        return '\n'.join((
            f'start: {self.start.strftime("%Y/%m/%d, %H:%M")}',
            f'  Event: {self.act}',
            f'  location: {self.place}',
            f'stop: {self.stop.strftime("%Y/%m/%d, %H:%M")}'
        ))


class Schedule:
    def __init__(self, user_name, user_password, user_id):
        self.schedule = self.get_schedule(user_name, user_password, user_id)
        self.was_made = datetime.datetime.now()

    def __iter__(self):
        for act in self.schedule:
            yield act

    def __str__(self):
        """Return a string representation of the schedule"""
        self_str = ''
        for x in self:
            self_str += str(x) + '\n'*2
        return self_str

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

    @staticmethod
    def get_schedule(user_name, user_password, user_id):
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')  # nescessary on windows systems
        options.add_argument("--window-size=1920x1080")  # TextBoxed get weird without this
        browser = webdriver.Chrome('chromedriver.exe', chrome_options=options)

        url = 'https://login001.stockholm.se/siteminderagent/forms/loginForm.jsp?SMAGENTNAME=login001-ext.stockholm.se&POSTTARGET=https://login001.stockholm.se/NECSedu/form/b64startpage.jsp?startpage=aHR0cHM6Ly9mbnMuc3RvY2tob2xtLnNlL25nL3RpbWV0YWJsZS90aW1ldGFibGUtdmlld2VyL2Zucy5zdG9ja2hvbG0uc2Uv&TARGET=-SM-https://fns.stockholm.se/ng/timetable/timetable-viewer/fns.stockholm.se/'
        browser.get(url)

        # Login
        browser.find_element_by_name('user').send_keys(user_name)
        browser.find_element_by_name('password').send_keys(user_password)
        browser.find_element_by_name('submit').click()

        # Wait until schedule-site is loaded
        WebDriverWait(browser, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'k-input')))

        # Get all the possible school options
        elem = browser.find_element_by_id('school')
        select = Select(elem)
        schools = select.options
        school_names = [school.get_property('textContent') for school in schools[1:]]  # [0] is 'Skola'

        # Print all of the school options
        for i, name in enumerate(school_names):
            i += 1
            print(f'{i}: {name}')

        # Ask the user which school they wish
        chosen_idx = int(input('choose school: ')) - 1
        chosen_school = school_names[chosen_idx]

        # Generate url depending on chosen school, then get the new url
        new_url = 'https://fns.stockholm.se/ng/timetable/timetable-viewer/fns.stockholm.se/' \
                  + chosen_school.replace(' ', '%20')
        browser.get(new_url)

        # Wait until schedule-site is loaded
        WebDriverWait(browser, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'k-input')))

        # input the personal id code
        id_input = browser.find_element_by_id('signatures')
        id_input.send_keys(user_id)
        browser.find_element_by_id('signatures-button').click()

        # Wait until the schedule has loaded
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'textBox')))

        text_boxes = [x for x in browser.find_elements_by_class_name('textBox')[36:] if x.text != '']
        day_coords = [x.location['x'] for x in browser.find_elements_by_class_name('box')[2:7]]
        day_coords.append(100000000000)
        year = datetime.datetime.now().year

        labels = []
        locs = []
        dates = []
        datetimes = []

        for box in text_boxes[:5]:
            text = box.text
            fslash_index = text.index('/')
            month = int(text[fslash_index+1:])
            day = int(text[fslash_index-2:fslash_index])
            dates.append((month, day))

        for box in text_boxes[5:]:
            text = box.text
            if ':' in text:  # if text specifies time
                for day_idx in range(5):
                    if day_coords[day_idx] <= box.location['x'] < day_coords[day_idx+1]:
                        colon_idx = text.index(':')
                        month, day = dates[day_idx]
                        hours = int(text[:colon_idx])
                        minutes = int(text[colon_idx+1:])
                        datetimes.append(datetime.datetime(year, month, day, hours, minutes))
                        break
            elif len(text) != 3:  # why 3?
                if len(labels) == len(locs):  # every other text is label/loc
                    labels.append(text)
                else:
                    locs.append(text)

        browser.close()

        return [
            Event(
                labels[i],
                locs[i],
                datetimes[i*2],
                datetimes[i*2+1]
            )
            for i in range(len(labels))
        ]


if __name__ == '__main__':
    username = 'ab61274'
    personal_id = 'a6vk6ka5'
    password = getpass('password: ')

    MySche = Schedule(username, password, personal_id)
    print(MySche)

# TODO handle events without location or simular: could be made by bundling elements by coordinates
# TODO add multiple week functionality
