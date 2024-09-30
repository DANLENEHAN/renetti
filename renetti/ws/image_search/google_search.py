# <script async src="https://cse.google.com/cse.js?cx=870431f83f7264ab0">
# </script>
# <div class="gcse-search"></div>

import os

import requests  # type: ignore

api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
search_engine_id = "870431f83f7264ab0"
query = "Life Fitness Leg Extension"
url = (
    f"https://www.googleapis.com/customsearch/v1?key={api_key}"
    f"&cx={search_engine_id}&q={query}&searchType=image"
)

response = requests.get(url=url)
results = response.json()
image_link = results["items"][0]["link"]

print(image_link)
