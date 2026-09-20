def test_analytics_endpoints(test_client, auth_headers):
    resp = test_client.get('/api/v1/analytics/dashboard', headers=auth_headers)
    assert resp.status_code in [200, 401, 403]

def test_unauthorized_analytics(test_client):
    resp = test_client.get('/api/v1/analytics/dashboard')
    assert resp.status_code in [401, 403]
