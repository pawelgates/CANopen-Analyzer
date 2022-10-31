from datetime import datetime
from time import sleep

dt = datetime.now()
ts = datetime.timestamp(dt)

print(ts)

start = ts

while True:
    sleep(1)
    dt = datetime.now()
    ts = datetime.timestamp(dt)
    print(ts - start)
