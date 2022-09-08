# import can, canopen

# # network = canopen.Network()
# # network.connect(bustype='pcan', channel='PCAN_USBBUS2', bitrate=1000000)
# bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS2', bitrate=1000000)

# last_sync = 0
# counter_node_4 = 0
# total_node_4 = 0
# avg_node_4 = 0
# counter_node_1 = 0
# total_node_1 = 0
# avg_node_1 = 0
# while True:
#     msg = bus.recv()



# sdasdasd
#     print(f"\n{msg.arbitration_id:03x} {msg.data} {msg.timestamp}")
    
#     if msg.arbitration_id == 0x80:
#         last_sync = msg.timestamp
#     elif msg.arbitration_id == 0x284:
#         delay_node_4 = msg.timestamp - last_sync
#         counter_node_4 += 1
#         total_node_4 += delay_node_4
#         avg_node_4 = total_node_4 / counter_node_4
#         print(f"NODE 4 SYNC RESPONCE: {delay_node_4}")
#         print(f"NODE 4 AVARAGE TIME: {avg_node_4}")
#     elif msg.arbitration_id == 0x283:
#         delay_node_1 = msg.timestamp - last_sync
#         counter_node_1 += 1
#         total_node_1 += delay_node_1
#         avg_node_1 = total_node_1 / counter_node_1
#         print(f"NODE 1 SYNC RESPONCE: {delay_node_1}")
#         print(f"NODE 1 AVARAGE TIME: {avg_node_1}")


# m = "['64010110', '64010210', '64010310', '64010410']"
m = "[]"
m = m.replace("[", "")
m = m.replace("]", "")
m = m.replace("'", "")
m = m.split(', ')
print(m)
new_list = []
if m[0].isnumeric():
    for num in m:
        temp = int(num, 16)
        new_list.append(temp)

print(new_list)
print(hex(new_list[2]))