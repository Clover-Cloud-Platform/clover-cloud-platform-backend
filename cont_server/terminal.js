
const os = require('os');
const pty = require('node-pty');
const io = require("socket.io-client")
const Convert = require('ansi-to-html');
const { exec } = require("child_process");

// Connect to the main server
const socket = io("http://10.143.7.57:8000");

// Send a message about that this script is running
socket.emit('TerminalConnected', os.hostname());

// Define shell for pty process
const shell = 'bash';

// Configure ansi to html
const convert = new Convert({
    newline:true
});

// Configure pty
const ptyConfig = {
    name: 'xterm-color',
    cols: 80,
    rows: 30,
    cwd: process.env.HOME,
    env: process.env
};

let sid = '';
let id = 0;

// Spawn pty processes
let streamTelemetryProcess = pty.spawn(shell, [], ptyConfig);
let gazeboProcess = pty.spawn(shell, [], ptyConfig);
let checkGazeboProcess;
const terminalProcess = pty.spawn(shell, [], {
    name: 'xterm-color',
    cols: 200,
    rows: 30,
    cwd: process.env.HOME,
    env: process.env
});

// Listen to command for running Gazebo
socket.on('RunGazebo', ()=>{
    // Launch virtual frame buffer
    gazeboProcess.write('Xvfb :1 &\r');
    gazeboProcess.write('export DISPLAY=:1\r');
    // Run Gazebo
    gazeboProcess.write(`/bin/bash -c 'source /home/ubuntu/catkin_ws/devel/setup.bash; roslaunch clover_simulation simulator.launch'\r`);
});
// Listen to command for stopping Gazebo
socket.on('StopGazebo', sid => {
    // Kill processes
    gazeboProcess.kill();
    streamTelemetryProcess.kill();
    // Send a response
    setTimeout(()=>{socket.emit('GazeboStopped', sid)}, 3000);
    // Spawn new processes waiting for commands
    gazeboProcess = pty.spawn(shell, [], ptyConfig);
    streamTelemetryProcess = pty.spawn(shell, [], ptyConfig);
});

// Listen to command for starting telemetry stream
socket.on('StartStreamTelemetry', uid => {
    // Start a process that checking Gazebo state
    checkGazeboProcess = pty.spawn(shell, [], ptyConfig);
    checkGazeboProcess.write('sleep 3; rostopic hz /mavros/state\r');
    // Check Gazebo state
    checkGazeboProcess.onData(data => {
        if(data.toString().includes('average rate')){
            // Gazebo is running
            checkGazeboProcess.kill();
            // Start streams
            streamTelemetryProcess.write(`/usr/bin/python3.8 /home/ubuntu/PngToSvg/stream_telemetry.py ${uid}\r`);
        }
    });
});

// Listen to commands from the web terminal
socket.on('ExecuteCommand', input => {
    if(input.command.type == 'kill'){
        // Stop all commands
        const cmdList = input.command.cmd;
        for(let i in cmdList){
            exec(`pkill -f "${cmdList[i]}"`);
        }
    } else{
        // Execute command
        terminalProcess.write(`${input.command.cmd}\r`);
        sid = input.user_sid;
    }
});

// Listen for terminal output
terminalProcess.onData(data => {
    // Send output
    socket.emit('CommandOutput', {output: convert.toHtml(data.toString()), id: id, user_sid: sid});
    id++;
});
