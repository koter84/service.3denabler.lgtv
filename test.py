import sys
sys.path.append('lib')
import serial

ser = serial.Serial(0) # open first serial port

print ser.portstr # check which port was really used

ser.write("ka 0 FF\r")
tv_onoff = ser.read(10) # read a '\n' terminated line
print tv_onoff

ser.close() # close port
