import requests
import json

def get_product_links(query):
    params = {
        "api_key": "496c86a4cd9773be0204caaf0a304d2533a895b2150fbb5aa7a72cdc738dbbb7",
        "engine": "google",
        "q": query,
        "location": "India",
        "google_domain": "google.co.in",
        "gl": "in",
        "hl": "en",
        "num": 1  # Limit to 5 results
    }

    # Disable SSL verification
    response = requests.get("https://serpapi.com/search.json", params=params, verify=False)
    # Suppress the warning about insecure requests
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    data = response.json()

    if data["organic_results"]:
        return data["organic_results"][0]["link"]
    else:
        return None

if __name__ == "__main__":
    results = get_product_links("JBL Flip 6 speakers")
    print(json.dumps(results, indent=4))
    with open('search_results_full.json', 'w', encoding='utf-8') as f:
        json.dump(results, indent=4, fp=f)