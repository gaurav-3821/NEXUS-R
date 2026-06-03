import urllib.request
import urllib.parse
import json
import time

with open('.nexus_token', 'r') as f:
    token = f.read().strip()

def api_post(path, data):
    req = urllib.request.Request('http://127.0.0.1:8000'+path+'?token='+token, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
    try: return json.loads(urllib.request.urlopen(req).read().decode())
    except Exception as e: return str(e)

def api_get(path):
    req = urllib.request.Request('http://127.0.0.1:8000'+path+'?token='+token)
    try: return json.loads(urllib.request.urlopen(req).read().decode())
    except Exception as e: return str(e)

print('Starting tinyllama...')
res = api_post('/api/v1/models/download', {'model_name': 'tinyllama'})
print(res)
if isinstance(res, dict):
    job_id = res.get('job_id')
    if job_id:
        for i in range(15):
            time.sleep(2)
            status = api_get(f'/api/v1/models/download-status/{job_id}')
            print(status.get('progress_percent'), status.get('message'))
            if status.get('status') == 'completed': break

print('Starting qwen2.5...')
res2 = api_post('/api/v1/models/download', {'model_name': 'qwen2.5'})
print(res2)
if isinstance(res2, dict):
    job_id2 = res2.get('job_id')
    if job_id2:
        for i in range(15):
            time.sleep(2)
            status = api_get(f'/api/v1/models/download-status/{job_id2}')
            print(status.get('progress_percent'), status.get('message'))
            if status.get('status') == 'completed': break
