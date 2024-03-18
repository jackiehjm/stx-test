#!/usr/bin/env python3

import subprocess
import pexpect

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

    # Check if the interface has a link up and the last character is not '0'
    if link_status == "up" and interface_name[-1] != '0' and interface_name[0] == 'e':
        found_interfaces.append(interface_name)
        count += 1

    # Exit the loop if two interfaces have been found
    if count == 2:
        break

def compare_fields(array, variable):
    for field in array:
        if variable in field:
            print(f"Variable '{variable}' is found in field '{field}'")
            index = field.find('virtfn')
            virtfn_card = field[index+6:index+7]
    return virtfn_card
#card1 = subprocess.check_output("ls -l /sys/class/net/ens1f2/device/virtfn*", shell=True) #Uncomment this line if entering interfaces manually.
card1 = subprocess.check_output("ls -l /sys/class/net/" + found_interfaces[0] + "/device/virtfn*", shell=True) #Comment this line if entering interfaces manually.
card1_broken = card1.decode().splitlines()
command_output = subprocess.check_output("kubectl exec -it dpdk-pktgen -- env|grep PCI | cut -d '=' -f2", shell=True)
pktgen = command_output.decode().strip()
match_card1 = compare_fields(card1_broken, pktgen)
print("Virtual interface in Card 1 is " + match_card1)
#card2 = subprocess.check_output("ls -l /sys/class/net/ens2f2/device/virtfn*", shell=True)
card2 = subprocess.check_output("ls -l /sys/class/net/" + found_interfaces[1] + "/device/virtfn*", shell=True)
card2_broken = card2.decode().splitlines()
command_output = subprocess.check_output("kubectl exec -it dpdk-testpmd -- env|grep PCI | cut -d '=' -f2", shell=True)
testpmd = command_output.decode().strip()
match_card2 = compare_fields(card2_broken, testpmd)
print("Virtual interface in Card 2 is " + match_card2)

#Card1_Assign = "ip link set ens1f2 vf " +  match_card1 + " mac 9e:fd:e6:dd:44:44" #Uncomment this line if entering interfaces manually.
Card1_Assign = "ip link set " + found_interfaces[0] + " vf " +  match_card1 + " mac 9e:fd:e6:dd:44:44" #Comment this line if entering interfaces manually.
print(Card1_Assign)
#Card2_Assign = "ip link set ens2f2 vf " +  match_card2 + " mac 9e:fd:e6:dd:55:55" #Uncomment this line if entering interfaces manually.
Card2_Assign = "ip link set " + found_interfaces[1] + " vf " +  match_card2 + " mac 9e:fd:e6:dd:55:55" #Comment this line if entering interfaces manually.
print(Card2_Assign)

print(pktgen)
print(testpmd)
