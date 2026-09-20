"""Create the first production administrator without any demo data."""
import getpass
from sqlalchemy import select
from .database import SessionLocal
from .models import User
from .security import passwords
from .defaults import install_defaults
from .services import audit

def main():
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role=='ADMIN')): raise SystemExit('An administrator already exists.')
        username=input('Administrator username: ').strip()
        name=input('Display name: ').strip()
        password=getpass.getpass('Password (12+ characters): ')
        if not username or not name or len(password)<12: raise SystemExit('Invalid administrator details.')
        user=User(username=username,name=name,role='ADMIN',password_hash=passwords.hash(password))
        db.add(user); db.flush(); install_defaults(db); audit(db,user,'created','users',user)
        db.commit()
        print('Administrator created. Default statuses installed. Configure asset types and locations in Settings.')
if __name__=='__main__': main()
