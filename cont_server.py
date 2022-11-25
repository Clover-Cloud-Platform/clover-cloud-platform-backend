import subprocess
from pngtosvg import *
import xml.etree.ElementTree as ET
import socketio


sio = socketio.Client()
sio.connect('your ngrok adress')


cont_code = subprocess.run("hostname", shell=True, stdout=subprocess.PIPE, text=True).stdout.replace("\n", '')
sio.emit('ContConnected', cont_code)


@sio.on('RunGazebo')
def run_gazebo(data):
    aruco_pose = []
    aruco_svg = []
    aruco_map = []
    root = ET.parse(r'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/aruco_cmit_txt/aruco_model.sdf').getroot()

    for type_tag in root.findall('.//pose'):
        aruco_pose.append(type_tag.text[0:7].split(' ').append('1.57079632679'))

    for type_tag in root.findall('.//name'):
        aruco_name = f'/home/ubuntu/catkin_ws/src/clover/clover_simulation/models/aruco_cmit_txt/materials/textures/{type_tag.text.replace("/", "_")}.png'
        svg_image = main(aruco_name)
        aruco_svg.append(svg_image)

    for index in range (len(aruco_pose)):
        aruco_map.append({'image': aruco_svg[index], 'position': aruco_pose[index]})
    print(aruco_map)
    sio.emit('GazeboModels', {'aruco_map': aruco_map, 'user_sid': data['user_sid']})
