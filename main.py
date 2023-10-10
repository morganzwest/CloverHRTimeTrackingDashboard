from flask import Flask, render_template, stream_with_context, Response
import calendar, json
from datetime import datetime, timedelta
from hubspot import fetch_companies_with_client_code, update_hubspot_company_risk_factor
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

# Set the consistent secret key
app.config["SECRET_KEY"] = "122e7daa-5ca7-4a63-a289-c7af7df2c1da"

SimpleLogin(app)

def calculate_quartiles(data):
    """
    Calculate the first and third quartiles of a dataset.

    :param data: List of numbers
    :return: Q1, Q3
    """
    sorted_data = sorted(data)
    n = len(sorted_data)

    if n % 2 == 0:
        median_pos = n // 2
        lower_data = sorted_data[:median_pos]
        upper_data = sorted_data[median_pos:]
    else:
        median_pos = n // 2
        lower_data = sorted_data[:median_pos]
        upper_data = sorted_data[median_pos + 1:]

    Q1 = median(lower_data)
    Q3 = median(upper_data)

    return Q1, Q3

def median(data):
    """
    Compute the median of a dataset.

    :param data: List of numbers
    :return: Median value
    """
    n = len(data)
    mid = n // 2

    if n % 2 == 0:
        return (data[mid - 1] + data[mid]) / 2
    else:
        return data[mid]

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

def calculate_risk_factors(hubspot_clients, averages, today):
    client_code = client[0]
    contracted_hours = float(client[3])
    average_time = averages.get(client_code, 0)
    
    # RAG rating to value
    rag_rating = client[6]
    rag_value = {'Red': 0, 'Amber': 16.65, 'Green': 33.3}.get(rag_rating, 0)
    
    # Calculate actual hours usage percentage
    usage_percentage = (average_time / contracted_hours) * 100 if contracted_hours != 0 else 0
    if usage_percentage > 100: usage_percentage = 100
    
    # Months since start
    start_date = datetime.fromtimestamp(int(client[5]) / 1000)
    months_since_start = (today.year - start_date.year) * 12 + today.month - start_date.month - 3
    if months_since_start > 33.3:
        months_since_start = 33.3
    elif months_since_start < 0:
        months_since_start = 0

    # Risk Factor calculation
    risk_factor = rag_value + (usage_percentage / 3) + months_since_start
    print("RISK:",client_code,rag_value,usage_percentage,months_since_start,risk_factor)
    risk_factors[client_code] = risk_factor

    return risk_factors

def calculate_client_risk_factor(client, average_time, today):
    client_code = client[0]
    contracted_hours = float(client[3])
    
    # RAG rating to value
    rag_rating = client[6]
    rag_value = {'Red': 0, 'Amber': 16.65, 'Green': 33.3}.get(rag_rating, 0)

    # Calculate actual hours usage percentage
    usage_percentage = (average_time / contracted_hours) * 100 if contracted_hours != 0 else 0
    if usage_percentage > 100: usage_percentage = 100
    print(f"For client {client_code}: Average Time = {average_time}, Contracted Hours = {contracted_hours}, Calculated Usage = {usage_percentage}")

    # Months since start
    start_date = datetime.fromtimestamp(int(client[5]) / 1000)
    months_since_start = (today.year - start_date.year) * 12 + today.month - start_date.month - 3
    if months_since_start > 33.3:
        months_since_start = 33.3
    elif months_since_start < 0:
        months_since_start = 0

    # Risk Factor calculation
    risk_factor = 100 - (rag_value + (usage_percentage / 3) + months_since_start)

    print("RISK:",client_code,rag_value,usage_percentage,months_since_start,risk_factor)
    
    return risk_factor



@app.route('/risk')
@login_required
def risk():
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
        print("Averages:",averages[client])

    merged_data = []
    for client in hubspot_clients:
        client_code = client[0]
        name = client[2]
        monthly_fee = client[4]
        rag = client[6]
        average_time = averages.get(client_code, 0)
        
        # Calculate risk factor
        risk_factor = calculate_client_risk_factor(client, average_time, today)
        
        # Calculate time variation (or any other metric for Percentage of Time Used)
        contracted_hours = float(client[3])

        # Calculate time variation (or any other metric for Percentage of Time Used)
        time_variation = (average_time - contracted_hours) / contracted_hours * 100 if contracted_hours != 0 else 0
        usage_percentage = (average_time / contracted_hours) * 100 if contracted_hours != 0 else 0

        # Months as a client
        start_date = datetime.fromtimestamp(int(client[5]) / 1000)
        months_as_client = (today.year - start_date.year) * 12 + today.month - start_date.month

        risk_factor = float(risk_factor)
        monthly_fee = float(monthly_fee)

        if contracted_hours > 0:
            merged_data.append({
            "code": client_code,
            "name": name,
            "risk_factor": risk_factor,
            "monthly_fee": monthly_fee,
            "usage": usage_percentage,
            "rag": rag,
            "months_as_client": months_as_client,
            "safe_revenue": monthly_fee - ((risk_factor / 100) * monthly_fee),
            "risk_revenue": (risk_factor / 100) * monthly_fee
        })    

    # Adjusting the month to display in the summary
    month_to_display = today.month - 1
    year_to_display = today.year
    if month_to_display == 0:
        month_to_display = 12
        year_to_display -= 1
    month_name = calendar.month_name[month_to_display]

    merged_data.sort(key=lambda x: x['risk_factor'], reverse=True)

    risk_factors = [entry['risk_factor'] for entry in merged_data]
    Q1, Q3 = calculate_quartiles(risk_factors)

    # Return the rendered template with the merged data
    return render_template('risk.html', summary_data=merged_data, month_name=month_name, year=year_to_display, Q1=Q1, Q3=Q3)

@app.route('/clockify')
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

    risk_factors = {}
    for client in hubspot_clients:
        client_code = client[0]
        contracted_hours = float(client[3])
        average_time = averages.get(client_code, 0)
        
        # RAG rating to value
        rag_rating = client[6]
        rag_value = {'Red': 0, 'Amber': 16.65, 'Green': 33.3}.get(rag_rating, 0)
        
        # Calculate actual hours usage percentage
        usage_percentage = (average_time / contracted_hours) * 100 if contracted_hours != 0 else 0
        if usage_percentage > 100: usage_percentage = 100
        
        # Months since start
        start_date = datetime.fromtimestamp(int(client[5]) / 1000)

        months_since_start = (today.year - start_date.year) * 12 + today.month - start_date.month - 3
        if months_since_start > 33.3:
            months_since_start = 33.3
        elif months_since_start < 0:
            months_since_start = 0

        # Risk Factor calculation
        risk_factor = 100 - (rag_value + (usage_percentage / 3) + months_since_start)
        print("RISK:",client_code,rag_value,usage_percentage,months_since_start,risk_factor)
        risk_factors[client_code] = risk_factor
        
    print("Calculated risk factors:", risk_factors)

    # Merging the averaged data with the client data
    merged_data = []
    for client in hubspot_clients:
        client_code = client[0]
        average_time = averages.get(client_code, 0)
        time_variation = time_variations.get(client_code, 0)

        # Reversing the order of monthly data for display purposes
        reversed_monthly_data = list(six_month_data[client_code])
        reversed_monthly_data.reverse()

        if float(client[3]) != 0:
            merged_data.append(
                {
                    "code": client[0],
                    "package": client[1],
                    "name": client[2],
                    "contracted_hours": client[3],
                    "monthly_fee": client[4],
                    "time_variation": time_variation,
                    "monthly_data": reversed_monthly_data,
                    "risk_factor": risk_factors.get(client_code, 0),
                    "id": client[7]
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

    # for entry in merged_data:
    #     company_id = entry['id']
    #     risk_factor = entry['risk_factor']
    #     update_hubspot_company_risk_factor(company_id, risk_factor, HUBSPOT_API_KEY)
    #     print(f"POST: {entry['id']} - {risk_factor}")

    for entry in merged_data:
        if float(entry["contracted_hours"]) == 0:
            print("Entry with zero contracted_hours:", entry)

    # Rendering the summary page with the computed data
    return render_template('clockify.html', summary_data=merged_data, months=last_six_months, month_name=month_name, year=year_to_display)

logs = []

@app.route('/')
@login_required
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run()
