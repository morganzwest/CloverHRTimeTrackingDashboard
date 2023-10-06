
# Clover HR: Time Tracking Dashboard
## Description:
This web application integrates with HubSpot and Clockify to provide a summarized dashboard that showcases the time spent on various projects over the past six months. It highlights variations in time spent compared to contracted hours, allowing users to quickly understand how projects are progressing.

## How it Works:
- The application fetches active clients from HubSpot.
- For each client, it retrieves time-tracking data from Clockify for the past six months.
- It computes the average time spent and variations from the contracted hours.
- The data is then presented in a summarized dashboard with colors indicating if the time spent exceeds the contracted hours.

##Deployment:
Prerequisites: Ensure you have Python 3.x installed.
Clone the repository:
```git clone <repository_url>```
Navigate to the project directory:
```cd <project_name>```
Install the required packages:
```pip install -r requirements.txt```

Run the application:
```python app.py```

The application should now be running on localhost:5000 or the port specified in your environment.
