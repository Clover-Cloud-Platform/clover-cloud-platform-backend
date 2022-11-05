import socketio, os
import subprocess



sio = socketio.Client()
sio.connect('your main server adress')


x_server_number = int(open('x_server_number.txt', 'r').read())


cont_list = (subprocess.run(f"lxc list --format=json | jq -r '.[] | .name", shell=True,stdout=subprocess.PIPE, text=True).stdout).split('\n')

print(x_server_number)
sio.emit('ConnectServer', cont_list)
print('ok')

@sio.on('CreateInstance')
def create(data):
    global x_server_number
    global cont_list


    cont_code = data['cont_code']


    print(subprocess.run(f"sudo lxc copy clover0 {cont_code}", shell=True,stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc config set {cont_code} limits.cpu 1", shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc config set {cont_code} limits.memory 2GB", shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc config set {cont_code} volatile.local.apply_quota 8GB", shell=True, stdout=subprocess.PIPE, text=True).stdout)

    print(subprocess.run(f"sudo lxc start {cont_code}", shell=True, stdout=subprocess.PIPE, text=True).stdout)

    os.system(f"sudo lxc exec {cont_code} -- Xvfb :{x_server_number} &")

    os.system(f"sudo lxc exec {cont_code} -- export DISPLAY=:{x_server_number}")

    os.system(f"sudo lxc exec {cont_code} -- history -c")

    print('pk')

    x_server_number+=1

    open('x_server_number.txt', 'w').write(str(x_server_number))

    cont_list.append(cont_code)

    sio.emit('InstanceCreated', {'cont_code': cont_code, 'uid': data['uid'], 'cont_name': data['cont_name'],
                                 'cont_list': data['cont_list'], 'server_cont_list': cont_list, 'create_status': True})


@sio.on('StartInstance')
def start(data):
    print(subprocess.run(f"sudo lxc start {data}", shell=True, stdout=subprocess.PIPE, text=True).stdout)


@sio.on('StopInstance')
def stop(data):
    print(subprocess.run(f"sudo lxc stop {data}", shell=True, stdout=subprocess.PIPE, text=True).stdout)


@sio.on('DeleteInstance')
def delete(data):
    global cont_list

    print(subprocess.run(f"sudo lxc delete {data} --force", shell=True, stdout=subprocess.PIPE, text=True).stdout)

    cont_list.remove(data)
