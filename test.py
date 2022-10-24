from serial import Serial
from time import sleep

port = Serial(f'COM9', 230400, timeout=0.3)
#TODO: CREATE PROPER CMD
command = ('cmd_hs'+'\r\n').encode()
port.write(command)
sleep(0.8)
resp = port.read_all()
port.close()
#TODO: CHECK PROPER RESP
print(f'RESP: {resp}')