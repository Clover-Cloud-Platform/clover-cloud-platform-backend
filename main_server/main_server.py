#   import standard python libs
import math
import uuid
import string
import random
import smtplib as smtp
#   import libs
import rsa
import socketio
import eventlet
from getpass4 import getpass
from pymongo import MongoClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

with open('private.pem', 'rb') as f:
    privkey = rsa.PrivateKey.load_pkcs1(f.read())
with open('public.pem', 'rb') as f:
    pubkey = rsa.PublicKey.load_pkcs1(f.read())

sio = socketio.Server(cors_allowed_origins='*',
                      cors_allowed_headers="Origin, X-Requested-With, Content-Type, Accept",
                      ping_timeout=60)
app = socketio.WSGIApp(sio)
subserver_list = {}
cont_server_list = {}
stream_telemetry_list = {}
terminals_list = {}
leds_list = {}
email = getpass('Email')
password = getpass('Password')
client = MongoClient("your mongodb key")
users = client.test.users


def send_mail(subject, data, auth_code):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = email
    msg['To'] = data['email']
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
    msg.attach(MIMEText(html, 'html'))
    server = smtp.SMTP_SSL('smtp.yandex.com')
    server.ehlo(email)
    server.login(email, password)
    server.sendmail(email, data['email'], msg.as_string())
    server.quit()


@sio.on('ConnectSubServer')
def new_subserver(sid, data):
    subserver_list[sid] = data


@sio.on('UpdateServerData')
def update_sever_data(sid, data):
    subserver_list[sid] = data


@sio.on('ContConnected')
def cont_connected(sid, data):
    cont_server_list[data] = sid

    for subserver_sid in subserver_list:
        if data in subserver_list[subserver_sid]['cont_list']:
            sio.emit('StartXServer', subserver_list[subserver_sid]['x_server_number'])

            subserver_list[subserver_sid]['x_server_number'] += 1
            sio.emit('UpdateServerData', subserver_list[subserver_sid], room=subserver_sid)


@sio.on('SignUp')
def auth_event(sid, data):
    if users.find_one({'email': data['email']}) is None:
        auth_code = random.randint(100000, 999999)
        send_mail('[Clover Cloud Platform Verification]', data, auth_code)
        sio.emit('SignUpRes', {'code': auth_code, 'error': False})
    else:
        sio.emit('SignUpRes', {'code': False, 'error': True})


@sio.on('AuthByEmail')
def add_user_event(sid, data):
    if data['resend_code'] is True:
        auth_code = random.randint(100000, 999999)
        send_mail('[Clover Cloud Platform Verification]', data, auth_code)
    else:
        user = {
            'email': data['email'],
            'uid': str(uuid.uuid4()),
            'username': data['username'],
            'password': rsa.encrypt(bytes(data['password'], 'utf-8'), pubkey),
            'cont_list': {}
        }
        users.insert_one(user)
        sio.emit('AuthByEmailRes', user['uid'])


@sio.on('SignIn')
def sign_in(sid, data):
    user = users.find_one({'email': data['email']})

    if user is None:
        sio.emit('SignInRes', {'error': 'email', 'uid': False, 'cont_list': False})
    else:
        if (rsa.decrypt(user['password'], privkey)).decode() == data['password']:
            sio.emit('SignInRes', {'error': False, 'uid': user['uid'], 'cont_list': user['cont_list']})
        else:
            sio.emit('SignInRes', {'error': "password", 'uid': False, 'cont_list': False})


@sio.on('CreateNewInstance')
def create_event(sid, data):
    user = users.find_one({'uid': data['uid']})
    cont_code = "c" + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))
    cont_list = user['cont_list']

    if user['cont_list'] == {}:
        for sid in subserver_list:
            if len(subserver_list[sid]['users_list']) < 8:
                subserver_sid = sid
                cont_list[data['cont_name']] = [cont_code, False]
                sio.emit('CreateNewInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'],
                                               'cont_list': cont_list, 'uid': data['uid']}, room=subserver_sid)
                break
    else:
        for sid in subserver_list:
            if data['uid'] in subserver_list[sid]['users_list']:
                subserver_sid = sid
                cont_list[data['cont_name']] = [cont_code, False]
                sio.emit('CreateNewInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'],
                                               'cont_list': cont_list, 'uid': data['uid']}, room=subserver_sid)
                break


@sio.on('InstanceCreated')
def created(sid, data):
    users.update_one({'uid': data['uid']}, {'$set': {'cont_list': data['cont_list']}})
    subserver_list[sid] = data['server_data']
    sio.emit('InstanceCreated', {'name': data['cont_name'], 'code': data['cont_code']})


@sio.on('GetUsername')
def get_username(sid, data):
    user = users.find_one({'uid': data})

    if user['cont_list'] != {}:
        for subserver_sid in subserver_list:
            if data in subserver_list[subserver_sid]['users_list']:
                sio.emit('GetRunningInstances', {'username': user['username'],
                                                 'cont_list': user['cont_list'], 'user_sid': sid}, room=subserver_sid)
    else:
        sio.emit('Username', {'username': user['username'], 'cont_list': {}})


@sio.on('RunningInstances')
def running(sid, data):
    print(data)
    sio.emit('Username', {'username': data['username'], 'cont_list': data['cont_list']}, room=data['user_sid'])


@sio.on('StartInstance')
def cont_start(sid, data):
    user = users.find_one({'uid': data['uid']})
    cont_name = data['cont_name']

    for subserver_sid in subserver_list:
        if data['uid'] in subserver_list[subserver_sid]['users_list']:
            sio.emit('StartInstance', {'cont_code': user['cont_list'][cont_name][0],
                                       'cont_name': cont_name, 'user_sid': sid}, room=subserver_sid)
            break


@sio.on('InstanceStarted')
def cont_started(sid, data):
    sio.emit('InstanceStarted', data['cont_name'], room=data['user_sid'])


@sio.on('StopInstance')
def cont_start(sid, data):
    user = users.find_one({'uid': data['uid']})
    cont_name = data['cont_name']

    for subserver_sid in subserver_list:
        if data['uid'] in subserver_list[subserver_sid]['users_list']:
            sio.emit('StopInstance', {'cont_code': user['cont_list'][cont_name][0],
                                      'cont_name': cont_name, 'user_sid': sid}, room=subserver_sid)
            break


@sio.on('InstanceStopped')
def cont_stopped(sid, data):
    sio.emit('InstanceStopped', data['cont_name'], room=data['user_sid'])
    cont_server_list.pop(data['cont_code'])


@sio.on('DeleteInstance')
def cont_delete(sid, data):
    cont_list = users.find_one({'uid': data['uid']})['cont_list']
    cont_code = cont_list[data['cont_name']]

    cont_list.pop(data['cont_name'])
    users.update_one({'uid': data['uid']}, {'$set': {'cont_list': cont_list}})

    for subserver_sid in subserver_list:
        if data['uid'] in subserver_list[subserver_sid]['users_list']:
            sio.emit('DeleteInstance', {'cont_code': cont_code, 'uid': data['uid'],
                                        'cont_list': cont_list}, room=subserver_sid)


@sio.on('GetInstanceData')
def get_cont_data(sid, data):
    user = users.find_one({'uid': data['uid']})

    for cont_name in user['cont_list']:
        if user['cont_list'][cont_name][0] == data['instance_id']:
            sio.emit("InstanceData", {'username': user['username'], 'instance_name': cont_name})
            break


@sio.on('RunGazebo')
def run_gazebo(sid, data):
    print('RunGazebo', sid)
    sio.emit('RunGazebo', room=terminals_list[data])
    sio.emit('GetGazeboModels', sid, room=cont_server_list[data])
    sio.emit('StartStreamTelemetry', sid, room=terminals_list[data])


@sio.on('GetGazeboModels')
def get_gazebo_models(sid, data):
    sio.emit('GetGazeboModels', sid, room=cont_server_list[data])


@sio.on('GazeboModels')
def gazebo_models(sid, data):
    sio.emit('GazeboModels', {'aruco_map': data['aruco_map'], 'user_objects': data['user_objects']},
             room=data['user_sid'])


@sio.on('GetGazeboState')
def gazebo_state(sid, data):
    print('GetGazeboState')
    sio.emit('GetGazeboState', {'cont_code': data, 'user_sid': sid}, room=cont_server_list[data])


@sio.on('GazeboStateRes')
def gazebo_stat_res(sid, data):
    sio.emit('GazeboStateRes', data['gazebo_state'], room=data['user_sid'])


@sio.on('TerminalConnected')
def terminal_connected(sid, data):
    terminals_list[data] = sid


@sio.on('CloverTelemetry')
def clover_telemetry(sid, data):
    if not math.isnan(data['position'][0]):
        print(data)
        user_sid = data.pop('sid')
        sio.emit('CloverPosition', data, room=user_sid)


@sio.on('LedState')
def led_state(sid, data):
    if not math.isnan(data['leds'][0]):
        print(data)
        sio.emit('LedState', data['leds'], room=data['sid'])


@sio.on('ExecuteCommand')
def execute_command(sid, data):
    print('Command', sid)
    for cont_code in terminals_list:
        print(terminals_list)
        if cont_code == data['instanceID']:
            sio.emit('ExecuteCommand', {'command': data['command'], 'user_sid': sid},
                     room=terminals_list[cont_code])


@sio.on('CommandOutput')
def command_output(sid, data):
    print(data)
    sio.emit('CommandOutput', {'output': data['output'], 'id': data['id']}, room=data['user_sid'])


@sio.on('DebugOutput')
def debug_output(sid, data):
    print('DEBUG_INFO: ' + str(data))


@sio.on('GetFiles')
def get_files(sid, data):
    sio.emit('GetFiles', sid, room=cont_server_list[data])


@sio.on('Files')
def files(sid, data):
    sio.emit('Files', data['files'], room=data['user_sid'])


@sio.on('MoveItem')
def move_item(sid, data):
    sio.emit('MoveItem', {'source': data['source'], 'target': data['target']}, room=cont_server_list[data['instanceID']])


@sio.on('EditName')
def edit_file_name(sid, data):
    sio.emit('EditName', {'path': data['path'], 'newName': data['newName']}, room=cont_server_list[data['instanceID']])


@sio.on('CreateNewFile')
def create_new_file(sid, data):
    sio.emit('CreateNewFile', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('DeleteFile')
def delete_file(sid, data):
    sio.emit('DeleteFile', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('CreateNewDirectory')
def create_new_directory(sid, data):
    sio.emit('CreateNewDirectory', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('DeleteDirectory')
def delete_file(sid, data):
    sio.emit('DeleteDirectory', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('GetFileContent')
def get_file_content(sid, data):
    sio.emit('GetFileContent', {'path': data['path'], 'user_sid': sid}, room=cont_server_list[data['instanceID']])


@sio.on('FileContent')
def file_content(sid, data):
    sio.emit('FileContent', {'path': data['path'], 'content': data['content']}, room=data['user_sid'])


@sio.on('WriteFile')
def write_file(sid, data):
    sio.emit('WriteFile', {'path': data['path'], 'value': data['value']}, room=cont_server_list[data['instanceID']])


@sio.on('StopGazebo')
def stop_gazebo(sid, data):
    sio.emit('StopGazebo', sid, room=cont_server_list[data])


@sio.on('GazeboStopped')
def gazebo_stopped(sid, data):
    sio.emit('GazeboStopped', '1', room=data)


@sio.on('AddCube')
def add_cube(sid, data):
    sio.emit('AddCube', '1', room=cont_server_list[data])


@sio.on('EditCube')
def edit_cube(sid, data):
    instance_id = data.pop('instanceID')
    sio.emit('EditCube', data, cont_server_list[instance_id])


@sio.on('EditMarker')
def edit_marker(sid, data):
    print(data)
    instance_id = data.pop('instanceID')
    sio.emit('EditMarker', data, cont_server_list[instance_id])


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 8000)), app)
