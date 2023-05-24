# import libs
import re
import os
import base64
import json
import shutil
import getpass
from pngtosvg import *
import subprocess
import xml.etree.ElementTree as ET
import socketio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sio = socketio.Client()
sio.connect('main_server_address')  # Connect to socket.io server

# Get the instance name by running the "hostname" command
user_name = subprocess.run("hostname", shell=True, stdout=subprocess.PIPE, text=True).stdout.replace("\n", '')
instance_name = getpass.getuser()
user_sid = None

# Emit an event to the server to indicate the connection of the controller
sio.emit('ContConnected', user_name)

# Read user objects from a JSON file
with open(f"/home/{instance_name}/CloverCloudPlatform/user_objects.json", "r") as read_file:
    user_objects = json.load(read_file)


def get_directory_structure(rootdir):
    dir = {
        'type': 'folder',
        'name': os.path.basename(rootdir),
        'path': rootdir.replace(f'/home/{instance_name}', ''),
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
                'path': item_path.replace(f'/home/{instance_name}', ''),
            })
    return dir


@sio.on('GetGazeboState')
def get_gazebo_state(data):
    gazebo_state = subprocess.run('ps -A | grep roslaunch', shell=True, stdout=subprocess.PIPE, text=True).stdout
    if gazebo_state != '':
        sio.emit("GazeboStateRes", {'gazebo_state': True, 'user_sid': data['user_sid'], 'cont_code': data['cont_code']})
    else:
        sio.emit("GazeboStateRes",
                 {'gazebo_state': False, 'user_sid': data['user_sid'], 'cont_code': data['cont_code']})


@sio.on('GetFiles')
def get_files(data):
    # Function to recursively get the directory structure
    global user_sid
    if user_sid != data:
        user_sid = data
    result = [get_directory_structure(rootdir=f'/home/{instance_name}/FILES')]
    sio.emit('Files', {'user_sid': user_sid, 'files': result})


@sio.on('MoveItem')
def move_item(data):
    shutil.move(f'/home/{instance_name}/' + data['source'], f'/home/{instance_name}/' + data['target'])


@sio.on('EditName')
def edit_file_name(data):
    old_file_name = os.path.basename(f'/home/{instance_name}/' + data['path'])
    new_file_path = f'/home/{instance_name}/' + data['path'].replace(old_file_name, data['newName'])
    os.rename(f'/home/{instance_name}/' + data['path'], new_file_path)


@sio.on('CreateNewFile')
def create_new_file(data):
    open(f'/home/{instance_name}/' + data, 'w+')


@sio.on('CreateNewDirectory')
def create_new_directory(data):
    os.mkdir(f'/home/{instance_name}/' + data)  # Creates a new directory in the specified path


@sio.on('DeleteFile')
def delete_file(data):
    os.remove(f'/home/{instance_name}/' + data)  # Deletes the specified file


@sio.on('DeleteDirectory')
def delete_file(data):
    shutil.rmtree(f'/home/{instance_name}/' + str(data))  # Deletes the specified directory and its contents


@sio.on('GetFileContent')
def get_file_content(data):
    try:
        file = open(f"/home/{instance_name}/" + data['path'], 'r')  # Opens the specified file in read mode
        file_content = file.read()  # Reads the content of the file
        sio.emit('FileContent', {'content': file_content, 'path': data['path'], 'user_sid': data['user_sid']})  # Send the file content to the client
    except Exception as E:
        sio.emit('FileContent', {'content': None, 'path': data['path'],
                                 'user_sid': data['user_sid']})  # Send the file content to the client if file not found


@sio.on('WriteFile')
def write_file(data):
    file = open(f"/home/{instance_name}/" + data['path'], 'w')  # Opens the specified file in write mode
    file.write(data['value'])  # Writes the provided value to the file
    file.close()  # Closes the file


@sio.on('ReadImage')
def read_image(data):
    if data['type'] == 'svg':
        svg = open(f"/home/{instance_name}/" + data['path'], 'r')  # Opens the specified file in read mode
        svg_content = svg.read()  # Reads the content of the file
        sio.emit('ImageData', {'content': svg_content,
                               'user_sid': data['user_sid'], 'type': data['type']})  # Send the file content to the client

    else:
        with open(f"/home/{instance_name}/" + data['path'], 'rb') as img:
            base64_img = base64.b64encode(img.read()).decode('utf-8')
            file_name, file_extension = os.path.splitext(f"/home/{instance_name}/" + data['path'])
            if file_extension.replace('.', '') == 'jpg':
                file_extension = 'jpeg'
            else:
                file_extension = 'png'

            sio.emit('ImageData', {'content': f'data:image/{file_extension};base64, {base64_img}',
                                   'user_sid': data['user_sid'], 'type': data['type']})  # Send the file content to the client


@sio.on('EditMarker')
def edit_marker(data):
    line_number = 0  # Counter for line number
    aruco_id = re.findall(r'\d+', data["aruco_name"])[1]  # Extracts the aruco_id from the marker name

    with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
        lines = map_txt.readlines()  # Reads all lines from the file
        for line in lines:
            if line.split('\t')[0] == aruco_id:  # Checks if the line starts with the aruco_id
                break
            line_number += 1  # Increments the line number

    if data['image'] is not None:  # Checks if image data is provided
        with open(fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/'
                  fr'{data["aruco_name"].replace("aruco_marker_", "")}.png', 'wb') as img:
            image_encode = bytes(data['image'], 'UTF-8')
            img.write(base64.decodebytes(image_encode))  # Decodes and writes the image data to a file
        user_objects["pictures"].append(data["aruco_name"])  # Adds the aruco_name to user_objects["pictures"]

    if data['size'] is not None:  # Checks if size data is provided
        with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
            lines = map_txt.readlines()  # Reads all lines from the file
            line = lines[line_number].split('\t')  # Retrieves the line corresponding to the aruco_id
            line[1] = str(data['size'])  # Updates the size in the line
            lines[line_number] = '\t'.join(line)  # Joins the line elements with tab delimiter

        # Update the 'cmit.txt' file with the given lines
        with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
            map_txt.writelines(lines)
            map_txt.close()

        # Update position if available
        if data['position'] is not None:
            # Read the 'cmit.txt' file
            with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
                lines = map_txt.readlines()
                line = lines[line_number].split('\t')
                line[2], line[3] = str(data['position'][0]), str(data['position'][1])
                lines[line_number] = '\t'.join(line)

            # Write the updated lines back to the 'cmit.txt' file
            with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
                map_txt.writelines(lines)
                map_txt.close()

        # Update marker ID if available
        if data['marker_id'] is not None:
            # Read the 'cmit.txt' file
            with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
                lines = map_txt.readlines()
                line = lines[line_number].split('\t')
                line[0] = str(data['marker_id'])
                lines[line_number] = '\t'.join(line)

            # Write the updated lines back to the 'cmit.txt' file
            with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
                map_txt.writelines(lines)
                map_txt.close()

            # Rename the corresponding image file
            os.rename(
                fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/{data["aruco_name"]}.png',
                fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/'
                fr'{data["aruco_name"].replace(aruco_id, data["marker_id"])}.png'
            )

            # Remove the old image file if it exists in the user_objects dictionary
            if data["aruco_name"] in user_objects['pictures']:
                user_objects['pictures'].remove(data["aruco_name"])
                os.remove(
                    fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/'
                    fr'{data["aruco_name"].replace("aruco_marker_", "")}.png'
                )

        # Run a subprocess to generate aruco markers
        subprocess.run(
            fr"/bin/bash -c 'source /home/{instance_name}/catkin_ws/devel/setup.bash; "
            fr"rosrun clover_simulation aruco_gen --single-model "
            fr"--source-world='/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover"
            fr".world' '/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt' > "
            fr"'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world''",
            shell=True
        )

        # Write the updated user_objects dictionary to a JSON file
        with open(fr"/home/{instance_name}/CloverCloudPlatform/user_objects.json", "w") as write_file:
            json.dump(user_objects, write_file)

        # Copy image files from one directory to another based on user_objects['pictures']
        for marker in user_objects['pictures']:
            shutil.copyfile(
                fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/'
                f'{marker.replace("aruco_marker_", "")}.png',
                fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/'
                f'{marker}.png'
            )


@sio.on('AddMarker')
def add_marker(data):
    # Extract the aruco ID from the marker name
    aruco_id = re.findall(r'\d+', data["name"])[1]

    # Append the marker information to the "cmit.txt" file
    with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'a') as map_txt:
        map_txt.write(f'\n{aruco_id}  0.33  0.0  -1.0  0  0  0  0')

    # Generate the aruco markers in the simulation world
    subprocess.run(fr""
                   fr"/bin/bash -c 'source /home/{instance_name}/catkin_ws/devel/setup.bash; "
                   fr"rosrun clover_simulation aruco_gen --single-model "
                   fr"--source-world='/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover"
                   fr".world' '/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt' > "
                   fr"'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world''",
                   shell=True)


@sio.on('DeleteMarker')
def delete_marker(data):
    x = 0
    # Extract the aruco ID from the marker name
    aruco_id = re.findall(r'\d+', data["name"])[1]

    # Remove the corresponding marker from the "cmit.txt" file
    with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
        lines = map_txt.readlines()
        for line in lines:
            if line.split('\t')[0] == aruco_id:
                lines.pop(x)
            x += 1

    with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'w') as map_txt:
        map_txt.writelines(lines)
        map_txt.close()

    # Remove the marker image file and update the user_objects.json file
    if data["name"] in user_objects['pictures']:
        user_objects['pictures'].remove(data['name'])
        os.remove(fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/'
                  fr'{data["name"].replace("aruco_marker_", "")}.png')
        with open(fr"/home/{instance_name}/CloverCloudPlatform/user_objects.json", "w") as write_file:
            json.dump(user_objects, write_file)

    # Regenerate the aruco markers in the simulation world
    subprocess.run(fr""
                   fr"/bin/bash -c 'source /home/{instance_name}/catkin_ws/devel/setup.bash; "
                   fr"rosrun clover_simulation aruco_gen --single-model "
                   fr"--source-world='/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover"
                   fr".world' '/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt' > "
                   fr"'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world''",
                   shell=True)


@sio.on('AddCube')
def add_cube(data):
    dir_name = data
    # Create a directory for the cube model
    os.mkdir(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{dir_name}')
    path_to_sdf = fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{dir_name}/model.sdf'
    path_to_config = fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{dir_name}/model.config'

    # Copy the default cube model files to the new directory
    shutil.copyfile(fr'/home/{instance_name}/CloverCloudPlatform/default_models/default_cube/model.sdf',
                    path_to_sdf)
    shutil.copyfile(fr'/home/{instance_name}/CloverCloudPlatform/default_models/default_cube/model.config',
                    path_to_config)

    # Add the cube model information to user_objects.json
    user_objects['models'].append(
        {'cubeID': dir_name, 'size': [1, 1, 1], 'position': [0, 1, 0.5], 'rotation': [0, 0, 0], 'color': 'Gray', 'colorHex': '#838383'}
    )

    # Update the name of the cube in the SDF and config files
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

    # Update the simulation world file to include the new cube model
    world_tree = ET.parse(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
    world_root = world_tree.getroot()

    new_include = ET.Element('include')
    new_include_uri = ET.SubElement(new_include, 'uri')
    new_include_uri.text = f'model://{dir_name}'
    new_include_pose = ET.SubElement(new_include, 'pose')
    new_include_pose.text = '0 1 0.5 0 0 0'

    world = world_root.find('world')
    world.append(new_include)

    world_tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
    world_tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover.world')

    # Update the user_objects.json file
    with open(f"/home/{instance_name}/CloverCloudPlatform/user_objects.json", "w") as write_file:
        json.dump(user_objects, write_file)


@sio.on('EditCube')
def edit_cube(data):
    if data['position'] is not None:
        # Edit the position and rotation of the cube in the simulation world
        tree = ET.parse(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
        root = tree.getroot()

        for include in root.findall('.//include'):
            if data['model_id'] in include.find('.//uri').text:
                include.find('.//pose').text = f'{data["position"][0]} {data["position"][1]} {data["position"][2]} ' \
                                               f'{data["rotation"][0]} {data["rotation"][1]} {data["rotation"][2]}'
                break
        tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
        tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover.world')

        # Update the position and rotation of the cube in user_objects.json
        next(item for item in user_objects['models'] if item["cubeID"] == data['model_id'])['position'] = data['position']
        next(item for item in user_objects['models'] if item["cubeID"] == data['model_id'])['rotation'] = data['rotation']

    if data['size'] is not None:
        # Edit the size of the cube model
        tree = ET.parse(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')
        root = tree.getroot()

        for type_tag in root.findall('.//size'):
            type_tag.text = ' '.join(map(str, data['size']))

        tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')

        # Update the size of the cube in user_objects.json
        next(item for item in user_objects['models'] if item["cubeID"] == data['model_id'])['size'] = data['size']

    if data['color'] is not None:
        # Edit the color of the cube model
        tree = ET.parse(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')
        root = tree.getroot()

        for type_tag in root.findall('.//name'):
            type_tag.text = 'Gazebo/' + data['color']

        tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{data["model_id"]}/model.sdf')

        # Update the color and colorHex of the cube in user_objects.json
        next(item for item in user_objects['models'] if item["cubeID"] == data['model_id'])['color'] = data['color']
        next(item for item in user_objects['models'] if item["cubeID"] == data['model_id'])['colorHex'] = data['colorHex']

    # Update the user_objects.json file
    with open(fr"/home/{instance_name}/CloverCloudPlatform/user_objects.json", "w") as write_file:
        json.dump(user_objects, write_file)


@sio.on('DeleteCube')
def delete_cube(data):
    # Delete the cube model directory
    shutil.rmtree(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/models/{data}')
    tree = ET.parse(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
    world_root = tree.getroot()

    # Remove the cube model from the simulation world
    for elem in world_root.findall('.//include'):
        uri_elem = elem.find('uri')
        if uri_elem is not None and data in str(uri_elem.text):
            world_root.find('.//world').remove(elem)

    tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover_aruco.world')
    tree.write(fr'/home/{instance_name}/catkin_ws/src/clover/clover_simulation/resources/worlds/clover.world')

    # Remove the deleted cube from user_objects.json
    user_objects["models"] = [item for item in user_objects["models"] if item["cubeID"] != data]

    # Write the updated user_objects.json file
    with open(fr"/home/{instance_name}/CloverCloudPlatform/user_objects.json", "w") as write_file:
        json.dump(user_objects, write_file)


@sio.on('GetGazeboModels')
def run_gazebo(data):
    aruco_poses = []
    aruco_sizes = []
    aruco_svg = []
    aruco_names = []
    aruco_map = []
    aruco_types = []

    # Read the aruco_model.sdf file to retrieve aruco poses
    with open(fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/aruco_model.sdf', 'r') as f:
        f.readline()
        xml_string = f.read()
        root = ET.fromstring(xml_string)

    # Retrieve aruco poses, sizes, names, and image types
    for type_tag in root.findall('.//pose'):
        aruco_poses.append(type_tag.text.split()[0:2])

    with open(fr'/home/{instance_name}/catkin_ws/src/clover/aruco_pose/map/cmit.txt', 'r') as map_txt:
        lines = map_txt.readlines()
        for line in range(len(lines)):
            if line != 17:
                aruco_sizes.append(lines[line].split('\t')[1])
            else:
                pass

    for type_tag in root.findall('.//name'):
        aruco_names.append(type_tag.text.replace("/", "_"))
        aruco_name = fr'/home/{instance_name}/.gazebo/models/aruco_cmit_txt/materials/textures/' \
                     fr'{type_tag.text.replace("/", "_")}.png'
        if type_tag.text.replace("/", "_") not in user_objects['pictures']:
            # Generate SVG image for aruco model
            svg_image = main(aruco_name)
            aruco_svg.append(svg_image)
            aruco_types.append('svg')
        else:
            # Load PNG image for aruco model
            with open(aruco_name, 'rb') as img:
                aruco_svg.append(str(base64.b64encode(img.read())))
                aruco_types.append('png')

    # Create the aruco_map with image, position, size, name, and type
    for index in range(len(aruco_poses)):
        aruco_map.append({'image': aruco_svg[index], 'position': aruco_poses[index], 'aruco_name': aruco_names[index],
                          'aruco_size': aruco_sizes[index], 'aruco_type': aruco_types[index]})

    # Emit the GazeboModels event with aruco_map, user_objects, and user_sid
    sio.emit('GazeboModels', {'aruco_map': aruco_map, 'user_objects': user_objects['models'], 'user_sid': data})


class MyHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        result = [get_directory_structure(rootdir=f'/home/{instance_name}/FILES')]
        sio.emit('Files', {'user_sid': user_sid, 'files': result})
        pass


observer = Observer()
observer.schedule(MyHandler(), f'/home/{instance_name}/FILES', recursive=True)
observer.start()
observer.join()
