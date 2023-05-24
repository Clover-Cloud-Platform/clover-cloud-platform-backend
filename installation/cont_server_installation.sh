#!/bin/sh
echo "Enter your main server address"
read adress

sudo apt install npm
pip3 install python-socketio
pip3 install Pillow

cd ~

mkdir FILES

mkdir CloverCloudPlatform

cd CloverCloudPlatform

npm i os node-pty socket.io-client ansi-to-html child_process

mkdir cont_server
mkdir user_objects
mkdir default_models

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/cont_server/cont_server.py

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/cont_server/stream_telemetry.py

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/cont_server/terminal.js

wget https://raw.githubusercontent.com/Astel-d/PngToSvgForCloverCloud/master/pngtosvg.py

https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/cont_server/user_objects.json

sed -i "s,main_server_address,${adress}," cont_server.py
sed -i "s,main_server_address,${adress}," stream_telemetry.py
sed -i "s,main_server_address,${adress}," terminal.js

cd default_models 
mkdir default_cube
cd default_cube 

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/cont_server/default_models/default_cube/model.config

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/cont_server/default_models/default_cube/model.sdf


echo "\e[32mInstallation sucsess\e[0m"
