from flask import redirect, request, session
from app import create_app
from app.db import Session
from app.models import User
app=create_app()
@app.route('/__typography_login')
def __typography_login():
    db=Session(); user=db.get(User,1)
    session['uid']=user.id; session['username']=user.username; session['nickname']=user.nickname or user.username; session['session_version']=int(user.session_version or 1); session['role']=user.role or 'admin'; session['must_change_password']=0; session['mfa_verified']=True; db.close()
    target=request.args.get('next') or '/'
    return redirect(target if target.startswith('/') else '/')
if __name__=='__main__': app.run(host='127.0.0.1',port=5033,debug=False)
