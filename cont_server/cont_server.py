import re
import os
import base64
import json
import shutil
from pngtosvg import *
import subprocess
import xml.etree.ElementTree as ET
import socketio

sio = socketio.Client()
sio.connect('your local adress')

cont_code = subprocess.run("hostname", shell=True, stdout=subprocess.PIPE, text=True).stdout.replace("\n", '')
sio.emit('ContConnected', cont_code)

with open("/home/ubuntu/CloverCloudPlatform/user_objects.json", "r") as read_file:
    user_objects = json.load(read_file)


@sio.on('GetGazeboState')
def get_gazebo_state(data):
    sio.emit("DebugOutput", data)
    gazebo_state = subprocess.run('ps -A | grep roslaunch', shell=True, stdout=subprocess.PIPE, text=True).stdout
    if gazebo_state != '':
        sio.emit("GazeboStateRes", {'gazebo_state': True, 'user_sid': data['user_sid'], 'cont_code': data['cont_code']})
    else:
        sio.emit("GazeboStateRes",
                 {'gazebo_state': False, 'user_sid': data['user_sid'], 'cont_code': data['cont_code']})


@sio.on('StopGazebo')
def stop_gazebo(data):
    print('Stop')
    sio.emit('DebugOutput', subprocess.run("pkill -f 'roslaunch clover_simulation simulator.launch'", shell=True, stderr=subprocess.PIPE, text=True).stderr)
    sio.emit('DebugOutput', subprocess.run("pkill -f '/usr/bin/python3.8 /home/ubuntu/PngToSvg/stream_telemetry.py'", shell=True, stderr=subprocess.PIPE, text=True).stderr)
    sio.emit('DebugOutput', subprocess.run("pkill -f '/usr/bin/python3.8 /home/ubuntu/PngToSvg/stream_led.py'", shell=True, stderr=subprocess.PIPE, text=True).stderr)
    sio.emit('GazeboStopped', data)


@sio.on('GetFiles')
def get_files(data):
    def get_directory_structure(rootdir):
        dir = {
            'type': 'folder',
            'name': os.path.basename(rootdir),
            'path': rootdir.replace('/home/ubuntu', ''),
            'children': [],
        }
        items = os.listdir(rootdir)
        for item in items:
            item_path = os.path.join(rootdir, item)
            if os.path.isdir(item_path):
                dir['children'].append(get_directory_structure(item_path))
            else:
                dir['children'].append({
                    'type': 'file',
                    'name': item,
                    'path': item_path.replace('/home/ubuntu', ''),
                })
        return dir

    result = [get_directory_structure(rootdir='/home/ubuntu/FILES')]
    sio.emit('Files', {'user_sid': data, 'files': result})


@sio.on('MoveItem')
def move_item(data):
    shutil.move('/home/ubuntu/' + data['source'], '/home/ubuntu/' + data['target'])


@sio.on('EditName')
def edit_file_name(data):
    old_file_name = os.path.basename('/home/ubuntu/' + data['path'])
    new_file_path = '/home/ubuntu/' + data['path'].replace(old_file_name, data['newName'])
    os.rename('/home/ubuntu/' + data['path'], new_file_path)


@sio.on('CreateNewFile')
def create_new_file(data):
    open('/home/ubuntu/' + data, 'w+')


@sio.on('CreateNewDirectory')
def create_new_directory(data):
    os.mkdir('/home/ubuntu/' + data)


@sio.on('DeleteFile')
def delete_file(data):
    os.remove('/home/ubuntu/' + data)


@sio.on('DeleteDirectory')
def delete_file(data):
    shutil.rmtree('/home/ubuntu/' + str(data))


@sio.on('GetFileContent')
def get_file_content(data):
    file = open("/home/ubuntu/" + data['path'], 'r')
    file_content = file.read()
    sio.emit('FileContent', {'content': file_content, 'path': data['path'], 'user_sid': data['user_sid']})


@sio.on('WriteFile')
def write_file(data):
    file = open("/home/ubuntu/" + data['path'], 'w')
    file.write(data['value'])
    file.close()


@sio.on('EditMarker')
def edit_marker(data):
    print('Marker', data)
    aruco_id = re.findall(r'\d+', data["aruco_name"])[1]

    if data['image'] is not None:
        print(data['aruco_name'].replace("aruco_marker_", ""))
        with open(fr'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/'
                  fr'{data["aruco_name"].replace("aruco_marker_", "")}.png', 'wb') as img:
            image_encode = bytes(data['image'], 'UTF-8')
            img.write(base64.decodebytes(image_encode))
        user_objects["pictures"].append(data["aruco_name"])

    if data['size'] is not None:
        with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
            lines = map_txt.readlines()
            line = lines[int(aruco_id)].split('\t')
            line[1] = str(data['size'])
            lines[int(aruco_id)] = '\t'.join(line)

        with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
            map_txt.writelines(lines)
            map_txt.close()

    if data['position'] is not None:
        with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
            lines = map_txt.readlines()
            line = lines[int(aruco_id)].split('\t')
            line[2], line[3] = str(data['position'][0]), str(data['position'][1])
            lines[int(aruco_id)] = '\t'.join(line)

        with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
            map_txt.writelines(lines)
            map_txt.close()

    if data['marker_id'] is not None:

        with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
            lines = map_txt.readlines()
            line = lines[int(aruco_id)].split('\t')
            line[0] = str(data['marker_id'])
            lines[int(aruco_id)] = '\t'.join(line)

        with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
            map_txt.writelines(lines)
            map_txt.close()

        os.rename(fr'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/{data["aruco_name"]}.png',

                  fr'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/'
                  fr'{data["aruco_name"].replace(aruco_id, data["marker_id"])}.png')

        if data["aruco_name"] in user_objects['pictures']:
            user_objects['pictures'].remove(data["aruco_name"])
            os.remove(fr'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/'
                      fr'{data["aruco_name"].replace("aruco_marker_", "")}.png')

    subprocess.run(""
                   "/bin/bash -c 'source /home/ubuntu/catkin_ws/devel/setup.bash; "
                   "rosrun clover_simulation aruco_gen --single-model "
                   "--source-world='/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover"
                   ".world' '/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt' > "
                   "'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world''",
                   shell=True)

    with open("/home/ubuntu/CloverCloudPlatform/user_objects.json", "w") as write_file:
        json.dump(user_objects, write_file)

    for marker in user_objects['pictures']:
        shutil.copyfile(
            f'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/'
            f'{marker.replace("aruco_marker_", "")}.png',

            f'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/'
            f'{marker}.png'
        )


@sio.on('AddCube')
def add_cube(data):
    dir_name = str(len(user_objects['models']))
    os.mkdir(fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{dir_name}')
    path_to_sdf = fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{dir_name}/model.sdf'
    path_to_config = fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{dir_name}/model.config'

    shutil.copyfile(r'/home/ubuntu/CloverCloudPlatform/default_models/default_cube/model.sdf',
                    path_to_sdf)

    shutil.copyfile(r'/home/ubuntu/CloverCloudPlatform/default_models/default_cube/model.config',
                    path_to_config)

    user_objects['models'].append(
        {'size': [1, 1, 1], 'position': [0, 1, 0.5], 'rotation': [0, 0, 0], 'color': 'Gray', 'colorHex': '#838383'}
    )

    sdf_tree = ET.parse(path_to_sdf)
    sdf_root = sdf_tree.getroot()
    for type_tag in sdf_root.findall('.//model'):
        type_tag.set('name', dir_name)
    sdf_tree.write(path_to_sdf)

    config_tree = ET.parse(path_to_config)
    config_root = config_tree.getroot()
    for type_tag in config_root.findall('.//name'):
        type_tag.text = dir_name
    config_tree.write(path_to_config)

    world_tree = ET.parse(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
    world_root = world_tree.getroot()

    new_include = ET.Element('include')
    new_include_uri = ET.SubElement(new_include, 'uri')
    new_include_uri.text = f'model://{dir_name}'
    new_include_pose = ET.SubElement(new_include, 'pose')
    new_include_pose.text = '0 1 0.5 0 0 0'

    world = world_root.find('world')
    world.append(new_include)

    world_tree.write(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
    world_tree.write(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover.world')

    with open("/home/ubuntu/CloverCloudPlatform/user_objects.json", "w") as write_file:
        json.dump(user_objects, write_file)


@sio.on('EditCube')
def edit_cube(data):
    print(data)
    if data['position'] is not None:
        tree = ET.parse(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
        root = tree.getroot()

        for include in root.findall('.//include'):
            if data['model_id'] in include.find('.//uri').text:
                include.find('.//pose').text = f'{data["position"][0]} {data["position"][1]} {data["position"][2]} ' \
                                               f'{data["rotation"][0]} {data["rotation"][1]} {data["rotation"][2]}'
                break
        tree.write(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
        tree.write(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/resources/worlds/clover.world')
        user_objects['models'][int(data['model_id'])]['position'] = data['position']
        user_objects['models'][int(data['model_id'])]['rotation'] = data['rotation']

    if data['size'] is not None:
        print('scale')
        tree = ET.parse(fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')
        root = tree.getroot()
        print('ok')

        for type_tag in root.findall('.//size'):
            print(data['size'])
            print(type_tag.text)
            type_tag.text = ' '.join(map(str, data['size']))

        tree.write(fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')
        user_objects['models'][int(data['model_id'])]['size'] = data['size']

    if data['color'] is not None:
        tree = ET.parse(fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')
        root = tree.getroot()

        for type_tag in root.findall('.//name'):
            type_tag.text = 'Gazebo/' + data['color']

        tree.write(fr'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')

        user_objects['models'][int(data['model_id'])]['color'] = data['color']
        user_objects['models'][int(data['model_id'])]['colorHex'] = data['colorHex']

    with open("/home/ubuntu/CloverCloudPlatform/user_objects.json", "w") as write_file:
        json.dump(user_objects, write_file)


@sio.on('GetGazeboModels')
def run_gazebo(data):
    aruco_poses = []
    aruco_sizes = []
    aruco_svg = []
    aruco_names = []
    aruco_map = []
    aruco_types = []

    with open(r'/home/ubuntu/.gazebo/models/aruco_cmit_txt/aruco_model.sdf', 'r') as f:
        f.readline()
        xml_string = f.read()
        root = ET.fromstring(xml_string)

    for type_tag in root.findall('.//pose'):
        aruco_poses.append(type_tag.text[0:7].split())

    with open(r'/home/ubuntu/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
        lines = map_txt.readlines()
        for line in range(len(lines)):
            if line != 17:
                aruco_sizes.append(lines[line].split('\t')[1])
            else:
                pass

    for type_tag in root.findall('.//name'):
        aruco_names.append(type_tag.text.replace("/", "_"))
        aruco_name = f'/home/ubuntu/.gazebo/models/aruco_cmit_txt/materials/textures/' \
                     f'{type_tag.text.replace("/", "_")}.png'
        if type_tag.text.replace("/", "_") not in user_objects['pictures']:
            svg_image = main(aruco_name)
            aruco_svg.append(svg_image)
            aruco_types.append('svg')
        else:
            with open(aruco_name, 'rb') as img:
                aruco_svg.append(str(base64.b64encode(img.read())))
                aruco_types.append('png')

    for index in range(len(aruco_poses)):
        aruco_map.append({'image': aruco_svg[index], 'position': aruco_poses[index], 'aruco_name': aruco_names[index],
                          'aruco_size': aruco_sizes[index], 'aruco_type': aruco_types[index]})

    sio.emit('GazeboModels', {'aruco_map': aruco_map, 'user_objects': user_objects['models'], 'user_sid': data})
