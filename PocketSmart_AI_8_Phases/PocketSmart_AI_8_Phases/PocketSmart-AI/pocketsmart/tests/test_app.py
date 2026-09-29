import os
os.environ['SECRET_KEY']='test-key-only-do-not-use-in-production-123456789'
os.environ['DATABASE_PATH']=':memory:'  # replaced in fixture with temporary file
os.environ.pop('GEMINI_API_KEY',None)
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'test.sqlite3'))
    with TestClient(app) as client:
        yield client

@pytest.fixture
def user(client):
    response=client.post('/register',json={'email':'test@example.com','password':'correctpassword123','name':'Dinesh'})
    assert response.status_code==201
    return client

def test_auth_and_history_isolation(client,user):
    assert user.get('/session-info').status_code==200
    assert user.get('/session-info').json()['name']=='Dinesh'
    assert user.get('/history').json()==[]
    user.post('/logout')
    assert user.get('/history').status_code==401
    assert user.post('/login',json={'email':'test@example.com','password':'wrongpassword'}).status_code==401
    assert user.post('/login',json={'email':'test@example.com','password':'correctpassword123'}).status_code==200

def test_existing_user_can_set_name(user):
    assert user.patch('/profile',json={'name':'  Dinesh Kumar  '}).json()['name']=='Dinesh Kumar'
    assert user.get('/session-info').json()['name']=='Dinesh Kumar'
    assert user.patch('/profile',json={'name':' '}).status_code==422

def test_planners_budget_and_history(user):
    home=user.post('/generate-home',json={'budget':500,'room':'Kitchen','style':'Modern','lights':4,'fans':1,'tables':1})
    assert home.status_code==200
    assert home.json()['total']<=500
    assert home.json()['remaining']>=0
    party=user.post('/generate-party',json={'budget':20000,'guests':30,'event_type':'Birthday','venue':'External','city':'Chennai'})
    assert party.status_code==200
    assert party.json()['total']<=20000
    jewelry=user.post('/generate-jewelry',data={'budget':4000,'occasion':'Wedding','style':'Classic','outfit_color':'red'})
    assert jewelry.status_code==200
    assert jewelry.json()['total']<=4000
    assert len(user.get('/history').json())==3
    assert user.get('/recommendations-details/999999').status_code==404

def test_validation_and_image(user):
    assert user.post('/generate-home',json={'budget':5000,'room':'Kitchen','style':'Modern','lights':0,'fans':0,'tables':0}).status_code==422
    invalid=user.post('/generate-jewelry',data={'budget':3000,'occasion':'Wedding','style':'Classic'},files={'image':('fake.png',b'not a png','image/png')})
    assert invalid.status_code==422
    image=user.post('/generate-jewelry',data={'budget':3000,'occasion':'Wedding','style':'Classic'},files={'image':('outfit.png',b'\x89PNG\r\n\x1a\n' + b'0'*10,'image/png')})
    assert image.status_code==200
    assert 'not analyzed' in ' '.join(image.json()['notes'])
