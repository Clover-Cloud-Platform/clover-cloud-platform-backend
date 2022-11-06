import socketio
import uuid
import rsa
import eventlet
import subprocess
import random
import string
import smtplib as smtp
from getpass4 import getpass
from pymongo import MongoClient
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



with open('private.pem', 'rb') as f:
    privkey = rsa.PrivateKey.load_pkcs1(f.read())
with open('public.pem', 'rb') as f:
    pubkey = rsa.PublicKey.load_pkcs1(f.read())



sio = socketio.Server(cors_allowed_origins='*', cors_allowed_headers="Origin, X-Requested-With, Content-Type, Accept")
app = socketio.WSGIApp(sio)
server_list = {}
email = getpass('email')
password = getpass('password')
client = MongoClient("mongodb adress")
db = client.test
users = db.users



def send_mail(subject, data, auth_code):
    msg = MIMEMultipart('alternative')
    auth_code = auth_code
    msg['Subject'] = subject
    msg['From'] = email
    msg['To'] = data['email']
    data = data
    html = f"""\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <title>Verify your email</title>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Google+Sans:400,500,700|Roboto:400,400italic,500,500italic,700,700italic|Roboto+Mono:400,500,700&amp;display=swap">
        <style>
@media screen and (max-width: 600px) {{
  .header {{
    font-size: 20px;
  }}

  .container {{
    margin: 5px;
    padding: 5px;
  }}
}}
</style>
    </head>
    <body style="margin: 0;">
        <div class="container" style="background-color: #f5f3ff; padding: 20px; border-radius: 10px; margin: 20px;">
            <img src="https://github.com/Clover-Cloud-Platform/clover-cloud-platform-frontend/raw/master/src/assets/email-logo.png" alt="logo" width="100px" height="100px" style="display: block; margin-left: auto; margin-right: auto;">
            <p class="header" style="font-family: Google Sans,Noto Sans,sans-serif; line-height: 1.2em; font-weight: 400; text-align: center; font-size: 30px; color: #000000e0;">Welcome to the Clover Cloud Platform!</p><p class="text" style="font-family: Roboto,sans-serif; font-size: 16px; line-height: 1.5em; font-weight: 400; text-align: center; color: #000000e0;">Your verification code is:</p>
            <p class="code" style="font-family: Google Sans,Noto Sans,sans-serif; font-size: 48px; font-weight: 700; text-align: center; color: #000000e0; letter-spacing: 4px; margin: 14px 0; width: 100%;">{str(auth_code)}</p>
            <p class="text" style="font-family: Roboto,sans-serif; font-size: 16px; line-height: 1.5em; font-weight: 400; text-align: center; color: #000000e0;">All you have to do is copy the verification code and paste it to your form to complete the registration process.</p>
        </div>
    </body>
</html>
"""
    content = MIMEText(html, 'html')
    msg.attach(content)
    server = smtp.SMTP_SSL('smtp.yandex.com')
    server.set_debuglevel(1)
    server.ehlo(email)
    server.login(email, password)
    server.sendmail(email, data['email'], msg.as_string())
    server.quit()


@sio.on('ConnectServer')
def new_server(sid, data):
    server_list[sid] = data
    print(server_list)


@sio.on('CreateNewInstance')
def create_event(sid, data):
    cont_name = data['cont_name']
    cont_code = "c" + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))
    cont_list = users.find_one({'uid': data['uid']})['cont_list']

    if cont_list[0] == False:
        cont_list[0] = {cont_name: cont_code}
    else:
        cont_list[1] = {cont_name: cont_code}

    for key in server_list:
        if len(server_list[key]) < 16:
            instance_sid = key
            break
        else:
            print('No cont')

    sio.emit('CreateInstance',
             {'cont_code': cont_code, 'uid': data['uid'], 'cont_name': data['cont_name'], 'cont_list': cont_list},
             room=instance_sid)


@sio.on('InstanceCreated')
def create_ok(sid, data):
    if data['create_status'] == True:
        users.update_one({'uid': data['uid']}, {'$set': {'cont_list': data['cont_list']}})
        server_list[sid] = data['server_cont_list']
        sio.emit('InstanceCreated', {'name': data['cont_name'], 'code': data['cont_code']})


@sio.on('GetUsername')
def get_username(sid, data):
    if users.find_one({'uid': str(data)}) != None:
        username = users.find_one({'uid': str(data)})['username']
        user_cont_list = users.find_one({'uid': str(data)})['cont_list']
        cont_list = []
        print('ok1')
        print(user_cont_list)
        for ind in user_cont_list:
            if ind != False:
                for key in ind:
                    print(key)
                    for s_key in server_list:
                        print(s_key)
                        print(ind[key])
                        print(server_list[s_key])
                        if ind[key] in server_list[s_key]:
                            print('ok2')
                            sio.emit('GetRunningInstances',
                                     {'username': username, 'user_cont_list': user_cont_list, 'sid': sid}, room=s_key)
            else:
                cont_list.append(False)

        if cont_list == [False, False]:
            user = {'username': username, 'cont_list': [], 'cont_codes': [], 'running': []}
            sio.emit('Username', user)

    else:
        sio.emit('Username', False)


@sio.on('RunningInstances')
def running(sid, data):
    user = {'username': data['username'], 'cont_list': data['cont_list'], 'cont_codes': data['cont_codes'],
            'running': data['running']}
    sio.emit('Username', user, room=data['sid'])


@sio.on('StartInstance')
def cont_start(sid, data):
    cont_list = users.find_one({'uid': data['uid']})['cont_list']
    cont_name = data['cont_name']

    if data['cont_name'] in cont_list[0]:
        cont_code = cont_list[0][cont_name]
        for key in server_list:
            if cont_code in server_list[key]:
                sio.emit('StartInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'], 'sid': sid},
                         room=key)

    elif data['cont_name'] in cont_list[1]:
        cont_code = cont_list[1][cont_name]
        for key in server_list:
            if cont_code in server_list[key]:
                sio.emit('StartInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'], 'sid': sid},
                         room=key)

    else:
        pass


@sio.on('InstanceStarted')
def started(sid, data):
    sio.emit('InstanceStarted', data['cont_name'], room=data['sid'])


@sio.on('StopInstance')
def cont_stop(sid, data):
    cont_list = users.find_one({'uid': data['uid']})['cont_list']
    cont_name = data['cont_name']

    if data['cont_name'] in cont_list[0]:
        cont_code = cont_list[0][cont_name]
        for key in server_list:
            if cont_code in server_list[key]:
                sio.emit('StopInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'], 'sid': sid}, room=key)

    elif data['cont_name'] in cont_list[1]:
        cont_code = cont_list[1][cont_name]
        for key in server_list:
            if cont_code in server_list[key]:
                sio.emit('StopInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'], 'sid': sid}, room=key)

    else:
        pass


@sio.on('InstanceStopped')
def stopped(sid, data):
    sio.emit('InstanceStopped', data['cont_name'], room=data['sid'])


@sio.on('DeleteInstance')
def cont_delete(sid, data):
    cont_list = users.find_one({'uid': data['uid']})['cont_list']
    cont_name = data['cont_name']

    if data['cont_name'] in cont_list[0]:
        cont_code = cont_list[0][cont_name]
        cont_list.pop(0)
        cont_list.append(False)
        users.update_one({'uid': data['uid']}, {'$set': {'cont_list': cont_list}})

        for key in server_list:
            if cont_code in server_list[key]:
                sio.emit('DeleteInstance', cont_code, room=key)
                server_list[key].remove(cont_code)

        cont_list.pop(0)
        cont_list.append(False)


    elif data['cont_name'] in cont_list[1]:
        cont_code = cont_list[1][cont_name]
        cont_list.pop(1)
        cont_list.append(False)
        users.update_one({'uid': data['uid']}, {'$set': {'cont_list': cont_list}})

        for key in server_list:
            if cont_code in server_list[key]:
                sio.emit('DeleteInstance', cont_code, room=key)
                server_list[key].remove(cont_code)

        cont_list.pop(1)
        cont_list.append(False)

    else:
        pass


@sio.on('SignUp')
def auth_event(sid, data):
    print('SignUp')
    if users.find_one({'email': data['email']}) == None:
        user = False
    else:
        user = True

    if user == True:
        sio.emit('SignUpRes', {'code': False, "error": True}, room=sid)
    elif user == False:
        auth_code = random.randint(100000, 999999)
        send_mail("[Clover Cloud Platform] Verification code", data, auth_code)
        sio.emit('SignUpRes', {'code': auth_code, "error": False}, room=sid)


@sio.on('AuthByEmail')
def add_user_event(sid, data):
    if data['resend_code'] == True:
        auth_code = random.randint(100000, 999999)
        send_mail("Test code", data, auth_code)
        sio.emit('SignUpRes', {'code': auth_code, "error": False}, room=sid)
    else:

        user = {
            'password': rsa.encrypt(bytes(data['password'], 'utf-8'), pubkey),
            'email': data['email'],
            'uid': str(uuid.uuid4()),
            'username': data['username'],
            'cont_list': [False, False]
        }
        users.insert_one(user)
        sio.emit('AuthByEmailRes', user['uid'])


@sio.on('SignIn')
def sign_in(sid, data):
    user = users.find_one({'email': data['email']})

    if user != None:

        if (rsa.decrypt(user['password'], privkey)).decode() == data['password']:
            sio.emit('SignInRes', {'error': False, 'uid': user['uid'], 'cont_list': user['cont_list']})

        else:
            sio.emit('SignInRes', {'error': "password", 'uid': False, 'cont_list': False})

    else:
        sio.emit('SignInRes', {'error': 'email', 'uid': False, 'cont_list': False})


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 8000)), app)
