import pickle
from abc import ABC
from datetime import datetime, timedelta, date
from getpass import getpass
from json import loads
from os import system
from os.path import exists
from subprocess import check_call

def clear():
    """Clears the console."""
    system("cls")

def install(package):
    """Uses pip to install a package. This will error if"""
    check_call(["pip", "install", package])

def __parse_config_file(config_file: str) -> None:
    """Parses a config file, which is basically a dictionary without the braces and commas which ignores comments (declared with #)."""
    prefix = "config"
    config_dict = {}
    with open(config_file) as f:
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
            raise ValueError(f"[{prefix}] appearance_mode in {config_file} is invalid.")
    else:
        print(f"[{prefix}] appearance_mode setting not found in '{config_file}'.")

    if config_dict["appearance_mode"]:
        try:
            ctk.set_default_color_theme(config_dict["default_color_theme"])
        except Exception:
            raise ValueError(f"[{prefix}] default_color_theme in {config_file} is invalid.")
    else:
        print(f"[{prefix}] default_color_theme setting not found in '{config_file}'.")

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
__parse_config_file("config.txt")

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

class Go4Schools_Session(object):
    def __init__(self, username: str, password: str):
        """Takes in a username and password as parameters and logs into the Go4Schools website using the Requests library.
        It extracts the student ID and bearer token from the HTML response and stores them as attributes of the class."""
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
                "Incorrect Username or Password. Please use Go4Schools_Session.verify_login_details() before declaring the class.")

        now = datetime.now()
        if now.month >= 9:
            self.academic_year = str(now.year + 1)
        else:
            self.academic_year = str(now.year)

        self.SchoolID = response.text.split("var s_schoolID = ")[1].split(";")[0]
        print(self.SchoolID)
        self.StudentID = response.text.split("?sid=")[1].split('"')[0]
        self.bearer = "Bearer " + response.text.split("var accessToken = ")[1].split('"')[1]
        print(f"[{self.prefix}] Logged in as '{username}' with student ID {self.StudentID}.")

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
    def StartEnd_OfWeek() -> tuple:
        """Returns start & end of current week."""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6, seconds=-1)
        start_of_week_str = start_of_week.strftime("%a, %d %b %Y 00:00:00 GMT")
        end_of_week_str = end_of_week.strftime("%a, %d %b %Y 23:59:59 GMT")

        return start_of_week_str, end_of_week_str

    @staticmethod
    def get_dates():
        """Prompts the user to enter a start and end date in the format "DD/MM/YYYY" and returns them as formatted strings.
        For use in sending requests to Go4Schools."""
        print("Enter start date in the format DD/MM/YYYY:")
        start_date = input()
        start_date = datetime.strptime(start_date, "%d/%m/%Y").date()

        print("Enter end date in the format DD/MM/YYYY:")
        end_date = input()
        end_date = datetime.strptime(end_date, "%d/%m/%Y").date()

        start_str = start_date.strftime("%a, %d %b %Y 00:00:00 GMT")
        end_str = end_date.strftime("%a, %d %b %Y 23:59:59 GMT")

        return start_str, end_str

    def GetTimetable(self, startDate: str = None, endDate: str = None) -> list[dict]:
        """Retrieves the student's timetable for a given start and end date (formatted as "Sat, 1 Jan 2000 00:00:00 GMT") from the Go4Schools API. If no dates are specified, it uses the StartEnd_OfWeek method to get the start and end dates of the current week. The method returns a list of dictionaries representing the lessons."""
        if not (startDate or endDate):
            startDate, endDate = self.StartEnd_OfWeek()

        print(f"{self.prefix}: Fetching timetable...")

        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        baseURL = "https://api.go4schools.com/web/stars/v1/timetable/student/academic-years/"
        TimetableURL = baseURL + str(
            datetime.now().year) + "/school-id/" + self.SchoolID + "/user-type/1/student-id/" + self.StudentID + "/from-date/"
        TimetableURL += str(startDate) + "/to-date/" + str(endDate) + "?caching=true"
        response = requests.get(TimetableURL, headers=headers)
        print(f"{self.prefix}: Status code from 'api.go4schools.com':", response.status_code)
        lessons = loads(response.text)["student_timetable"]

        # replace all weird names
        for i in range(len(lessons)):
            if lessons[i]["subject_name"] == "Rg":
                lessons[i]["subject_name"] = "Form"
            elif lessons[i]["subject_name"] == "Computer Sci":
                lessons[i]["subject_name"] = "Computer Science"

        return lessons

    def GetAttendance(self) -> str:
        """Retrieves the student's attendance data from the Go4Schools API. It returns the attendance data as a string."""
        print(f"{self.prefix}: Fetching attendance...")

        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        baseURL = "https://api.go4schools.com/web/stars/v1/attendance/session/academic-years/"
        AttendanceURL = baseURL + str(
            datetime.now().year) + "/school-id/" + self.SchoolID + "/user-type/1/year-groups/12/student-id/" + self.StudentID + "?caching=false&includeSettings=true"
        response = requests.get(AttendanceURL, headers=headers)
        print("Status code:", response.status_code)
        return response.text

    def GetGrades(self) -> str:
        """Gets grades using the Go4Schools API"""
        URL = "https://api.go4schools.com/web/stars/v1/attainment/student-grades/academic-years/" + self.academic_year + "/school-id/" + self.SchoolID + "/user-type/1/year-group/12/student-id/" \
              + self.StudentID + "?caching=false&includeSettings=false"
        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        response = requests.get(URL, headers=headers)
        print(f"{self.prefix}: Status code:", response.status_code)
        return response.text

    def GetHomework(self) -> list[dict]:
        """Gets homework using the Go4Schools API"""
        headers = {
            "authorization": self.bearer,
            "origin": "https://www.go4schools.com",
            "referer": "https://www.go4schools.com/"
        }
        URL = "https://api.go4schools.com/web/stars/v1/homework/student/academic-years/" + self.academic_year + "/school-id/" + self.SchoolID + "/user-type/1/student-id/" + self.StudentID + "?caching=true&includeSettings=true"
        response = requests.get(URL, headers=headers)
        homework = loads(response.text)["student_homework"]["homework"]

        futureTasks = []
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday() + 1)
        for task in homework:
            date_str = task["due_date"]
            date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
            if date >= start_of_week:
                futureTasks.append(task)
        return futureTasks

class TimetableTab(ctk.CTkTabview, ABC):
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
                label.configure(text_color="#9B9FB5") #grey
                label.pack()

class HomeworkTab(ctk.CTkTabview, ABC):
    def __init__(self, root: ctk.CTk, homeworkData: list[dict], **kwargs):
        super().__init__(root, **kwargs)

        def sort_key(task: dict):
            if task["due_date"] == "Today":
                return date.today()
            elif task["due_date"] == "Tomorrow":
                return date.today() + timedelta(days=1)
            else:
                due_datetime = datetime.strptime(task["due_date"], "%Y-%m-%dT%H:%M:%S")
                return due_datetime.date()

        sorted_tasks = sorted(homeworkData, key=sort_key)

        self.add("Homework")

        today = date.today()
        # titleFont = ctk.CTkFont(family='Arial', size=16, weight='bold')
        # bodyFont = ctk.CTkFont(family='Arial', size=12)
        futureTasks = []
        for task in sorted_tasks:
            due_date = datetime.strptime(task["due_date"], "%Y-%m-%dT%H:%M:%S").date()

            #customise task details
            i = 1
            breakOn = 80
            details = task["details"]
            while i < len(details):
                if i % breakOn == 0:
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
                futureTasks.append(task)

class timetable_and_homework_GUI(ctk.CTk, ABC):
    def __init__(self, lessonData: list[dict], homeworkData: list[dict]):
        super().__init__()

        self.title("Timetable and Homework")
        self.tabview = TimetableTab(root=self, data=lessonData)
        self.tabview.grid(row=0, column=0, padx=20, pady=20)
        self.tabview = HomeworkTab(root=self, homeworkData=homeworkData)
        self.tabview.grid(row=0, column=1, padx=20, pady=20)

class GoogleCalendarSession(object):

    def __init__(self):
        self.prefix = "[Google Calendar]"
        self.service = None
        if exists("credentials.json"):
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            CREDENTIALS_FILE = 'credentials.json'
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
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

            self.service = build('calendar', 'v3', credentials=creds)
        else:
            raise Exception("'credentials.json' cannot not found. This can be fetched from https://console.cloud.google.com/apis/credentials. A guide for generating these credentials can be found at https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/")

    def event_exists(self, eventBody: dict) -> bool:
        # eventBody example: eventBody = {"summary": title,"description": description,"colorId": DefineColour(title),"start": {"dateTime": start, "timeZone": 'Greenwich'},"end": {"dateTime": end, "timeZone": 'Greenwich'}}
        events_result = self.service.events().list(calendarId='primary', timeMin=eventBody['start']['dateTime'],
                                                   timeMax=eventBody['end']['dateTime'], singleEvents=True,
                                                   orderBy='startTime').execute()
        for event in events_result.get("items", []):
            if event['summary'] == eventBody['summary']:
                return True
        return False

    def create_event(self, title, description, start, end):

        def DefineColour(title):
            title = str(title)  # idk what integer titles ppl be making but yk
            return str(ord(title[0]) % 11 + 1)

        # example start:
        # "start": {"dateTime": "2015-09-15T06:00:00+02:00, "timeZone": "Europe/Zurich"},

        eventBody = {"summary": title, "description": description, "colorId": DefineColour(title),
                     "start": {"dateTime": start, "timeZone": 'Greenwich'},
                     "end": {"dateTime": end, "timeZone": 'Greenwich'}}

        if not self.event_exists(eventBody):
            self.service.events().insert(calendarId='primary', body=eventBody).execute()
            print(f"{self.prefix}: Created Event  ({title} at {start})")
        else:
            print(f"{self.prefix}: Event already exists  ({title} at {start})")

    def day_event_exists(self, eventBody: dict) -> bool:
        # eventBody example: eventBody = {"summary": title,"description": description,"colorId": DefineColour(title),"start": {"dateTime": start, "timeZone": 'Greenwich'},"end": {"dateTime": end, "timeZone": 'Greenwich'}}
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
            if event['summary'] == eventBody['summary']:
                return True
        return False

    def create_day_event(self, title, description, start, end):
        def define_color(title):
            return str((ord(title[0]) % 11) + 1)

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

    def create_event_from_lessons(self, data: list[dict]):
        for lesson in data:
            self.create_event_from_lesson_singular(lesson)

    def create_event_from_lesson_singular(self, lesson: dict):
        subject_name = lesson["subject_name"]
        if subject_name not in ["None", None]:
            start = lesson["date"][:-8] + lesson["start_time"] + ":00+00:00"
            end = lesson["date"][:-8] + lesson["end_time"] + ":00+00:00"
            description = lesson["group_code"] + "\n" + lesson["teacher_list"][
                list(lesson["teacher_list"].keys())[0]] + "\n" + lesson["room_list"]
            self.create_event(subject_name, description, start, end)

    def create_event_from_homework_singular(self, task: dict):
        title = task["title"]
        description = task["details"].replace("\\r\\", "\n")
        due_date = task["due_date"]
        date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M:%S')
        next_date = date + timedelta(days=1)
        date = date.strftime('%Y-%m-%d')
        next_date = next_date.strftime('%Y-%m-%d')
        self.create_day_event(title, description, date, next_date)

    def CreateEventFromHomework(self, data: list[dict]):
        for task in data:
            self.create_event_from_homework_singular(task)

    def remove_duplicate_events(self):
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

def mainMenu(G4S=None):
    print("\n -------------------- Main Menu -------------------- \n")
    if not G4S:
        __username = input("Username: ")
        __password = getpass()
        G4S = Go4Schools_Session(__username, __password)

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
            start, end = G4S.get_dates()
        else:
            print("Getting dates from the start and end of current week...")
            start, end = G4S.StartEnd_OfWeek()

        lessonData = G4S.GetTimetable(start, end)
        homeworkData = G4S.GetHomework()
        app = timetable_and_homework_GUI(lessonData, homeworkData)
        app.mainloop()
    
    elif choice in ["2", "3"]:
        GoogleSession = GoogleCalendarSession()

        if choice == "2":
            print("Timetable Viewing Options:\n1) From start to end of current week\n2) Custom start & end dates")
            start_end_choice = input()
            if start_end_choice == "2":
                print("Getting dates from custom dates...")
                start, end = G4S.get_dates()
            else:
                print("Getting dates from the start and end of current week...")
                start, end = G4S.StartEnd_OfWeek()
            lessonData = G4S.GetTimetable(start, end)
            GoogleSession.create_event_from_lessons(lessonData)

        elif choice == "3":
            homeworkData = G4S.GetHomework()
            GoogleSession.CreateEventFromHomework(homeworkData)

    mainMenu(G4S)

class GUI(ctk.CTk, ABC):
    def __init__(self, G4S: Go4Schools_Session = None, GoogleSession: GoogleCalendarSession = None):
        super().__init__()

        self.GoogleSession = GoogleSession
        self.G4S = G4S
        self.startDate_textBox = None
        self.endDate_textBox = None
        self.startDate = None
        self.endDate = None
        self.login_attempts = 0
        self.redirect_flag = None
        self.lessonData = None
        self.homeworkData = None

        def submit_login_details():
            self.login_attempts += 1
            __username = self.username_box.get()
            __password = self.password_box.get()
            if Go4Schools_Session.verify_login_details(__username, __password):
                self.G4S = Go4Schools_Session(__username, __password)
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
            self.GoogleSession = GoogleCalendarSession()

    def main_menu(self):
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

        mainText = ctk.CTkLabel(self, text="Main Menu\n\n", font=("Aharoni", 20, "bold", "underline"))
        mainText.grid(row=0, column=1, padx=40, pady=20)

        tab1 = ctk.CTkTabview(self)
        tab1.add(name="View Timetable & Homework Details")
        tab1.grid(row=1, column=0, padx=40, pady=20, sticky="nsew")
        Option1 = ctk.CTkButton(tab1, text="View Timetable & Homework Details",
                                command=__menu_option_1_command)
        Option1.grid(row=3, column=0, padx=40, pady=20)

        tab2 = ctk.CTkTabview(self)
        tab2.add(name="Add Current Week's Timetable to Google Calendar")
        tab2.grid(row=1, column=1, padx=40, pady=20, sticky="nsew")
        Option2 = ctk.CTkButton(tab2, text="Add Current Week's Timetable to Google Calendar",
                                command=__menu_option_2_command)
        Option2.grid(row=3, column=0, padx=40, pady=20)

        tab3 = ctk.CTkTabview(self)
        tab3.add(name="Add Homework to Google Calendar")
        tab3.grid(row=1, column=2, padx=40, pady=20, sticky="nsew")
        Option3 = ctk.CTkButton(tab3, text="Add Homework to Google Calendar",
                                command=__menu_option_3_command)
        Option3.grid(row=3, column=0, padx=40, pady=20)

    def clear_window(self):
        # destroy all child widgets of the window
        for child in self.winfo_children():
            child.destroy()

    def date_selector(self):
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
        self.title("Go4Schools GUI")

        def format_date(dt):
            day = dt.day
            suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            return dt.strftime(f"%d{suffix} of %B %Y")

        lessonData = self.G4S.GetTimetable(self.startDate - timedelta(days=1),
                                           self.endDate)  # not sure why I have to take away a day
        homeworkData = self.G4S.GetHomework()
        week_starting_label = ctk.CTkLabel(self, text=f"Week Starting {format_date(self.startDate)}",
                                           font=("Aharoni", 20, "bold"))
        week_starting_label.grid(row=0, column=0, padx=30, pady=30)
        next_week_button = ctk.CTkButton(self, text="View Next Week", command=self.increment_dates)
        next_week_button.grid(row=0, column=1, pady=20)
        tabview = TimetableTab(root=self, data=lessonData)
        tabview.grid(row=1, column=0, padx=20, pady=20, sticky="nw")
        tabview = HomeworkTab(root=self, homeworkData=homeworkData)
        tabview.grid(row=1, column=1, padx=20, pady=20, sticky="ne")

    def increment_dates(self):
        self.startDate += timedelta(days=7)
        self.endDate += timedelta(days=7)
        self.clear_window()
        self.display_timetable_and_homework()

    def add_timetable_to_calendar(self):
        def add_lesson_to_calendar():
            number_of_lessons = len(self.lessonData)
            progress = 0

            def update_progress():
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
        self.lessonData = self.G4S.GetTimetable(self.startDate,
                                                self.endDate)  # list of dictionaries (each one is a lesson)

        button = ctk.CTkButton(self, text="Add to Calendar", command=add_lesson_to_calendar)
        button.grid(column=0, row=2, padx=20, pady=15)

    def add_homework_to_calendar(self):
        def add_task_to_calendar():
            number_of_tasks = len(self.homeworkData)
            progress = 0

            def update_progress():
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
        self.homeworkData = self.G4S.GetHomework()  # list of dictionaries (each one is a lesson)

        button1 = ctk.CTkButton(self, text="Add to Calendar", command=add_task_to_calendar)
        button1.grid(column=0, row=2, padx=20, pady=10)

        button2 = ctk.CTkButton(self, text="Remove Duplicate Events",
                                command=self.GoogleSession.remove_duplicate_events)
        button2.grid(column=0, row=3, padx=20, pady=15)


if __name__ == "__main__":
    App = GUI()
    App.mainloop()
