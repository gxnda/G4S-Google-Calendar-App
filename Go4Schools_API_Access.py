"""Go4Schools API Communication using username and password. By Gabriel Lancaster-West"""

import pickle
from abc import ABC
from datetime import datetime, timedelta, date
from getpass import getpass
from json import loads
from os.path import exists

from useful_functions import *


def __parse_config_file(config_file_txt: str) -> None:
    """Parses a config file, which is basically a dictionary without the braces and commas which ignores comments (
    declared with #). """
    prefix = "config"
    config_dict = {}
    with open(config_file_txt) as f:
        for line in f:
            # ignore comments and blank lines
            if line.strip() == '' or line.strip().startswith('#'):
                continue
            key, value = line.strip().split(':')
            # strip whitespace from the key and value
            key = key.strip()
            value = value.strip()
            # handle the case where value has a comment after it
            if '#' in value:
                value = value[:value.index('#')].strip()
            config_dict[key] = value

    if config_dict["appearance_mode"]:
        try:
            ctk.set_appearance_mode(config_dict["appearance_mode"])
        except Exception:
            raise ValueError(f"[{prefix}] appearance_mode in {config_file_txt} is invalid.")
    else:
        print(f"[{prefix}] appearance_mode setting not found in '{config_file_txt}'.")

    if config_dict["appearance_mode"]:
        try:
            ctk.set_default_color_theme(config_dict["default_color_theme"])
        except Exception:
            raise ValueError(f"[{prefix}] default_color_theme in {config_file_txt} is invalid.")
    else:
        print(f"[{prefix}] default_color_theme setting not found in '{config_file_txt}'.")


# imports
try:
    import requests
except ImportError:
    install("requests")
    import requests

try:
    import customtkinter as ctk
except ImportError:
    install("customtkinter")
    import customtkinter as ctk
config_file = "config.txt"
__parse_config_file(config_file)

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
except ImportError:
    install("google-api-python-client")
    install("google-auth-httplib2")
    install("google-auth-oauthlib")
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request


class go4schools_session(object):
    """
    Go4Schools session using username and password, only currently works for students.
    """

    def __init__(self, username: str, password: str):
        """Takes in a username and password as parameters and logs into the Go4Schools website using the Requests 
        library. It extracts the student ID and bearer token from the HTML response and stores them as attributes of 
        the class. """
        self.prefix = "Go4Schools"
        login_url = "https://www.go4schools.com/sso/account/login?site=Student"
        session = requests.Session()
        response = session.get(login_url)
        # Parse the CSRF token from the HTML form.
        csrf_token = response.text.split('name="__RequestVerificationToken" type="hidden" value="')[1].split('"')[0]
        # Login using the username and password.
        login_data = {
            "username": username,
            "password": password,
            "__RequestVerificationToken": csrf_token
        }
        response = session.post(login_url, data=login_data)
        # Extract the student ID and bearer token from the HTML.
        if "login" in response.url:
            raise Exception(
                "Incorrect Username or Password. Please use Go4Schools_Session.verify_login_details() before "
                "declaring the class.")

        now = datetime.now()
        if now.month >= 9:
            self.academic_year = str(now.year + 1)
        else:
            self.academic_year = str(now.year)

        self.SchoolID = response.text.split("var s_schoolID = ")[1].split(";")[0]
        print(self.SchoolID)
        self.student_id = response.text.split("?sid=")[1].split('"')[0]
        self.bearer = "Bearer " + response.text.split("var accessToken = ")[1].split('"')[1]
        print(f"[{self.prefix}] Logged in as '{username}' with student ID {self.student_id}.")

    @staticmethod
    def verify_login_details(username, password):
        """Takes in a username and password and returns True if the login details are valid and False otherwise."""
        login_url = "https://www.go4schools.com/sso/account/login?site=Student"
        session = requests.Session()
        response = session.get(login_url)
        # Parse the CSRF token from the HTML form.
        csrf_token = response.text.split('name="__RequestVerificationToken" type="hidden" value="')[1].split('"')[0]
        # Login using the username and password.
        login_data = {
            "username": username,
            "password": password,
            "__RequestVerificationToken": csrf_token
        }
        response = session.post(login_url, data=login_data)

        if "login" in response.url:
            return False  # invalid
        else:
            return True  # valid

    @staticmethod
    def start_end_of_week() -> tuple:
        """Returns start & end of current week."""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6, seconds=-1)
        start_of_week_str = start_of_week.strftime("%a, %d %b %Y 00:00:00 GMT")
        end_of_week_str = end_of_week.strftime("%a, %d %b %Y 23:59:59 GMT")

        return start_of_week_str, end_of_week_str

    @staticmethod
    def get_dates_with_console_prompt():
        """Prompts the user to enter a start and end date in the format "DD/MM/YYYY" and returns them as formatted 
        strings. For use in sending requests to Go4Schools. """
        print("Enter start date in the format DD/MM/YYYY:")
        start_date = input()
        start_date = datetime.strptime(start_date, "%d/%m/%Y").date()

        print("Enter end date in the format DD/MM/YYYY:")
        end_date = input()
        end_date = datetime.strptime(end_date, "%d/%m/%Y").date()

        start_str = start_date.strftime("%a, %d %b %Y 00:00:00 GMT")
        end_str = end_date.strftime("%a, %d %b %Y 23:59:59 GMT")

        return start_str, end_str

    def get_timetable(self, start_date: str = None, end_date: str = None) -> list[dict]:
        """Retrieves the student's timetable for a given start and end date (formatted as "Sat, 1 Jan 2000 00:00:00 
        GMT") from the Go4Schools API. If no dates are specified, it uses the StartEnd_OfWeek method to get the start 
        and end dates of the current week. The method returns a list of dictionaries representing the lessons. """
        if not (start_date or end_date):
            start_date, end_date = self.start_end_of_week()

        print(f"{self.prefix}: Fetching timetable...")

        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        base_url = "https://api.go4schools.com/web/stars/v1/timetable/student/academic-years/"
        timetable_url = base_url + str(
            datetime.now().year) + "/school-id/" + self.SchoolID + "/user-type/1/student-id/" + self.student_id + \
                        "/from-date/ "
        timetable_url += str(start_date) + "/to-date/" + str(end_date) + "?caching=true"
        response = requests.get(timetable_url, headers=headers)
        print(f"{self.prefix}: Status code from 'api.go4schools.com':", response.status_code)
        lessons = loads(response.text)["student_timetable"]

        # replace all weird names
        for i in range(len(lessons)):
            if lessons[i]["subject_name"] == "Rg":
                lessons[i]["subject_name"] = "Form"
            elif lessons[i]["subject_name"] == "Computer Sci":
                lessons[i]["subject_name"] = "Computer Science"

        return lessons

    def get_attendance(self) -> str:
        """Retrieves the student's attendance data from the Go4Schools API. It returns the attendance data as a 
        string. """
        print(f"{self.prefix}: Fetching attendance...")

        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        base_url = "https://api.go4schools.com/web/stars/v1/attendance/session/academic-years/"
        attendance_url = base_url + str(
            datetime.now().year) + "/school-id/" + self.SchoolID + "/user-type/1/year-groups/12/student-id/" + \
                         self.student_id + "?caching=false&includeSettings=true"
        response = requests.get(attendance_url, headers=headers)
        print("Status code:", response.status_code)
        return response.text

    def get_grades(self) -> str:
        """Gets grades using the Go4Schools API"""
        url = "https://api.go4schools.com/web/stars/v1/attainment/student-grades/academic-years/" + \
              self.academic_year + "/school-id/" + self.SchoolID + "/user-type/1/year-group/12/student-id/" \
              + self.student_id + "?caching=false&includeSettings=false"
        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        response = requests.get(url, headers=headers)
        print(f"{self.prefix}: Status code:", response.status_code)
        return response.text

    def get_homework(self) -> list[dict]:
        """Gets homework using the Go4Schools API"""
        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        url = "https://api.go4schools.com/web/stars/v1/homework/student/academic-years/" + self.academic_year + \
              "/school-id/" + self.SchoolID + "/user-type/1/student-id/" + self.student_id + \
              "?caching=true&includeSettings=true"
        response = requests.get(url, headers=headers)
        homework = loads(response.text)["student_homework"]["homework"]

        future_tasks = []
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday() + 1)
        for task in homework:
            date_str = task["due_date"]
            date_str_as_datetime = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
            if date_str_as_datetime >= start_of_week:
                future_tasks.append(task)
        return future_tasks


class timetable_tab(ctk.CTkTabview, ABC):
    """
    Tab to display the users' timetable, in timetable_and_homework_display() class.
    Can only display one week only, it will add multiple days into one tab otherwise.
    """

    def __init__(self, root, data: list[dict], **kwargs):

        super().__init__(root, **kwargs)

        weekdays = {1: "Monday",
                    2: "Tuesday",
                    3: "Wednesday",
                    4: "Thursday",
                    5: "Friday",
                    6: "Saturday",
                    7: "Sunday"}

        self.add("Monday")
        self.add("Tuesday")
        self.add("Wednesday")
        self.add("Thursday")
        self.add("Friday")

        for entry in data:
            date_string = entry["date"]
            date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
            weekday = weekdays[date_object.weekday() + 1]
            if entry["subject_name"] is not None:
                if entry["subject_name"] == "Rg":
                    entry["subject_name"] = "Form"
                label = ctk.CTkLabel(self.tab(weekday), text=entry["start_time"] + " - " + entry['end_time'] + "\n")
                label.configure(text_color="#0CCE6B")
                label.pack()
                label_text = entry["subject_name"] + "\n"
                teacher = list(entry["teacher_list"].values())[0]
                label_text += teacher + "\n"
                label_text += " Room: " + entry["room_list"] + "\n"
                label = ctk.CTkLabel(self.tab(weekday), text=label_text, padx=20)
                # label.configure(text_color="#FF0000")
                label.pack()

            else:
                label_text = entry["start_time"] + " - " + entry['end_time'] + "\n"
                label_text += "______________\n_________\n___________\n"
                label = ctk.CTkLabel(self.tab(weekday), text=label_text)
                label.configure(text_color="#9B9FB5")  # grey
                label.pack()


class homework_tab(ctk.CTkTabview, ABC):
    """
    Tab to display the users' pending homework, in timetable_and_homework_display() class.
    Sorted by due date, with it displaying "today" and "tomorrow" to the corresponding dates.
    """

    def __init__(self, root: ctk.CTk, homework_data: list[dict], **kwargs):
        super().__init__(root, **kwargs)

        def sort_key(homework_task: dict):
            """Function for sorting dates to display homework in order they're due."""
            if homework_task["due_date"] == "Today":
                return date.today()
            elif homework_task["due_date"] == "Tomorrow":
                return date.today() + timedelta(days=1)
            else:
                due_datetime = datetime.strptime(homework_task["due_date"], "%Y-%m-%dT%H:%M:%S")
                return due_datetime.date()

        sorted_tasks = sorted(homework_data, key=sort_key)

        self.add("Homework")

        today = date.today()
        # titleFont = ctk.CTkFont(family='Arial', size=16, weight='bold')
        # bodyFont = ctk.CTkFont(family='Arial', size=12)
        future_tasks = []
        for task in sorted_tasks:
            due_date = datetime.strptime(task["due_date"], "%Y-%m-%dT%H:%M:%S").date()

            # customise task details
            i = 1
            break_on = 80
            details = task["details"]
            while i < len(details):
                if i % break_on == 0:
                    details = details[:i] + "-\n" + details[i:]

                i += 1

            if due_date >= today:
                if due_date == today:
                    task["due_date"] = "Today"
                elif due_date == today + timedelta(days=1):
                    task["due_date"] = "Tomorrow"
                else:
                    task["due_date"] = due_date.strftime("%A %d %B %Y")
                label = ctk.CTkLabel(self.tab("Homework"), text=("\n\n" + task["title"]))
                label.configure(text_color="#0CCE6B")
                label.pack(padx=20, pady=1)
                label = ctk.CTkLabel(self.tab("Homework"), text=(task["subject_name"]))
                label.pack(padx=20, pady=1)
                label = ctk.CTkLabel(self.tab("Homework"), text=details)
                label.pack(padx=20, pady=1)
                label = ctk.CTkLabel(self.tab("Homework"), text=("Due: " + task["due_date"]))
                label.pack(padx=20, pady=1)
                future_tasks.append(task)


class timetable_and_homework_display(ctk.CTk, ABC):
    """
    GUI for displaying timetable and homework in a customtkinter GUI.
    """

    def __init__(self, lesson_data: list[dict], homework_data: list[dict]):
        super().__init__()

        self.title("Timetable and Homework")
        self.tabview = timetable_tab(root=self, data=lesson_data)
        self.tabview.grid(row=0, column=0, padx=20, pady=20)
        self.tabview = homework_tab(root=self, homework_data=homework_data)
        self.tabview.grid(row=0, column=1, padx=20, pady=20)


class google_calendar_session(object):
    """
    Session for the user to create events in their Google Calendar.
    Not really designed to be used externally, the formatting is heavily balanced towards usage in this specific
    project, therefore the syntax and formatting of parameters may be very strange in other circumstances.
    """

    def __init__(self):
        self.prefix = "[Google Calendar]"
        self.service = None
        if exists("credentials.json"):
            scopes = ['https://www.googleapis.com/auth/calendar']
            credentials_file = 'credentials.json'
            creds = None
            # The file token.pickle stores the user's access and refresh tokens, and is
            # created automatically when the authorization flow completes for the first
            # time.
            if exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

            self.service = build('calendar', 'v3', credentials=creds)
        else:
            raise Exception(
                "'credentials.json' cannot not found. This can be fetched from "
                "https://console.cloud.google.com/apis/credentials. A guide for "
                "generating these credentials can be found at "
                "https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/")

    def event_exists(self, event_body: dict) -> bool:
        """
        Checks if an event specified by "eventBody" already exists in the users calendar. This is to prevent duplicates
        when creating events in the users calendar.

        "eventBody" should contain eventBody['start']['dateTime'], eventBody['end']['dateTime'] and
        eventBody['summary']. These are all strings I think.

        I may sort this out at some point because this hard coding is very poor from me.
        """
        events_result = self.service.events().list(calendarId='primary', timeMin=event_body['start']['dateTime'],
                                                   timeMax=event_body['end']['dateTime'], singleEvents=True,
                                                   orderBy='startTime').execute()
        for event in events_result.get("items", []):
            if event['summary'] == event_body['summary']:
                return True
        return False

    def create_event(self, title, description, start, end, time_zone=None):
        """
        Creates an event in the users Google Calendar.
        Creates this event in the primary calendar, with a colour corresponding to the first character of the title.

        Defaults to Greenwich timezone, unless specified under the time_zone parameter. Check the Google Calendar API
        documentation for information on valid timezones.

        This will print a "Created Event" or "Event already exists" correspondingly.

        """

        def define_colour(event_title: any) -> str:
            """
            Defines colour by the title's first digit. Cycles through 11 possible colours, these correspond to the 11
            colours available in Google Calendar. Returns a string because I'm lazy.
            """
            event_title = str(event_title)  # idk what integer titles ppl be making but yk
            return str(ord(event_title[0]) % 11 + 1)

        # example start:
        # "start": {"dateTime": "2015-09-15T06:00:00+02:00, "timeZone": "Europe/Zurich"},

        if not time_zone:
            time_zone = "Greenwich"

        event_body = {"summary": title, "description": description, "colorId": define_colour(title),
                      "start": {"dateTime": start, "timeZone": time_zone},
                      "end": {"dateTime": end, "timeZone": time_zone}}

        if not self.event_exists(event_body):
            self.service.events().insert(calendarId='primary', body=event_body).execute()
            print(f"{self.prefix}: Created Event  ({title} at {start})")
        else:
            print(f"{self.prefix}: Event already exists  ({title} at {start})")

    def day_event_exists(self, event_body: dict) -> bool:
        """
        TLDR: basically the event_exists() method but for full day events

        Checks if a full day event specified by "eventBody" already exists in the users calendar. This is to prevent
        duplicates when creating events in the users calendar.

        "eventBody" should contain eventBody['summary']. This is a string I think.

        I may sort this out at some point because this hard coding is very poor from me.
        """

        # eventBody example: eventBody = {"summary": title,"description": description,"colorId": DefineColour(title),
        # "start": {"dateTime": start, "timeZone": 'Greenwich'},"end": {"dateTime": end, "timeZone": 'Greenwich'}}
        # events_result = self.service.events().list(calendarId='primary', timeMin=eventBody['start']['date'],
        #                                           timeMax=eventBody['end']['date'], singleEvents=True,
        #                                           orderBy='startTime').execute()

        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = self.service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=10, singleEvents=True,
            orderBy='startTime').execute()
        events = events_result.get('items', [])
        for event in events:
            if event['summary'] == event_body['summary']:
                return True
        return False

    def create_day_event(self, title, description, start, end):
        """
        Creates a full day event in the users Google Calendar.
        Creates this event in the primary calendar, with a colour corresponding to the first character of the title.

        This will print a "Created Event" or "Event already exists" correspondingly.
        """

        def define_color(event_title) -> str:
            """
            Defines colour by the title's first digit. Cycles through 11 possible colours, these correspond to the 11
            colours available in Google Calendar. event_title must be mutable.
            """
            event_title = str(event_title)
            return str((ord(event_title[0]) % 11) + 1)

        event_body = {
            "summary": title,
            "description": description,
            "colorId": define_color(title),
            "start": {
                "date": start,
            },
            "end": {
                "date": end,
            },
        }

        if not self.day_event_exists(event_body):
            self.service.events().insert(calendarId='primary', body=event_body).execute()
            print(f"{self.prefix}: Created Event ({title} at {start})")
        else:
            print(f"{self.prefix}: Event already exists ({title} at {start})")

    def create_event_from_lessons(self, data: list[dict]) -> None:
        """
        Creates events from a list of lessons using the create_event_from_lesson_singular() method.
        """
        for lesson in data:
            self.create_event_from_lesson_singular(lesson)

    def create_event_from_lesson_singular(self, lesson: dict):
        """
        Creates an event from a single lesson. This lesson must contain the following:
        - lesson["subject_name"]
        - lesson["date"]
        - lesson["start_time"]
        - lesson["end_time"]
        - lesson["group_code"]
        - lesson["teacher_list"]
        - lesson["room_list"]
        """
        subject_name = lesson["subject_name"]
        if subject_name not in ["None", None]:
            start = lesson["date"][:-8] + lesson["start_time"] + ":00+00:00"
            end = lesson["date"][:-8] + lesson["end_time"] + ":00+00:00"
            description = lesson["group_code"] + "\n" + lesson["teacher_list"][
                list(lesson["teacher_list"].keys())[0]] + "\n" + lesson["room_list"]
            self.create_event(subject_name, description, start, end)

    def create_event_from_homework_singular(self, task: dict):
        """
        Creates a single homework event using create_day_event(). This event must include the following:
        - task["title"]
        - task["details"]
        - task["due_date"] (which must be in the format '%Y-%m-%dT%H:%M:%S')
        """

        title = task["title"]
        description = task["details"].replace("\\r\\", "\n")
        due_date = task["due_date"]
        due_date_as_datetime = datetime.strptime(due_date, '%Y-%m-%dT%H:%M:%S')
        next_date = due_date_as_datetime + timedelta(days=1)
        due_date_as_datetime = due_date_as_datetime.strftime('%Y-%m-%d')
        next_date = next_date.strftime('%Y-%m-%d')
        self.create_day_event(title, description, due_date_as_datetime, next_date)

    def create_event_from_homework(self, data: list[dict]):
        """
        Creates Google Calendar events for multiple homework events using the create_event_from_homework_singular()
        method.
        """
        for task in data:
            self.create_event_from_homework_singular(task)

    def remove_duplicate_events(self):
        """
        !!!Made by ChatGPT
        Kind of works, it might randomly glitch out with double lessons though :/ sorry
        """

        # Retrieve all events from the calendar
        events_result = self.service.events().list(calendarId='primary', maxResults=2500).execute()
        events = events_result.get('items', [])

        # Create a set to store unique event summaries and start dates
        unique_events = set()

        # Loop through each event and check for duplicates
        for event in events:
            # Extract the summary and start date of the event
            try:
                summary = event['summary']
                start = event['start'].get('date', event['start'].get('dateTime')).split('T')[0]

                # If the event is a duplicate, delete it
                if (summary, start) in unique_events:
                    self.service.events().delete(calendarId='primary', eventId=event['id']).execute()
                    print(f"Deleted duplicate event '{summary}' on {start}")
                else:
                    # Otherwise, add the event to the set of unique events
                    unique_events.add((summary, start))

            except Exception as error:
                print(f"{event}\n\n{error}")

        print(f"{self.prefix} Duplicate events removed.")


def main_menu(g4s=None):
    """
    Main Menu text function, this isn't actually needed, but it can be used for development if GUI is broken.
    """
    print("\n -------------------- Main Menu -------------------- \n")
    if not g4s:
        __username = input("Username: ")
        __password = getpass()
        g4s = go4schools_session(__username, __password)

    choices = {"1": "View Timetable and Homework Details", "2": "Add Current Week's Timetable to Google Calendar",
               "3": "Add Homework to Google Calendar"}
    valid = False

    choice = ""
    while not valid:
        for key in list(choices.keys()):
            print(key + ") " + choices[key])
        choice = input("\nOption: ")
        if choice in list(choices.keys()):
            valid = True

    if choice == "1":

        print("Timetable Viewing Options:\n1) From start to end of current week\n2) Custom start & end dates")
        start_end_choice = input()
        if start_end_choice == "2":
            print("Getting dates from custom dates...")
            start, end = g4s.get_dates_with_console_prompt()
        else:
            print("Getting dates from the start and end of current week...")
            start, end = g4s.start_end_of_week()

        lesson_data = g4s.get_timetable(start, end)
        homework_data = g4s.GetHomework()
        app = timetable_and_homework_display(lesson_data, homework_data)
        app.mainloop()

    elif choice in ["2", "3"]:
        google_session = google_calendar_session()

        if choice == "2":
            print("Timetable Viewing Options:\n1) From start to end of current week\n2) Custom start & end dates")
            start_end_choice = input()
            if start_end_choice == "2":
                print("Getting dates from custom dates...")
                start, end = g4s.get_dates_with_console_prompt()
            else:
                print("Getting dates from the start and end of current week...")
                start, end = g4s.start_end_of_week()
            lesson_data = g4s.get_timetable(start, end)
            google_session.create_event_from_lessons(lesson_data)

        elif choice == "3":
            homework_data = g4s.GetHomework()
            google_session.create_event_from_homework(homework_data)

    main_menu(g4s)


class GUI(ctk.CTk, ABC):
    """
    A customtkinter GUI which boots a login window, where the user will be prompted to log in with their
    Go4Schools login, which will reject the user if it is incorrect, prompting them to try again. Otherwise, it will
    send them to a page where they have the option of viewing their timetable and homework, adding their timetable to
    their Google Calendar, or adding their homework to their Google Calendar. These buttons all point to corresponding
    windows, however I haven't added a "Return to Main Menu" button to any of them yet, so you do just have to restart
    to do multiple things.
    """

    def __init__(self, g4s: go4schools_session = None, google_session: google_calendar_session = None):
        super().__init__()

        self.GoogleSession = google_session
        self.G4S = g4s
        self.startDate_textBox = None
        self.endDate_textBox = None
        self.startDate = None
        self.endDate = None
        self.login_attempts = 0
        self.redirect_flag = None
        self.lessonData = None
        self.homeworkData = None

        def submit_login_details():
            """
            A function to get and verify the users' login credentials, if valid, it will carry on, otherwise, it will
            configure a label to notify the user of their skill issue (they got their password wrong)
            """

            self.login_attempts += 1
            __username = self.username_box.get()
            __password = self.password_box.get()
            if go4schools_session.verify_login_details(__username, __password):
                self.G4S = go4schools_session(__username, __password)
                self.main_menu()
            else:
                self.is_correct_text.configure(text=f"Incorrect username or password. Attempts: {self.login_attempts}")

        if not self.G4S:
            self.title("Login")

            title_label = ctk.CTkLabel(self, text="\nLogin", font=("Aharoni", 20, "bold"))
            title_label.grid(column=0, row=0)

            self.username_box = ctk.CTkEntry(self, placeholder_text="Username", width=400)
            self.username_box.grid(column=0, row=1, padx=20, pady=20)

            self.password_box = ctk.CTkEntry(self, placeholder_text="Password", show="•", width=400)
            self.password_box.grid(column=0, row=2, padx=20, pady=1)

            self.submit_login_button = ctk.CTkButton(self, text="Submit", command=submit_login_details)
            self.submit_login_button.grid(column=0, row=3, padx=20, pady=20)

            self.is_correct_text = ctk.CTkLabel(self, text="", text_color="red")
            self.is_correct_text.grid(column=0, row=4, padx=20, pady=20)

        if not self.GoogleSession:
            self.GoogleSession = google_calendar_session()

    def main_menu(self):
        """
        Menu which displays 3 fairly self explaining buttons:
        - Display timetable and Homework, which opens a prompt asking the user for the dates they would like to view.
        - Add timetable to calendar, which also opens a prompt asking the user for the dates they would like added to
        their Google Calendar.
        - Add homework to calendar, which does what it says.
        """
        self.clear_window()
        self.title("Main Menu")

        def __menu_option_1_command():
            self.redirect_flag = "display_timetable_and_homework"
            self.date_selector()

        def __menu_option_2_command():
            self.redirect_flag = "add_timetable_to_calendar"
            self.date_selector()

        def __menu_option_3_command():
            self.add_homework_to_calendar()

        main_text = ctk.CTkLabel(self, text="Main Menu\n\n", font=("Aharoni", 20, "bold", "underline"))
        main_text.grid(row=0, column=1, padx=40, pady=20)

        tab1 = ctk.CTkTabview(self)
        tab1.add(name="View Timetable & Homework Details")
        tab1.grid(row=1, column=0, padx=40, pady=20, sticky="nsew")
        option1 = ctk.CTkButton(tab1, text="View Timetable & Homework Details",
                                command=__menu_option_1_command)
        option1.grid(row=3, column=0, padx=40, pady=20)

        tab2 = ctk.CTkTabview(self)
        tab2.add(name="Add Current Week's Timetable to Google Calendar")
        tab2.grid(row=1, column=1, padx=40, pady=20, sticky="nsew")
        option2 = ctk.CTkButton(tab2, text="Add Current Week's Timetable to Google Calendar",
                                command=__menu_option_2_command)
        option2.grid(row=3, column=0, padx=40, pady=20)

        tab3 = ctk.CTkTabview(self)
        tab3.add(name="Add Homework to Google Calendar")
        tab3.grid(row=1, column=2, padx=40, pady=20, sticky="nsew")
        option3 = ctk.CTkButton(tab3, text="Add Homework to Google Calendar",
                                command=__menu_option_3_command)
        option3.grid(row=3, column=0, padx=40, pady=20)

    def clear_window(self):
        """
        Clears customtkinter window, by destroying all child widgets of the window.
        """
        for child in self.winfo_children():
            child.destroy()

    def date_selector(self):
        """
        Allows the user to select a date. As this method/window is used multiple times, it utilises a hard coded flag
        system which then redirects the user once the dates have been submitted.
        """

        def submit_dates_button():
            """does the actual logic in the date_selector function"""
            startDateStr = self.startDate_textBox.get()
            endDateStr = self.endDate_textBox.get()
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6, seconds=-1)
            try:
                if startDateStr:
                    self.startDate = datetime.strptime(startDateStr, '%d/%m/%Y').replace(hour=0, minute=0, second=0)
                else:
                    self.startDate = start_of_week.replace(hour=0, minute=0, second=0)
                if endDateStr:
                    self.endDate = datetime.strptime(endDateStr, '%d/%m/%Y').replace(hour=23, minute=59, second=59)
                else:
                    self.endDate = end_of_week.replace(hour=23, minute=59, second=59)
            except ValueError:
                self.date_selector()

            self.clear_window()

            if self.redirect_flag == "display_timetable_and_homework":
                self.display_timetable_and_homework()
            elif self.redirect_flag == "add_timetable_to_calendar":
                self.add_timetable_to_calendar()

        self.clear_window()
        self.title("Date Selector")
        self.endDate_textBox = ctk.CTkEntry(self, placeholder_text="End Date: DD/MM/YYYY (leave blank for this Sunday)",
                                            width=350)
        self.startDate_textBox = ctk.CTkEntry(self, placeholder_text="Start: DD/MM/YYYY (leave blank for this Monday)",
                                              width=350)
        self.startDate_textBox.grid(row=0, column=0, padx=40, pady=20)
        self.endDate_textBox.grid(row=1, column=0, padx=40, pady=20)

        submit_button = ctk.CTkButton(self, text="Submit Dates", command=submit_dates_button)
        submit_button.grid(row=2, column=0, padx=40, pady=20)

    def display_timetable_and_homework(self):
        """
        Makes a customtkinter window which displays the users timetable and homework.
        The timetable start and end date have already been chosen in the date_selector method, which are then stored
        in self.startDate and self.endDate.
        There is also a button to view the week after that, because its really annoying retyping everything to view the
        next date.
        """

        self.title("Go4Schools GUI")

        def format_date(dt):
            """
            Formats the dates in the form "1st of April 1970" (get it? because this code is a joke).
            """
            day = dt.day
            suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            return dt.strftime(f"%d{suffix} of %B %Y")

        lesson_data = self.G4S.get_timetable(self.startDate - timedelta(days=1),
                                             self.endDate)  # not sure why I have to take away a day
        homework_data = self.G4S.get_homework()
        week_starting_label = ctk.CTkLabel(self, text=f"Week Starting {format_date(self.startDate)}",
                                           font=("Aharoni", 20, "bold"))
        week_starting_label.grid(row=0, column=0, padx=30, pady=30)
        next_week_button = ctk.CTkButton(self, text="View Next Week", command=self.increment_dates)
        next_week_button.grid(row=0, column=1, pady=20)
        tabview = timetable_tab(root=self, data=lesson_data)
        tabview.grid(row=1, column=0, padx=20, pady=20, sticky="nw")
        tabview = homework_tab(root=self, homework_data=homework_data)
        tabview.grid(row=1, column=1, padx=20, pady=20, sticky="ne")

    def increment_dates(self):
        """
        Increments the start and end date by 7 days, and reloads the display_timetable_and_homework window, to allow
        the user to view the next week.
        """
        self.startDate += timedelta(days=7)
        self.endDate += timedelta(days=7)
        self.clear_window()
        self.display_timetable_and_homework()

    def add_timetable_to_calendar(self):
        """
        Adds the users' timetable to their Google Calendar. The dates for this have already been selected by the
        date_selector method. It has a very nice progress bar to show you how many years are left (I'm sorry it takes
        so long, Google has tons of ping in its API to prevent spam or something probably), so get yourself a cuppa
        if your timetable is more than a month.
        """

        def add_lesson_to_calendar():
            """
            Adds lesson to Google calendar. I'm not sure that I need the update_progress method, I might just be
            able to demote it, but I'm scared it will all shatter apart, getting the progress bar working was so
            painful.
            """
            number_of_lessons = len(self.lessonData)
            progress = 0

            def update_progress():
                """
                !!!Generated by ChatGPT
                Genuine witchcraft don't contact me asking how this works;
                It uses nonlocal functions to update a progress bar. It's so complicated to prevent a bug
                to do with customtkinter hogging all Pythons processing, which doesn't let the progress bar be
                updated.
                """
                nonlocal progress
                try:
                    lesson = next(lesson_generator)
                    self.GoogleSession.create_event_from_lesson_singular(lesson)
                    progress += 1
                    progress_bar.set(progress / number_of_lessons)
                    progress_bar.after(100, update_progress)
                except StopIteration:
                    pass

            lesson_generator = (lesson for lesson in self.lessonData)
            update_progress()

        self.clear_window()

        title = ctk.CTkLabel(self, text="Timetable to Google Calendar", font=("Aharoni", 20, "bold"))
        title.grid(column=0, row=0, padx=20, pady=10)

        progress_bar = ctk.CTkProgressBar(master=self)
        progress_bar.grid(column=0, row=1, padx=20, pady=10)
        progress_bar.set(0)
        # get timetable data
        self.lessonData = self.G4S.get_timetable(self.startDate,
                                                 self.endDate)  # list of dictionaries (each one is a lesson)

        button = ctk.CTkButton(self, text="Add to Calendar", command=add_lesson_to_calendar)
        button.grid(column=0, row=2, padx=20, pady=15)

    def add_homework_to_calendar(self):
        """
        Adds the users' homework to their Google Calendar. It has a very nice progress bar to show you how many years
        are left (I'm sorry it takes so long, Google has tons of ping in its API to prevent spam or something
        probably), so get yourself a cuppa if your timetable is more than a month.
        """

        def add_task_to_calendar():
            """
            Adds homework to Google calendar. I'm not sure that I need the update_progress method, I might just be
            able to demote it, but I'm scared it will all shatter apart, getting the progress bar working was so
            painful.
            """
            number_of_tasks = len(self.homeworkData)
            progress = 0

            def update_progress():
                """
                !!!Generated by ChatGPT
                Genuine witchcraft don't contact me asking how this works;
                It uses nonlocal functions to update a progress bar. It's so complicated to prevent a bug
                to do with customtkinter hogging all Pythons processing, which doesn't let the progress bar be
                updated.
                """
                nonlocal progress
                try:
                    task = next(task_generator)
                    self.GoogleSession.create_event_from_homework_singular(task)
                    progress += 1
                    progress_bar.set(progress / number_of_tasks)
                    progress_bar.after(100, update_progress)
                except StopIteration:
                    pass

            task_generator = (task for task in self.homeworkData)
            update_progress()

        self.clear_window()

        title = ctk.CTkLabel(self, text="Homework to Google Calendar", font=("Aharoni", 20, "bold"))
        title.grid(column=0, row=0, padx=20, pady=10)

        progress_bar = ctk.CTkProgressBar(master=self)
        progress_bar.grid(column=0, row=1, padx=20, pady=10)
        progress_bar.set(0)
        # get timetable data
        self.homeworkData = self.G4S.get_homework()  # list of dictionaries (each one is a lesson)

        button1 = ctk.CTkButton(self, text="Add to Calendar", command=add_task_to_calendar)
        button1.grid(column=0, row=2, padx=20, pady=10)

        button2 = ctk.CTkButton(self, text="Remove Duplicate Events",
                                command=self.GoogleSession.remove_duplicate_events)
        button2.grid(column=0, row=3, padx=20, pady=15)


if __name__ == "__main__":
    App = GUI()
    App.mainloop()
