import json
import requests

url = "https://ai-based-mock-interviewe-64e51-default-rtdb.firebaseio.com/mock_interviews.json"

response = requests.get(url)

# Debugging step: Print the response text
print("Raw Response:", response.text)

try:
    data = response.json()  # Try to decode JSON
    print("Decoded Data:", data)
except json.decoder.JSONDecodeError:
    print("Error: Response is not valid JSON!")
