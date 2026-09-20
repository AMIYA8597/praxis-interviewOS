import os
import json
from fastapi.testclient import TestClient
from backend.app.main import app

def run():
    print('WITH KEY:')
    os.environ['GROQ_API_KEY'] = 'fake-groq-key'
    os.environ['LOCAL_ONLY_MODE'] = 'false'
    with TestClient(app) as client:
        resp = client.get('/api/v1/health/providers')
        print(json.dumps(resp.json(), indent=2))
        
    print('WITHOUT KEY:')
    del os.environ['GROQ_API_KEY']
    with TestClient(app) as client:
        resp = client.get('/api/v1/health/providers')
        print(json.dumps(resp.json(), indent=2))

if __name__ == '__main__':
    run()
