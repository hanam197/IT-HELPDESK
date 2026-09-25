import time
from collections import defaultdict, deque
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from .database import get_db, settings
from .models import User

passwords = PasswordHash.recommended()
attempts = defaultdict(deque)

def check_login_limit(key):
    window = attempts[key]
    while window and window[0] < time.monotonic() - 300: window.popleft()
    if len(window) >= 10: raise HTTPException(429, 'Đăng nhập quá nhiều lần. Vui lòng thử lại sau 5 phút.')
    window.append(time.monotonic())

def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get('helpdesk_session')
    if not token: raise HTTPException(401, 'Vui lòng đăng nhập')
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=['HS256'])
        user = db.get(User, int(claims['sub']))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Phiên đăng nhập đã hết hạn')
    if not user or user.archived: raise HTTPException(401, 'Tài khoản đã ngừng hoạt động')
    return user

ADMIN_RESOURCES = {'users', 'master-data', 'asset-types', 'locations'}
SUPPORT_RESOURCES = {'tickets', 'maintenance', 'articles', 'ticket-articles', 'operations'}
def authorize(user, resource):
    if user.role == 'ADMIN': return
    if resource in ADMIN_RESOURCES or user.role == 'VIEWER': raise HTTPException(403, 'Bạn không có quyền thực hiện thao tác này')
    if user.role == 'IT_MANAGER': return
    if user.role == 'IT_SUPPORT' and resource in SUPPORT_RESOURCES: return
    raise HTTPException(403, 'Bạn không có quyền thực hiện thao tác này')
