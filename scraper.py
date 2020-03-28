from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import datetime
import pickle
from getpass import getpass
import os
import csv
from pprint import pprint


class Activity:
    """"""
    def __init__(self, act, place, start_obj, stop_obj):
        self.act = act
        self.place = place
        self.start = start_obj
        self.stop = stop_obj

    def __str__(self):
        return str('activity: ' + str(self.act) +
                   '\nplace: ' + str(self.place) +
                   '\nstarts: ' + str(self.start.strftime("%Y/%m/%d, %H:%M")) +
                   '\nends: ' + str(self.stop.strftime("%Y/%m/%d, %H:%M")))


class Schedule:
    def __init__(self, username, password):
        self.schedule = self.get_schedule(username, password)

    def __str__(self):
        self_str = ''
        for x in self.schedule:
            self_str += str(x) + '\n'*2
        return self_str

    def save_csv(self):
        """Used when importing schedule rather than manipulating calendar directly with api"""
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
        """Delete schedule.pkl if it exists, pickle self to schedule.pkl"""
        if os.path.exists('schedule.pkl'):
            os.remove('schedule.pkl')
        with open('schedule.pkl', 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def get_schedule(username, password):
        """Make Activity objects from browser and return them in list"""
        browser = webdriver.Chrome('chromedriver.exe')
        url = 'https://login001.stockholm.se/siteminderagent/forms/loginForm.jsp?SMAGENTNAME=login001-ext.stockholm.se&POSTTARGET=https://login001.stockholm.se/NECSedu/form/b64startpage.jsp?startpage=aHR0cHM6Ly9mbnMuc3RvY2tob2xtLnNlL25nL3RpbWV0YWJsZS90aW1ldGFibGUtdmlld2VyL2Zucy5zdG9ja2hvbG0uc2Uv&TARGET=-SM-https://fns.stockholm.se/ng/timetable/timetable-viewer/fns.stockholm.se/'

        browser.get(url)

        browser.find_element_by_name('user').send_keys(username)
        browser.find_element_by_name('password').send_keys(password)
        browser.find_element_by_name('submit').click()

        WebDriverWait(browser, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'k-input')))
        # WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.ID, 'school')))

        elem = browser.find_element_by_id('school')
        browser.execute_script("arguments[0].click();", elem)
        select = Select(elem)
        schools = select.options
        school_names = [school.get_property('textContent') for school in schools]
        pprint(school_names)
        # browser.execute_script("document.getElementsByTagName('option')[5].selected='selected';")
        # select.select_by_visible_text('Anna Whitlocks gymnasium')
        input()


        # WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'textBox')))
        #
        # text_boxes = [x for x in browser.find_elements_by_class_name('textBox')[36:] if x.text != '']
        # day_coords = [x.location['x'] for x in browser.find_elements_by_class_name('box')[2:7]]
        # day_coords.append(100000000000)
        # year = datetime.datetime.now().year
        #
        # labels = []
        # locs = []
        # dates = []
        # datetimes = []
        #
        # for box in text_boxes[:5]:
        #     text = box.text
        #     fslash_index = text.index('/')
        #     month = int(text[fslash_index+1:])
        #     day = int(text[fslash_index-2:fslash_index])
        #     dates.append((month, day))
        #
        # for box in text_boxes[5:]:
        #     text = box.text
        #     if ':' in text:  # if text specifies time
        #         for day_idx in range(5):
        #             if day_coords[day_idx] <= box.location['x'] < day_coords[day_idx+1]:
        #                 colon_idx = text.index(':')
        #                 month, day = dates[day_idx]
        #                 hours = int(text[:colon_idx])
        #                 minutes = int(text[colon_idx+1:])
        #                 datetimes.append(datetime.datetime(year, month, day, hours, minutes))
        #                 break
        #     elif len(text) != 3:  # why 3?
        #         if len(labels) == len(locs):  # every other text is label/loc
        #             labels.append(text)
        #         else:
        #             locs.append(text)
        #
        # browser.close()
        #
        # return [
        #     Activity(
        #         labels[i],
        #         locs[i],
        #         datetimes[i*2],
        #         datetimes[i*2+1]
        #     )
        #     for i in range(len(labels))
        # ]


def main(username, password):
    Schedule(username, password).save_pickle()


if __name__ == '__main__':
    password = getpass('password')
    Schedule.get_schedule('ab61274', password)
