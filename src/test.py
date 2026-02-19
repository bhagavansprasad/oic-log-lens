import requests

with open('flow-logs/01_flow-log.json', 'r') as f:
    log_content = f.read()

response = requests.post(
    'http://localhost:8000/search',
    json={'log_content': log_content}
)

print(response.json())
