import json
from pylxd import Client
import socketio
import random
import string

sio = socketio.Client()
sio.connect('main_server_address')
client = Client()

with open("db.json", "r") as read_file:
    server_data = json.load(read_file)

for cont_name in client.containers.all():
    server_data['cont_list'].append(cont_name.name)

sio.emit('ConnectSubServer', server_data)


@sio.on('UpdateServerData')
def update_server_data(data):
    server_data = data

    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)


@sio.on('CreateNewInstance')
def create_instance(data):
    cont_code = data['cont_code']
    global server_data

    client.instances.create({'name': cont_code, 'source': {'type': 'copy', 'source': 'clover0'}})

    if data['uid'] not in server_data['users_list']:
        server_data['users_list'].append(data['uid'])

    server_data['cont_list'].append(cont_code)
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    sio.emit('InstanceCreated', {'cont_code': cont_code, 'uid': data['uid'], 'cont_name': data['cont_name'],
                                 'cont_list': data['cont_list'], 'server_data': server_data})


@sio.on('Instances')
def running(data):
    cont_list = data['cont_list']
    print(cont_list)
    for cont in cont_list:
        print(cont)
        print(client.instances.get(cont_list[cont][0]).status)
        if client.instances.get(cont_list[cont][0]).status == 'Running':
            cont_list[cont][1] = True
        else:
            pass
    sio.emit('RunningInstances', {'cont_list': cont_list,
                                  'user_sid': data['user_sid']})


@sio.on('StartInstance')
def start(data):
    client.instances.get(data['cont_code']).start()
    sio.emit('InstanceStarted', {'user_sid': data['user_sid'], 'cont_name': data['cont_name']})


@sio.on('StopInstance')
def start(data):
    client.instances.get(data['cont_code']).stop(wait=True)
    sio.emit('InstanceStopped', {'user_sid': data['user_sid'], 'cont_name': data['cont_name'],
                                 'cont_code': data['cont_code']})


@sio.on('DeleteInstance')
def delete(data):
    global server_data

    client.instances.get(data['cont_code'][0]).delete()
    server_data['cont_list'].remove(data['cont_code'][0])

    sio.emit('UpdateServerData', server_data)

    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    if data['cont_list'] == {}:
        server_data['users_list'].remove(data['uid'])

        sio.emit('UpdateServerData', server_data)

        with open("db.json", "w") as write_file:
            json.dump(server_data, write_file)


@sio.on('CreateNewTemplate')
def create_new_template(data):

    cont_code = "c" + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))

    client.instances.create({'name': cont_code, 'source': {'type': 'copy', 'source': data['instanceID']}})
    data['instanceID'] = cont_code
    data['server_data'] = server_data

    server_data['cont_list'].append(cont_code)

    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    sio.emit('TemplateCreated', data)


@sio.on('InstallTemplate')
def install_template(data):
    global server_data

    client.instances.get(data['oldID']).stop(wait=True)
    client.instances.get(data['oldID']).delete(wait=True)

    client.instances.create({'name': data['oldID'], 'source': {'type': 'copy', 'source': data['newID']}}, wait=True)

    server_data['cont_list'].append(data['oldID'])
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    client.instances.get(data['oldID']).start(wait=True)

    sio.emit('TemplateInstalled', {'server_data': server_data, 'user_sid': data['sid']})


@sio.on('DeleteTemplate')
def delete_template(data):
    global server_data

    client.instances.get(data).delete()
    server_data['cont_list'].remove(data)

    sio.emit('UpdateServerData', server_data)

    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)


@sio.on('RevertToInitial')
def revert_to_initial(data):
    client.instances.get(data).stop(wait=True)
    client.instances.get(data).delete(wait=True)

    client.instances.create({'name': data, 'source': {'type': 'copy', 'source': 'clover0'}}, wait=True)
