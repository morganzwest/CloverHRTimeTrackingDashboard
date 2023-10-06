from flask import Flask, render_template
import calendar, json
from datetime import datetime, timedelta
from hubspot import fetch_companies_with_client_code
from clockify import extract_summary, get_data_for_month
from flask_simplelogin import SimpleLogin, login_required

# Constants related to the Clockify API
API_URL = "https://api.clockify.me/api/v1"
REPORTS_API_URL = "https://reports.api.clockify.me/v1"
API_KEY = "ZmU5NWNjNTQtZmNmNS00ZjFhLThlZDQtMDkyMmZkNzczYzE4"  # Clockify API Key
CLOCKIFY_HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}
WORKSPACE_ID = "618246e19fb91229a633b569"  # Workspace ID for Clockify

# Load HubSpot configuration
with open('config/hubspot_config.json', 'r') as f:
    hubspot_config = json.load(f)
HUBSPOT_API_KEY = hubspot_config["API_KEY"]

app = Flask(__name__)
SimpleLogin(app)

# Function to determine the color based on a comparison of two values
def color_based_on_value(value, comparison):
    if value > comparison:
        return 'red'
    else:
        return 'green'

# Registering a custom filter for Jinja templates
app.jinja_env.filters['color_based_on_value'] = color_based_on_value

# Function to merge data from projects and client data
def merge_project_and_client_data(projects_data, client_data):
    merged_data = []
    
    for client in client_data:
        for project in projects_data:
            p_code = project["project"].split()[0]

            if client[0] == project["project"].split()[0]:
                merged_data.append(
                    [
                        client[0], #code
                        client[1], #package
                        client[2], #name
                        client[3], #contracted hours
                        client[4], #monthly fee
                        project["actual_time"] #used time
                    ]
                )
    return merged_data

@app.route('/')
@login_required
def summary():
    today = datetime.today()
    year = today.year
    month = today.month

    # Decrement the month to skip the current month's data
    month -= 1
    if month == 0:  # If month becomes 0 (i.e., it was January), adjust to December of the previous year
        month = 12
        year -= 1

    # Fetching active clients from HubSpot
    hubspot_clients = fetch_companies_with_client_code(HUBSPOT_API_KEY=HUBSPOT_API_KEY)

    # Dictionary to store the data for the past six months for each client
    six_month_data = {}
    for client in hubspot_clients:
        client_code = client[0]
        six_month_data[client_code] = []

    # Function to get the names of the last six months
    def get_last_six_months(today):
        month_names = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
        months = []
        month, year = today.month, today.year
        for _ in range(6):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
            months.append(month_names[month - 1])
        return months[::-1]

    # Looping through the past six months to fetch and process data
    for _ in range(6):
        monthly_data = get_data_for_month(year, month)
        summary_data = extract_summary(monthly_data)

        # Extracting the actual time for each client
        for client in hubspot_clients:
            client_code = client[0]
            actual_time = next((entry["actual_time"] for entry in summary_data if entry["project"].startswith(client_code)), 0)
            six_month_data[client_code].append(actual_time)

        # Adjusting the date for the next iteration
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    # Computing the average time for the past six months for each client
    averages = {}
    for client, times in six_month_data.items():
        avg = sum(times) / 6
        averages[client] = avg

    # Calculating the variation in time from the contracted hours for each client
    time_variations = {}
    for client in hubspot_clients:
        client_code = client[0]
        contracted_hours = float(client[3])
        average_time = averages.get(client_code, 0)
        time_variations[client_code] = average_time - contracted_hours

    # Merging the averaged data with the client data
    merged_data = []
    for client in hubspot_clients:
        client_code = client[0]
        average_time = averages.get(client_code, 0)
        time_variation = time_variations.get(client_code, 0)

        # Reversing the order of monthly data for display purposes
        reversed_monthly_data = list(six_month_data[client_code])
        reversed_monthly_data.reverse()

        merged_data.append(
            {
                "code": client[0],
                "package": client[1],
                "name": client[2],
                "contracted_hours": client[3],
                "monthly_fee": client[4],
                "time_variation": time_variation,
                "monthly_data": reversed_monthly_data
            }
        )

    # Sorting the merged data by time variation in descending order
    merged_data.sort(key=lambda x: x['time_variation'], reverse=True)

    # Adjusting the month to display in the summary
    month_to_display = today.month - 1
    year_to_display = today.year
    if month_to_display == 0:
        month_to_display = 12
        year_to_display -= 1
    month_name = calendar.month_name[month_to_display]
    
    last_six_months = get_last_six_months(today)

    # Rendering the summary page with the computed data
    return render_template('summary.html', summary_data=merged_data, months=last_six_months, month_name=month_name, year=year_to_display)

if __name__ == '__main__':
    app.run()
