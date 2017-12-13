#!/bin/bash

kodi="root@192.168.32.191"

ssh ${kodi} 'mkdir -p /storage/.kodi/addons/service.3denabler.lgtv/'
ssh ${kodi} 'rm -r /storage/.kodi/addons/service.3denabler.lgtv/*'
ssh ${kodi} 'rm /storage/.kodi/userdata/addon_data/service.3denabler.lgtv/settings.xml'

scp -r ./* ${kodi}:/storage/.kodi/addons/service.3denabler.lgtv/
