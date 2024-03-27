#!/bin/bash

NIC=$1

# POD is dpdk-pktgen or dpdk-testpmd
POD=$2

vf_id=$(kubectl exec -it $POD -- env | grep PCI | cut -d '=' -f2|tr -d '[:space:]')
vf_path=$(ls -l /sys/class/net/$NIC/device/virtfn*|grep $vf_id)
vf_num=$(echo $vf_path | cut -d " " -f 9| sed 's/.*virtfn//')

echo $vf_id
echo $vf_path

echo "Virtual interface in Card 1 is $vf_num"

vf_cmd="ip link set $NIC vf $vf_num mac 9e:fd:e6:dd:44:44"
echo "Setting the mac for the vf $vf_id:"
echo "$vf_cmd"
$vf_cmd
