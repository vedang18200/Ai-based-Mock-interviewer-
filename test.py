import requests

API_KEY = "AIzaSyBa6y10WFEQu2SDoLACcHKo86tzfhNetaQ"
url = f"https://generativelanguage.googleapis.com/v1/models?key={API_KEY}"

response = requests.get(url)
print(response.json())  # Check available models
