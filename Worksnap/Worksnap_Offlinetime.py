import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# API token and user information
API_TOKEN = 'gFg35iyYKgFnHVdfymA3iThG7Q0ehpXMwweqR5nR'  # Replace with your API token

# Headers and Authentication setup
headers = {
    'Accept': 'application/xml',
    'Content-Type': 'application/xml'
}
auth = (API_TOKEN, 'ignored')  # Basic Auth using API token


# Function to fetch available projects
def fetch_projects():
    url = "https://www.worksnaps.net/api/projects.xml"
    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        projects = root.findall(".//project")
        return projects
    else:
        st.error(f"Failed to fetch projects. Status Code: {response.status_code}")
        return []


# Function to fetch tasks for a specific project
def fetch_tasks(project_id):
    url = f"https://www.worksnaps.net/api/projects/{project_id}/tasks.xml"
    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        tasks = root.findall(".//task")
        return tasks
    else:
        st.error(f"Failed to fetch tasks for project {project_id}. Status Code: {response.status_code}")
        return []


# Function to get project and task from the user
def select_project_and_task():
    projects = fetch_projects()
    if not projects:
        return None, None

    project_names = ["Select a project"] + [project.find('name').text for project in projects]
    project_choice = st.selectbox("Choose a project", project_names, index=0)

    if project_choice == "Select a project":
        return None, None

    selected_project = projects[project_names.index(project_choice) - 1]
    project_id = selected_project.find('id').text

    tasks = fetch_tasks(project_id)
    if not tasks:
        return None, None

    task_names = ["Select a task"] + [task.find('name').text for task in tasks]
    task_choice = st.selectbox("Choose a task", task_names, index=0)

    if task_choice == "Select a task":
        return None, None

    selected_task = tasks[task_names.index(task_choice) - 1]
    task_id = selected_task.find('id').text

    return project_id, task_id


# Function to round time to nearest 10-minute interval
def round_to_nearest_10_minutes(dt):
    rounded_minutes = round(dt.minute / 10) * 10
    if rounded_minutes == 60:
        dt = dt.replace(hour=dt.hour + 1, minute=0)
    else:
        dt = dt.replace(minute=rounded_minutes)
    return dt.replace(second=0, microsecond=0)


# Convert the rounded start time to Unix timestamp
def convert_to_unix_timestamp(dt):
    return int(time.mktime(dt.timetuple()))


# Fetch project and task
project_id, task_id = select_project_and_task()
if not project_id or not task_id:
    st.warning("Please select a valid project and task before proceeding.")
    st.stop()

# Multiple date selection
date_options = [datetime.today() - timedelta(days=i) for i in range(30)]
selected_dates = st.multiselect("Select multiple dates for offline time entry:", date_options, format_func=lambda x: x.strftime('%Y-%m-%d'))

if not selected_dates:
    st.warning("Please select at least one date.")
    st.stop()

# User comment input
user_comment = st.text_input("Enter a comment for the offline time entry:", "Team Management & RS_Tasks")
user_comment = user_comment.replace("&", "&amp;")

# Submit button
if st.button('Submit Offline Time Entries'):
    success_count = 0
    failure_count = 0

    for date in selected_dates:
        date_input = date.strftime('%Y-%m-%d')
        start_time = f"{date_input}T10:00:00+05:30"  # 10 AM IST
        end_time = f"{date_input}T19:00:00+05:30"  # 7 PM IST

        start_time_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S+05:30")
        rounded_start_time = round_to_nearest_10_minutes(start_time_obj)

        unix_timestamp = convert_to_unix_timestamp(rounded_start_time)
        end_time_obj = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S+05:30")
        duration_in_minutes = int((end_time_obj - rounded_start_time).total_seconds() / 60)

        xml_data = f"""
        <time_entry>
            <task_id>{task_id}</task_id>
            <user_comment>{user_comment}</user_comment>
            <from_timestamp>{unix_timestamp}</from_timestamp>
            <duration_in_minutes>{duration_in_minutes}</duration_in_minutes>
        </time_entry>
        """

        # API call to submit the offline time entry
        url = f"https://www.worksnaps.net/api/projects/{project_id}/time_entries.xml"
        response = requests.post(url, data=xml_data, headers=headers, auth=auth)

        if response.status_code == 201:
            success_count += 1
        else:
            failure_count += 1
            st.error(f"Failed to create entry for {date_input}. Status Code: {response.status_code}")

    st.success(f"Successfully submitted {success_count} entries. {failure_count} failed.")
