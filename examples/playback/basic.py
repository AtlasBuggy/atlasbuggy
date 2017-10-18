import time
from log.parser import LogParser

t0 = time.time()
with open("../subscriptions/logs/demo/ImmutableConsumer/demo.log") as file:
    parser = LogParser(file.read())
t1 = time.time()

print(t1 - t0)

for line in parser:
    print(line.full)
    time.sleep(parser.delta_t())
