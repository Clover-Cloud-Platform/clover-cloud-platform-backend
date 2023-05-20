#import libraries
import json
from pylxd import Client
import socketio
import random
import string

# Create socketio client and connect to the server
sio = socketio.Client()
sio.connect('http://10.143.7.57:8000')

# Create pylxd client object
client = Client()

# Read server data from the "db.json" file
with open("db.json", "r") as read_file:
    server_data = json.load(read_file)

# Update server data with container names that are not already in the list
for cont_name in client.containers.all():
    if cont_name.name not in server_data['cont_list']:
        server_data['cont_list'].append(cont_name.name)

# Send the server data to the main server
sio.emit('ConnectSubServer', server_data)


# Update server data when received from the main server
@sio.on('UpdateServerData')
def update_server_data(data):
    server_data = data

    # Write the updated server data to the "db.json" file
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)


# Create a new instance when requested
@sio.on('CreateNewInstance')
def create_instance(data):
    cont_code = data['cont_code']
    global server_data

    # Create a new LXD instance with the given name and source
    client.instances.create({'name': cont_code, 'source': {'type': 'copy', 'source': 'clover0'}})

    # Add the user ID to the server data if it doesn't exist
    if data['uid'] not in server_data['users_list']:
        server_data['users_list'].append(data['uid'])

    # Add the new container code to the server data
    server_data['cont_list'].append(cont_code)

    # Update the "db.json" file with the updated server data
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    # Emit an event to notify the main server about the new instance
    sio.emit('InstanceCreated', {'cont_code': cont_code, 'uid': data['uid'], 'cont_name': data['cont_name'],
                                 'cont_list': data['cont_list'], 'server_data': server_data})


# Check the status of instances and send the information back to the main server
@sio.on('Instances')
def running(data):
    print('Instances')
    cont_list = data['cont_list']
    for cont in cont_list:
        # Check the status of each instance and update the status in the container list
        print(client.instances.get(cont_list[cont][0]).status)
        if client.instances.get(cont_list[cont][0]).status == 'Running':
            cont_list[cont][1] = True
        else:
            pass
    # Emit an event to send the updated container list and user session ID back to the main server
    sio.emit('RunningInstances', {'cont_list': cont_list, 'user_sid': data['user_sid']})


# Start an instance when requested
@sio.on('StartInstance')
def start(data):
    # Start the specified instance
    client.instances.get(data['cont_code']).start()
    # Emit an event to notify the main server about the instance start
    sio.emit('InstanceStarted', {'user_sid': data['user_sid'], 'cont_name': data['cont_name']})


# Stop an instance when requested
@sio.on('StopInstance')
def stop(data):
    # Stop the specified instance
    client.instances.get(data['cont_code']).stop(wait=True)
    # Emit an event to notify the main server about the instance stop
    sio.emit('InstanceStopped', {'user_sid': data['user_sid'], 'cont_name': data['cont_name'], 'cont_code': data['cont_code']})


# Delete an instance when requested
@sio.on('DeleteInstance')
def delete(data):
    global server_data

    # Delete the specified instance
    client.instances.get(data['cont_code'][0]).delete()

    # Remove the container code from the server data
    server_data['cont_list'].remove(data['cont_code'][0])

    # Update the server data on the main server
    sio.emit('UpdateServerData', server_data)

    # Update the "db.json" file with the updated server data
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    # If the container list is empty, remove the user ID from the server data
    if data['cont_list'] == {}:
        server_data['users_list'].remove(data['uid'])

        # Update the server data on the main server
        sio.emit('UpdateServerData', server_data)

        # Update the "db.json" file with the updated server data
        with open("db.json", "w") as write_file:
            json.dump(server_data, write_file)


# Create a new template instance when requested
@sio.on('CreateNewTemplate')
def create_new_template(data):
    cont_code = "c" + ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(6))

    # Create a new LXD instance based on the specified instance as the source
    client.instances.create({'name': cont_code, 'source': {'type': 'copy', 'source': data['instanceID']}})

    # Update the data with the new instance ID and server data
    data['instanceID'] = cont_code
    data['server_data'] = server_data

    # Add the new container code to the server data
    server_data['cont_list'].append(cont_code)

    # Update the "db.json" file with the updated server data
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)

    # Emit an event to notify the main server about the new template creation
    sio.emit('TemplateCreated', data)


# Install a template when requested
@sio.on('InstallTemplate')
def install_template(data):
    global server_data

    # Stop and delete the old instance
    client.instances.get(data['oldID']).stop(wait=True)
    client.instances.get(data['oldID']).delete(wait=True)

    # Create a new instance based on the new template
    client.instances.create({'name': data['oldID'], 'source': {'type': 'copy', 'source': data['newID']}}, wait=True)

    # Start the new instance
    client.instances.get(data['oldID']).start(wait=True)

    # Emit an event to notify the main server about the template installation
    sio.emit('TemplateInstalled', data['sid'])


# Delete a template when requested
@sio.on('DeleteTemplate')
def delete_template(data):
    global server_data

    # Delete the specified template instance
    client.instances.get(data).delete()

    # Remove the container code from the server data
    server_data['cont_list'].remove(data)

    # Update the server data on the main server
    sio.emit('UpdateServerData', server_data)

    # Update the "db.json" file with the updated server data
    with open("db.json", "w") as write_file:
        json.dump(server_data, write_file)


# Revert to the initial template when requested
@sio.on('RevertToInitial')
def revert_to_initial(data):
    # Stop and delete the current instance
    client.instances.get(data['instanceID']).stop(wait=True)
    client.instances.get(data['instanceID']).delete(wait=True)

    # Create a new instance based on the initial template
    client.instances.create({'name': data['instanceID'], 'source': {'type': 'copy', 'source': 'clover0'}}, wait=True)

    # Start the new instance
    client.instances.get(data['instanceID']).start(wait=True)

    # Emit an event to notify the main server about the template installation
    sio.emit('TemplateInstalled', data['sid'])
