import requests
# response = requests.get("https://randomuser.me/api/")
# print(response.text)

response = requests.get("https://api.thecatapi.com/v1/breedz")
response

print(response.status_code)

print(response.reason)

print(response.request.headers)