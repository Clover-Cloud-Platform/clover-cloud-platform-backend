const os = require('os');
const pty = require('node-pty');
const io = require("socket.io-client")
const Convert = require('ansi-to-html');
const { exec } = require("child_process");

const socket = io("yor local adress");

socket.emit('TerminalConnected', os.hostname());

const shell = 'bash';

const convert = new Convert({
    newline:true
});

let sid = '';
let id = 0;

socket.on('StartStreamTelemetry', uid => {
    const ptyProcess2 = pty.spawn(shell, [], {
        name: 'xterm-color',
        cols: 80,
        rows: 30,
        cwd: process.env.HOME,
        env: process.env
    });
    const ptyProcess4 = pty.spawn(shell, [], {
        name: 'xterm-color',
        cols: 80,
        rows: 30,
        cwd: process.env.HOME,
        env: process.env
    });
    setTimeout(() => {
    ptyProcess2.write(`/usr/bin/python3.8 /home/ubuntu/PngToSvg/stream_telemetry.py ${uid}\r`);
    ptyProcess4.write(`/usr/bin/python3.8 /home/ubuntu/PngToSvg/stream_led.py ${uid}\r`);
    }, 12000);
});

const ptyProcess = pty.spawn(shell, [], {
    name: 'xterm-color',
    cols: 80,
    rows: 30,
    cwd: process.env.HOME,
    env: process.env
});

socket.on('ExecuteCommand', input => {
    if(input.command.type == 'kill'){
        const cmdList = input.command.cmd;
        for(let i in cmdList){
            exec(`pkill -f "${cmdList[i]}"`);
        }
    } else{
        ptyProcess.write(`${input.command.cmd}\r`);
        sid = input.user_sid;
    }
});
socket.on('RunGazebo', ()=>{
    const ptyProcess3 = pty.spawn(shell, [], {
        name: 'xterm-color',
        cols: 80,
        rows: 30,
        cwd: process.env.HOME,
        env: process.env
    });
    ptyProcess3.write('Xvfb :1 &\r');
    ptyProcess3.write('export DISPLAY=:1\r');
    ptyProcess3.write(`/bin/bash -c 'source /home/clover/catkin_ws/devel/setup.bash; roslaunch clover_simulation simulator.launch'\r`);
});
ptyProcess.on('data', function(data) {
    socket.emit('CommandOutput', {output: convert.toHtml(data.toString()), id: id, user_sid: sid});
    id++;
});
