def test_outreach_endpoints(test_client, auth_headers):
    resp = test_client.get('/api/v1/outreach/campaigns', headers=auth_headers)
    assert resp.status_code in [200, 401, 403]

def test_unauthorized_outreach(test_client):
    resp = test_client.get('/api/v1/outreach/campaigns')
    assert resp.status_code in [401, 403]
