#!/bin/sh
echo "Enter the address of the main server, in the format http://address:port"
read address

mkdir CloverCloudSubserver
cd CloverCloudSubserver

pip3 install pylxd
pip3 install python-socketio

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/subserver/subserver.py

wget https://raw.githubusercontent.com/Clover-Cloud-Platform/clover-cloud-platform-backend/main/subserver/db.json

sed -i "s,your main server adress,${address}," subserver.py

python3 subserver.py
