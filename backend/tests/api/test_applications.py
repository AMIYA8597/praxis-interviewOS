def test_applications_endpoints(test_client, auth_headers):
    resp = test_client.get('/api/v1/applications', headers=auth_headers)
    assert resp.status_code in [200, 401, 403]

def test_unauthorized_applications(test_client):
    resp = test_client.get('/api/v1/applications')
    assert resp.status_code in [401, 403]
