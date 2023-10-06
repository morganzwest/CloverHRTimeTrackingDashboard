
# Clover HR: Time Tracking Dashboard
## Description:
This web application integrates with HubSpot and Clockify to provide a summarized dashboard that showcases the time spent on various projects over the past six months. It highlights variations in time spent compared to contracted hours, allowing users to quickly understand how projects are progressing.

## How it Works:
1. The application fetches active clients from HubSpot.
2. For each client, it retrieves time-tracking data from Clockify for the past six months.
3. It computes the average time spent and variations from the contracted hours.
4. The data is then presented in a summarized dashboard with colors indicating if the time spent exceeds the contracted hours.

## Deployment:
Prerequisites: Ensure you have Python 3.7 installed.

1. Clone the repository:
  ```bash
  git clone https://github.com/morganzwest/CloverHRTimeTrackingDashboard.git
  cd CloverHRTimeTrackingDashboard
  ```

2. Configuration
  Configuration is done through JSON files for each API:

HubSpot Configuration:
  Create a file named `hubspot_config.json` inside the `config` folder:
  ```json
  {
      "API_KEY": "YOUR_HUBSPOT_API_KEY"
  }
  ```
Clockify Configuration:
  Create a file named `clockify_config.json` inside the `config` folder:
  ```json
  {
      "API_URL": "https://api.clockify.me/api/v1",
      "REPORTS_API_URL": "https://reports.api.clockify.me/v1",
      "API_KEY": "YOUR_CLOCKIFY_API_KEY",
      "WORKSPACE_ID": "YOUR_WORKSPACE_ID"
  }
  ```

3. Install Requirements
   ```
   pip install -r requirements.txt
   ```
4. Run the app
   ```
   python app.py
   ```
