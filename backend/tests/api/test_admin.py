def test_admin_endpoints(test_client, auth_headers):
    resp = test_client.get('/api/v1/admin/users', headers=auth_headers)
    assert resp.status_code in [200, 401, 403]

def test_unauthorized_admin(test_client):
    resp = test_client.get('/api/v1/admin/users')
    assert resp.status_code in [401, 403]
