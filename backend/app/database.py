from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Settings(BaseSettings):
    database_url: str = 'sqlite:///./helpdesk.db'
    secret_key: str
    seed_password: str = ''
    frontend_url: str = 'http://localhost:8080'
    secure_cookie: bool = False
    upload_dir: str = './uploads'
    model_config = {'env_file': '.env', 'extra': 'ignore'}

settings = Settings()
engine = create_engine(settings.database_url, connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}, pool_pre_ping=True)
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as db:
        yield db
