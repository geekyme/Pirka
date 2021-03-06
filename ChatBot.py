import json
import os
from flask import Flask
from flask import make_response
from flask import render_template
from flask import request

from selenium import webdriver
import platform

from database import DatabaseConnector
from database import DatabaseInserter
from database.Course import Course
from threading import Thread
from database import DatabaseExtractor
from scraper import LoginHandler
from scraper.tempScraper import tempScraper
import time

import netifaces as ni
ni.ifaddresses('en0')
ip = ni.ifaddresses('en0')[2][0]['addr']
print("my ip address is: ", ip)

# Flask app should start in global layout
app = Flask(__name__)

validLogin = False


class ChatBot:
    # Starts the webserver and is ready to listen to incoming actions
    def __init__(self):

        # Bind to PORT if defined, otherwise default to 5000.
        port = int(os.environ.get('PORT', 8080))
        print(port, "er porten")
        app.run(debug=True, host='', port=port, threaded=True)

    # Receives action-name, gets the data and returns a string ready to send back to API.AI
    @staticmethod
    def process_actions(parameter: str, action_name: str) -> str:
        if action_name == "login":
            print(parameter)
            return ChatBot.create_followup_event_data(parameter)
        elif action_name == "get_exam_date":
            return ChatBot.create_data_response(DatabaseExtractor.get_exam_date(parameter[1]))
        elif action_name == "get_assessment_form":
            return ChatBot.create_data_response(DatabaseExtractor.get_assessment_form(parameter[1]))
        elif action_name == "get_contact_mail":
            return ChatBot.create_data_response(DatabaseExtractor.get_contact_mail(parameter[1]))
        elif action_name == "get_contact_name":
            return ChatBot.create_data_response(DatabaseExtractor.get_contact_name(parameter[1]))
        elif action_name == "get_contact_phone":
            return ChatBot.create_data_response(DatabaseExtractor.get_contact_phone(parameter[1]))
        elif action_name == "get_contact_website":
            return ChatBot.create_data_response(DatabaseExtractor.get_contact_website(parameter[1]))
        elif action_name == "get_office":
            return ChatBot.create_data_response(DatabaseExtractor.get_contact_office(parameter[1]))
        elif action_name == "get_teaching_form":
            return ChatBot.create_data_response(DatabaseExtractor.get_teaching_form(parameter[1]))
        elif action_name == "get_course_name":
            return ChatBot.create_data_response(DatabaseExtractor.get_course_name(parameter[1]))
        elif action_name == "get_credit":
            return ChatBot.create_data_response(DatabaseExtractor.get_credit(parameter[1]))
        elif action_name == "get_url":
            return ChatBot.create_data_response(DatabaseExtractor.get_url(parameter[1]))
        elif action_name == "get_prereq_knowledge":
            return ChatBot.create_data_response(DatabaseExtractor.get_prereq_knowledge(parameter[1]))
        elif action_name == "get_course_content":
            return ChatBot.create_data_response(DatabaseExtractor.get_course_content(parameter[1]))
        elif action_name == "get_course_material":
            return ChatBot.create_data_response(DatabaseExtractor.get_course_material(parameter[1]))
        elif action_name == "get_teaching_form":
            return ChatBot.create_data_response(DatabaseExtractor.get_teaching_form(parameter[1]))
        # personal:
        elif action_name == "get_exercise_status":
            return ChatBot.create_data_response(DatabaseExtractor.get_exercise_status(parameter[1], parameter[0]))
        elif action_name == "get_project_status":
            return ChatBot.create_data_response(DatabaseExtractor.get_project_status(parameter[1], parameter[0]))
        elif action_name == "get_lab_status":
            return ChatBot.create_data_response(DatabaseExtractor.get_lab_status(parameter[1], parameter[0]))
        elif action_name == "get_next_event":
            return ChatBot.create_data_response(DatabaseExtractor.get_next_event(parameter[0]))
        else:
            return "I didn't understand anything, you probably broke me :("

    @staticmethod
    def create_data_response(speech: str) -> str:
        data = {
            "speech": speech,
            "displayText": speech,
            # "data": data,
            # "contextOut": [],
            "source": "Pirka-chatbot-webserver"
        }
        return data

    @staticmethod
    def create_followup_event_data(parameter_value: str):
        data = {
            "followupEvent": {
                "name": "custom_event",
                "data": {
                    "user_id": parameter_value,
                    "ip_address": ip
                }
            }
        }

        print(json.dumps(data, indent=4))

        return data


@app.route('/favicon.ico', methods=['GET'])
def scrape_data_from_last_user():

    users = DatabaseExtractor.get_users()
    lastUsername = users[len(users) - 1][0]
    lastPassword = users[len(users) - 1][1]

    thread = Thread(target=thread_function(lastUsername, lastPassword))
    thread.start()

    return render_template("login_success.html")


@app.route('/login/<current_sender_id>', methods=['POST', 'GET'])
def login(current_sender_id):
    """
    This method handles the login so we can get user information to the blackboard scraper.
    We load a template so the user can login and send us the email and password.
    :return:
    """
    print("login")

    error = None
    if request.method == 'POST':

        username = request.form["username"]
        password = request.form["password"]

        print(username, password)

        thread = Thread(target=valid_login(username, password))
        thread.start()
        thread.join()

        global validLogin

        if validLogin:
            DatabaseInserter.add_user(username, password, current_sender_id)
            validLogin = False
            return render_template("login_success.html")
        else:
            return render_template('login.html')

    return render_template('login.html')

    # the code below is executed if the request method
    # was GET or the credentials were invalid


def thread_function(username: str, password: str):
    """
    This function runs when the user has logged in. It adds the data that is relevant for this user in its own thread.

    It first add all the non-user specific data to the database
    :param username:
    :param password:
    :return:
    """

    # To be removed?
    # Get a list of course codes that the user has
    # course_list = LoginHandler.get_course_list(username, password)

    print("starter scraping")

    # Scrapes for additional data that is user specific
    # scraper = ItsLearningScraper(username, password)
    myScraper = tempScraper(username, password)

    # returns a list of courses that the user has, and adds user-course relation to database
    course_list = myScraper.get_course_list()

    # adds user's associated assignment data
    myScraper.get_all_assignments()

    # Adds the users courses (and course-data) to the database
    # for course in course_list:
    #    DatabaseInserter.add_subject_data(course.split()[0])


def valid_login(username: str, password: str):
    print("starter valid login")

    try:
        LoginHandler.login(username, password)
        print("setter til true")
        global validLogin
        validLogin = True
    except:
        print("setter til false")
        validLogin = False


@app.route('/', methods=['POST'])
def webhook():
    json_request = request.get_json(silent=True, force=True)

    print(json.dumps(json_request, indent=4))

    # Extract the data from the json-request (first get the result section of the json)
    result = json_request.get("result")

    # Then get the parameters and action_name of the result
    parameters = result.get("parameters")

    action_name = result.get("action")

    # Handles different parameters to the process-actions method
    if action_name == "login":

        # Depending on if the event "WELCOME_FACEBOOK" or if the user typed "login, get started ect" the
        # resulting json request is different, hence we get the parameter in different ways
        if len(result.get("contexts")) > 1:
            parameter = result.get("contexts")[1].get("parameters").get("facebook_sender_id")
        else:
            parameter = result.get("contexts")[0].get("parameters").get("facebook_sender_id")
    else:
        facebook_id = ""
        if len(result.get("contexts")) > 1:
            facebook_id = result.get("contexts")[1].get("parameters").get("facebook_sender_id")
        elif len(result.get("contexts")) == 0:
            facebook_id = json_request.get("originalRequest").get("data").get("sender").get("id")
        else:
            facebook_id = result.get("contexts")[0].get("parameters").get("facebook_sender_id")

        print(facebook_id, " er face id")
        username = \
        DatabaseConnector.get_values("Select username from user where facebook_id = \"" + facebook_id + "\"")[0][0]
        parameter = [username, parameters.get("course_code")]

    speech = ChatBot.process_actions(parameter, action_name)

    response = json.dumps(speech, indent=4)
    created_response = make_response(response)
    created_response.headers['Content-Type'] = 'application/json'

    return created_response


# Start the application
bot = ChatBot()
