from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options as ChromeOptions
from getpass import getpass
from urllib.parse import quote
from string import digits
import operator
from JsonDateTime import JsonDateTime
from pprint import pprint
import json
import os
import csv
from rich.progress import track


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

class SnappyElement:
    """SnappyElement contains the information from WebElement that is used"""

    def __init__(self, element):
        self.text = element.text
        self.coords = Coords.from_element(element)
        self.style = self.parse_attribute(element, 'style')

    @staticmethod
    def parse_attribute(element, attribute):
        style_str = element.get_attribute(attribute)
        style_list = style_str.split('; ')
        attr_dict = {}
        for item in style_list:
            key, value = item.split(': ')
            attr_dict[key] = value
        return attr_dict

class Event:
    def __init__(self, act, place, start_obj, stop_obj, info=''):
        self.act = act
        self.place = place
        self.start = start_obj
        self.stop = stop_obj
        self.info = info

    def __str__(self):
        return '\n'.join(
            (
                f'start: {self.start.strftime("%Y/%m/%d, %H:%M")}',
                f'  Event: {self.act}',
                f'  location: {self.place}',
                f'info: {self.info}',
                f'stop: {self.stop.strftime("%Y/%m/%d, %H:%M")}'
            )
        )

    @property
    def dict_(self):
        return {
            'title': self.act,
            'location': self.place,
            'start': self.start.dict_,
            'stop':self.stop.dict_,
            'info': self.info
        }

    @classmethod
    def from_dict(cls, dict_):
        return cls(
            dict_['title'],
            dict_['location'],
            JsonDateTime.from_dict(dict_['start']),
            JsonDateTime.from_dict(dict_['stop']),
            dict_['info']
        )

class Schedule:
    def __init__(self, events, date_created, days_updated):
        self.date_created = date_created
        self.days_updated = days_updated
        self.schedule = events

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

    @classmethod
    def from_selenium(cls, username, password):
        dt = JsonDateTime.now()
        schedule, days_updated = cls.get_schedule(username, password, dt)
        return cls(schedule, dt, days_updated)

    @classmethod
    def from_dict(cls, dict_):
        return cls(
            [Event.from_dict(dict_) for dict_ in dict_['data']],
            JsonDateTime.from_dict(dict_['info']['created']),
            [JsonDateTime.from_dict(day) for day in dict_['info']['days updated']]
        )

    @property
    def dict_(self):
        return {
            'info': {
                'created': self.date_created.dict_,
                'days updated': [day.dict_ for day in self.days_updated],
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

    @classmethod
    def get_schedule(cls, user_name, user_password, dt):
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
        school_names = cls.get_dropdown_options(browser.find_element_by_id('school'))
        chosen_school = cls.choose_dropdown_option(school_names)
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
            for sche_type in sche_types:
                print(sche_type)
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

            schedule_choices = cls.get_dropdown_options(browser.find_element_by_id(drop_down_id[sche_type]))
            chosen_schedule = cls.choose_dropdown_option(schedule_choices)
            url += sche_type + '/' + chosen_schedule
            quote(url)
            browser.get(url)

        schedule = []
        days_updated = []
        while True:
            input('choose a week in the browser and press enter to resume')
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'textBox')))
            new_sche, new_updated = cls.parse(browser, dt)
            schedule += (new_sche)
            days_updated += (new_updated)
            if input('Add another week? (y/n): ').lower() == 'n':
                break
        browser.close()
        return schedule, days_updated

    @classmethod
    def parse(cls, selenium, dt):
        year = dt.year
        allowed_timestamp_characters = digits + ':'

        # clrs that boxes representing events don't have
        non_class_clrs = (
            (0, 0, 0),
            (204, 204, 204),
            (211, 211, 211)
        )

        #TODO 34 is 36 in my schedule, depends on how many timestamps are in the peripheral
        textboxes = [SnappyElement(element) for element in track(selenium.find_elements_by_class_name('textBox'), description='getting textboxes from website') if element.text]
        boxes = list(map(SnappyElement, track(selenium.find_elements_by_class_name('box'), description='getting boxes from website')))
        day_textboxes = [box for box in textboxes if '/' in box.text and 'dag' in box.text]
        day_boxes = boxes[2:7]

        # TODO fix
        day_width = float(day_boxes[0].style['width'][:-2])

        days = [
            {
                'coords': box.coords,
                'date': cls.make_date(textbox)
            }
            for box, textbox in zip(day_boxes, day_textboxes)
        ]

        # Seperate textboxes into timestamps and misc attributes
        timestamps = []
        attributes = []
        for element in textboxes:
            if ':' in element.text and all(char in allowed_timestamp_characters for char in element.text):
                for day in days:
                    if day['coords'].x + day_width > element.coords.x > day['coords'].x:
                        month, day = day['date']
                        hour, minute = cls.make_time(element)
                        dt = JsonDateTime(year, month, day, hour, minute)
                        timestamps.append(
                            {
                                'datetime': dt,
                                'coords': element.coords
                            }
                        )
                        break
            else:
                attributes.append(element)

        # TODO fix
        # Get fontsize for timestamps
        for element in textboxes:
            if ':' in element.text and all(char in allowed_timestamp_characters for char in element.text):
                font_size = float(element.style['font-size'][:-2])
                break

        # get boxes that represent events
        class_boxes = []
        for box in boxes:
            if days[0]['coords'].x <= box.coords.x <= days[-1]['coords'].x + day_width:
                clr_str = box.style['background-color'][4:-1]
                clr = clr_str.split(', ')
                clr = tuple([int(num) for num in clr])
                if clr not in non_class_clrs:
                    class_boxes.append(box)

        # Get start, stop attributes for each event
        events = []
        for box in class_boxes:
            box_coords = box.coords
            box_style_dict = box.style
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
                    if box_coords < attribute.coords < corner:
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
                events.append(Event(event, location, start, stop, teacher))

        days_updated = []
        for day in days:
            month, day = day['date']
            days_updated.append(JsonDateTime(year, month, day))
        return events, days_updated


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


def main(username, password):
    mysche = Schedule.from_selenium(username, password)
    with open('schedule.json', 'w') as file:
        json.dump(mysche.dict_, file, indent=4)


if __name__ == '__main__':
    mysche = Schedule.from_selenium('ab61274', getpass('pass: '))
    with open('schedule.json', 'w') as file:
        json.dump(mysche.dict_, file, indent=True)
    # with open('schedule.json', 'r') as file:
    #     mysche = Schedule.from_dict(json.load(file))
    #     pprint(mysche.dict_)
    #     print('\n'*5, print(len(mysche)))

# TODO handle if user chooses schedule_type that isn't avalible
# TODO handle events without location or simular: could be made by bundling elements by coordinates
# TODO add multiple week functionality
# TODO if two lessons are besides each other, one might end when the other one starts !!!
# TODO logging
# TODO maybe make __init__ generator
# TODO comment and document
