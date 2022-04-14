#!/bin/sh
sudo systemctl stop missionalertbot.service
git checkout main
git pull
export PTN_MISSION_ALERT_SERVICE=‘True’
sudo systemctl start missionalertbot.service
