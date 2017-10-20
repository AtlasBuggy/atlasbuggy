import logging

try:
    from ..arduino import Arduino
except ValueError:
    from device.arduino import Arduino

addresses = Arduino.list_addresses()

print("addresses:", addresses)

logging.basicConfig(level=logging.INFO)
Arduino.collect_all_devices(addresses, logging.getLogger(""))
