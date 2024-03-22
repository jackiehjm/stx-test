#!/bin/bash
#This scripts configures DUT as PTP slave

source /etc/platform/openrc

NODE=$1
PTP_IF=$2

#set global clock to ptp
system host-update $NODE clock_synchronization=ptp

system ptp-instance-add ptpinst1 ptp4l
system ptp-instance-add phcinst1 phc2sys

system ptp-interface-add ptp-iface1 ptpinst1
system ptp-interface-add phcif1 phcinst1

system ptp-instance-parameter-add ptpinst1 domainNumber=0 slaveOnly=1

system host-if-ptp-assign $NODE $PTP_IF ptp-iface1
system host-if-ptp-assign $NODE $PTP_IF phcif1

system ptp-instance-parameter-add phcinst1 uds_address=/var/run/ptp4l-ptpinst1
system ptp-instance-parameter-add phcinst1 domainNumber=0

system host-ptp-instance-assign $NODE ptpinst1
system host-ptp-instance-assign $NODE phcinst1

system ptp-instance-apply
