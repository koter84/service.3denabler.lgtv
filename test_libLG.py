import os
import sys
import simplejson
import re
import urllib2
from xml.dom.minidom import parseString
import base64
import uuid
import select

sys.path.append('./lib')
sys.path.append('./lib/libLGTV_serial')

from libLGTV_serial import LGTV
import serial

print "done"
