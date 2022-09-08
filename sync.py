import can, canopen
from time import sleep


bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS1', bitrate=1000000)
sync_msg = can.Message(arbitration_id=0x80, data=None, is_extended_id=False)
time_cycle = 0.01
counter = 0

while True:
    bus.send(sync_msg)
    sleep(time_cycle)
    counter += 1
    print(f"{counter}   SYNC MSG every {time_cycle} sec")