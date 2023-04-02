#Temporary file, soon to be moved to stream_telemetry.py
import re
import sys
import time

import rospy
import socketio
from led_msgs.msg import LEDStateArray


sid = sys.argv[1]
sio = socketio.Client()
sio.connect('your local adress')


rospy.init_node('cloverst')


def callback(msg):
    return msg


leds = []
rospy.Subscriber('/led/state', LEDStateArray, callback)
while not rospy.is_shutdown():
    msg = rospy.wait_for_message('/led/state', LEDStateArray)
    values = msg.leds
    for value in values:
        led = [re.findall(r'\d+', str(value).split(' ')[1])[0], re.findall(r'\d+', str(value).split(' ')[2])[0],
               re.findall(r'\d+', str(value).split(' ')[3])[0]]
        leds.append(led)
    sio.emit('LedState', {'leds': leds, 'sid': sid})
    print(leds)
    leds.clear()
    time.sleep(0.05)
