def test_smoke(test_client):
    assert test_client.get('/api/v1/health/live').status_code == 200
