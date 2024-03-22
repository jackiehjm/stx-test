#!/bin/bash
#This scripts configures DUT as PTP Grand Master

source /etc/platform/openrc

NODE=$1
PTP_IF=$2

#set global clock to ptp
system host-update $NODE clock_synchronization=ptp

system ptp-instance-add ptpinst0 ptp4l
system ptp-instance-add phcinst0 phc2sys

system ptp-interface-add ptp-iface0 ptpinst0
system ptp-interface-add phcif0 phcinst0

system ptp-instance-parameter-add ptpinst0 domainNumber=0
system ptp-instance-parameter-add ptpinst0 priority1=120 priority2=121 clockClass=6

system host-if-ptp-assign $NODE $PTP_IF ptp-iface0
system host-if-ptp-assign $NODE $PTP_IF phcif0

system ptp-instance-parameter-add phcinst0 uds_address=/var/run/ptp4l-ptpinst0
system ptp-instance-parameter-add phcinst0 domainNumber=0

system host-ptp-instance-assign $NODE ptpinst0
system host-ptp-instance-assign $NODE phcinst0

system ptp-instance-apply
