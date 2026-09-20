import os
import tempfile
os.environ['SECRET_KEY']='test-secret-key-with-at-least-thirty-two-characters'
os.environ['DATABASE_URL']=os.environ.get('TEST_DATABASE_URL','sqlite:///'+tempfile.mktemp(suffix='.db'))
os.environ['SEED_PASSWORD']='TestPassword2026!'
os.environ['UPLOAD_DIR']=tempfile.mkdtemp()
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app
from app.seed import seed

@pytest.fixture(scope='session',autouse=True)
def setup():
    Base.metadata.create_all(engine)
    seed()
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    with TestClient(app,headers={'X-Requested-With':'Helpdesk'}) as c:
        assert c.post('/api/auth/login',json={'username':'admin','password':'TestPassword2026!'}).status_code==200
        yield c

@pytest.fixture
def meta(client): return client.get('/api/meta').json()
