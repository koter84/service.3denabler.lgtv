#!/bin/bash

scp -r ./* root@192.168.32.177:/storage/.kodi/addons/service.3denabler.lgtv/
ssh root@192.168.32.177 'rm /storage/.kodi/userdata/addon_data/service.3denabler.lgtv/settings.xml'
