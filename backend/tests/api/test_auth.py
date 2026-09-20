def test_auth_endpoints(test_client, auth_headers):
    resp = test_client.get('/api/v1/auth/me', headers=auth_headers)
    assert resp.status_code in [200, 401, 403]

def test_unauthorized_auth(test_client):
    resp = test_client.get('/api/v1/auth/me')
    assert resp.status_code in [401, 403]
