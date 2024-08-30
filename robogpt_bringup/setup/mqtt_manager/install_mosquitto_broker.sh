#!/bin/sh

sudo apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
echo "--------------"
sudo apt-get update
echo "--------------"
sudo apt-get install mosquitto
echo "--------------"
sudo apt-get install mosquitto-clients
