def test_successful_logins_do_not_lock_out_admin(client):
    for _ in range(12):
        response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'TestPassword2026!'})
        assert response.status_code == 200
    for _ in range(10):
        response = client.post('/api/auth/login', json={'username': 'missing-user', 'password': 'invalid-password'})
        assert response.status_code == 401
    assert client.post('/api/auth/login', json={'username': 'missing-user', 'password': 'invalid-password'}).status_code == 429
