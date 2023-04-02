import sys
import time

import rospy
import socketio
from clover import srv


sid = sys.argv[1]
sio = socketio.Client()
sio.connect('your local adress')


rospy.init_node('clovert')
get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
while not rospy.is_shutdown():
    telemetry = get_telemetry()
    sio.emit('CloverTelemetry', {'position': [telemetry.y, telemetry.z, telemetry.x],
                                 'rotation': [telemetry.roll, telemetry.yaw, telemetry.pitch],
                                 'armed': telemetry.armed,
                                 'sid': sid})
    time.sleep(0.04)
