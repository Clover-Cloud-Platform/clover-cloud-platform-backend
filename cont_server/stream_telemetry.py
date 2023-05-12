import sys
import time
import re

import rospy
import socketio
from clover import srv
from led_msgs.msg import LEDStateArray


sid = sys.argv[1]
sio = socketio.Client()
sio.connect('main_server_address')


rospy.init_node('clovert')

get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
leds = []


def telemetry_led_callback(msg):
    global leds
    telemetry = get_telemetry()
    values = msg.leds
    for value in values:
        led = [re.findall(r'\d+', str(value).split(' ')[2])[0], re.findall(r'\d+', str(value).split(' ')[3])[0],
               re.findall(r'\d+', str(value).split(' ')[4])[0]]
        leds.append(led)
    sio.emit('CloverTelemetry', {'position': [telemetry.y, telemetry.z, telemetry.x],
                                 'rotation': [telemetry.roll, telemetry.yaw, telemetry.pitch],
                                 'armed': telemetry.armed,
                                 'led': leds,
                                 'sid': sid})
    leds.clear()


telemetry_led_sub = rospy.Subscriber('/telemetry', srv.Telemetry, telemetry_led_callback)


while not rospy.is_shutdown():
    rospy.spin()
