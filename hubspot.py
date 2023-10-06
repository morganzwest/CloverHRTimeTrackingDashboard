# hubspot_helper.py

import requests
import json
import urllib.parse

def fetch_companies_with_client_code(max_results=15000, HUBSPOT_API_KEY=None, limit=250):
    """
    Fetches a list of companies from HubSpot that have a client code.

    Parameters:
    - max_results: The maximum number of companies to fetch.
    - HUBSPOT_API_KEY: The API key used to authenticate with HubSpot.
    - limit: The number of companies fetched in each request.

    Returns:
    - A list of companies where each company is represented by a list of attributes:
      [client_code, package, name, hours, fee]
    """
    
    # Initialize the list to store companies data
    company_list = []

    # HubSpot API endpoint to fetch companies
    get_all_companies_url = "https://api.hubapi.com/companies/v2/companies/paged?"

    # Parameters to send with each request
    parameter_dict = {
        'limit': limit,
        'properties': ['name', 'client_code', 'status', 'hours_per_month', 'package_type', 'income_per_month']
    }

    # Headers for the request
    headers = {
        'Authorization': f"Bearer {HUBSPOT_API_KEY}",
        'Content-Type': 'application/json'
    }

    # Paginate the request using offset
    has_more = True
    while has_more:
        # Construct the full URL with parameters
        parameters = urllib.parse.urlencode(parameter_dict, doseq=True)
        get_url = get_all_companies_url + parameters

        # Make the GET request
        r = requests.get(url=get_url, headers=headers)
        response_dict = json.loads(r.text)

        # Update the flag for pagination based on response
        has_more = response_dict.get('has-more', False)

        # Extend the company list with the fetched data
        company_list.extend(response_dict.get('companies', []))

        # Update the offset for the next set of results
        parameter_dict['offset'] = response_dict.get('offset', None)

        # Break the loop if no more companies or reached the max_results
        if not parameter_dict['offset'] or len(company_list) >= max_results:
            break

    # Extract relevant data from the company list
    companies_with_client_code = []

    for company in company_list:
        properties = company.get('properties', {})

        # Only consider companies with a client_code
        if 'client_code' in properties:
            try:
                # Extract properties of each company
                name = properties.get('name', {}).get('value', 'Unknown Name')
                client_code = properties['client_code']['value']
                status = properties['status']['value']
                hours = properties['hours_per_month']['value']
                package = properties['package_type']['value']
                fee = properties['income_per_month']['value']

                # Only add companies with 'Active' status to the list
                if status == "Active":
                    companies_with_client_code.append(
                        [
                            client_code,  # 0
                            package,      # 1
                            name,         # 2
                            hours,        # 3
                            fee           # 4
                        ]
                    )
            except KeyError:  # Skip the company if any property is missing
                continue

    return companies_with_client_code
