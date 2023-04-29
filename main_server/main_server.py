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
    privkey = rsa.PrivateKey.load_pkcs1(f.read())  # Open the file with the private key for decryption
with open('public.pem', 'rb') as f:
    pubkey = rsa.PublicKey.load_pkcs1(f.read())  # Open the file with the public key for encryption

sio = socketio.Server(cors_allowed_origins='*',
                      cors_allowed_headers="Origin, X-Requested-With, Content-Type, Accept",
                      ping_timeout=60)  # Create socketio server object
app = socketio.WSGIApp(sio)

client = MongoClient("your mongodb key")
users = client.test.users  # connect to mongodb

email = getpass("email") #declare variables
password = getpass("password")
subserver_list = {}
cont_server_list = {}
stream_telemetry_list = {}
terminals_list = {}
leds_list = {}


def send_mail(subject, data, auth_code):  # send mail function
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
    server = smtp.SMTP_SSL('smtp.yandex.com')  # connect to smtp yandex server
    server.ehlo(email)
    server.login(email, password)
    server.sendmail(email, data['email'], msg.as_string())
    server.quit()


@sio.on('ConnectSubServer')  # add subserver sid to dict
def new_subserver(sid, data):
    subserver_list[sid] = data


@sio.on('UpdateServerData')  # data update from subserver
def update_sever_data(sid, data):
    subserver_list[sid] = data


@sio.on('ContConnected')  # add cont sid to dict
def cont_connected(sid, data):
    cont_server_list[data] = sid

    for subserver_sid in subserver_list:
        if data in subserver_list[subserver_sid]['cont_list']:
            sio.emit('StartXServer', subserver_list[subserver_sid]['x_server_number'])  # xserver starts

            subserver_list[subserver_sid]['x_server_number'] += 1
            sio.emit('UpdateServerData', subserver_list[subserver_sid], room=subserver_sid)  # update xserver number


@sio.on('SignUp')  # sign up user function
def auth_event(sid, data):
    if users.find_one({'email': data['email']}) is None:  # check email availability
        auth_code = random.randint(100000, 999999)  # generate code
        send_mail('[Clover Cloud Platform Verification]', data, auth_code)  # use send mail funct
        sio.emit('SignUpRes', {'code': auth_code, 'error': False})  # send code to user
    else:
        sio.emit('SignUpRes', {'code': False, 'error': True})  # email is not availible


@sio.on('AuthByEmail')  # add user to db funct
def add_user_event(sid, data):
    if data['resend_code'] is True:  # If the user entered the wrong code
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
        users.insert_one(user)  # else add user to db
        sio.emit('AuthByEmailRes', user['uid'])  # registration successful


@sio.on('SignIn')  # sign in user funct
def sign_in(sid, data):
    user = users.find_one({'email': data['email']})  # find user in db

    if user is None:
        sio.emit('SignInRes', {'error': 'email', 'uid': False, 'cont_list': False})  # if the user is not in ds
    else:
        if (rsa.decrypt(user['password'], privkey)).decode() == data['password']:  # check password
            sio.emit('SignInRes', {'error': False, 'uid': user['uid'], 'cont_list': user['cont_list']})  # successful
        else:
            sio.emit('SignInRes', {'error': "password", 'uid': False, 'cont_list': False})  # if the password is wrong


@sio.on('CreateNewInstance')  # create new cont
def create_event(sid, data):
    user = users.find_one({'uid': data['uid']})  # find user in db
    cont_code = "c" + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))
    cont_list = user['cont_list']  # get user cont list from db

    if user['cont_list'] == {}:  # if the user has no conts
        for sid in subserver_list:
            if len(subserver_list[sid]['users_list']) < 8:  # finding for a free subserver
                subserver_sid = sid
                cont_list[data['cont_name']] = [cont_code, False]  # add user cont to db
                # send create socket to subserver
                sio.emit('CreateNewInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'],
                                               'cont_list': cont_list, 'uid': data['uid']}, room=subserver_sid)
                break
    else:  # if user with conts
        for sid in subserver_list:
            if data['uid'] in subserver_list[sid]['users_list']:
                subserver_sid = sid
                cont_list[data['cont_name']] = [cont_code, False]  # add user cont to db
                # send create socket to subserver
                sio.emit('CreateNewInstance', {'cont_code': cont_code, 'cont_name': data['cont_name'],
                                               'cont_list': cont_list, 'uid': data['uid']}, room=subserver_sid)
                break


@sio.on('InstanceCreated')  # cont creation confirmation
def created(sid, data):
    users.update_one({'uid': data['uid']}, {'$set': {'cont_list': data['cont_list']}})  # update user db
    subserver_list[sid] = data['server_data']
    sio.emit('InstanceCreated', {'name': data['cont_name'], 'code': data['cont_code']})  # confirm socker from client


@sio.on('GetUsername')  # getting username and running conts for client by uid
def get_username(sid, data):
    user = users.find_one({'uid': data})  # find user in db

    if user['cont_list'] != {}:  # if user conts is not none
        for subserver_sid in subserver_list:
            if data in subserver_list[subserver_sid]['users_list']:  # find user subserver
                # send get running conts socket to subserver
                sio.emit('GetRunningInstances', {'username': user['username'],
                                                 'cont_list': user['cont_list'], 'user_sid': sid}, room=subserver_sid)
    else:  # else there are no containers
        sio.emit('Username', {'username': user['username'], 'cont_list': {}})


@sio.on('RunningInstances')  # running cont list to client
def running(sid, data):
    # send list of running conts
    sio.emit('Username', {'username': data['username'], 'cont_list': data['cont_list']}, room=data['user_sid'])


@sio.on('StartInstance')  # start cont socket
def cont_start(sid, data):
    user = users.find_one({'uid': data['uid']})  # find user in db
    cont_name = data['cont_name']

    for subserver_sid in subserver_list:
        if data['uid'] in subserver_list[subserver_sid]['users_list']:  # find user subserver
            # send start cont socket to subserver
            sio.emit('StartInstance', {'cont_code': user['cont_list'][cont_name][0],
                                       'cont_name': cont_name, 'user_sid': sid}, room=subserver_sid)
            break


@sio.on('InstanceStarted')  # cont started confirm to client
def cont_started(sid, data):
    sio.emit('InstanceStarted', data['cont_name'], room=data['user_sid'])  # send confirmation


@sio.on('StopInstance')  # stop cont socket
def cont_start(sid, data):
    user = users.find_one({'uid': data['uid']})  # find user in db
    cont_name = data['cont_name']

    for subserver_sid in subserver_list:
        if data['uid'] in subserver_list[subserver_sid]['users_list']:  # find user subserver
            # send stop cont to subserver
            sio.emit('StopInstance', {'cont_code': user['cont_list'][cont_name][0],
                                      'cont_name': cont_name, 'user_sid': sid}, room=subserver_sid)
            break


@sio.on('InstanceStopped')  # cont stopped confirmation
def cont_stopped(sid, data):
    sio.emit('InstanceStopped', data['cont_name'], room=data['user_sid'])  # send confirmation
    cont_server_list.pop(data['cont_code'])  # delete cont code from cont dict


@sio.on('DeleteInstance')  # delete cont socket
def cont_delete(sid, data):
    cont_list = users.find_one({'uid': data['uid']})['cont_list']  # find user in db
    cont_code = cont_list[data['cont_name']]

    cont_list.pop(data['cont_name'])  # delete cont code from db
    users.update_one({'uid': data['uid']}, {'$set': {'cont_list': cont_list}})  # update user db

    for subserver_sid in subserver_list:
        if data['uid'] in subserver_list[subserver_sid]['users_list']:  # find user subserver
            # send delete cont socket to subserver
            sio.emit('DeleteInstance', {'cont_code': cont_code, 'uid': data['uid'],
                                        'cont_list': cont_list}, room=subserver_sid)


@sio.on('GetInstanceData')  # get cont data for client
def get_cont_data(sid, data):
    user = users.find_one({'uid': data['uid']})

    for cont_name in user['cont_list']:
        if user['cont_list'][cont_name][0] == data['instance_id']:
            # send data to client
            sio.emit("InstanceData", {'username': user['username'], 'instance_name': cont_name})
            break


@sio.on('RunGazebo')  # run gazebo socket
def run_gazebo(sid, data):
    sio.emit('RunGazebo', room=terminals_list[data])  # start gazebo
    sio.emit('GetGazeboModels', sid, room=cont_server_list[data])  # get models from cont
    sio.emit('StartStreamTelemetry', sid, room=terminals_list[data])  # start stream telemetry from cont


@sio.on('GetGazeboModels')
def get_gazebo_models(sid, data):
    sio.emit('GetGazeboModels', sid, room=cont_server_list[data])  # get models from cont


@sio.on('GazeboModels')
def gazebo_models(sid, data):
    # send models to client
    sio.emit('GazeboModels', {'aruco_map': data['aruco_map'], 'user_objects': data['user_objects']},
             room=data['user_sid'])


@sio.on('GetGazeboState')
def gazebo_state(sid, data):
    # get gazebo state for client
    sio.emit('GetGazeboState', {'cont_code': data, 'user_sid': sid}, room=cont_server_list[data])


@sio.on('GazeboStateRes')
def gazebo_stat_res(sid, data):
    # send gazebo state to client
    sio.emit('GazeboStateRes', data['gazebo_state'], room=data['user_sid'])


@sio.on('TerminalConnected')
def terminal_connected(sid, data):
    terminals_list[data] = sid  # add terminal file sid to dict


@sio.on('CloverTelemetry')
def clover_telemetry(sid, data):
    if not math.isnan(data['position'][0]):  # check clover position
        user_sid = data.pop('sid')  # get user sid and delete from data dict
        sio.emit('CloverPosition', data, room=user_sid)  # send clover pose to client


@sio.on('LedState')
def led_state(sid, data):
    sio.emit('LedState', data['leds'], room=data['sid'])  # sed led state to client


@sio.on('ExecuteCommand')  # execute command in terminal socket
def execute_command(sid, data):
    for cont_code in terminals_list:
        if cont_code == data['instanceID']:  # find terminal sid in dict
            # send command to the terminal
            sio.emit('ExecuteCommand', {'command': data['command'], 'user_sid': sid},
                     room=terminals_list[cont_code])


@sio.on('CommandOutput')
def command_output(sid, data):
    # send output from terminal to user
    sio.emit('CommandOutput', {'output': data['output'], 'id': data['id']}, room=data['user_sid'])


"""
# debug info socket
@sio.on('DebugOutput')
def debug_output(sid, data):
    print('DEBUG_INFO: ' + str(data))
"""


@sio.on('GetFiles')  # get files from cont socket
def get_files(sid, data):
    sio.emit('GetFiles', sid, room=cont_server_list[data])


@sio.on('Files')  # send files to client socket
def files(sid, data):
    sio.emit('Files', data['files'], room=data['user_sid'])


@sio.on('MoveItem')  # move file in cont socket
def move_item(sid, data):
    sio.emit('MoveItem', {'source': data['source'], 'target': data['target']},
             room=cont_server_list[data['instanceID']])


@sio.on('EditName')  # edit file name in cont
def edit_file_name(sid, data):
    sio.emit('EditName', {'path': data['path'], 'newName': data['newName']}, room=cont_server_list[data['instanceID']])


@sio.on('CreateNewFile')  # create new file in cont
def create_new_file(sid, data):
    sio.emit('CreateNewFile', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('DeleteFile')  # delete file in cint
def delete_file(sid, data):
    sio.emit('DeleteFile', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('CreateNewDirectory')  # create new folder in cont
def create_new_directory(sid, data):
    sio.emit('CreateNewDirectory', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('DeleteDirectory')  # delete folder in cont
def delete_file(sid, data):
    sio.emit('DeleteDirectory', data['path'], room=cont_server_list[data['instanceID']])


@sio.on('GetFileContent')  # get file content
def get_file_content(sid, data):
    sio.emit('GetFileContent', {'path': data['path'], 'user_sid': sid}, room=cont_server_list[data['instanceID']])


@sio.on('FileContent')  # send file content to client
def file_content(sid, data):
    sio.emit('FileContent', {'path': data['path'], 'content': data['content']}, room=data['user_sid'])


@sio.on('WriteFile')  # write file content
def write_file(sid, data):
    sio.emit('WriteFile', {'path': data['path'], 'value': data['value']}, room=cont_server_list[data['instanceID']])


@sio.on('StopGazebo')  # stop gazebo
def stop_gazebo(sid, data):
    sio.emit('StopGazebo', sid, room=cont_server_list[data])


@sio.on('GazeboStopped')  # gazebo stop confirmation
def gazebo_stopped(sid, data):
    sio.emit('GazeboStopped', '1', room=data)


@sio.on('AddCube')  # add cube to gazbeo map
def add_cube(sid, data):
    sio.emit('AddCube', '1', room=cont_server_list[data])


@sio.on('EditCube')  # edit cube
def edit_cube(sid, data):
    instance_id = data.pop('instanceID')
    sio.emit('EditCube', data, cont_server_list[instance_id])


@sio.on('EditMarker')  # edit aruco marker
def edit_marker(sid, data):
    print(data)
    instance_id = data.pop('instanceID')
    sio.emit('EditMarker', data, cont_server_list[instance_id])


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 8000)), app)  # start server on 8000 port
