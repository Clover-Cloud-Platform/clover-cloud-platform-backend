#!/bin/bash
mkdir ./CloverCloudServer
cd CloverCloudServer

pip3 install rsa
pip3 install getpass4
pip3 install python-socketio
pip3 install eventlet
pip3 install pymongo

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/main_server/generate_keys.py

python3 generate_keys.py

echo 'Enter your mongodb key'
read -s -p mongokey

echo 'Enter the available port'
read port


wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/main_server/main_server.py


sed -i "s/your mongodb key/${mongokey}/g" main_server.py
sed -i "s,8000,${port}," main_server.py

python3 main_server.py
