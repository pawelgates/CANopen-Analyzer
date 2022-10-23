import can, canopen
from time import sleep

network = canopen.Network()
# network.connect(bustype='pcan', channel='PCAN_USBBUS2', bitrate=1000000)
bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS2', bitrate=1000000)
node = network.add_node(4, 'PEAK.eds')

# bitrate = "BPS0"
# bitrate_bytes = bitrate.encode()
# print(bitrate_bytes)
# node.sdo.download(0x1f50, 3, bitrate_bytes)
network.bus = bus

while True:
    
    listeners = network.listeners
    
    notifier = can.Notifier(bus, listeners, 0.5)
    print(notifier.data)
