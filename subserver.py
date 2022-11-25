import subprocess
import json
import os

import socketio

sio = socketio.Client()
sio.connect('https://f9d5-94-29-126-249.eu.ngrok.io')

with open("db.json", "r") as read_file:
    server_data = json.load(read_file)

server_data['cont_list'] = (subprocess.run(f"lxc list --format=json | jq -r '.[] | .name'",
                            shell=True, stdout=subprocess.PIPE, text=True).stdout).split('\n')

sio.emit('ConnectSubServer', {'cont_list': server_data['cont_list'], 'users_list': server_data['users_list']})


@sio.on('CreateNewInstance')
def create_instance(data):
    cont_code = data['cont_code']
    global server_data

    print(subprocess.run(f"sudo lxc copy clover0 {cont_code}",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc config set {cont_code} limits.cpu 1",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc config set {cont_code} limits.memory 2GB",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc config set {cont_code} volatile.local.apply_quota 8GB",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc start {cont_code}",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)

    os.system(f"sudo lxc exec {cont_code} -- Xvfb :{server_data['x_server_number']} &")

    os.system(f"sudo lxc exec {cont_code} -- export DISPLAY=:{server_data['x_server_number']} &")

    if data['uid'] not in server_data['users_list']:
        server_data['users_list'].append(data['uid'])

    server_data['x_server_number'] += 1
    server_data['cont_list'].append(cont_code)
    with open("db.json", "w") as write_file:
        print('OKKKKKKKKKKKKKKKKKKKKKKKKKK')
        json.dump(server_data, write_file)

    sio.emit('InstanceCreated', {'cont_code': cont_code, 'uid': data['uid'], 'cont_name': data['cont_name'],
                                 'cont_list': data['cont_list'], 'server_data': server_data})


@sio.on('GetRunningInstances')
def running(data):
    running_user_conts = []
    running_conts = str(
        subprocess.run("lxc list --format=json | jq -r '.[] | select(.state.status == \"Running\") | .name + \",\"'",
                       shell=True, stdout=subprocess.PIPE, text=True).stdout)

    for cont_name in data['cont_list']:
        if data['cont_list'][cont_name] in running_conts:
            running_user_conts.append(True)
        else:
            running_user_conts.append(False)

    sio.emit('RunningInstances', {'username': data['username'], 'cont_list': data['cont_list'],
                                  'running': running_user_conts, 'user_sid': data['user_sid']})
    print('send_running')


@sio.on('StartInstance')
def start(data):
    print(subprocess.run(f"sudo lxc start {data['cont_code']}",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)
    sio.emit('InstanceStarted', {'user_sid': data['user_sid'], 'cont_name': data['cont_name']})


@sio.on('StopInstance')
def start(data):
    print(subprocess.run(f"sudo lxc stop {data['cont_code']}",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)
    sio.emit('InstanceStopped', {'user_sid': data['user_sid'], 'cont_name': data['cont_name']})


@sio.on('DeleteInstance')
def delete(data):
    global server_data

    print(subprocess.run(f"sudo lxc delete {data['cont_code']} --force",
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)

    server_data['cont_list'].remove(data['cont_code'])
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    if data['cont_list'] == {}:
        server_data['users_list'].remove(data['uid'])
        with open("db.json", "w") as write_file:
            json.dump(server_data, write_file)
