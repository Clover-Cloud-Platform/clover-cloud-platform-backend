import subprocess
from pngtosvg import *
import xml.etree.ElementTree as ET
import socketio
import os
#import rospy
#from clover import srv



sio = socketio.Client()
sio.connect('your ngrok')


cont_code = subprocess.run("hostname", shell=True, stdout=subprocess.PIPE, text=True).stdout.replace("\n", '')
sio.emit('ContConnected', cont_code)


@sio.on('StartXServer')
def start_x_server(data):
    os.system(f"Xvfb :{data} &")
    os.system(f"export DISPLAY=:{data} &")


@sio.on('GetGazeboState')
def get_gazebo_state(data):
    gazebo_state = subprocess.run('ps -A | grep roslaunch', shell=True, stdout=subprocess.PIPE, text=True).stdout

    if gazebo_state != '':
        sio.emit("GazeboStateRes", {'gazebo_state': True, 'user_sid': data['user_sid']})
    else:
        sio.emit("GazeboStateRes", {'gazebo_state': False, 'user_sid': data['user_sid']})


@sio.on('RunGazebo')
def run_gazebo(data):
    aruco_poses = []
    aruco_svg = []
    aruco_map = []
    gazebo_state = subprocess.run('ps -A | grep roslaunch', shell=True, stdout=subprocess.PIPE, text=True).stdout
    print(type(gazebo_state))
    root = ET.parse(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/aruco_cmit_txt/aruco_model.sdf') \
        .getroot()

    for type_tag in root.findall('.//pose'):
        print(type_tag.text[0:7].split())
        aruco_poses.append(type_tag.text[0:7].split())
    for type_tag in root.findall('.//name'):
        aruco_name = f'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/aruco_cmit_txt/materials/textures/' \
                     f'{type_tag.text.replace("/", "_")}.png'
        svg_image = main(aruco_name)
        aruco_svg.append(svg_image)

    for index in range(len(aruco_poses)):
        aruco_map.append({'image': aruco_svg[index], 'position': aruco_poses[index]})
    if gazebo_state != '\n':
        sio.emit('GazeboModels', {'aruco_map': aruco_map, 'user_sid': data['user_sid']})
        subprocess.run('roslaunch clover_simulation simulator.launch', shell=True, text=True)
    else:
        sio.emit('GazeboModels', {'aruco_map': aruco_map, 'user_sid': data['user_sid']})

