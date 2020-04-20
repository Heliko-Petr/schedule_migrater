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
import datetime
from urllib.parse import quote
from string import digits
import operator

class Coords:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def from_element(cls, element):
        coords = element.location
        x, y = coords['x'], coords['y']
        return cls(x, y)

    def __str__(self):
        return f'({self.x}, {self.y})'

    def compare(self, other, op):
        return op(self.x, other.x) and op(self.y, other.y)

    def __gt__(self, other):
        return self.compare(other, operator.__gt__)

    def __lt__(self, other):
        return self.compare(other, operator.__lt__)

    def __ge__(self, other):
        return self.compare(other, operator.__ge__)

    def __le__(self, other):
        return self.compare(other, operator.__le__)


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


class Schedule:
    def __init__(self, user_name, user_password):
        self.date_created = datetime.datetime.now()
        self.schedule = self.get_schedule(user_name, user_password)

    def __iter__(self):
        for act in self.schedule:
            yield act

    def __str__(self):
        """Return a string representation of the schedule"""

        self_str = ''
        for event in self:
            self_str += str(event) + '\n' * 2
        return self_str

    def __len__(self):
        return len(self.schedule)

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
            id_input.click()
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

        # All of the characters allowed in timestamps
        allowed_timestamp_characters = digits + ':'

        # clrs that boxes representing events don't have
        non_class_clrs = (
            (0, 0, 0),
            (204, 204, 204),
            (211, 211, 211)
        )

        #TODO 34 is 36 in my schedule, depends on how many timestamps are in the peripheral
        textboxes = [element for element in selenium.find_elements_by_class_name('textBox') if element.text]
        day_textboxes = [box for box in textboxes if '/' in box.text and 'dag' in box.text]
        boxes = selenium.find_elements_by_class_name('box')
        day_boxes = boxes[2:7]

        # TODO fix
        day_width = float(self.parse_style(day_boxes[0])['width'][:-2])

        days = [
            {
                'coords': Coords.from_element(box),
                'date': self.make_date(textbox)
            }
            for box, textbox in zip(day_boxes, day_textboxes)
        ]

        # Seperate textboxes into timestamps and misc attributes
        timestamps = []
        attributes = []
        for element in textboxes:
            if ':' in element.text and all(char in allowed_timestamp_characters for char in element.text):
                for day in days:
                    if day['coords'].x + day_width > Coords.from_element(element).x > day['coords'].x:
                        month, day = day['date']
                        hour, minute = self.make_time(element)
                        dt = datetime.datetime(year, month, day, hour, minute)
                        timestamps.append(
                            {
                                'datetime': dt,
                                'coords': Coords.from_element(element)
                            }
                        )
                        break
            else:
                attributes.append(element)

        # TODO fix
        # Get fontsize for timestamps
        for element in textboxes:
            if ':' in element.text and all(char in allowed_timestamp_characters for char in element.text):
                style = self.parse_style(element)
                font_size = float(style['font-size'][:-2])
                break

        # get boxes that represent events
        class_boxes = []
        for box in boxes:
            if days[0]['coords'].x <= Coords.from_element(box).x <= days[-1]['coords'].x + day_width:
                box_style = self.parse_style(box)
                clr_str = box_style['background-color'][4:-1]
                clr = clr_str.split(', ')
                clr = tuple([int(num) for num in clr])
                if clr not in non_class_clrs:
                    class_boxes.append(box)

        # Get start, stop attributes for each event
        events = []
        for box in class_boxes:
            box_coords = Coords.from_element(box)
            box_style_dict = self.parse_style(box)
            width = int(box_style_dict['width'][:-2])
            height = int(box_style_dict['height'][:-2])
            corner = Coords(box_coords.x + width, box_coords.y + height)

            for day in days[::-1]:
                day_coords = day['coords']
                if box_coords >= day_coords:
                    break


            # TODO check for conflict
            # get start and stop datetime
            start, stop = False, False
            for stamp in timestamps:
                stamp_coords = stamp['coords']
                if stamp_coords.y < box_coords.y < box_coords.y + font_size\
                and day_coords.x < stamp_coords.x < day_coords.x + day_width:
                    start = stamp['datetime']
                if stamp_coords.y < corner.y < corner.y + font_size\
                and box_coords.x < stamp_coords.x < day_coords.x + day_width:
                    stop = stamp['datetime']
            if start and stop:
                # TODO delete attributes that are local from global
                local_attributes = []
                for attribute in attributes:
                    if box_coords < Coords.from_element(attribute) < corner:
                        local_attributes.append(attribute)

                if len(local_attributes) == 3:
                    event, teacher, location = [attribute.text for attribute in local_attributes]
                elif local_attributes:
                    event = local_attributes[0].text
                    teacher = ''
                    location = ''
                else:
                    event = ''
                    teacher = ''
                    location = ''
                events.append(Event(event, location, start, stop))
        return events


    # Make dictionary from elements style attribute
    @staticmethod
    def parse_style(element):
        style_str = element.get_attribute('style')
        style_list = style_str.split('; ')
        attr_dict = {}
        for item in style_list:
            key, value = item.split(': ')
            attr_dict[key] = value
        return attr_dict

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


def main():
    pass

if __name__ == '__main__':
    sche = Schedule('ab61274', getpass('password: '))
    print('\n'*10)
    print(f'len: {len(sche)}\n')
    print(sche)

# TODO handle if user chooses schedule_type that isn't avalible
# TODO add multiple week functionality