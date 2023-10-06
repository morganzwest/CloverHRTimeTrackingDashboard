import requests
import json
import calendar
from datetime import datetime, timedelta

# Load Clockify configuration
with open('config/clockify_config.json', 'r') as f:
    clockify_config = json.load(f)
API_URL = clockify_config["API_URL"]
REPORTS_API_URL = clockify_config["REPORTS_API_URL"]
API_KEY = clockify_config["API_KEY"]
WORKSPACE_ID = clockify_config["WORKSPACE_ID"]
CLOCKIFY_HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

def extract_summary(data):
    """
    Extract and compute the summary of logged hours for each project.

    :param data: The JSON response data from the Clockify API.
    :return: A list of dictionaries containing summary information for each project.
    """
    summary_list = []
    # Loop through each project in the data
    for project in data.get('groupOne', []):
        project_name = project.get('name', "Unknown Project")
        # Filter tasks named "Retained Hours" within the project
        retained_hours_tasks = [task for task in project.get('children', []) if task.get('name') == "Retained Hours"]
        # Calculate the total duration for the retained hours tasks and convert it to hours
        actual_time_duration = sum([task.get('duration', 0) for task in retained_hours_tasks]) / (60 * 60)
        estimated_time_duration = 0  # Placeholder for future enhancements
        summary_list.append({
            "client": project.get('clientName', 'Unknown Client'),
            "project": project_name,
            "actual_time": actual_time_duration,
        })
    return summary_list

def get_data_for_month(year, month):
    """
    Fetch the time entry data for a specific month and year from the Clockify API.

    :param year: The year for which data is required.
    :param month: The month for which data is required.
    :return: The JSON response from the Clockify API.
    """
    # Calculate the start and end dates for the month
    first_day_of_month = datetime(year, month, 1).isoformat() + "Z"
    if month == 12:
        last_day_of_month = datetime(year + 1, 1, 1) - timedelta(seconds=1)  # Last second of December
    else:
        last_day_of_month = datetime(year, month + 1, 1) - timedelta(seconds=1)  # Last second of the month
    # Define parameters for the API request
    params = {
        "dateRangeStart": first_day_of_month,
        "dateRangeEnd": last_day_of_month.isoformat() + "Z",
        "summaryFilter": {
            "groups": ["CLIENT", "PROJECT", "TIMEENTRY"]
        }
    }
    # Make the API request to fetch the data
    response = requests.post(f"{REPORTS_API_URL}/workspaces/{WORKSPACE_ID}/reports/summary", headers=CLOCKIFY_HEADERS, json=params)
    return response.json()
