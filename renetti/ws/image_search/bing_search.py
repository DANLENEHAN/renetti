"""
Pricing: currently on F1: https://www.microsoft.com/en-us/bing/apis/pricing
(azure) resource group -> gymnet -> resource gymnetsearch
"""

import os

import requests  # type: ignore

endpoint = "https://api.bing.microsoft.com/v7.0/images/search"
query = "Life Fitness Leg Extension"
mkt = "en-US"
params = {"q": query, "mkt": mkt}
headers = {"Ocp-Apim-Subscription-Key": os.getenv("MICROSOFT_SEARCH_API_KEY")}

# Call the API
try:
    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()
    print(response.json())
except Exception as ex:
    raise ex
