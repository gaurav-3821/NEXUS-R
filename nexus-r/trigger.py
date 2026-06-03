import requests
import time

token = 'nexus-1Ntmef77xH9COytY '
url = 'http://127.0.0.1:8000/api/v1/models/download'
res = requests.post(url, params={'token': token}, json={'model_name': 'qwen2.5:0.5b'})
print('Start qwen:', res.status_code, res.text)
if res.status_code == 200:
    job = res.json().get('job_id')
    for i in range(15):
        time.sleep(2)
        s = requests.get(f'http://127.0.0.1:8000/api/v1/models/download-status/{job}', params={'token': token})
        if s.status_code == 200:
            print(f"Progress: {s.json().get('progress_percent')}% {s.json().get('message')}")
            if s.json().get('status') in ('completed', 'failed'):
                break

res2 = requests.post(url, params={'token': token}, json={'model_name': 'tinyllama'})
print('Start tinyllama:', res2.status_code, res2.text)
if res2.status_code == 200:
    job2 = res2.json().get('job_id')
    for i in range(15):
        time.sleep(2)
        s = requests.get(f'http://127.0.0.1:8000/api/v1/models/download-status/{job2}', params={'token': token})
        if s.status_code == 200:
            print(f"Progress: {s.json().get('progress_percent')}% {s.json().get('message')}")
            if s.json().get('status') in ('completed', 'failed'):
                break

models = requests.get('http://127.0.0.1:8000/api/v1/models/local', params={'token': token})
print('Local models:', models.json())
