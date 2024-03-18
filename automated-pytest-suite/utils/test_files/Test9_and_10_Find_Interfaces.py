#!/usr/bin/env python3

import subprocess

# Get the list of network interfaces
interfaces = subprocess.check_output(["ip", "-o", "link", "show"]).decode().splitlines()
found_interfaces = []
count = 0

# Loop through each interface
for interface in interfaces:
    interface_parts = interface.split(": ")
    interface_name = interface_parts[1].split("@")[0]

    # Get the link status of the interface
    link_status = subprocess.run(["cat", f"/sys/class/net/{interface_name}/operstate"], capture_output=True, text=True).stdout.strip()

    # Check if the interface has a link up, starts with 'e', and the last character is not '0'
    if link_status == "up" and interface_name.startswith('e') and interface_name[-1] != '0':
        if not any(interface_name[:5] == iface[:5] for iface in found_interfaces):
            found_interfaces.append(interface_name)
            count += 1

    # Exit the loop if two interfaces have been found
    if count == 2:
        break

if count == 2:
    print(found_interfaces[0])
    print(found_interfaces[1])
else:
    print("Could not find two interfaces with link up and whose last character is not '0'.")
