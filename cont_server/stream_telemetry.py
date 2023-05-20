import sys
import time
import re

import rospy
import socketio
from clover import srv
from led_msgs.msg import LEDStateArray

# Get the session ID from the command line arguments
sid = sys.argv[1]

# Connect to the socket.io server
sio = socketio.Client()
sio.connect('http://10.143.7.57:8000')

# Initialize the ROS node
rospy.init_node('clovert')

# Create a service proxy to get telemetry data
get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
leds = []

# Callback function for telemetry and LED data
def telemetry_led_callback(msg):
    global leds
    # Get telemetry data from the get_telemetry service
    telemetry = get_telemetry()
    # Extract LED values from the received message
    values = msg.leds
    for value in values:
        # Extract RGB values from the LED message and store them in a list
        led = [re.findall(r'\d+', str(value).split(' ')[2])[0], re.findall(r'\d+', str(value).split(' ')[3])[0],
               re.findall(r'\d+', str(value).split(' ')[4])[0]]
        leds.append(led)
    # Send telemetry and LED data to the server using the CloveTelemetry event
    sio.emit('CloverTelemetry', {'position': [telemetry.y, telemetry.z, telemetry.x],
                                 'rotation': [telemetry.roll, telemetry.yaw, telemetry.pitch],
                                 'armed': telemetry.armed,
                                 'led': leds,
                                 'sid': sid})
    leds.clear()

# Subscribe to the telemetry topic and register the callback function
telemetry_led_sub = rospy.Subscriber('/telemetry', srv.Telemetry, telemetry_led_callback)

# Keep the ROS node running
while not rospy.is_shutdown():
    rospy.spin()
