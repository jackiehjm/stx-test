# Copyright Notice
Copyright © 2020‑2022 Wind River Systems, Inc.

All rights reserved. No part of this publication may be reproduced or transmitted in any form or by any means without the prior written permission of Wind River Systems, Inc.

Wind River, Simics, Tornado, and VxWorks are registered trademarks of Wind River Systems, Inc. Helix, Pulsar, Rocket, Titanium Cloud, Titanium Control, Titanium Core, Titanium Edge, Titanium Edge SX, Titanium Server, and the Wind River logo are trademarks of Wind River Systems, Inc. Any third‑party trademarks referenced are the property of their respective owners. For further
information regarding Wind River trademarks, please see:

www.windriver.com/company/terms/trademark.html

This product may include software licensed to Wind River by third parties. Relevant notices (if any) are provided for your production the Wind River download and installation portal, Wind Share:

windshare.windriver.com

Wind River may refer to third‑party documentation by listing publications or providing links to third‑party websites for informational purposes. Wind River accepts no responsibility for the information provided in such third‑party documentation.

# Corporate Headquarters
Wind River

500 Wind River Way

Alameda, CA 94501‑1153

U.S.A.

Toll free (U.S.A.): +1‑800‑545‑WIND

Telephone: +1‑510‑748‑4100

Facsimile: +1‑510‑749‑2010

For additional contact information, see the Wind River website:

www.windriver.com

For information on how to contact Customer Support, see:

www.windriver.com/support

# Introduction

## Purpose and scope
This document contains and describes all the WRCP ATP test cases which need to be performed when WRCP platform has been installed, configured and is ready for application onboarding.

## Arthure and owner
PS_EMEA CLOAD TEAM.

## ATP test cases

### 3.2.1 Validate the Real Time CaaS container performance and latency with 0% load

**Expected Results**
CaaS container latency with 0% load is < 20 microseconds.

**Procedure and Results**
```bash
#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available under APPENDIX-end of the document

# files needed
#	- cyclictest image(any prefered version)
#	- pod creation yaml file

#create a yaml file with the following content
apiVersion: v1
kind: Pod
metadata:
  name: cyclictest
spec:
  containers:
  - name: cyclictest
    image: registry.local:9001/ps_emea/cyclictest:v2.1 
    imagePullPolicy: IfNotPresent
    command: ["/bin/bash", "-ec", "sleep infinity"]
    securityContext:
      privileged: true
      capabilities:
        add:
        - SYS_NICE
        - IPC_LOCK
    resources:
      requests:
        windriver.com/isolcpus: 12
        memory: "4Gi"
      limits:
        windriver.com/isolcpus: 12
        memory: "4Gi"
  imagePullSecrets:
    - name: registry-creds
    
#create the pod using the previously created file
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl apply -f cyclictest.yaml
pod/cyclictest created

[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pods -n default
NAME         READY   STATUS    RESTARTS   AGE
cyclictest   1/1     Running   0          8s

#check pods
[sysadmin@controller-0 wr(keystone_admin)]$ watch kubectl get pods -n default -o wide
NAME          READY   STATUS    RESTARTS   AGE   IP              NODE       NOMINATED NODE   READINESS GATES
cyclictest1   1/1     Running   0          18s   172.16.43.9     worker-0   <none>           <none>

#Executing test on worker-0
controller-0:~$
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec -it -n default cyclictest1 -- /bin/bash
[root@cyclictest1 /]#  cyclictest -p99 -n -m -d0 -t 12 -a  $(taskset -pc 1 | sed 's/.*://')  -D 10m --histofall 12
WARN: distance is ignored and set to 0, if histogram enabled
# /dev/cpu_dma_latency set to 0us
policy: fifo: loadavg: 1.57 2.10 3.39 2/1106 203          

T: 0 (  192) P:99 I:1000 C: 599995 Min:      1 Act:    1 Avg:    1 Max:      13
T: 1 (  193) P:99 I:1000 C: 599999 Min:      1 Act:    1 Avg:    1 Max:       3
T: 2 (  194) P:99 I:1000 C: 599995 Min:      1 Act:    1 Avg:    1 Max:      15
T: 3 (  195) P:99 I:1000 C: 599995 Min:      1 Act:    1 Avg:    1 Max:       7
T: 4 (  196) P:99 I:1000 C: 599995 Min:      1 Act:    1 Avg:    1 Max:       3
T: 5 (  197) P:99 I:1000 C: 599994 Min:      1 Act:    1 Avg:    1 Max:       3
T: 6 (  198) P:99 I:1000 C: 599995 Min:      1 Act:    1 Avg:    1 Max:       3
T: 7 (  199) P:99 I:1000 C: 599983 Min:      1 Act:    1 Avg:    1 Max:       2
T: 8 (  200) P:99 I:1000 C: 599983 Min:      1 Act:    1 Avg:    1 Max:       2
T: 9 (  201) P:99 I:1000 C: 599983 Min:      1 Act:    1 Avg:    1 Max:       2
T:10 (  202) P:99 I:1000 C: 599983 Min:      1 Act:    1 Avg:    1 Max:       2
T:11 (  203) P:99 I:1000 C: 599983 Min:      1 Act:    1 Avg:    1 Max:       4
# Histogram
000000 000000000000000000000000000000000000000000000000000000000000000000000000000000
000001 4954845886505093865946155909065986925759885981725917215772025980765978316916723
000002 103410011349090609005379009089001302024003001813008264022783001909002152282062
000003 001032000001000001000001000001000001000005000000000000000000000000000001001043
000004 000063000000000000000001000000000000000000000000000000000000000000000001000065
000005 000007000000000000000000000000000000000000000000000000000000000000000000000007
000006 000000000000000000000000000000000000000000000000000000000000000000000000000000
000007 000000000000000000000001000000000000000000000000000000000000000000000000000001
000008 000000000000000000000000000000000000000000000000000000000000000000000000000000
000009 000000000000000000000000000000000000000000000000000000000000000000000000000000
000010 000000000000000000000000000000000000000000000000000000000000000000000000000000
000011 000000000000000000000000000000000000000000000000000000000000000000000000000000
# Total: 000599996 000600000 000599996 000599997 000599996 000599995 000599996 000599985 000599985 000599985 000599985 000599985 007199901
# Min Latencies: 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001
# Avg Latencies: 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001
# Max Latencies: 00013 00003 00015 00007 00003 00003 00003 00002 00002 00002 00002 00004 00015
# Histogram Overflows: 00001 00000 00001 00000 00000 00000 00000 00000 00000 00000 00000 00000 00002
# Histogram Overflow at cycle number:
# Thread 0: 454965
# Thread 1:
# Thread 2: 454965
# Thread 3:
# Thread 4:
# Thread 5:
# Thread 6:
# Thread 7:
# Thread 8:
# Thread 9:
# Thread 10:
# Thread 11:

```

### 3.2.2 Validate the Real Time CaaS container performance and latency with 70% load

**Expected Results**
CaaS container latency with 70% load is < 20 microseconds.

**Procedure and Results**

```bash
#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document

# files needed
#	- cyclictest image(any prefered version)
#	- pod creation yaml file

# create a pod creation yaml file with the following content
apiVersion: v1
kind: Pod
metadata:
  name: cyclictest
spec:
  containers:
  - name: cyclictest
    image: registry.local:9001/ps_emea/cyclictest:v2.1
    imagePullPolicy: IfNotPresent
    command: ["/bin/bash", "-ec", "sleep infinity"]
    securityContext:
      privileged: true
      capabilities:
        add:
        - SYS_NICE
        - IPC_LOCK
    resources:
      requests:
        windriver.com/isolcpus: 12
        memory: "4Gi"
      limits:
        windriver.com/isolcpus: 12
        memory: "4Gi"
  imagePullSecrets:
    - name: registry-creds
    
#create the pod using the previously created file
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl apply -f cyclictest.yaml
pod/cyclictest created
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pods -n default
NAME         READY   STATUS    RESTARTS   AGE
cyclictest   1/1     Running   0          8s

#Executing test for 10m on worker-0 (where the pod was deployed)
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl exec -it -n default cyclictest -- /bin/bash
#Create the shell script to execute the 70% load that should look like this:
[root@cyclictest /]# cat stress-ng.sh                                                         
#!/bin/sh
cpu_list=$(taskset -pc 1 | sed 's/.*://' | sed 's/,/ /g')                                       
arr=($cpu_list)                                                                                 
                                                                                                
for i in ${arr[@]}; do                                                                          
  taskset -c $i stress-ng --cpu 1 --cpu-load 70 --timeout 11m &                                 
done
#Enter new sessions and connect to the pod and execute:                                                                                      
#open two parallel sessions - first start stress-ng.sh                                          
[root@cyclictest /]# ./strtress-ng.sh 
[root@cyclictest /]# stress-ng: info:  [103] dispatching hogs: 1 cpu
stress-ng: info:  [109] dispatching hogs: 1 cpu
stress-ng: info:  [111] dispatching hogs: 1 cpu
stress-ng: info:  [102] dispatching hogs: 1 cpu
stress-ng: info:  [101] dispatching hogs: 1 cpu
stress-ng: info:  [105] dispatching hogs: 1 cpu
stress-ng: info:  [108] dispatching hogs: 1 cpu
stress-ng: info:  [107] dispatching hogs: 1 cpu
stress-ng: info:  [112] dispatching hogs: 1 cpu
stress-ng: info:  [106] dispatching hogs: 1 cpu
stress-ng: info:  [110] dispatching hogs: 1 cpu
stress-ng: info:  [104] dispatching hogs: 1 cpu
stress-ng: info:  [104] successful run completed in 660.00s (11 mins, 0.00 secs)
stress-ng: info:  [110] successful run completed in 660.00s (11 mins, 0.00 secs)
stress-ng: info:  [111] successful run completed in 660.06s (11 mins, 0.06 secs)
stress-ng: info:  [105] successful run completed in 660.06s (11 mins, 0.06 secs)
stress-ng: info:  [112] successful run completed in 660.08s (11 mins, 0.08 secs)
stress-ng: info:  [106] successful run completed in 660.08s (11 mins, 0.08 secs)
stress-ng: info:  [108] successful run completed in 660.09s (11 mins, 0.09 secs)
stress-ng: info:  [102] successful run completed in 660.09s (11 mins, 0.09 secs)
stress-ng: info:  [103] successful run completed in 660.10s (11 mins, 0.10 secs)
stress-ng: info:  [109] successful run completed in 660.10s (11 mins, 0.10 secs)
stress-ng: info:  [107] successful run completed in 660.16s (11 mins, 0.16 secs)
stress-ng: info:  [101] successful run completed in 660.16s (11 mins, 0.16 secs)             
#on the second parallel session execute:
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec -it -n default cyclictest1 -- /bin/bash
[root@cyclictest1 /]#  cyclictest -p99 -n -m -d0 -t 12 -a  $(taskset -pc 1 | sed 's/.*://')  -D 10m --histofall 12
#Result of Max Latencies should be less than 20 microseconds (00020)
# Histogram
000000 000000   000000  000000  000000  000000  000000  000000  000000  000000  000000  000000  000000  000000
000001 013095   112625  104820  139172  163024  101102  134197  175276  169272  169006  168968  173517  1624074
000002 292056   293533  230372  181507  242397  282835  298191  321630  243942  243095  242911  215472  3087941
000003 291082   182912  253149  271023  183112  203798  167225  102681  170309  170124  170504  193368  2359287
000004 003528   010458  010225  008287  009849  009560  000369  000395  013639  011168  012537  013553  103568
000005 000226   000471  001433  000007  001608  002694  000012  000004  002815  006567  005060  004058  024955
000006 000008   000001  000001  000000  000004  000004  000000  000000  000005  000017  000001  000015  000056
000007 000000   000000  000000  000000  000001  000000  000000  000000  000000  000001  000001  000000  000003
000008 000000   000000  000000  000000  000000  000000  000000  000000  000002  000000  000000  000001  000003
000009 000000   000000  000000  000000  000000  000000  000000  000000  000000  000001  000000  000000  000001
000010 000000   000000  000000  000000  000000  000000  000000  000000  000000  000000  000000  000000  000000
000011 000000   000000  000000  000000  000000  000000  000000  000000  000001  000002  000000  000000  000003
# Total: 000599995 000600000 000600000 000599996 000599995 000599993 000599994 000599986 000599985 000599981 000599982 000599984 007199891
# Min Latencies: 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001 00001
# Avg Latencies: 00002 00002 00002 00002 00002 00002 00002 00001 00002 00002 00002 00002
# Max Latencies: 00014 00006 00006 00005 00007 00015 00015 00005 00011 00017 00017 00015 00017 # < 00020
# Histogram Overflows: 00001 00000 00000 00000 00000 00001 00001 00000 00000 00004 00003 00001 00011
# Histogram Overflow at cycle number:
# Thread 0: 281480
# Thread 1:
# Thread 2:
# Thread 3:
# Thread 4:
# Thread 5: 458543
# Thread 6: 471667
# Thread 7:
# Thread 8:
# Thread 9: 79661 224259 230356 402071
# Thread 10: 99954 320324 578160
# Thread 11: 367005

#While the test is running
#Enter new sessions and connect to the pod and execute/check top to see the cpus usage going up to 70%
top - 11:03:14 up 20:07,  3 users,  load average: 16.90, 17.39, 13.59
Tasks: 1662 total,   4 running, 1275 sleeping,   0 stopped,   0 zombie
%Cpu0  : 78.5 us, 17.5 sy,  0.0 ni,  3.0 id,  0.0 wa,  0.0 hi,  1.0 si,  0.0 st
%Cpu1  : 70.3 us,  0.7 sy,  0.0 ni, 29.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
%Cpu2  : 63.7 us, 25.0 sy,  0.0 ni, 10.3 id,  0.0 wa,  0.0 hi,  1.0 si,  0.0 st
...
```

### 3.2.3 Validate GPS accuracy of LLS-C1

**Expected Results**

GPS  accuracy of LLS-C1 meets the crieteria of the O-RAN 

**Procedure and Results**

```bash
#Connec to any node configured for using PTP and execute the following command
controller-0:~$ sudo cat /sys/kernel/debug/ice/0000:51:00.0/cgu
Found ZL80032 CGU
DPLL Config ver: 1.3.0.1

CGU Input status:
                   |            |      priority     |
      input (idx)  |    state   | EEC (0) | PPS (1) |
  ---------------------------------------------------
     CVL-SDP22 (0) |    invalid |       8 |       8 |
     CVL-SDP20 (1) |    invalid |      15 |       3 |
  C827_0-RCLKA (2) | validating |       4 |       4 |
  C827_0-RCLKB (3) |    invalid |       5 |       5 |
          SMA1 (4) |    invalid |       1 |       1 |
    SMA2/U.FL2 (5) |    invalid |       2 |       2 |
     GNSS-1PPS (6) |      valid |       0 |       0 |

EEC DPLL:
        Current reference:      GNSS-1PPS
        Status:                 locked_ho_ack # traffic is locked

PPS DPLL:
        Current reference:      GNSS-1PPS
        Status:                 locked_ho_ack # traffic is locked
        Phase offset:                   251
        
#Expected result is that 
EEC DPLL:
        Current reference:      GNSS-1PPS
        Status:                 locked_ho_ack # traffic is locked

PPS DPLL:
        Current reference:      GNSS-1PPS
        Status:                 locked_ho_ack # traffic is locked

```
### 3.2.4 Validate PTP accuracy of LLS-C1 in T-GM

**Expected Results**

PTP packets are send out on data ports

**Procedure and Results**

```bash
sudo cat /sys/kernel/debug/ice/0000:51:00.0/cgu
```

### 3.2.5 Validate the ability of platform to recover from outage

**Expected Results**

The standby  controller should take over from the Active controller after shutdown of the Active controller

**NOTE: The connection should be lost after the swact as the floating ip is assigned to the standby controller**

**Procedure and Results**
```bash
# active controller -> controller-0
# standby controller -> controller-1
# Check the sm services on controller-1 before controller-0 (active controller) is powerd off.
controller-1:~$ sudo sm-dump
#notice services are on standby
-Service_Groups------------------------------------------------------------------------
oam-services                     standby              standby                        
controller-services              standby              standby                        
cloud-services                   standby              standby                        
patching-services                standby              standby                        
directory-services               active               active                         
web-services                     active               active                         
storage-services                 active               active                         
storage-monitoring-services      standby              standby                        
vim-services                     standby              standby                        
distributed-cloud-services       standby              standby                        
---------------------------------------------------------------------------------------
#notice services are enabled-standby and/or disabled
-Services------------------------------------------------------------------------------
oam-ip                           enabled-standby      disabled                        
management-ip                    enabled-standby      disabled                        
drbd-pg                          enabled-standby      enabled-standby                 
drbd-rabbit                      enabled-standby      enabled-standby                 
drbd-platform                    enabled-standby      enabled-standby                 
pg-fs                            enabled-standby      disabled                        
rabbit-fs                        enabled-standby      disabled                        
nfs-mgmt                         enabled-standby      disabled                        
platform-fs                      enabled-standby      disabled                        
postgres                         enabled-standby      disabled                        
rabbit                           enabled-standby      disabled                        
platform-export-fs               enabled-standby      disabled                        
platform-nfs-ip                  enabled-standby      disabled                        
sysinv-inv                       enabled-standby      disabled                        
sysinv-conductor                 enabled-standby      disabled                        
mtc-agent                        enabled-standby      disabled                        
hw-mon                           enabled-standby      disabled                        
dnsmasq                          enabled-standby      disabled                        
fm-mgr                           enabled-standby      disabled                        
keystone                         enabled-standby      disabled                        
lighttpd                         enabled-active       enabled-active                  
patch-alarm-manager              enabled-standby      disabled                        
mgr-restful-plugin               enabled-active       enabled-active                  
ceph-manager                     enabled-standby      disabled                        
vim                              enabled-standby      disabled                        
vim-api                          enabled-standby      disabled                        
vim-webserver                    enabled-standby      disabled                        
haproxy                          enabled-standby      disabled                        
pxeboot-ip                       enabled-standby      disabled                        
drbd-extension                   enabled-standby      enabled-standby                 
extension-fs                     enabled-standby      disabled                        
extension-export-fs              enabled-standby      disabled                        
etcd                             enabled-standby      disabled                        
drbd-etcd                        enabled-standby      enabled-standby                 
etcd-fs                          enabled-standby      disabled                        
barbican-api                     enabled-standby      disabled                        
barbican-keystone-listener       enabled-standby      disabled                        
barbican-worker                  enabled-standby      disabled                        
cluster-host-ip                  enabled-standby      disabled                        
dcdbsync-api                     enabled-standby      disabled                        
docker-distribution              enabled-standby      disabled                        
dockerdistribution-fs            enabled-standby      disabled                        
drbd-dockerdistribution          enabled-standby      enabled-standby                 
ceph-mon                         enabled-standby      disabled                        
cephmon-fs                       enabled-standby      disabled                        
drbd-cephmon                     enabled-standby      enabled-standby                 
ceph-osd                         enabled-active       enabled-active                  
helmrepository-fs                enabled-standby      disabled                        
registry-token-server            enabled-standby      disabled                        
cert-mon                         enabled-standby      disabled                        
device-image-fs                  enabled-standby      disabled                        
cert-alarm                       enabled-standby      disabled                        
------------------------------------------------------------------------------
 #Poweroff the server directly from the BMC console or unplug the power cable and  check if the services are up on other standby controller.
 [sysadmin@controller-1 ~(keystone_admin)]$ system host-list
 +----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | disabled    | offline      |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

# The SSH connection should be disconnected and when logged in back using the floating ip, controller-1 should be u'Controller-Active'
 
[sysadmin@controller-1 ~(keystone_admin)]$ system host-show controller-1

 +-----------------------+----------------------------------------------------------------------+
| Property              | Value                                                                |
+-----------------------+----------------------------------------------------------------------+
| action                | none                                                                 |
| administrative        | unlocked                                                             |
| availability          | available                                                            |
| bm_ip                 | 192.168.110.34                                                       |
| bm_type               | redfish                                                              |
| bm_username           | root                                                                 |
| boot_device           | /dev/sda                                                             |
| capabilities          | {u'stor_function': u'monitor', u'Personality': u'Controller-Active'} |
| clock_synchronization | ntp                                                                  |
| config_applied        | 01d7fe19-6129-4c2a-966b-51465fdcbfcf                                 |
| config_status         | None                                                                 |
| config_target         | 01d7fe19-6129-4c2a-966b-51465fdcbfcf                                 |
| console               | ttyS0,115200                                                         |
| created_at            | 2022-04-18T22:21:05.096702+00:00                                     |
| device_image_update   | None                                                                 |
| hostname              | controller-1                                                         |
| id                    | 2                                                                    |
| install_output        | text                                                                 |
| install_state         | completed                                                            |
| install_state_info    | None                                                                 |
| inv_state             | inventoried                                                          |
| invprovision          | provisioned                                                          |
| location              | {}                                                                   |
| mgmt_ip               | 11.11.11.36                                                          |
| mgmt_mac              | 40:a6:b7:2c:41:48                                                    |
| operational           | enabled                                                              |
| personality           | controller                                                           |
| reboot_needed         | False                                                                |
| reserved              | False                                                                |
| rootfs_device         | /dev/sda                                                             |
| serialid              | None                                                                 |
| software_load         | 21.12                                                                |
| subfunction_avail     | available                                                            |
| subfunction_oper      | enabled                                                              |
| subfunctions          | controller,worker,lowlatency                                         |
| task                  |                                                                      |
| tboot                 | false                                                                |
| ttys_dcd              | None                                                                 |
| updated_at            | 2022-05-05T07:54:16.870273+00:00                                     |
| uptime                | 29613                                                                |
| uuid                  | 681202c2-7ed0-4cb1-a9f0-2a3744a01493                                 |
| vim_progress_status   | services-enabled                                                     |
+-----------------------+----------------------------------------------------------------------+

# Check the sm services status on controller-1
 [sysadmin@controller-1 ~(keystone_admin)]$  sudo sm-dump
#notice services are active
 -Service_Groups------------------------------------------------------------------------
oam-services                     active               active
controller-services              active               active
cloud-services                   active               active
patching-services                active               active
directory-services               active               active
web-services                     active               active
storage-services                 active               active
storage-monitoring-services      active               active
vim-services                     active               active
distributed-cloud-services       active               active
---------------------------------------------------------------------------------------
#notice services are enabled-active
-Services------------------------------------------------------------------------------
oam-ip                           enabled-active       enabled-active
management-ip                    enabled-active       enabled-active
drbd-pg                          enabled-active       enabled-active
drbd-rabbit                      enabled-active       enabled-active
drbd-platform                    enabled-active       enabled-active
pg-fs                            enabled-active       enabled-active
rabbit-fs                        enabled-active       enabled-active
nfs-mgmt                         enabled-active       enabled-active
platform-fs                      enabled-active       enabled-active
postgres                         enabled-active       enabled-active
rabbit                           enabled-active       enabled-active
platform-export-fs               enabled-active       enabled-active
platform-nfs-ip                  enabled-active       enabled-active
sysinv-inv                       enabled-active       enabled-active
sysinv-conductor                 enabled-active       enabled-active
mtc-agent                        enabled-active       enabled-active
hw-mon                           enabled-active       enabled-active
dnsmasq                          enabled-active       enabled-active
fm-mgr                           enabled-active       enabled-active
keystone                         enabled-active       enabled-active
lighttpd                         enabled-active       enabled-active
patch-alarm-manager              enabled-active       enabled-active
mgr-restful-plugin               enabled-active       enabled-active
ceph-manager                     enabled-active       enabled-active
vim                              enabled-active       enabled-active
vim-api                          enabled-active       enabled-active
vim-webserver                    enabled-active       enabled-active
haproxy                          enabled-active       enabled-active
pxeboot-ip                       enabled-active       enabled-active
drbd-extension                   enabled-active       enabled-active
extension-fs                     enabled-active       enabled-active
extension-export-fs              enabled-active       enabled-active
etcd                             enabled-active       enabled-active
drbd-etcd                        enabled-active       enabled-active
etcd-fs                          enabled-active       enabled-active
barbican-api                     enabled-active       enabled-active
barbican-keystone-listener       enabled-active       enabled-active
barbican-worker                  enabled-active       enabled-active
cluster-host-ip                  enabled-active       enabled-active
dcdbsync-api                     enabled-active       enabled-active
docker-distribution              enabled-active       enabled-active
dockerdistribution-fs            enabled-active       enabled-active
drbd-dockerdistribution          enabled-active       enabled-active
ceph-mon                         enabled-active       enabled-active
cephmon-fs                       enabled-active       enabled-active
drbd-cephmon                     enabled-active       enabled-active
ceph-osd                         enabled-active       enabled-active
helmrepository-fs                enabled-active       enabled-active
registry-token-server            enabled-active       enabled-active
cert-mon                         enabled-active       enabled-active
device-image-fs                  enabled-active       enabled-active
cert-alarm                       enabled-active       enabled-active
------------------------------------------------------------------------------
#notice controller-0 comming back to enabled-available state after restart/power-on
 [sysadmin@controller-1 ~(keystone_admin)]$  watch system host-list
 +----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+
```


### 3.2.6 Validate the ability of platform to support SR-IOV Network device plugin SRIOV-MACVLAN

**Description**
Validate the functionality of the SRIOV netdevice vf by creating two pods communication with oneanother. 

**Expected Results**

Virtual Function of the physical nic is seen from the pod as a second interface

**Procedure and Results**
```bash
#download and copy the image to the subcloud active controller - centos image used for this test
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret
#steps available APPENDIX-end of the document

# files needed
#	- centos image(or any other prefered os or version)
#	- network attachment and pod creation yaml file

# create or select an already existing sriov net device 
[sysadmin@controller-0 wr(keystone_admin)]$ system host-if-show 1 fh1com
+------------------+--------------------------------------+
| Property         | Value                                |
+------------------+--------------------------------------+
| ifname           | fh1com                               |
| iftype           | ethernet                             |
| ports            | [u'enp81s0f2']                       |
| imac             | 50:7c:6f:01:67:3e                    |
| imtu             | 9000                                 |
| ifclass          | pci-sriov                            |
| ptp_role         | none                                 |
| aemode           | None                                 |
| schedpolicy      | None                                 |
| txhashpolicy     | None                                 |
| primary_reselect | None                                 |
| uuid             | 621a75b6-cb99-4ee2-b7a7-6f6a55018231 |
| ihost_uuid       | 42156cd5-72b6-4b51-94d2-c18bdc76e211 |
| vlan_id          | None                                 |
| uses             | []                                   |
| used_by          | [u'fh1m', u'fh1']                    |
| created_at       |                                      |
| updated_at       |                                      |
| sriov_numvfs     | 8                                    |
| sriov_vf_driver  | netdevice                            |
| max_tx_rate      | None                                 |
| accelerated      | [False]                              |
+------------------+--------------------------------------+
#Create a deploy file 
[sysadmin@controller-0 wr(keystone_admin)]$ vim sriov-test.yaml
################Static SRIOV configuration for the first pod #################
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-static-pod
  annotations:
    k8s.v1.cni.cncf.io/resourceName: intel.com/pci_sriov_net_fh1com
spec:
  config: '{
  "type": "sriov",
  "vlan": 1500,
  "ipam": {
     "type": "static",
     "addresses": [ { "address": "25.25.25.12/24" } ]
  }
}'


######### 1st pod configuration ############
# net1: static 25.25.25.x
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod-sriov
  annotations:
    k8s.v1.cni.cncf.io/networks:  sriov-static-pod

spec:
  containers:
  - name: test-pod-sriov
    image:  registry.local:9001/ps_emea/centos:v22
    imagePullPolicy: IfNotPresent
    command: [ "/bin/bash", "-c", "--" ]
    args: [ "while true; do sleep 300000; done;" ]
    securityContext:
      privileged: true
      capabilities:
        add:
        - ALL
    resources:
      requests:
        windriver.com/isocpus: 2
        memory: 4Gi
        intel.com/pci_sriov_net_fh1com: '1'
      limits:
        windriver.com/isocpus: 2
        hugepages-1Gi: 2Gi
        memory: 4Gi
        intel.com/pci_sriov_net_fh1com: '1'
  imagePullSecrets:
    - name: registry-creds

  nodeName: controller-0
---
#########Second SRIOV configuration for the second pod #################
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-static-pod2
  annotations:
    k8s.v1.cni.cncf.io/resourceName: intel.com/pci_sriov_net_fh1com
spec:
  config: '{
  "type": "sriov",
  "vlan": 1500,
  "ipam": {
     "type": "static",
     "addresses": [ { "address": "25.25.25.24/24" } ]
  }
}'


######### 2nd pod configuration ############
# net1: static 25.25.25.x
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod-sriov2
  annotations:
    k8s.v1.cni.cncf.io/networks:  sriov-static-pod2

spec:
  containers:
  - name: test-pod-sriov2
    image:  registry.local:9001/ps_emea/centos:v22
    imagePullPolicy: IfNotPresent
    command: [ "/bin/bash", "-c", "--" ]
    args: [ "while true; do sleep 300000; done;" ]
    securityContext:
      privileged: true
      capabilities:
        add:
        - ALL
    resources:
      requests:
        windriver.com/isocpus: 2
        memory: 4Gi
        intel.com/pci_sriov_net_fh1com: '1'
      limits:
        windriver.com/isocpus: 2
        hugepages-1Gi: 2Gi
        memory: 4Gi
        intel.com/pci_sriov_net_fh1com: '1'
  imagePullSecrets:
    - name: registry-creds

  nodeName: controller-0
---
#create the network attachemts and the pods
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl apply -f sriov-test.yaml
networkattachmentdefinition.k8s.cni.cncf.io/sriov-static-pod unchanged
pod/test-pod-sriov configured
networkattachmentdefinition.k8s.cni.cncf.io/sriov-static-pod2 unchanged
pod/test-pod-sriov2 configured
#check pod status
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pods -n default
NAME              READY   STATUS    RESTARTS   AGE
test-pod-sriov    1/1     Running   0          3m49s
test-pod-sriov2   1/1     Running   0          3m49s
#check network attachment status
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get network-attachment-definitions.k8s.cni.cncf.io -n default
NAME                AGE
sriov-static-pod    4m
sriov-static-pod2   4m

#connect on the first pod
controller-0:/opt/backups/wr$  kubectl exec -it -n default test-pod-sriov -- /bin/bash
#check the pod network configuration
[root@test-pod-sriov /]# ip a                                                                                           
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000                             
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00                                                               
    inet 127.0.0.1/8 scope host lo                                                                                      
       valid_lft forever preferred_lft forever                                                                          
    inet6 ::1/128 scope host                                                                                            
       valid_lft forever preferred_lft forever                                                                          
3: eth0@if612: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default                          
    link/ether 0e:06:ff:8c:b9:0f brd ff:ff:ff:ff:ff:ff link-netnsid 0                                                   
    inet 172.16.192.79/32 brd 172.16.192.79 scope global eth0                                                           
       valid_lft forever preferred_lft forever                                                                          
    inet6 fe80::c06:ffff:fe8c:b90f/64 scope link                                                                        
       valid_lft forever preferred_lft forever                                                                          
40: net1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000                          
    link/ether 96:70:a0:2e:86:6e brd ff:ff:ff:ff:ff:ff                                                                  
    inet 25.25.25.12/24 brd 25.25.25.255 scope global net1                                                              
       valid_lft forever preferred_lft forever                                                                          
    inet6 fe80::9470:a0ff:fe2e:866e/64 scope link                                                                       
       valid_lft forever preferred_lft forever
#ping the second pod ip                                                                          
[root@test-pod-sriov /]# ping 25.25.25.24 -c 6                                                                          
PING 25.25.25.24 (25.25.25.24) 56(84) bytes of data.                                                                    
64 bytes from 25.25.25.24: icmp_seq=1 ttl=64 time=0.028 ms                                                              
64 bytes from 25.25.25.24: icmp_seq=2 ttl=64 time=0.029 ms                                                              
64 bytes from 25.25.25.24: icmp_seq=3 ttl=64 time=0.025 ms                                                              
64 bytes from 25.25.25.24: icmp_seq=4 ttl=64 time=0.026 ms                                                              
64 bytes from 25.25.25.24: icmp_seq=5 ttl=64 time=0.026 ms                                                              
64 bytes from 25.25.25.24: icmp_seq=6 ttl=64 time=0.030 ms                                                              

--- 25.25.25.24 ping statistics ---
6 packets transmitted, 6 received, 0% packet loss, time 5132ms                                  
rtt min/avg/max/mdev = 0.025/0.027/0.030/0.004 ms

#check the environment                   
[root@test-pod-sriov /]# env                                                                                
LANG=en_US.UTF-8                                                                                            
HOSTNAME=test-pod-sriov                                                                                     
KUBERNETES_PORT_443_TCP_PROTO=tcp                                                                           
KUBERNETES_PORT_443_TCP_ADDR=10.96.0.1                                                                      
KUBERNETES_PORT=tcp://10.96.0.1:443                                                                         
PWD=/                                                                                                       
HOME=/root                                                                                                  
KUBERNETES_SERVICE_PORT_HTTPS=443                                                                           
KUBERNETES_PORT_443_TCP_PORT=443                                                                            
KUBERNETES_PORT_443_TCP=tcp://10.96.0.1:443                                                                 
TERM=xterm                                                                                                  
PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_FH1COM=0000:51:11.0                                                       
SHLVL=1                                                                                                     
KUBERNETES_SERVICE_PORT=443                                                                                 
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin                                           
KUBERNETES_SERVICE_HOST=10.96.0.1                                                                           
LESSOPEN=||/usr/bin/lesspipe.sh %s                                                                          
_=/usr/bin/env                        
#confirm the pci interface used                                                                      
[root@test-pod-sriov /]# env | grep PCI
PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_FH1COM=0000:51:11.0

#connect on the second pod
controller-0:/opt/backups/wr$ kubectl exec -it -n default test-pod-sriov2 -- /bin/bash
#check the pod network configuration
[root@test-pod-sriov2 /]# ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
    valid_lft forever preferred_lft forever
3: eth0@if613: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default
    link/ether be:83:e7:82:40:3a brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 172.16.192.80/32 brd 172.16.192.80 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::bc83:e7ff:fe82:403a/64 scope link
       valid_lft forever preferred_lft forever
43: net1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 66:ca:87:6b:e2:dd brd ff:ff:ff:ff:ff:ff
    inet 25.25.25.24/24 brd 25.25.25.255 scope global net1
       valid_lft forever preferred_lft forever
    inet6 fe80::64ca:87ff:fe6b:e2dd/64 scope link
       valid_lft forever preferred_lft forever
#ping the first pod       
[root@test-pod-sriov2 /]# ping 25.25.25.12 -c 6
PING 25.25.25.12 (25.25.25.12) 56(84) bytes of data.
64 bytes from 25.25.25.12: icmp_seq=1 ttl=64 time=0.040 ms
64 bytes from 25.25.25.12: icmp_seq=2 ttl=64 time=0.029 ms
64 bytes from 25.25.25.12: icmp_seq=3 ttl=64 time=0.028 ms
64 bytes from 25.25.25.12: icmp_seq=4 ttl=64 time=0.032 ms
64 bytes from 25.25.25.12: icmp_seq=5 ttl=64 time=0.022 ms
64 bytes from 25.25.25.12: icmp_seq=6 ttl=64 time=0.020 ms

--- 25.25.25.12 ping statistics ---
6 packets transmitted, 6 received, 0% packet loss, time 5107ms
rtt min/avg/max/mdev = 0.020/0.028/0.040/0.008 ms

#check the environment
[root@test-pod-sriov2 /]# env
LANG=en_US.UTF-8
HOSTNAME=test-pod-sriov2
KUBERNETES_PORT_443_TCP_PROTO=tcp
KUBERNETES_PORT_443_TCP_ADDR=10.96.0.1
KUBERNETES_PORT=tcp://10.96.0.1:443
PWD=/
HOME=/root
KUBERNETES_SERVICE_PORT_HTTPS=443
KUBERNETES_PORT_443_TCP_PORT=443
KUBERNETES_PORT_443_TCP=tcp://10.96.0.1:443
TERM=xterm
PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_FH1COM=0000:51:11.1
SHLVL=1
KUBERNETES_SERVICE_PORT=443
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
KUBERNETES_SERVICE_HOST=10.96.0.1
LESSOPEN=||/usr/bin/lesspipe.sh %s
_=/usr/bin/env
#confirm the PCI interface that is used on the pod
[root@test-pod-sriov2 /]# env | grep PCI
PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_FH1COM=0000:51:11.1

#exit the pods and delete them

[sysadmin@controller-0 wr(keystone_admin)]$ kubectl delete -f sriov-test.yaml
networkattachmentdefinition.k8s.cni.cncf.io "sriov-static-pod" deleted
pod "test-pod-sriov" deleted
networkattachmentdefinition.k8s.cni.cncf.io "sriov-static-pod2" deleted
pod "test-pod-sriov2" deleted


```

### 3.2.7 Validate the platform’s ability to provide Zero-Touch Deployment/Provisioning for CaaS Manager (System Controller)

**Expected Results**

The cluster should be installed using the zero touch Deployment (Without Manual intervention) with the help of Caas Manager and Deploy config file.

**Files Required**
- bootstrap.yaml -> dx-bootstrap-config_CFI_XR11.yaml
- install-values.yaml -> dx-install-config_CFI_XR11.yaml
- /usr/local/share/applications/helm/wind-river-cloud-platform-deployment-manager-x.x.x.tgz 
- /usr/local/share/applications/playbooks/wind-river-cloud-platform-deployment-manager.yaml 
- /usr/local/share/applications/overrides/wind-river-cloud-platform-deployment-manageroverrides.yaml 
- /usr/local/share/applications/overrides/wind-river-cloud-platform-deployment-manager-overridessubcloud.yaml 
- localhost.yml 
- deployment-config.yaml. (This file will be generated on installed platform using the deploy tool) 
- setup.sh 
- master-bootstrap-and-deploy-playbook.yaml 
- dm-helm-overrides.yaml 
- dm-playbook-overrides.yaml 
- registry.ca 

**Procedure and Results**
```bash
#On the CaaS manager controller get the docker registry password:
Description: Verify that the CaaS-manager site can be deployed using deployment manager.  

Expected Results: The CaaS manager site should be installed using installation iso and should be bootstrapped and deployed using deployment manager. 

Files Required  
 

Procedure and Results: 
# Power on the first controller (controller-0) and start the installation using installation iso 
      # the standard installation procedure.  

# ZTP installation. 
required files 

    ca.crt 
    deployment-config.yaml 
    dm-helm-overrides.yaml 
    dm-playbook-overrides.yaml 
    localhost.yml 
    master-bootstrap-and-deploy-playbook.yaml 
    setup.sh 
    wind-river-cloud-platform-deployment-manager-2.0.8-1.tgz (if version 21.12 patch2 iso is installed) 
    wind-river-cloud-platform-deployment-manager-playbook.yaml (if version 21.12 patch2 iso is installed) 
    wr.lic 
    wind-river-cloud-platform-host-installer-21.12-b45-PATCH_0002.sig 
    wind-river-cloud-platform-host-installer-21.12-b45-PATCH_0002.iso  

#connect on the host and configure the network as per the standard procedure before bootstrapping on the oam dedicated port 

localhost:~$ ip link add link ens2f0 name ens2f0.12 type vlan id 12 
localhost:~$ ip link set ens2f0.12 up 
localhost:~$ ip addr add 128.224.212.80/24 dev ens2f0.12 
localhost:~$ ip route add default via 128.224.212.1 dev ens2f0.12 

#copy the necessary files on the node. 
#where: 

    localhost.yml is the controller-0 bootstrap file. 
    deployment-config.yaml is the caas manager configuration for both controller-0/1 (generated with the deploy tool during backup) 
    ca.crt is the private harbor registry certificate (mentioned in the localhost.yml as well) 
    wr.lic is the active license (the deployment-config file contains license information as well) 
    wind-river-cloud-platform-host-installer-21.12-b45-PATCH_0002.iso 
    wind-river-cloud-platform-host-installer-21.12-b45-PATCH_0002.sig 

#additional files to copy/create on the node: 
#download from delivers.windriver.com for 21.12 PATCH 2: patches -> deployment-manager-2.0.8-1 (only if using 21.12 version) 

    wind-river-cloud-platform-deployment-manager.yaml    
    wind-river-cloud-platform-deployment-manager-2.0.8-1.tgz 	 

#copy after download to /home/sysadmin 
#create additional files 

    dm-heml-overrides.yaml 		    			(created locally) 
    dm-playbook-overrides.yaml   				(created locally) 
    master-bootstrap-and-deploy-playbook.yaml   		(created locally) 
    setup.sh 						(created locally) 

#prepare for platform reinstallation 
#create the files: 
#setup.sh must have the following content 

localhost:~$ cat setup.sh  

#!/bin/bash 

ANSIBLE_LOG_PATH=~/ansible_$(date "+%Y%m%d%H%M%S").log ansible-playbook /home/sysadmin/master-bootstrap-and-deploy-playbook.yaml -e "@/home/sysadmin/dm-playbook-overrides.yaml" 

#dm-helm-overrides.yaml should contain the following information 
IMPORTANT: image version must be relevant for the installing version - in this test 21.12 Patch 2 iso 

localhost:~$ cat dm-helm-overrides.yaml  

manager:  
   image:  
      repository: registry.local:9001/docker.io/wind-river/cloud-platform-deployment-manager  
      tag: WRCP_21.12  
      pullPolicy: IfNotPresent   

rbacProxy:  
   image: registry.local:9001/gcr.io/kubebuilder/kube-rbac-proxy:v0.4.0  
   pullPolicy: IfNotPresent 

#dm-playbook-overrides.yaml must contain the following info 
IMPORTANT: image version must be relevant for the installation version - in this test 21.12 Patch 2 iso 

localhost:~$ cat dm-playbook-overrides.yaml  
--- 
deployment_config: /home/sysadmin/deployment-config.yaml 
deployment_manager_overrides: /home/sysadmin/dm-helm-overrides.yaml 
deployment_manager_chart: /home/sysadmin/wind-river-cloud-platform-deployment-manager-2.0.8-1.tgz 
ansible_become_pass: 'password' 

#master-bootstrap-and-deploy-playbook.yaml must contain: 

localhost:~$ cat master-bootstrap-and-deploy-playbook.yaml  
- import_playbook: /usr/share/ansible/stx-ansible/playbooks/bootstrap.yml 
- import_playbook: /home/sysadmin/wind-river-cloud-platform-deployment-manager-playbook.yaml 

#confirm that you have all these files in /home/sysadmin 
    ca.crt 
    deployment-config.yaml 
    dm-helm-overrides.yaml 
    dm-playbook-overrides.yaml 
    localhost.yml 
    master-bootstrap-and-deploy-playbook.yaml 
    setup.sh 
    wind-river-cloud-platform-deployment-manager-2.0.8-1.tgz 
    wind-river-cloud-platform-deployment-manager-playbook.yaml 
    wr.lic 
    wind-river-cloud-platform-host-installer-21.12-b45-PATCH_0002.sig 
    wind-river-cloud-platform-host-installer-21.12-b45-PATCH_0002.iso  

#confirm you can ping/resolve the harbor registry 

localhost:~$ ping harbor.kista.wrs.local -c 3 
PING harbor.kista.wrs.local (128.224.212.144) 56(84) bytes of data. 
64 bytes from 128.224.212.144 (128.224.212.144): icmp_seq=1 ttl=64 time=0.187 ms 
64 bytes from 128.224.212.144 (128.224.212.144): icmp_seq=2 ttl=64 time=0.230 ms 
64 bytes from 128.224.212.144 (128.224.212.144): icmp_seq=3 ttl=64 time=0.170 ms 
--- harbor.kista.wrs.local ping statistics --- 
3 packets transmitted, 3 received, 0% packet loss, time 2036ms 
rtt min/avg/max/mdev = 0.170/0.195/0.230/0.029 ms 

# we can now use automation to bootstrap and configure the caas-manager site. 
# run the setup.sh 

localhost$ screen –S reinstall 
localhost$ ./setup.sh 

# expected output of the ansible log: 

PLAY RECAP ******************************************************************************************************************** 
localhost                  : ok=430  changed=241  unreachable=0    failed=0    
Wednesday 22 June 2022  19:59:48 +0200 (0:00:00.472)       0:35:48.574 ******** ===========================================================  
bootstrap/apply-manifest : Applying puppet bootstrap manifest -------------------------------------------- 307.86s 
bootstrap/persist-config : Wait for service endpoints reconfiguration to complete ------------------------ 298.72s 
bootstrap/bringup-essential-services : Wait for 120 seconds to ensure kube-system pods are all started --- 120.33s 
bootstrap/bringup-bootstrap-applications : Wait until application is in the applied state ---------------- 117.36s 
bootstrap/persist-config : Wait for sysinv inventory ------------------------------------------------------ 57.28s 
bootstrap/persist-config : Saving config in sysinv database ----------------------------------------------- 54.69s 
bootstrap/bringup-bootstrap-applications : pause ---------------------------------------------------------- 30.04s 
bootstrap/bringup-bootstrap-applications : Wait until application is in the applied state ----------------- 25.75s 
bootstrap/persist-config : Find old registry secrets in Barbican ------------------------------------------ 22.92s 
bootstrap/bringup-essential-services : Initializing Kubernetes master ------------------------------------- 22.77s 
bootstrap/persist-config : Wait for system controller database configuration to complete ------------------ 19.24s 
bootstrap/bringup-essential-services : Add loopback interface --------------------------------------------- 14.84s 
bootstrap/validate-config : Generate config ini file for python sysinv db population script --------------- 13.02s 
bootstrap/bringup-essential-services : Check controller-0 is in online state ------------------------------ 10.78s 
bootstrap/bringup-bootstrap-applications : Wait until application is in the uploaded state ---------------- 10.69s 
bootstrap/bringup-bootstrap-applications : Wait until application is in the uploaded state----------------- 10.67s 
wait_for -------------------------------------------------------------------------------------------------- 10.20s 
bootstrap/bringup-essential-services : Start parallel tasks to wait for Kubernetes component and Networking pods to reach ready state 
----------------------------------------------------------------------------------------- 7.79s 
bootstrap/bringup-bootstrap-applications : Save the current system and network config for reference in subsequent replays 
--------------------------------------------------------------------------------------------------- 7.05s 
bootstrap/bringup-essential-services : Activate Calico Networking ----------------------------------------- 6.98s 

localhost:~$   

# After bootstrapping the node now controller-0 will be automatically configured/rebooted 
#controller-1 will now be automatically booted via pxe and installed/configured 

#connect back to the node via ssh and observe the status 

controller-0:~$ uptime 
20:12:55 up 9 min,  1 user,  load average: 6,13, 1,96, 0,77 
controller-0:~$ date 
miercuri 22 iunie 2022, 20:12:56 +0200 
controller-0:~$ . /etc/platform/openrc  
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list  

+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | locked         | disabled    | power-off    | 
+----+--------------+-------------+----------------+-------------+--------------+ 

#observe the first controller status:  

[sysadmin@controller-0 ~(keystone_admin)]$ system host-show controller-0 

+-----------------------+----------------------------------------------------------------------+ 
| Property              | Value                                                                | 
+-----------------------+----------------------------------------------------------------------+ 
| action                | none                                                                 | 
| administrative        | unlocked                                                             | 
| availability          | available                                                            | 
| bm_ip                 | 128.224.210.13                                                       | 
| bm_type               | dynamic                                                              | 
| bm_username           | admin                                                                | 
| boot_device           | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6744567a000-lun-0      | 
| capabilities          | {u'stor_function': u'monitor', u'Personality': u'Controller-Active'} | 
| clock_synchronization | ntp                                                                  | 
| config_applied        | 50cf3192-9d12-44cc-a52f-97500fc975f5                                 | 
| config_status         | Config out-of-date                                                   | 
| config_target         | 04d891f6-7ade-4f77-81de-9114cf025840                                 | 
| console               | tty0                                                                 | 
| created_at            | 2022-06-22T19:31:12.511123+00:00                                     | 
| device_image_update   | None                                                                 | 
| hostname              | controller-0                                                         | 
| id                    | 1                                                                    | 
| install_output        | text                                                                 | 
| install_state         | None                                                                 | 
| install_state_info    | None                                                                 | 
| inv_state             | inventoried                                                          | 
| invprovision          | provisioned                                                          | 
| location              | {}                                                                   | 
| mgmt_ip               | 192.168.30.21                                                        | 
| mgmt_mac              | 00:1e:67:44:56:7a                                                    | 
| operational           | enabled                                                              | 
| personality           | controller                                                           | 
| reboot_needed         | False                                                                | 
| reserved              | False                                                                | 
| rootfs_device         | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6744567a000-lun-0      | 
| serialid              | None                                                                 | 
| software_load         | 21.12                                                                | 
| task                  |                                                                      | 
| tboot                 | false                                                                | 
| ttys_dcd              | None                                                                 | 
| updated_at            | 2022-06-22T20:16:17.852231+00:00                                     | 
| uptime                | 783                                                                  | 
| uuid                  | 7a288bb6-f9d7-48b4-a8a3-8a23658c572d                                 | 
| vim_progress_status   | services-enabled                                                     | 
+-----------------------+----------------------------------------------------------------------+ 

#observe the second controller being installed 

[sysadmin@controller-0 ~(keystone_admin)]$ system host-show controller-1 

+-----------------------+-----------------------------------------------------------------+ 
| Property              | Value                                                           | 
+-----------------------+-----------------------------------------------------------------+ 
| action                | none                                                            | 
| administrative        | locked                                                          | 
| availability          | offline                                                         | 
| bm_ip                 | 128.224.210.12                                                  | 
| bm_type               | dynamic                                                         | 
| bm_username           | admin                                                           | 
| boot_device           | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6762ece7000-lun-0 | 
| capabilities          | {u'Personality': u'Controller-Standby'}                         | 
| clock_synchronization | ntp                                                             | 
| config_applied        | None                                                            | 
| config_status         | None                                                            | 
| config_target         | None                                                            | 
| console               | ttyS0,115200                                                    | 
| created_at            | 2022-06-22T20:13:26.663367+00:00                                | 
| device_image_update   | None                                                            | 
| hostname              | controller-1                                                    | 
| id                    | 2                                                               | 
| install_output        | graphical                                                       | 
| install_state         | None                                                            | 
| install_state_info    | None                                                            | 
| inv_state             | reinstalling                                                    | 
| invprovision          | None                                                            | 
| location              | {}                                                              | 
| mgmt_ip               | 192.168.30.22                                                   | 
| mgmt_mac              | 00:1e:67:62:ec:e7                                               | 
| operational           | disabled                                                        | 
| personality           | controller                                                      | 
| reboot_needed         | False                                                           | 
| reserved              | False                                                           | 
| rootfs_device         | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6762ece7000-lun-0 | 
| serialid              | None                                                            | 
| software_load         | 21.12                                                           | 
| task                  | Reinstalling                                                    | 
| tboot                 | false                                                           | 
| ttys_dcd              | None                                                            | 
| updated_at            | 2022-06-22T20:14:35.125103+00:00                                | 
| uptime                | 0                                                               | 
| uuid                  | 952e0829-5802-4b50-9ba7-3bf31ae104f5                            | 
| vim_progress_status   | None                                                            | 
+-----------------------+-----------------------------------------------------------------+ 

 

#after the os is installed on controller-1, the status will be 

[sysadmin@controller-0 ~(keystone_admin)]$ system host-list  

+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | locked         | disabled    | online       | 
+----+--------------+-------------+----------------+-------------+--------------+ 

#observe the resources configured for controller-1 

[sysadmin@controller-0 ~(keystone_admin)]$ system host-if-list controller-1 

+--------------------------------------+-------------+----------+----------+---------+-----------+---------------+-------------------------------------------------+ 
| uuid                                 | name        | class    | type     | vlan id | ports     | uses i/f      | used by i/f                        | attributes | 
+--------------------------------------+-------------+----------+----------+---------+-----------+---------------+-------------------------------------------------+
| 4d7828dc-280e-47b6-b3b6-972bcde0aea9 | pxeboot0    | platform | ethernet | None    | [u'eno1'] | []            | [u'clusterhost', u'mgmt0', u'oam'] | MTU=1500   | 
| a2ddf27b-32b9-4bff-90df-352b617c9783 | clusterhost | platform | vlan     | 311     | []        | [u'pxeboot0'] | []                                 | MTU=1500   | 
| c387ad00-e54f-4eff-a1e5-3dc8f672ae25 | oam         | platform | vlan     | 12      | []        | [u'pxeboot0'] | []                                 | MTU=1500   | 
| d92ffbfd-8889-45e2-94f3-add7b348cc18 | mgmt0       | platform | vlan     | 301     | []        | [u'pxeboot0'] | []                                 | MTU=1500   | 
+--------------------------------------+-------------+----------+----------+---------+-----------+---------------+------------------------------------+------------+ 

[sysadmin@controller-0 ~(keystone_admin)]$ system host-disk-list controller-1 

+--------------------------------------+-----------+---------+---------+-------+------------+-----+-------------+-----------------------------------------------------------------+ 
| uuid                                 | device_no | device_ | device_ | size_ | available_ | rpm | serial_id   | device_path                                                     | 
|                                      | de        | num     | type    | gib   | gib        |     |             |                                                                 | 
+--------------------------------------+-----------+---------+---------+-------+------------+-----+-------------+-----------------------------------------------------------------+ 
| 7d11d334-c0c4-407c-b22d-b2b18207dea5 | /dev/sda  | 2048    | SSD     | 1117. | 0.0        | N/A | PHWA610500V | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6762ece7000-lun-0 | 
|                                      |           |         |         | 813   |            |     | H1P2JGN     |                                                                 | 
|                                      |           |         |         |       |            |     |             |                                                                 | 
| c21198c3-2372-473d-91f3-e49676b40fcf | /dev/sdb  | 2064    | SSD     | 465.  | 465.758    | N/A | S62BNF0R963 | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6762ece7001-lun-0 | 
|                                      |           |         |         | 761   |            |     | 470R        |                                                                 | 
|                                      |           |         |         |       |            |     |             |                                                                 | 
+--------------------------------------+-----------+---------+---------+-------+------------+-----+-------------+-----------------------------------------------------------------+ 

 

#the node will be automatically unlocked hence the node will reboot, during unlocking: 

[sysadmin@controller-0 ~(keystone_admin)]$ system host-list; fm alarm-list 

+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | enabled     | degraded     | 
+----+--------------+-------------+----------------+-------------+--------------+ 

+----------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------+----------+-----------------------+ 
| Alarm ID | Reason Text                                                                                                           | Entity ID                            | Severity | Time Stamp            | 
+----------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------+----------+-----------------------+ 
| 750.006  | A configuration change requires a reapply of the cert-manager application.                                            | k8s_application=cert-manager         | warning  | 2022-06-22T22:15:43.  | 
|          |                                                                                                                       |                                      |          | 925596                | 
|          |                                                                                                                       |                                      |          |                       | 
| 400.001  | Service group controller-services degraded; drbd-dockerdistribution(enabled-standby, degraded, data-syncing), drbd-   | service_domain=controller.           | major    | 2022-06-22T22:15:37.  | 
|          | etcd(enabled-standby, degraded, data-syncing), drbd-dc-vault(enabled-standby, degraded, data-syncing), ...            | service_group=controller-services.   |          | 382900                | 
|          |                                                                                                                       | host=controller-1                    |          |                       | 
|          |                                                                                                                       |                                      |          |                       | 
| 400.003  | Evaluation license key will expire on 19-aug-2022; there are 58 days remaining in this evaluation                     | host=controller-1                    | minor    | 2022-06-22T22:15:14.  | 
|          |                                                                                                                       |                                      |          | 545390                | 
|          |                                                                                                                       |                                      |          |                       | 
| 800.001  | Storage Alarm Condition: HEALTH_WARN. Please check 'ceph -s' for more details.                                        | cluster=49fa0498-53ca-               | warning  | 2022-06-22T22:09:24.  | 
|          |                                                                                                                       | 4a16-8a38-0c28feab370b               |          | 674070                | 
|          |                                                                                                                       |                                      |          |                       | 
| 400.003  | Evaluation license key will expire on 19-aug-2022; there are 58 days remaining in this evaluation                     | host=controller-0                    | minor    | 2022-06-22T20:12:47.  | 
|          |                                                                                                                       |                                      |          | 504036                | 
|          |                                                                                                                       |                                      |          |                       | 
+----------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------+----------+-----------------------+ 

#no alarms as soon as the node becomes online and available, platform applications are applied/uploaded 

[sysadmin@controller-0 ~(keystone_admin)]$ system host-list; fm alarm-list; system application-list 

+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | enabled     | available    | 
+----+--------------+-------------+----------------+-------------+--------------+ 
 

 

+--------------------------+----------+-----------------------------------+----------------------------------------+----------+-----------+ 
| application              | version  | manifest name                     | manifest file                          | status   | progress  | 
+--------------------------+----------+-----------------------------------+----------------------------------------+----------+-----------+ 
| cert-manager             | 21.12-28 | cert-manager-manifest             | certmanager-manifest.yaml              | applied  | completed | 
| nginx-ingress-controller | 21.12-18 | nginx-ingress-controller-manifest | nginx_ingress_controller_manifest.yaml | applied  | completed | 
| oidc-auth-apps           | 21.12-61 | oidc-auth-manifest                | manifest.yaml                          | uploaded | completed | 
| platform-integ-apps      | 21.12-44 | platform-integration-manifest     | manifest.yaml                          | uploaded | completed | 
| rook-ceph-apps           | 1.0-14   | rook-ceph-manifest                | manifest.yaml                          | uploaded | completed | 
+--------------------------+----------+-----------------------------------+----------------------------------------+----------+-----------+ 

 
```

#### 3.2.9 Validate the platform’s Cluster scalability
**Expected Results**

Verify if we are able to add a new node

**Procedure and Results**
```bash
#Power on the node that has to be added and make sure that it is pxebooted from the correct nic and wait for the node to come to waiting for configuration state.
source /etc/platform/openrc
watch system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | None         | None        | locked         | disabled    | offline      |
+----+--------------+-------------+----------------+-------------+--------------+

system host-update 11 personality=worker hostname=worker-1
+-----------------------+--------------------------------------+
| Property              | Value                                |
+-----------------------+--------------------------------------+
| action                | none                                 |
| administrative        | locked                               |
| availability          | offline                              |
| bm_i                  | None                                 |
| bm_type               | None                                 |
| bm_username           | None                                 |
| boot_device           | /dev/sda                             |
| capabilities          | {}                                   |
| clock_synchronization | ntp                                  |
| config_applied        | None                                 |
| config_status         | None                                 |
| config_target         | None                                 |
| console               | ttyS0,115200                         |
| created_at            | 2022-05-05T06:57:33.897840+00:00     |
| device_image_update   | None                                 |
| hostname              | worker-1                             |
| id                    | 11                                   |
| install_output        | text                                 |
| install_state         | None                                 |
| install_state_info    | None                                 |
| inv_state             | None                                 |
| invprovision          | None                                 |
| location              | {}                                   |
| mgmt_ip               | 11.11.11.46                          |
| mgmt_mac              | 40:a6:b7:2c:41:6c                    |
| operational           | disabled                             |
| personality           | worker                               |
| reboot_needed         | False                                |
| reserved              | False                                |
| rootfs_device         | /dev/sda                             |
| serialid              | None                                 |
| software_load         | 21.12                                |
| task                  | None                                 |
| tboot                 | false                                |
| ttys_dcd              | None                                 |
| updated_at            | None                                 |
| uptime                | 0                                    |
| uuid                  | 08f725d9-8cc6-4c8f-a8f9-ccb19e760f01 |
| vim_progress_status   | None                                 |
+-----------------------+--------------------------------------+

system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | locked         | disabled    | offline      |
+----+--------------+-------------+----------------+-------------+--------------+

#configure the worker as per the needs and unlock the node
system host-unlock worker-1
#check the status after unlock
system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

#Deleting the host: 
#Host was powered from iDRAC 
#From the active controller source as admin 
controller-0:~$ source /etc/platform/openrc 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list 
+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | enabled     | available    | 
| 9  | worker-0     | worker      | unlocked       | enabled     | available    | 
| 11 | worker-1     | worker      | unlocked       | disabled    | offline      | 
+----+--------------+-------------+----------------+-------------+--------------+ 

#Delete the host 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-delete worker-1 

#Check the result 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list 
+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | enabled     | available    | 
| 9  | worker-0     | worker      | unlocked       | enabled     | available    | 
+----+--------------+-------------+----------------+-------------+--------------+ 

```
**NOTE The added node should come up and show online and locked state in host-list**

### 3.2.10 Validate the application management of the platform

**Expected Results**

Application is installed and deleted using the helm chart

**Procedure and Results**
```bash

# files needed
#	- pod image(any prefered version)
#	- helm.tar.gz
#   - files to be modified in the helm directory:
#		- helm/values.yaml
#		- templates/docker-static-deployment.yaml 

#download and copy the image you want to use to the subcloud active controller
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document


# copy the helm tar file to the active controller to a dedicated directory and untar the archinve and operate the following changes (directory created here is helm-test)
[sysadmin@controller-0 helm-test(keystone_admin)]$ tar -zxvf test-helm.tar.gz 
[sysadmin@controller-0 helm-test(keystone_admin)]$ ls
helm  test-helm.tar.gz
# cd to helm directory and/or templates and make sure the folloing files are modified:
[sysadmin@controller-0 helm(keystone_admin)]$ vim values.yaml 
authorText: "Docker Static Site"
replicaCount: 3 # set the replica count to a desired number
image:
  repository: registry.local:9001/ps_emea/centos #chage with the downloaded image or an existing test image
  tag: v22 #use the version as displayed in docker
  secret: registry-creds #use an existing secret or create a secret for the image pull policy
service:
  nodePort: 31121
[sysadmin@controller-0 helm(keystone_admin)]$ vim templates/docker-static-deployment.yaml 
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "docker-static-site.name" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ include "docker-static-site.name" . }}
  template:
    metadata:
      labels:
        app: {{ include "docker-static-site.name" . }}
    spec:
      containers:
      - name: {{ include "docker-static-site.name" . }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        command: ["/bin/bash", "-ec", "sleep infinity"]
        env:
        - name: AUTHOR
          value: {{ .Values.authorText }}
        ports:
        - containerPort: 80
      imagePullSecrets:
        - name: "{{ .Values.image.secret }}"

#after the files are modified to the purpouse create a tar of the helm directory with the updated info
[sysadmin@controller-0 helm-test(keystone_admin)]$ tar -czvf test-helm.tar.gz helm/ 
helm/
helm/values.yaml
helm/templates/
helm/templates/_helper.tpl
helm/templates/docker-static-site-service.yaml
helm/templates/docker-static-deployment.yaml
helm/Chart.yaml
#Deploy the new archive using helm
[sysadmin@controller-0 helm-test(keystone_admin)]$ helm install test-helm test-helm.tar.gz
NAME: test-helm
LAST DEPLOYED: Wed Jun  8 12:06:02 2022
NAMESPACE: default
STATUS: deployed
REVISION: 1
TEST SUITE: None
#Check deployment 
[sysadmin@controller-0 helm-test(keystone_admin)]$ helm list
NAME              	NAMESPACE	REVISION	UPDATED                                	STATUS  	CHART                                               	APP VERSION
test-helm         	default  	1       	2022-06-08 12:06:02.628652766 +0000 UTC	deployed	docker-static-site-0.1.0                            	1.0        
#check the pods - as the replicaset was 3 - we have 3 pods
[sysadmin@controller-0 helm-test(keystone_admin)]$ kubectl get pods
NAME                                  READY   STATUS    RESTARTS   AGE
cyclictest                            1/1     Running   0          5h5m
docker-static-site-7948476c88-56qk5   1/1     Running   0          14s
docker-static-site-7948476c88-c7977   1/1     Running   0          14s
docker-static-site-7948476c88-r6dzx   1/1     Running   0          14s
# scale up 
[sysadmin@controller-0 helm-test(keystone_admin)]$ kubectl scale --replicas 5 deployments/docker-static-site
deployment.apps/docker-static-site scaled
# replicas are now set to 5
[sysadmin@controller-0 helm-test(keystone_admin)]$ kubectl get pods
NAME                                  READY   STATUS    RESTARTS   AGE
docker-static-site-7948476c88-56qk5   1/1     Running   0          2m46s
docker-static-site-7948476c88-c7977   1/1     Running   0          2m46s
docker-static-site-7948476c88-pngtv   1/1     Running   0          9s
docker-static-site-7948476c88-q5ktr   1/1     Running   0          9s
docker-static-site-7948476c88-r6dzx   1/1     Running   0          2m46s
#scale down 
[sysadmin@controller-0 helm-test(keystone_admin)]$ kubectl scale --replicas 3 deployments/docker-static-site
deployment.apps/docker-static-site scaled
[sysadmin@controller-0 helm-test(keystone_admin)]$ kubectl get pods -o wide
NAME                                  READY   STATUS        RESTARTS   AGE    IP               NODE           NOMINATED NODE   READINESS GATES
docker-static-site-7948476c88-56qk5   1/1     Running       0          4m4s   172.16.226.71    worker-1       <none>           <none>
docker-static-site-7948476c88-c7977   1/1     Terminating   0          4m4s   172.16.43.14     worker-0       <none>           <none>
docker-static-site-7948476c88-pngtv   1/1     Running       0          87s    172.16.166.133   controller-1   <none>           <none>
docker-static-site-7948476c88-q5ktr   1/1     Terminating   0          87s    172.16.43.15     worker-0       <none>           <none>
docker-static-site-7948476c88-r6dzx   1/1     Running       0          4m4s   172.16.192.88    controller-0   <none>           <none>
#replicas are now back to 3
[sysadmin@controller-0 helm-test(keystone_admin)]$ kubectl get pods -o wide
NAME                                  READY   STATUS        RESTARTS   AGE    IP               NODE           NOMINATED NODE   READINESS GATES
docker-static-site-7948476c88-56qk5   1/1     Running       0          4m4s   172.16.226.71    worker-1       <none>           <none>
docker-static-site-7948476c88-pngtv   1/1     Running       0          87s    172.16.166.133   controller-1   <none>           <none>
docker-static-site-7948476c88-r6dzx   1/1     Running       0          4m4s   172.16.192.88    controller-0   <none>           <none>

```



### 3.2.11 Validate the Cluster Persistent Storage for PODs

**Expected Results**

1. Attach a persistent volume inside the kubernetes pod
2. Create and delete files inside the persistent storage from the pod 
3. The contents should be stored even after deleting the pod, for other pods to use it

**Procedure and Results**
```bash
#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document

# files needed
#	- pod image - centos image used for this test
#	- pod creation yaml files

# Create a file which contains the manifests for the pvc and pod using the below content
[sysadmin@controller-0 wr(keystone_admin)]$ vim claimdisks.yaml 
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-claim1
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: cephfs
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod2
spec:
  imagePullSecrets:
    - name: registry-creds
  containers:
   - name: test-pod2
     image: registry.local:9001/ps_emea/centos:v22 
     volumeMounts:
       - name: ceph-volume
         mountPath: /mnt
     command: ["/bin/sh","-c", "--"]
     args: ["while true; do sleep 10; done;"]
  volumes:
    - name: ceph-volume
      persistentVolumeClaim:
        claimName: test-claim1

[sysadmin@controller-0 wr(keystone_admin)]$ vim claimdisks2.yaml 
apiVersion: v1
kind: Pod
metadata:
  name: test-pod2
spec:
  imagePullSecrets:
    - name: registry-creds
  containers:
   - name: test-pod2
     image: registry.local:9001/ps_emea/centos:v22 
     volumeMounts:
       - name: ceph-volume
         mountPath: /mnt
     command: ["/bin/sh","-c", "--"]
     args: ["while true; do sleep 10; done;"]
  volumes:
    - name: ceph-volume
      persistentVolumeClaim:
        claimName: test-claim1
        
#create the first pod
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl apply -f claimdisks.yaml 
persistentvolumeclaim/test-claim1 created
pod/test-pod created
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pods
NAME                                  READY   STATUS    RESTARTS   AGE
test-pod                              1/1     Running   0          6s
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pvc
NAME          STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
test-claim1   Bound    pvc-2abb8f35-9f26-420a-8847-d0075f932b1b   1Gi        RWO            cephfs         15s
#connect to the pod create a directory and a file on the mounted volume
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl exec -it test-pod -- /bin/sh
sh-4.4# df -h /mnt/
Filesystem      Size  Used Avail Use% Mounted on
ceph-fuse       849G     0  849G   0% /mnt
sh-4.4# cd mnt/
sh-4.4# mkdir test
sh-4.4# cd test
sh-4.4# date > test.txt
sh-4.4# ls
test.txt
sh-4.4# cat test.txt 
Wed Jun  8 12:29:18 UTC 2022
sh-4.4# exit
exit
#delete the pod that you have just created
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl delete pods test-pod
pod "test-pod" deleted
#confirm your pvc is present after pod deletion
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pvc
NAME          STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
test-claim1   Bound    pvc-2abb8f35-9f26-420a-8847-d0075f932b1b   1Gi        RWO            cephfs         4m14s
#create the second pod
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl apply -f claimdisks2.yaml 
pod/test-pod2 created
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl get pods
NAME                                  READY   STATUS    RESTARTS   AGE
test-pod2                             1/1     Running   0          5s
#connect on the pod and check the access of the previously created resources
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl exec -it test-pod2 -- /bin/bash
[root@test-pod2 /]# ls mnt/
test
[root@test-pod2 /]# ls mnt/test/
test.txt
[root@test-pod2 /]# cat mnt/test/test.txt 
Wed Jun  8 12:29:18 UTC 2022
# delete the resources first the pod and afterwads the pvc

```


### 3.2.12 Verify the number of CPU cores consumed by the Cloud Infrastructure overhead on a worker

**Expected Results**

For the controllers the number of cpus assigned to the platform is 2 and on the workers it is 1, if hyperthreading is enabled it should be 4 cpus on controllers and 2 on the workers.

**NOTE: For the Central cloud there is no requirement**

**Procedure and Results**
**On Central Cloud**
```bash
[sysadmin@controller-0 ~(keystone_admin)]$ for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-cpu-list $host | grep Platform | wc -l ;done
controller-0
#####
112
controller-1
#####
112

```

**On Subclouds**
```bash
[sysadmin@controller-0 ~(keystone_admin)]$ for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-cpu-list $host | grep Platform | wc -l ;done
controller-0
#####
4
controller-1
#####
4
worker-0
#####
2
worker-1
#####
2

```

### 3.2.13 Validate the Memory consumed by the Cloud Infrastructure overhead on a worker

**Expected Results**

On the controllers the assigned platform Memory should be 8G for controller and 7G for the workers

**NOTE: For the Central cloud there is no requirement**

**Procedure and Results**
**On Central Cloud**
```bash
# Third column (mem_platform) in the below output should be checked
[sysadmin@controller-0 ~(keystone_admin)]$ for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-memory-list $host;done
controller-0
#####
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 115643  | 12250      | 115643  | True           | 1024   | 0      | 0      | None  | 29604608  | False       | 0      | 0      | None     | 0      | 0      | None     | True   |
| 1         | 116727  | 12250      | 116727  | True           | 1024   | 0      | 0      | None  | 29882112  | False       | 0      | 0      | None     | 0      | 0      | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
controller-1
#####
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 115614  | 12250      | 115614  | True           | 1024   | 0      | 0      | None  | 29597184  | False       | 0      | 0      | None     | 0      | 0      | None     | True   |
| 1         | 116756  | 12250      | 116756  | True           | 1024   | 0      | 0      | None  | 29889536  | False       | 0      | 0      | None     | 0      | 0      | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+

```
**On Subcloud**
```bash
# Third column (mem_platform) in the below output should be checked
[sysadmin@controller-0 ~(keystone_admin)]$ for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-memory-list $host;done
controller-0
#####
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 248693  | 8000       | 248693  | True           | 1024   | 0      | 0      | None  | 46888192  | False       | 0      | 0      | None     | 64     | 64     | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
controller-1
#####
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 248693  | 8000       | 248693  | True           | 1024   | 0      | 0      | None  | 46888192  | False       | 0      | 0      | None     | 64     | 64     | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
worker-0
#####
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 249690  | 7000       | 249690  | True           | 1024   | 0      | 0      | None  | 47143424  | False       | 0      | 0      | None     | 64     | 64     | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
worker-1
#####
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 249690  | 7000       | 249690  | True           | 1024   | 0      | 0      | None  | 47143424  | False       | 0      | 0      | None     | 64     | 64     | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
```

### 3.2.14 Validate the CPU allocation ratio

**Expected Results**

For the controllers the number of cpus assigned to the platform is 2 and on the workers it is 1, if hyperthreading is enabled it should be 4 cpus on controllers and 2 on the workers.

**NOTE: For the Central cloud there is no requirement**

**Procedure and Results**
**On Central Cloud**
```bash
[sysadmin@controller-0 ~(keystone_admin)]$ for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-cpu-list $host | grep Platform | wc -l ;done
controller-0
#####
112
controller-1
#####
112

```

**On Subclouds**
```bash
[sysadmin@controller-0 ~(keystone_admin)]$ for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-cpu-list $host | grep Platform | wc -l ;done
controller-0
#####
4
controller-1
#####
4
worker-0
#####
2
worker-1
#####
2

```


### 3.2.15 Verify the Host CPU usage

**Expected Results**

List alarm threshold in the events suppression GUI interface. Platform CPU threshold exceeded; threshold x%, actual y%. 

CRITICAL @ 95%
MAJOR @ 90%

**Procedure and Results**

![Alarm Suppression](.\images\Alarm-Supression.png)

### 3.2.16 Verify the maximum Disk Utilization

**Expected Results**
List alarm threshold in the events suppression GUI interface.
CRITICAL @ 90%
MAJOR @ 80%

**Procedure and Results**

![Alarm Suppression](.\images\Alarm-Supression.png)




### 3.2.17 Verify the maximum Memory Utilization

**Expected Results**

List alarm threshold in the events suppression GUI interface.
CRITICAL @ 90%
MAJOR @ 80%

**Procedure and Results**
![Alarm Suppression](.\images\Alarm-Supression.png)

### 3.2.18 Validate the Cloud Platform’s Image management

**Expected Results**

Able to push and pull images from local registry and list the images in local registry

**Procedure and Results**

```bash
# files needed
#	- pod image(busybox was used here)

#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 

# Load the image that has to be pushed to the local registry on the active controller
sudo docker load < busybox.tar.gz 
eb6b01329ebe: Loading layer [==================================================>]  1.459MB/1.459MB
Loaded image: busybox:latest

# Check if the image is loaded properly
sudo docker images | grep busy
busybox                                                                        latest                                                   1a80408de790        2 weeks ago         1.24MB

# Tag the image with the local registry
sudo docker tag busybox:latest registry.local:9001/k8s.gcr.io/busybox:v22
The push refers to repository [registry.local:9001/k8s.gcr.io/busybox]
eb6b01329ebe: Pushed 
latest: digest: sha256:52f431d980baa76878329b68ddb69cb124c25efa6e206d8b0bd797a828f0528e size: 527

# Push the image to the local registry
sudo docker push registry.local:9001/k8s.gcr.io/busybox:v22

# Check if the image is seen in the system image registry list
system registry-image-list | grep "Image\|busy\|+"
+----------------------------------------------------------+
| Image Name                                               |
+----------------------------------------------------------+
| k8s.gcr.io/busybox                                       |
+----------------------------------------------------------+

system registry-image-list
+----------------------------------------------------------+
| Image Name                                               |
+----------------------------------------------------------+
| docker.io/jettech/kube-webhook-certgen                   |
| docker.io/starlingx/ceph-config-helper                   |
| docker.io/starlingx/n3000-opae                           |
| docker.io/starlingx/rvmc                                 |
| docker.io/wind-river/cloud-platform-deployment-manager   |
| docker.io/wind-river/cmk                                 |
| docker.io/wind-river/dm-monitor                          |
| gcr.io/kubebuilder/kube-rbac-proxy                       |
| ghcr.io/helm/tiller                                      |
| ghcr.io/k8snetworkplumbingwg/multus-cni                  |
| ghcr.io/k8snetworkplumbingwg/sriov-cni                   |
| ghcr.io/k8snetworkplumbingwg/sriov-network-device-plugin |
| k8s.gcr.io/coredns/coredns                               |
| k8s.gcr.io/defaultbackend                                |
| k8s.gcr.io/etcd                                          |
| k8s.gcr.io/ingress-nginx/controller                      |
| k8s.gcr.io/kube-apiserver                                |
| k8s.gcr.io/kube-controller-manager                       |
| k8s.gcr.io/kube-proxy                                    |
| k8s.gcr.io/kube-scheduler                                |
| k8s.gcr.io/pause                                         |
| mantri425/wind-test                                      |
| ps_emea/node-hello                                       |
| ps_emea/resource-consumer                                |
| ps_emea/wrcptestsuite                                    |
| quay.io/airshipit/armada                                 |
| quay.io/calico/cni                                       |
| quay.io/calico/kube-controllers                          |
| quay.io/calico/node                                      |
| quay.io/calico/pod2daemon-flexvol                        |
| quay.io/external_storage/rbd-provisioner                 |
| quay.io/jetstack/cert-manager-acmesolver                 |
| quay.io/jetstack/cert-manager-cainjector                 |
| quay.io/jetstack/cert-manager-controller                 |
| quay.io/jetstack/cert-manager-webhook                    |
| quay.io/k8scsi/snapshot-controller                       |
| quay.io/stackanetes/kubernetes-entrypoint                |
+----------------------------------------------------------+
sudo docker rmi registry.local:9001/k8s.gcr.io/busybox:v22
Untagged: registry.local:9001/ps_emea/busybox:v22
Untagged: registry.local:9001/ps_emea/busybox@sha256:a1801b843b1bfaf77c501e7a6d3f709401a1e0c83863037fa3aab063a7fdb9dc
Deleted: sha256:5d0da3dc976460b72c77d94c8a1ad043720b0416bfc16c52c45d4847e53fadb6
Deleted: sha256:74ddd0ec08fa43d09f32636ba91a0a3053b02cb4627c35051aff89f853606b59

system registry-image-list | grep "Image\|busy\|+"
+----------------------------------------------------------+
| Image Name                                               |
+----------------------------------------------------------+
+----------------------------------------------------------+


```
**NOTE: The output may vary depending on the number of images in the registry**

### 3.2.19 Verify CaaS reconfiguration

**Expected Results**

1G Huge pages is configured in the platform 

**Procedure and Results**

**NOTE: In the below example the CaaS node is configured to new state**

```bash
source /etc/platform/openrc
# Lock the worker which has to be reconfigured
system host-lock worker-1

# List the memory of the worker
system host-memory-list worker-1

+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 249690  | 7000       | 249690  | True           | 1024   | 0      | 0      | None  | 47143424  | False       | 0      | 0      | None     | 64     | 64     | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+

# Modify the memory to a grater value than the configured
system host-memory-modify worker-1 0 -f application -1G 68

+-----------------------------------------------+--------------------------------------+
| Property                                      | Value                                |
+-----------------------------------------------+--------------------------------------+
| Memory: Usable Total (MiB)                    | 249690                               |
|         Platform     (MiB)                    | 7000                                 |
|         Available    (MiB)                    | 249690                               |
| Huge Pages Configured                         | True                                 |
| vSwitch Huge Pages: Size (MiB)                | 1024                                 |
|                     Total                     | 0                                    |
|                     Available                 | 0                                    |
|                     Required                  | None                                 |
| Application  Pages (4K): Total                | 47143424                             |
| Application  Huge Pages Pending As Percentage | False                                |
| Application  Huge Pages (2M): Total           | 0                                    |
|                 Available                     | 0                                    |
| Application  Huge Pages (1G): Total           | 64                                   |
|                 Total Pending                 | 68                                   |
|                 Available                     | 64                                   |
| uuid                                          | b9506160-6a59-44a5-88bd-76f4d354a4b0 |
| ihost_uuid                                    | 564edd47-ec6b-4994-90e3-1f8aeea54be9 |
| inode_uuid                                    | 2d57d120-dc8e-4173-a3f6-a5a39b0fbd14 |
| created_at                                    | 2022-04-29T14:55:52.649871+00:00     |
| updated_at                                    | 2022-05-03T08:02:26.405299+00:00     |
+-----------------------------------------------+--------------------------------------+

# Unlock the host
system host-unlock worker-1

+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| processor | mem_tot | mem_platfo | mem_ava | hugepages(hp)_ | vs_hp_ | vs_hp_ | vs_hp_ | vs_hp | app_total | app_hp_as_p | app_hp | app_hp | app_hp_p | app_hp | app_hp | app_hp_p | app_hp |
|           | al(MiB) | rm(MiB)    | il(MiB) | configured     | size(M | total  | avail  | _reqd | _4K       | ercentage   | _total | _avail | ending_2 | _total | _avail | ending_1 | _use_1 |
|           |         |            |         |                | iB)    |        |        |       |           |             | _2M    | _2M    | M        | _1G    | _1G    | G        | G      |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+
| 0         | 249690  | 7000       | 249690  | True           | 1024   | 0      | 0      | None  | 47143424  | False       | 0      | 0      | None     | 68     | 68     | None     | True   |
+-----------+---------+------------+---------+----------------+--------+--------+--------+-------+-----------+-------------+--------+--------+----------+--------+--------+----------+--------+

```


### 3.2.20 Validate the System Optimization techniques  and Verify DPDK performance 

**Expected Results**
1. SRIOV devices are attached to the kubernetes pods.
2. Spoof checking of the Virtual Function should be disabled
3. Send and Receive packets between the pods using Virtual Functions
4. The Pkts/s Max/Rx section in the packet generator should be updated constantly and MBits/s Rx/Tx  should be almost equal, with different packet sizes

**Procedure and Results**
```bash
**Prerquisites**
#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document

# files needed
#	- pod images: 
#		- dpdk-pktgen-and-apps:20.11 (or other version)
#	- pod creation yaml files
#		- testpmd.yaml
#		- packetge.yaml

**From the Jump host**
```bash
# Copy the images that are required for the test
scp mf-docker-image-dpdk-pktgen-and-apps-20.11.tar.gz sysadmin@10.10.1.2:/home/sysadmin/
```
**On the active Controller**
```bash
# Load and push the required images to the local registry
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker load -i pktgen.tar.gz
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker tag dpdk-pktgen-and-apps:20.11 registry.local:9001/k8s.gcr.io/dpdk-pktgen-and-apps:20.11
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker push registry.local:9001/k8s.gcr.io/dpdk-pktgen-and-apps:20.11

# Create secret for pulling the image from local registry
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl create secret docker-registry registry-creds --docker-username=sysinv --docker-password=$(keyring get sysinv services) --docker-server=registry.local:9001
```
**NOTE**

**1. Make sure to use the vfio driver interface**

**2. Make sure to note the logical cpus assigned in each pod**

**3. Make sure to note the vfio device address in the pod**

**4. make sure to note the Mac Address of the vf**

**5. Make sure to disable mac spoofing for the vfs**


1. Bringing up Packet Generator

**Procedure and Results**

```bash
#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document

# files needed
#	- pod images: 
#		- dpdk-pktgen-and-apps:20.11 (or other version)
#	- pod creation yaml files
#		- testpmd.yaml
#		- packetge.yaml

# Check if the required sriov network is created

[sysadmin@controller-0 ~(keystone_admin)]$ system host-if-show worker-0 fh1

+------------------+--------------------------------------+
| Property         | Value                                |
+------------------+--------------------------------------+
| ifname           | fh1                                  |
| iftype           | vf                                   |
| ports            | []                                   |
| imac             | 40:a6:b7:72:c4:02                    |
| imtu             | 9000                                 |
| ifclass          | pci-sriov                            |
| ptp_role         | none                                 |
| aemode           | None                                 |
| schedpolicy      | None                                 |
| txhashpolicy     | None                                 |
| primary_reselect | None                                 |
| uuid             | a707eb56-90bf-45a7-af49-cdcf735f4021 |
| ihost_uuid       | d9bbefe0-65db-40a8-b084-5bd72b1a58b4 |
| vlan_id          | None                                 |
| uses             | [u'fh1com']                          |
| used_by          | []                                   |
| created_at       |                                      |
| updated_at       |                                      |
| sriov_numvfs     | 2                                    |
| sriov_vf_driver  | vfio                                 |
| max_tx_rate      | None                                 |
| accelerated      | [False]                              |
+------------------+--------------------------------------+

# Create the manifest for the packet generator pod
[sysadmin@controller-0 ~(keystone_admin)]$ cat < EOF> pktgen.yml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: mf-vfio
  annotations:
    k8s.v1.cni.cncf.io/resourceName: intel.com/pci_sriov_net_fh1
spec:
  config: '{
  "type": "sriov",
  "name": "mf-vfio"
}'
---
apiVersion: v1
kind: Pod
metadata:
  name: pktgen
  annotations:
    k8s.v1.cni.cncf.io/networks: '[
       {"name": "mf-vfio"}
    ]'
spec:
  restartPolicy: Never
  imagePullSecrets:
   - name: registry-creds
  containers:
  - name: pktgen
    image: registry.local:9001/k8s.gcr.io/dpdk-pktgen-and-apps:20.11
    imagePullPolicy: IfNotPresent
    volumeMounts:
    - mountPath: /mnt/huge-2048
      name: hugepage
    - name: lib-modules
      mountPath: /lib/modules
    - name: src
      mountPath: /usr/src
    command: ["/bin/bash", "-ec", "sleep infinity"]
    securityContext:
      privileged: false
      capabilities:
        add:
          ["IPC_LOCK", "SYS_ADMIN"]
    resources:
      requests:
        memory: 4Gi
        hugepages-1Gi: 4Gi
        intel.com/pci_sriov_net_fh1: '1'
        windriver.com/isolcpus: 2
      limits:
        memory: 4Gi
        hugepages-1Gi: 4Gi
        intel.com/pci_sriov_net_fh1: '1'
        windriver.com/isolcpus: 2
  volumes:
  - name: hugepage
    emptyDir:
        medium: HugePages
  - name: lib-modules
    hostPath:
      path: /lib/modules
  - name: src
    hostPath:
      path: /usr/src
EOF
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl apply -f pktgen.yml
networkattachmentdefinition.k8s.cni.cncf.io/mf-vfio created
pod/pktgen created

# Connect to the pod that is created
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec -it pktgen bash
[root@pktgen opt]# ----> This means you are inside container

#Make sure that you are inside the container before proceeding
[root@pktgen opt]# taskset -pc 1
[root@pktgen opt]#  pid 1's current affinity list: 2,34

# Check if the VF is attached to the pod
[root@pktgen opt]# env | grep -i pci
PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_FH1=0000:51:11.6

# Build the app
[root@pktgen opt]#  export PKG_CONFIG_PATH=/usr/local/lib64/pkgconfig
[root@pktgen opt]#  cd  /opt/pktgen-dpdk-pktgen-20.11.3
[root@pktgen opt]#  make rebuild
[root@pktgen opt]# cd Builddir/app

# Run the packet generator
[root@pktgen opt]# ./pktgen -l 2,34 n 3 -w 0000:51:11.6 --proc-type auto --socket-mem 1024 --file-prefix pg --  -P -m "34.0" --crc-strip
*** Copyright (c) <2010-2020>, Intel Corporation. All rights reserved.
*** Pktgen  created by: Keith Wiles -- >>> Powered by DPDK <<<

 Port: Name         IfIndex Alias        NUMA  PCI
    0: net_iavf        0                   0   8086:1889/51:17.6

Initialize Port 0 -- TxQ 1, RxQ 1
iavf_init_rss(): RSS is enabled by PF by default
Src MAC 6a:42:55:5d:f5:35 -----------------------------------------------------------------> This should be the peer mac for the pmd driver
 <Promiscuous mode Enabled>

iavf_configure_queues(): request RXDID[22] in Queue[0]
/ Ports 0-0 of 1   <Main Page>  Copyright (c) <2010-2020>, Intel Corporation
  Flags:Port        : P------Single      :0
Link State          :         <UP-25000-FD>      ---Total Rate---
Pkts/s Max/Rx       :                   2/0                   2/0
       Max/Tx       :                   0/0                   0/0
MBits/s Rx/Tx       :                   0/0                   0/0
Broadcast           :                     0
Multicast           :                    36
Sizes 64            :                     0
      65-127        :                     0
      128-255       :                     0
      256-511       :                    36
      512-1023      :                     0
      1024-1518     :                     0
Runts/Jumbos        :                   0/0
ARP/ICMP Pkts       :                   0/0
Errors Rx/Tx        :                   0/0
Total Rx Pkts       :                    36
      Tx Pkts       :                     0
      Rx MBs        :                     0
      Tx MBs        :                     0
                    :
Pattern Type        :               abcd...
Tx Count/% Rate     :         Forever /100%
Pkt Size/Tx Burst   :             64 /   32
TTL/Port Src/Dest   :         4/ 1234/ 5678
Pkt Type:VLAN ID    :       IPv4 / TCP:0001
802.1p CoS/DSCP/IPP :             0/  0/  0
VxLAN Flg/Grp/vid   :      0000/    0/    0
IP  Destination     :           192.168.1.1
    Source          :        192.168.0.1/24
MAC Destination     :     00:00:00:00:00:00
    Source          :     6a:42:55:5d:f5:35
PCI Vendor/Addr     :     8086:1889/51:17.6

-- Pktgen 20.11.3 (DPDK 20.11.0)  Powered by DPDK  (pid:337) ------------------

```
1. Bringing up the pmd pod

**Procedure and Results**
```bash
# Create a manifest for the pmd pod.
[sysadmin@controller-0 ~(keystone_admin)]$ cat <EOF >testpmd.yml
apiVersion: v1
kind: Pod
metadata:
  name: testpmd
  annotations:
    k8s.v1.cni.cncf.io/networks: '[
       {"name": "mf-vfio"}
    ]'
spec:
  restartPolicy: Never
  imagePullSecrets:
   - name: registry-creds
  containers:
  - name: testpmd
    image: registry.local:9001/k8s.gcr.io/dpdk-pktgen-and-apps:20.11
    imagePullPolicy: IfNotPresent
    volumeMounts:
    - mountPath: /mnt/huge-2048
      name: hugepage
    - name: lib-modules
      mountPath: /lib/modules
    - name: src
      mountPath: /usr/src
    command: ["/bin/bash", "-ec", "sleep infinity"]
    securityContext:
      privileged: false
      capabilities:
        add:
          ["IPC_LOCK", "SYS_ADMIN"]
    resources:
      requests:
        memory: 4Gi
        hugepages-1Gi: 4Gi
        intel.com/pci_sriov_net_fh1: '1'
        windriver.com/isolcpus: 2
      limits:
        memory: 4Gi
        hugepages-1Gi: 4Gi
        intel.com/pci_sriov_net_fh1: '1'
        windriver.com/isolcpus: 2
  volumes:
  - name: hugepage
    emptyDir:
        medium: HugePages
  - name: lib-modules
    hostPath:
      path: /lib/modules
  - name: src
    hostPath:
      path: /usr/src
EOF

# Create the pmd pod
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl apply -f testpmd.yml
pod/testpmd created

# Check if the pmd pod is running 
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl get pods -o wide
NAME      READY   STATUS    RESTARTS   AGE    IP              NODE       NOMINATED NODE   READINESS GATES
pktgen    1/1     Running   0          11m    172.16.43.24    worker-0   <none>           <none>
testpmd   1/1     Running   0          5s     172.16.43.25    worker-0   <none>           <none>

[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec -it testpmd -- bash

# Run the dpdk pmd to send the packets to the packet generator
 [root@pktgen opt]# cd /opt/dpdk-20.11/build/app/

[root@pktgen opt]# ./dpdk-testpmd --socket-mem 1024 -l 4,36 -w 0000:51:11.7 --file-prefix=testpmd_ -- --forward-mode=mac --auto-start --stats-period 1 --eth-peer=0,"6a:42:55:5d:f5:35" #Get the macaddress logical cpus and vf path from Expected outputs
EAL: Detected 64 lcore(s)
EAL: Detected 1 NUMA nodes
Option -w, --pci-whitelist is deprecated, use -a, --allow option instead
EAL: Multi-process socket /var/run/dpdk/testpmd_/mp_socket
EAL: Selected IOVA mode 'VA'
EAL: No available hugepages reported in hugepages-2048kB
EAL: Probing VFIO support...
EAL: VFIO support initialized
EAL:   using IOMMU type 1 (Type 1)
EAL: Probe PCI driver: net_iavf (8086:1889) device: 0000:51:11.7 (socket 0)
EAL: No legacy callbacks, legacy socket not created
Set mac packet forwarding mode
Auto-start selected
testpmd: create a new mbuf pool <mb_pool_0>: n=155456, size=2176, socket=0
testpmd: preferred mempool ops selected: ring_mp_mc

Warning! port-topology=paired and odd forward ports number, the last port will pair with itself.

Configuring Port 0 (socket 0)
iavf_init_rss(): RSS is enabled by PF by default
iavf_configure_queues(): request RXDID[22] in Queue[0]

Port 0: link state change event

Port 0: link state change event
Port 0: B6:CC:7C:18:4A:F4 ------------------------------------------------------------> Note the mac address this should be the destination mac in the packet generator

```
1. Generating Packets
   
**On the worker where the packetgenerator and the pmd pods are up**
```bash
ip l
enp81s0f2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9000 qdisc mq state UP mode DEFAULT group default qlen 1000
    link/ether 40:a6:b7:72:c4:02 brd ff:ff:ff:ff:ff:ff
    vf 0     link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff, spoof checking on, link-state auto, trust off
    vf 1     link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff, spoof checking on, link-state auto, trust off
    vf 2     link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff, spoof checking on, link-state auto, trust off
    vf 3     link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff, spoof checking on, link-state auto, trust off
    vf 4     link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff, spoof checking on, link-state auto, trust off
    vf 5     link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff, spoof checking on, link-state auto, trust off
    vf 6     link/ether 6a:42:55:5d:f5:35 brd ff:ff:ff:ff:ff:ff, spoof checking off, link-state auto, trust off
    vf 7     link/ether b6:cc:7c:18:4a:f4 brd ff:ff:ff:ff:ff:ff, spoof checking off, link-state auto, trust off

# Disable spoof check for  both the VF's on the hosts
sudo ip link set enp81s0f2 vf 6 spoofchk off
sudo ip link set enp81s0f2 vf 7 spoofchk off
```

**In the packet generator pod**
```bash
# Set the size and rate in the packet generator
[root@pktgen opt] Pktgen:/> set 0 dst b6:cc:7c:18:4a:f4
[root@pktgen opt] Pktgen:/> set 0 size 1024
[root@pktgen opt] Pktgen:/> set 0 rate 40%

# Start the packets in the packet generator
[root@pktgen opt] Pktgen:/> start 0
```bash
avf_configure_queues(): request RXDID[22] in Queue[0]
/ Ports 0-0 of 1   <Main Page>  Copyright (c) <2010-2020>, Intel Corporation
  Flags:Port        : P------Single      :0
Link State          :         <UP-25000-FD>      ---Total Rate---
Pkts/s Max/Rx       :       1211461/1210502       1211461/1210502
       Max/Tx       :       1211461/1210528       1211461/1210528
MBits/s Rx/Tx       :           10071/10110           10071/10110
Broadcast           :                     0
Multicast           :                   587
Sizes 64            :                     0
      65-127        :                     0
      128-255       :                     0
      256-511       :                   731
      512-1023      :                     0
      1024-1518     :              39752704
Runts/Jumbos        :                   0/0
ARP/ICMP Pkts       :                   0/0
Errors Rx/Tx        :                   0/0
Total Rx Pkts       :              39070203
      Tx Pkts       :              39069504
      Rx MBs        :                325060
      Tx MBs        :                326308
                    :
Pattern Type        :               abcd...
Tx Count/% Rate     :          Forever /40%
Pkt Size/Tx Burst   :           1024 /   32
TTL/Port Src/Dest   :         4/ 1234/ 5678
Pkt Type:VLAN ID    :       IPv4 / TCP:0001
802.1p CoS/DSCP/IPP :             0/  0/  0
VxLAN Flg/Grp/vid   :      0000/    0/    0
IP  Destination     :           192.168.1.1
    Source          :        192.168.0.1/24
MAC Destination     :     b6:cc:7c:18:4a:f4
    Source          :     6a:42:55:5d:f5:35
PCI Vendor/Addr     :     8086:1889/51:17.6

-- Pktgen 20.11.3 (DPDK 20.11.0)  Powered by DPDK  (pid:337) ------------------

```

### 3.2.21 Validation of Cloud Platform using eASIC Acceleration

**Expected Results**

Intel Acceleration card is seen in the kubernetes pod.

**Procedure and Results**

```bash
# files needed
#	- pod images: busybox was used here
#	- pod creation yaml file
#	- network creation yaml file

#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX - end of the document

# Load the image that is used for the test
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker load < busybox.tar.gz 
eb6b01329ebe: Loading layer [==================================================>]  1.459MB/1.459MB
Loaded image: busybox:latest

#check the load is complete
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker images | grep busy

busybox                                                                        latest                                                   1a80408de790        2 weeks ago         1.24MB


#tag the image
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker tag busybox:latest registry.local:9001/k8s.gcr.io/busybox:latest

#push the image
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker push registry.local:9001/k8s.gcr.io/busybox:latest
eb6b01329ebe: Pushed 
latest: digest: sha256:52f431d980baa76878329b68ddb69cb124c25efa6e206d8b0bd797a828f0528e size: 527

[sysadmin@controller-0 ~(keystone_admin)]$ system registry-image-list | grep "Image\|busy\|+"
+----------------------------------------------------------+
| Image Name                                               |
+----------------------------------------------------------+
| k8s.gcr.io/busybox                                       |
+----------------------------------------------------------+

#create the pod deployment yml that should look like this:

#network attachment
[sysadmin@controller-0 wr(keystone_admin)]$ cat network.yaml 
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: mf-vfio
  annotations:
    k8s.v1.cni.cncf.io/resourceName: intel.com/pci_sriov_net_fh1
spec:
  config: '{
  "type": "sriov",
  "name": "mf-vfio"
}'


#pod
cat acc-test.yml

apiVersion: v1
kind: Pod
metadata:
  name: acc-test
  annotations:
    k8s.v1.cni.cncf.io/networks: '[
       {"name": "mf-vfio"}
    ]'
spec:
  restartPolicy: Never
  imagePullSecrets:
   - name: registry-creds
  containers:
  - name: acc-test
    image: registry.local:9001/k8s.gcr.io/busybox:latest
    imagePullPolicy: IfNotPresent
    volumeMounts:
    - mountPath: /mnt/huge-2048
      name: hugepage
    - name: lib-modules
      mountPath: /lib/modules
    - name: src
      mountPath: /usr/src
    command: ['sh','-c']
    args: ['while true;do sleep 10;done;']
    securityContext:
      privileged: false
      capabilities:
        add:
          ["IPC_LOCK", "SYS_ADMIN"]
    resources:
      requests:
        memory: 4Gi
        hugepages-1Gi: 4Gi
        intel.com/pci_sriov_net_fh1: '1'
        windriver.com/isolcpus: 2
        intel.com/intel_acc100_fec: 1
      limits:
        memory: 4Gi
        hugepages-1Gi: 4Gi
        intel.com/pci_sriov_net_fh1: '1'
        windriver.com/isolcpus: 2
        intel.com/intel_acc100_fec: 1
  volumes:
  - name: hugepage
    emptyDir:
        medium: HugePages
  - name: lib-modules
    hostPath:
      path: /lib/modules
  - name: src
    hostPath:
      path: /usr/src

#create the pod secret
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl create secret docker-registry registry-creds --docker-username=sysinv --docker-password=$(keyring get sysinv services) --docker-server=registry.local:9001 -n default
#create the network attachment
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl apply -f network.yml
#create the pod
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl apply -f acc-test.yml 
#get the pod host:
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl get pods -n default acc-test -o wide

NAME       READY   STATUS    RESTARTS   AGE     IP             NODE       NOMINATED NODE   READINESS GATES
acc-test   1/1     Running   0          2m30s   172.16.43.23   worker-0   <none>           <none>

#describe the pod and check for the acceleratir resource
[sysadmin@controller-0 wr(keystone_admin)]$  kubectl describe node worker-0 | grep "name\|intel_acc100_fec" | grep -v "hostname="
  Hostname:    worker-0
  intel.com/intel_acc100_fec:      3 #avalable
  intel.com/intel_acc100_fec:      3 #limit
  intel.com/intel_acc100_fec      1            1 #used
#connect in the pod and check the resources
[sysadmin@controller-0 wr(keystone_admin)]$ kubectl exec -it acc-test -n default -- /bin/bash
[root@acc-test /]# lspci | grep accelerators
c3:00.0 Processing accelerators: Intel Corporation Device 0d5c
c4:00.0 Processing accelerators: Intel Corporation Device 0d5d
c4:00.1 Processing accelerators: Intel Corporation Device 0d5d
c4:00.2 Processing accelerators: Intel Corporation Device 0d5d

[root@acc-test /]# env
LANG=en_US.UTF-8
HOSTNAME=acc-test
KUBERNETES_PORT_443_TCP_PROTO=tcp
KUBERNETES_PORT_443_TCP_ADDR=10.96.0.1
KUBERNETES_PORT=tcp://10.96.0.1:443
PWD=/
HOME=/root
KUBERNETES_SERVICE_PORT_HTTPS=443
KUBERNETES_PORT_443_TCP_PORT=443
KUBERNETES_PORT_443_TCP=tcp://10.96.0.1:443
TERM=xterm
PCIDEVICE_INTEL_COM_INTEL_ACC100_FEC=0000:c4:00.0
SHLVL=1
PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_FH1=0000:51:11.6
KUBERNETES_SERVICE_PORT=443
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
KUBERNETES_SERVICE_HOST=10.96.0.1
LESSOPEN=||/usr/bin/lesspipe.sh %s
_=/usr/bin/env
[root@acc-test /]# env | grep -i "acc"
HOSTNAME=acc-test
PCIDEVICE_INTEL_COM_INTEL_ACC100_FEC=0000:c4:00.0
```

### 3.2.22 Verify minor, major and critical alarms of the Cloud Platform are generated.

**Expected Results**

1. Major Alarms are generated in the platform, whenever there is a disruption.
2. Minor Alarms are generated in the platform, whenever there is a disruption. 
3. Warnings are generated in platform, whenever there is a disruption.
4. Critical Alarms are generated in the platform, whenever there is a disruption.
   
**Procedure and Results**

**NOTE: This test assumes that controller-0 is the active controller**
```bash
# Source the openrc file on the active controller
[sysadmin@controller-0 ~(keystone_admin)]$ source /etc/platform/openrc

# Check no alarms are present
[sysadmin@controller-0 ~(keystone_admin)]$ fm alarm-list


# List the hosts that are part of the cluster
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 4  | controller-1 | controller  | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

# Lock the standby controller ( This will make the standby controller to be disabled)
 [sysadmin@controller-0 ~(keystone_admin)]$ system host-lock controller-1

# Check if the alarms are generated for major, minor and critical
fm alarm-list 
+-------+------------------------------------+--------------------------------------+----------+-------------+
| Alarm | Reason Text                        | Entity ID                            | Severity | Time Stamp  |
| ID    |                                    |                                      |          |             |
+-------+------------------------------------+--------------------------------------+----------+-------------+
| 800.  | Loss of replication in replication | cluster=43425d6e-bc1f-4e1b-          | major    | 2022-05-31T |
| 011   | group  group-0: OSDs are down      | 8f18-ae3ea8baf3cc.peergroup=group-0. |          | 12:11:29.   |
|       |                                    | host=controller-1                    |          | 113835      |
|       |                                    |                                      |          |             |
| 800.  | Storage Alarm Condition:           | cluster=43425d6e-bc1f-4e1b-          | warning  | 2022-05-31T |
| 001   | HEALTH_WARN [PGs are               | 8f18-ae3ea8baf3cc                    |          | 12:11:28.   |
|       | degraded/stuck or undersized].     |                                      |          | 926687      |
|       | Please check 'ceph -s' for more    |                                      |          |             |
|       | details.                           |                                      |          |             |
|       |                                    |                                      |          |             |
| 200.  | controller-1 was administratively  | host=controller-1                    | warning  | 2022-05-31T |
| 001   | locked to take it out-of-service.  |                                      |          | 12:11:23.   |
|       |                                    |                                      |          | 233846      |
|       |                                    |                                      |          |             |
| 400.  | Service group oam-services loss of | service_domain=controller.           | major    | 2022-05-31T |
| 002   | redundancy; expected 1 standby     | service_group=oam-services           |          | 12:11:22.   |
|       | member but no standby members      |                                      |          | 353819      |
|       | available                          |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group controller-services  | service_domain=controller.           | major    | 2022-05-31T |
| 002   | loss of redundancy; expected 1     | service_group=controller-services    |          | 12:11:22.   |
|       | standby member but no standby      |                                      |          | 351433      |
|       | members available                  |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group cloud-services loss  | service_domain=controller.           | major    | 2022-05-31T |
| 002   | of redundancy; expected 1 standby  | service_group=cloud-services         |          | 12:11:22.   |
|       | member but no standby members      |                                      |          | 309014      |
|       | available                          |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group vim-services loss of | service_domain=controller.           | major    | 2022-05-31T |
| 002   | redundancy; expected 1 standby     | service_group=vim-services           |          | 12:11:22.   |
|       | member but no standby members      |                                      |          | 265994      |
|       | available                          |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group patching-services    | service_domain=controller.           | major    | 2022-05-31T |
| 002   | loss of redundancy; expected 1     | service_group=patching-services      |          | 12:11:22.   |
|       | standby member but no standby      |                                      |          | 263470      |
|       | members available                  |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group directory-services   | service_domain=controller.           | major    | 2022-05-31T |
| 002   | loss of redundancy; expected 2     | service_group=directory-services     |          | 12:11:22.   |
|       | active members but only 1 active   |                                      |          | 220395      |
|       | member available                   |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group web-services loss of | service_domain=controller.           | major    | 2022-05-31T |
| 002   | redundancy; expected 2 active      | service_group=web-services           |          | 12:11:22.   |
|       | members but only 1 active member   |                                      |          | 217449      |
|       | available                          |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group storage-services     | service_domain=controller.           | major    | 2022-05-31T |
| 002   | loss of redundancy; expected 2     | service_group=storage-services       |          | 12:11:22.   |
|       | active members but only 1 active   |                                      |          | 174280      |
|       | member available                   |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group storage-monitoring-  | service_domain=controller.           | major    | 2022-05-31T |
| 002   | services loss of redundancy;       | service_group=storage-monitoring-    |          | 12:11:22.   |
|       | expected 1 standby member but no   | services                             |          | 131183      |
|       | standby members available          |                                      |          |             |
|       |                                    |                                      |          |             |
| 400.  | Service group distributed-cloud-   | service_domain=controller.           | major    | 2022-05-31T |
| 002   | services loss of redundancy;       | service_group=distributed-cloud-     |          | 12:11:22.   |
|       | expected 1 standby member but no   | services                             |          | 127924      |
|       | standby members available          |                                      |          |             |
|       |                                    |                                      |          |             |
| 280.  | simplex is offline                 | subcloud=simplex                     | critical | 2022-05-31T |
| 001   |                                    |                                      |          | 12:11:15.   |
|       |                                    |                                      |          | 998556      |
|       |                                    |                                      |          |             |
+-------+------------------------------------+--------------------------------------+----------+-------------+
```

### 3.2.23 Verify remote system access

**Expected Results**

Successfully SSH login from a remote SSH client

**Procedure and Results**
```bash
ssh sysadmin@<floating-ip>

Release 21.12
------------------------------------------------------------------------
W A R N I N G *** W A R N I N G *** W A R N I N G *** W A R N I N G ***
------------------------------------------------------------------------
THIS IS A PRIVATE COMPUTER SYSTEM.
This computer system including all related equipment, network devices
(specifically including Internet access), are provided only for authorized use.
All computer systems may be monitored for all lawful purposes, including to
ensure that their use is authorized, for management of the system, to
facilitate protection against unauthorized access, and to verify security
procedures, survivability and operational security. Monitoring includes active
attacks by authorized personnel and their entities to test or verify the
security of the system. During monitoring, information may be examined,
recorded, copied and used for authorized purposes. All information including
personal information, placed on or sent over this system may be monitored. Uses
of this system, authorized or unauthorized, constitutes consent to monitoring
of this system. Unauthorized use may subject you to criminal prosecution.
Evidence of any such unauthorized use collected during monitoring may be used
for administrative, criminal or other adverse action. Use of this system
constitutes consent to monitoring for these purposes.

X11 forwarding request failed on channel 0
Last login: Wed May 25 17:14:30 2022 from 192.168.133.2
/etc/motd.d/00-header:

WARNING: Unauthorized access to this system is forbidden and will be
prosecuted by law. By accessing this system, you agree that your
actions may be monitored if unauthorized usage is suspected.

[sysadmin@controller-0 ~(keystone_admin)]$

ssh sysadmin@<controller-0-ip>

Release 21.12
------------------------------------------------------------------------
W A R N I N G *** W A R N I N G *** W A R N I N G *** W A R N I N G ***
------------------------------------------------------------------------
THIS IS A PRIVATE COMPUTER SYSTEM.
This computer system including all related equipment, network devices
(specifically including Internet access), are provided only for authorized use.
All computer systems may be monitored for all lawful purposes, including to
ensure that their use is authorized, for management of the system, to
facilitate protection against unauthorized access, and to verify security
procedures, survivability and operational security. Monitoring includes active
attacks by authorized personnel and their entities to test or verify the
security of the system. During monitoring, information may be examined,
recorded, copied and used for authorized purposes. All information including
personal information, placed on or sent over this system may be monitored. Uses
of this system, authorized or unauthorized, constitutes consent to monitoring
of this system. Unauthorized use may subject you to criminal prosecution.
Evidence of any such unauthorized use collected during monitoring may be used
for administrative, criminal or other adverse action. Use of this system
constitutes consent to monitoring for these purposes.

X11 forwarding request failed on channel 0
Last login: Wed May 25 17:14:30 2022 from 192.168.133.2
/etc/motd.d/00-header:

WARNING: Unauthorized access to this system is forbidden and will be
prosecuted by law. By accessing this system, you agree that your
actions may be monitored if unauthorized usage is suspected.

[sysadmin@controller-0 ~(keystone_admin)]$

ssh sysadmin@<controller-1-ip>

Release 21.12
------------------------------------------------------------------------
W A R N I N G *** W A R N I N G *** W A R N I N G *** W A R N I N G ***
------------------------------------------------------------------------
THIS IS A PRIVATE COMPUTER SYSTEM.
This computer system including all related equipment, network devices
(specifically including Internet access), are provided only for authorized use.
All computer systems may be monitored for all lawful purposes, including to
ensure that their use is authorized, for management of the system, to
facilitate protection against unauthorized access, and to verify security
procedures, survivability and operational security. Monitoring includes active
attacks by authorized personnel and their entities to test or verify the
security of the system. During monitoring, information may be examined,
recorded, copied and used for authorized purposes. All information including
personal information, placed on or sent over this system may be monitored. Uses
of this system, authorized or unauthorized, constitutes consent to monitoring
of this system. Unauthorized use may subject you to criminal prosecution.
Evidence of any such unauthorized use collected during monitoring may be used
for administrative, criminal or other adverse action. Use of this system
constitutes consent to monitoring for these purposes.

X11 forwarding request failed on channel 0
Last login: Wed May 25 17:14:30 2022 from 192.168.133.2
/etc/motd.d/00-header:

WARNING: Unauthorized access to this system is forbidden and will be
prosecuted by law. By accessing this system, you agree that your
actions may be monitored if unauthorized usage is suspected.

[sysadmin@controller-1 ~(keystone_admin)]$
```

### 3.2.24 Verify remote update procedure

**Description**

Create and deploy a patch update strategy to automatically install a patch over the platform

**Expected Results**
Platform is updated as per the implemented strategy

**Procedure and Results**

**NOTE: This  test case assumes controller-0 to be Active Controller**
```bash
Using username "sysadmin".
Release 21.12

WARNING: If a private registry is used do not install a patch before you confirm from the release notes that new images are not needed to be uploaded first.
For patches that require new images first update the private registry and the central site registry before starting the update.


#transfer the patch to the active controller on the CaaS Manager
#connect to the active controller on the CaaS Manager
#make sure you are sourced as platform admin and change location to the directory where the patch is located
[sysadmin@controller-0 ~(keystone_admin)]$ cd /opt/backups/wr/
[sysadmin@controller-0 wr(keystone_admin)]$ ls | grep patch
WRCP_21.12_PATCH_0002.patch

#upload the patch
[sysadmin@controller-0 wr(keystone_admin)]$ sudo sw-patch upload WRCP_21.12_PATCH_0002.patch
Password: 
WRCP_21.12_PATCH_0002 is now available

#check the patch repo
[sysadmin@controller-0 wr(keystone_admin)]$ sudo sw-patch query
Password: 
      Patch ID         RR  Release  Patch State
=====================  ==  =======  ===========
WRCP_21.12_PATCH_0001  Y    21.12     Applied  
WRCP_21.12_PATCH_0002  Y    21.12    Available 

#apply the patch so that it will be initiated by the upgrade strategy
[sysadmin@controller-0 wr(keystone_admin)]$ sudo sw-patch apply WRCP_21.12_PATCH_0002
WRCP_21.12_PATCH_0002 is now in the repo
[sysadmin@controller-0 ~(keystone_admin)]$ sudo sw-patch query
Password:
      Patch ID         RR  Release   Patch State
=====================  ==  =======  =============
WRCP_21.12_PATCH_0001  Y    21.12      Applied
WRCP_21.12_PATCH_0002  Y    21.12   Partial-Apply


[sysadmin@controller-0 wr(keystone_admin)]$ sw-manager patch-strategy create
Strategy Patch Strategy:
  strategy-uuid:                          c3c07201-1122-44c4-86db-f6748bdeafe4 
  controller-apply-type:                  serial 
  storage-apply-type:                     serial 
  worker-apply-type:                      serial 
  default-instance-action:                stop-start 
  alarm-restrictions:                     strict 
  current-phase:                          build 
  current-phase-completion:               0% 
  state:                                  building 
  inprogress:                             true 
[sysadmin@controller-0 wr(keystone_admin)]$ sw-manager patch-strategy show
Strategy Patch Strategy:
  strategy-uuid:                          c3c07201-1122-44c4-86db-f6748bdeafe4 
  controller-apply-type:                  serial 
  storage-apply-type:                     serial 
  worker-apply-type:                      serial 
  default-instance-action:                stop-start 
  alarm-restrictions:                     strict 
  current-phase:                          build 
  current-phase-completion:               100% 
  state:                                  ready-to-apply 
  build-result:                           success 
  build-reason:                            
[sysadmin@controller-0 wr(keystone_admin)]$ sw-manager patch-strategy apply 
Strategy Patch Strategy:
  strategy-uuid:                          c3c07201-1122-44c4-86db-f6748bdeafe4 
  controller-apply-type:                  serial 
  storage-apply-type:                     serial 
  worker-apply-type:                      serial 
  default-instance-action:                stop-start 
  alarm-restrictions:                     strict 
  current-phase:                          apply 
  current-phase-completion:               0% 
  state:                                  applying 
  inprogress:                             true 
[sysadmin@controller-0 wr(keystone_admin)]$ 
#the node will swact and patch will be installed on the initial active controller,so if 
#the active controller was controller-0 now the active controller will be controller-1
#Connect to the active controlelr and follow the progress:
[sysadmin@controller-1 ~(keystone_admin)]$ sw-manager patch-strategy show
Strategy Patch Strategy:
  strategy-uuid:                          c3c07201-1122-44c4-86db-f6748bdeafe4
  controller-apply-type:                  serial
  storage-apply-type:                     serial
  worker-apply-type:                      serial
  default-instance-action:                stop-start
  alarm-restrictions:                     strict
  current-phase:                          apply
  current-phase-completion:               35%
  state:                                  applying
  inprogress:                             true
#after the patch is installed on controller-0 the controllers will swact again making controller-0 active to install the patch on the now locked controller-1
[sysadmin@controller-0 ~(keystone_admin)]$ sw-manager patch-strategy show
Strategy Patch Strategy:
  strategy-uuid:                          c3c07201-1122-44c4-86db-f6748bdeafe4
  controller-apply-type:                  serial
  storage-apply-type:                     serial
  worker-apply-type:                      serial
  default-instance-action:                stop-start
  alarm-restrictions:                     strict
  current-phase:                          apply
  current-phase-completion:               64%
  state:                                  applying
  inprogress:                             true

#observe the status of the nodes - controller-0 is updated while controller-1 not yet
[sysadmin@controller-0 ~(keystone_admin)]$ sudo sw-patch query-hosts
  Hostname    IP Address  Patch Current  Reboot Required  Release  State
============  ==========  =============  ===============  =======  =====
controller-0  11.11.11.3       Yes             No          21.12   idle
controller-1  11.11.11.4       No              Yes         21.12   idle
#logs can be observed from /var/log on the active CaaS Manager controller
[sysadmin@controller-0 log(keystone_admin)]$ tailf patching.log
2022-06-15T10:00:09: sw-patch-agent[32097]: patch_agent.py(559): INFO: To install: {}
2022-06-15T10:00:09: sw-patch-agent[32097]: patch_agent.py(560): INFO: To remove: []
2022-06-15T10:00:09: sw-patch-agent[32097]: patch_agent.py(561): INFO: Missing: []
2022-06-15T10:00:09: sw-patch-agent[32097]: patch_agent.py(189): INFO: Handling detailed query
2022-06-15T10:00:09: sw-patch-agent[32097]: patch_agent.py(189): INFO: Handling detailed query
2022-06-15T10:08:37: sw-patch-controller-daemon[32116]: patch_controller.py(2122): INFO: Running host-install for controller-1 (11.11.11.4), force=False, async_req=True
2022-06-15T10:08:37: sw-patch-controller-daemon[32116]: patch_controller.py(500): INFO: sending install request to node: 11.11.11.4
2022-06-15T10:08:37: sw-patch-controller-daemon[32116]: patch_controller.py(2146): INFO: host-install async_req: Patch installation request sent to controller-1.
2022-06-15T10:09:42: sw-patch-controller-daemon[32116]: patch_controller.py(146): INFO: Agent controller-1 (11.11.11.4) reporting out_of_date=False, requires_reboot=True
2022-06-15T10:09:42: sw-patch-controller-daemon[32116]: patch_controller.py(524): INFO: Handling install resp from 11.11.11.4

#when complete
[sysadmin@controller-0 log(keystone_admin)]$ sw-manager patch-strategy show
Strategy Patch Strategy:
  strategy-uuid:                          c3c07201-1122-44c4-86db-f6748bdeafe4
  controller-apply-type:                  serial
  storage-apply-type:                     serial
  worker-apply-type:                      serial
  default-instance-action:                stop-start
  alarm-restrictions:                     strict
  current-phase:                          apply
  current-phase-completion:               100%
  state:                                  applied
  apply-result:                           success
  apply-reason:
#hosts status
[sysadmin@controller-0 log(keystone_admin)]$ system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 4  | controller-1 | controller  | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+
[sysadmin@controller-0 log(keystone_admin)]$ sudo sw-patch query-hosts
Password:
  Hostname    IP Address  Patch Current  Reboot Required  Release  State
============  ==========  =============  ===============  =======  =====
controller-0  11.11.11.3       Yes             No          21.12   idle
controller-1  11.11.11.4       Yes             No          21.12   idle
#subcloud status
[sysadmin@controller-0 log(keystone_admin)]$ fm alarm-list
+----------+-------------------------------------------------+----------------------------------+----------+-----------------------+
| Alarm ID | Reason Text                                     | Entity ID                        | Severity | Time Stamp            |
+----------+-------------------------------------------------+----------------------------------+----------+-----------------------+
| 280.002  | simplex patching sync_status is out-of-sync     | subcloud=simplex.resource=       | major    | 2022-06-15T09:51:39.  |
|          |                                                 | patching                         |          | 832275                |
|          |                                                 |                                  |          |                       |
| 280.002  | duplex patching sync_status is out-of-sync      | subcloud=duplex.resource=        | major    | 2022-06-15T09:51:39.  |
|          |                                                 | patching                         |          | 731934                |
|          |                                                 |                                  |          |                       |
+----------+-------------------------------------------------+----------------------------------+----------+-----------------------+

#for the overall patch instalation of the subcloud
#copy the patch to the dedicated location
[sysadmin@controller-0 log(keystone_admin)]$ sudo cp /opt/backups/wr/WRCP_21.12_PATCH_0002.patch /opt/dc-vault/patches/21.12/
Password:
#delete the old strategy (if it exists)
[sysadmin@controller-0 log(keystone_admin)]$ dcmanager patch-strategy delete
+------------------------+----------------------------+
| Field                  | Value                      |
+------------------------+----------------------------+
| strategy type          | patch                      |
| subcloud apply type    | parallel                   |
| max parallel subclouds | 2                          |
| stop on failure        | False                      |
| state                  | deleting                   |
| created_at             | 2022-06-15T10:44:56.076092 |
| updated_at             | 2022-06-15T10:47:40.001473 |
+------------------------+----------------------------+
#create a new patch strategy for parallel deployment on 2 subclouds
[sysadmin@controller-0 log(keystone_admin)]$ dcmanager patch-strategy create --subcloud-apply-type parallel --max-parallel-subclouds 2
+------------------------+----------------------------+
| Field                  | Value                      |
+------------------------+----------------------------+
| strategy type          | patch                      |
| subcloud apply type    | parallel                   |
| max parallel subclouds | 2                          |
| stop on failure        | False                      |
| state                  | initial                    |
| created_at             | 2022-06-15T10:48:14.723482 |
| updated_at             | None                       |
+------------------------+----------------------------+
#apply the strategy - this action will initialize the patch installation
[sysadmin@controller-0 log(keystone_admin)]$ dcmanager patch-strategy apply
+------------------------+----------------------------+
| Field                  | Value                      |
+------------------------+----------------------------+
| strategy type          | patch                      |
| subcloud apply type    | parallel                   |
| max parallel subclouds | 2                          |
| stop on failure        | False                      |
| state                  | applying                   |
| created_at             | 2022-06-15T10:48:14.723482 |
| updated_at             | 2022-06-15T10:48:25.198881 |
+------------------------+----------------------------+
#check the strategy status
[sysadmin@controller-0 log(keystone_admin)]$ dcmanager patch-strategy show
+------------------------+----------------------------+
| Field                  | Value                      |
+------------------------+----------------------------+
| strategy type          | patch                      |
| subcloud apply type    | parallel                   |
| max parallel subclouds | 2                          |
| stop on failure        | False                      |
| state                  | applying                   |
| created_at             | 2022-06-15 10:48:14.723482 |
| updated_at             | 2022-06-15 10:48:25.198881 |
+------------------------+----------------------------+
#check the installation progress
[sysadmin@controller-0 log(keystone_admin)]$ dcmanager strategy-step list
+------------------+-------+-----------+---------+----------------------------+-------------+
| cloud            | stage | state     | details | started_at                 | finished_at |
+------------------+-------+-----------+---------+----------------------------+-------------+
| SystemController |     1 | finishing |         | 2022-06-15 10:48:28.005621 | None        |
| duplex           |     2 | initial   |         | None                       | None        |
| simplex          |     2 | initial   |         | None                       | None        |
+------------------+-------+-----------+---------+----------------------------+-------------+
[sysadmin@controller-0 log(keystone_admin)]$ dcmanager strategy-step list
+------------------+-------+------------------+---------+----------------------------+----------------------------+
| cloud            | stage | state            | details | started_at                 | finished_at                |
+------------------+-------+------------------+---------+----------------------------+----------------------------+
| SystemController |     1 | complete         |         | 2022-06-15 10:48:28.005621 | 2022-06-15 10:48:48.029677 |
| duplex           |     2 | updating patches |         | 2022-06-15 10:48:58.037474 | None                       |
| simplex          |     2 | updating patches |         | 2022-06-15 10:48:58.043408 | None                       |
+------------------+-------+------------------+---------+----------------------------+----------------------------+

#Watch the logs:
[sysadmin@controller-0 log(keystone_admin)]$ tailf /var/log/dcmanager/dcmanager.log
2022-06-15 10:47:40.004 159899 INFO eventlet.wsgi.server [req-49bf20ad-5cfe-4e30-8f51-6c28aa16a32a 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "DELETE /v1.0/sw-update-strategy?type=patch HTTP/1.1" status: 200  len: 444 time: 0.0560281
2022-06-15 10:47:49.620 159899 INFO eventlet.wsgi.server [req-78977cf7-1f19-4add-bc72-ae37c5b97793 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "POST /v1.0/sw-update-strategy/ HTTP/1.1" status: 422  len: 475 time: 0.0445518
2022-06-15 10:48:09.496 159903 INFO eventlet.wsgi.server [req-fe4ee194-28f9-4f13-8fa5-39bcc0e2bfda 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "GET /v1.0/sw-update-strategy?type=patch HTTP/1.1" status: 404  len: 402 time: 0.0492039
2022-06-15 10:48:14.743 159903 INFO eventlet.wsgi.server [req-af2283d7-22ee-412a-bbe9-393e4ffd16fa 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "POST /v1.0/sw-update-strategy/ HTTP/1.1" status: 200  len: 419 time: 0.0733690
2022-06-15 10:48:25.201 159899 INFO eventlet.wsgi.server [req-43a49385-eb85-48c2-8939-b2335c8c0081 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "POST /v1.0/sw-update-strategy/actions?type=patch HTTP/1.1" status: 200  len: 444 time: 0.0558181
2022-06-15 10:48:32.286 159899 INFO eventlet.wsgi.server [req-b7b5e35a-efcd-48f4-b4f9-2c279746319a 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "GET /v1.0/sw-update-strategy?type=patch HTTP/1.1" status: 200  len: 444 time: 0.0366211
2022-06-15 10:48:41.434 159899 INFO eventlet.wsgi.server [req-ac3fe546-c998-4d9e-9259-8eba6faca388 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "GET /v1.0/sw-update-strategy/steps HTTP/1.1" status: 200  len: 837 time: 0.0408509
2022-06-15 10:49:31.476 156896 INFO dcmanager.manager.service [req-9c515fc6-5d23-47ae-9d86-cfa613717ed6 - - - - -] Handling update_subcloud_endpoint_status request for subcloud: (simplex) endpoint: (platform) status:(in-sync)
2022-06-15 10:49:33.870 159899 INFO eventlet.wsgi.server [req-5f3b6672-e172-4076-bc5b-1c4bd926c719 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "GET /v1.0/sw-update-strategy/steps HTTP/1.1" status: 200  len: 974 time: 0.0516090
2022-06-15 10:49:36.510 156896 INFO dcmanager.manager.service [req-155a146e-30a8-4497-a48c-a1f172b24773 - - - - -] Handling update_subcloud_endpoint_status request for subcloud: (simplex) endpoint: (identity) status:(in-sync)
...
#check progress
[sysadmin@controller-0 dcmanager(keystone_admin)]$ dcmanager strategy-step list
+------------------+-------+-------------------+-----------------------------+----------------------------+----------------------------+
| cloud            | stage | state             | details                     | started_at                 | finished_at                |
+------------------+-------+-------------------+-----------------------------+----------------------------+----------------------------+
| SystemController |     1 | complete          |                             | 2022-06-15 10:48:28.005621 | 2022-06-15 10:48:48.029677 |
| duplex           |     2 | applying strategy | apply phase is 5% complete  | 2022-06-15 10:48:58.037474 | None                       |
| simplex          |     2 | applying strategy | apply phase is 50% complete | 2022-06-15 10:48:58.043408 | None                       |
+------------------+-------+-------------------+-----------------------------+----------------------------+----------------------------+
#check progress
[sysadmin@controller-0 dcmanager(keystone_admin)]$ dcmanager subcloud list;dcmanager strategy-step list; tail -20 dcmanager.log
+----+-------------+------------+--------------+---------------+-------------+
| id | name        | management | availability | deploy status | sync        |
+----+-------------+------------+--------------+---------------+-------------+
| 53 | duplex      | managed    | online       | complete      | out-of-sync |
| 58 | simplex     | managed    | online       | complete      | in-sync     |
+----+-------------+------------+--------------+---------------+-------------+
+------------------+-------+-------------------+-----------------------------+----------------------------+----------------------------+
| cloud            | stage | state             | details                     | started_at                 | finished_at                |
+------------------+-------+-------------------+-----------------------------+----------------------------+----------------------------+
| SystemController |     1 | complete          |                             | 2022-06-15 10:48:28.005621 | 2022-06-15 10:48:48.029677 |
| duplex           |     2 | applying strategy | apply phase is 90% complete | 2022-06-15 10:48:58.037474 | None                       |
| simplex          |     2 | complete          |                             | 2022-06-15 10:48:58.043408 | 2022-06-15 11:04:19.531900 |
+------------------+-------+-------------------+-----------------------------+----------------------------+----------------------------+
2022-06-15 11:27:13.870 159899 INFO eventlet.wsgi.server [req-38992fd4-5832-45ec-b0e3-5a0d3e658470 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "GET /v1.0/subclouds/ HTTP/1.1" status: 200  len: 3531 time: 0.0414219
2022-06-15 11:27:14.809 159899 INFO eventlet.wsgi.server [req-6525cff4-a9da-4494-bf16-0916f769189b 9046fa9663004615b84064d5aa191e42 - - default default] 11.11.11.3 "GET /v1.0/sw-update-strategy/steps HTTP/1.1" status: 200  len: 1018 time: 0.0370080
...
#Results:
[sysadmin@controller-0 dcmanager(keystone_admin)]$ dcmanager subcloud list
+----+-------------+------------+--------------+---------------+---------+
| id | name        | management | availability | deploy status | sync    |
+----+-------------+------------+--------------+---------------+---------+
| 53 | duplex      | managed    | online       | complete      | in-sync |
| 58 | simplex     | managed    | online       | complete      | in-sync |
+----+-------------+------------+--------------+---------------+---------+
[sysadmin@controller-0 dcmanager(keystone_admin)]$ dcmanager strategy-step list
+------------------+-------+----------+---------+----------------------------+----------------------------+
| cloud            | stage | state    | details | started_at                 | finished_at                |
+------------------+-------+----------+---------+----------------------------+----------------------------+
| SystemController |     1 | complete |         | 2022-06-15 10:48:28.005621 | 2022-06-15 10:48:48.029677 |
| duplex           |     2 | complete |         | 2022-06-15 10:48:58.037474 | 2022-06-15 11:32:41.114983 |
| simplex          |     2 | complete |         | 2022-06-15 10:48:58.043408 | 2022-06-15 11:04:19.531900 |
+------------------+-------+----------+---------+----------------------------+----------------------------+
[sysadmin@controller-0 dcmanager(keystone_admin)]$ fm alarm-list
#no alarms shown
[sysadmin@controller-0 dcmanager(keystone_admin)]$
```


### 3.2.25 Verify Geo-Redundant failover / failback process

**Expected Results**

A subcloud is rehomed properly from one distributed cloud to another, both manually and using automation.

**Procedure and Results**

**NOTE: Controller-0 should be the active controller on the subcloud that is to  be migrated and controller-1 should be locked**

1. Migrate subcloud manually

```bash
#On subcloud that is to be migrated.
[sysadmin@controller-0 ~(keystone_admin)]$ source /etc/platform/openrc
[sysadmin@controller-0 ~(keystone_admin)]$ system host-lock controller-1
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | locked         | disabled    | online       |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

#On the old system controller
[sysadmin@controller-0 ~(keystone_admin)]$ source /etc/platform/openrc
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud unmanage duplex

# Set the Openstack password in the subcloud as per the new system controller
[sysadmin@controller-0 ~(keystone_admin)]$ openstack user password set

# Make sure to backup the below files to the new system controller
# deployment-config-nduplex.yaml - deploymnet config file generated using the deploy tool
# dx-bootstrap_CFI_XR11.yaml - bootstrap file
# dx-install-config_CFI_XR11.yaml - install values file
# scp these files to the new CaaS Manager

#Only if Duplex
[sysadmin@controller-0 ~(keystone_admin)]$ system host-swact controller-1
[sysadmin@controller-0 ~(keystone_admin)]$ system host-lock controller-1

#On the New system controller
#Update the systemcontroller_gateway_address parameter in the bootstrap file to point to new system controller gateway

# Make sure that the active controller is controller-0 on the new system controller
# SSH using the floating IP of the new system controller
[sysadmin@controller-0 ~(keystone_admin)]$ system --os-region-name SystemController load-import --active wind-river-cloud-platform-host-installer-21.12-b45.iso wind-river-cloud-platform-host-installer-21.12-b45.sig
This operation will take a while. Please wait.
.......
+--------------------+--------+
| Property           | Value  |
+--------------------+--------+
| id                 | 1      |
| state              | active |
| software_version   | 21.12  |
| compatible_version | N/A    |
| required_patches   | N/A    |
+--------------------+--------+

[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud add --migrate --bootstrap-address 10.10.1.27 --bootstrap-values dx-bootstrap-config.yaml --sysadmin-password Dell0SS! --install-values /home/sysadmin/dx-install-config.yaml --bmc-password Dell0SS!

# Wait for the subcloud to be completed state
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud list 
+----+------------+------------+--------------+---------------+---------+
| id | name       | management | availability | deploy status | sync    |
+----+------------+------------+--------------+---------------+---------+
|  2 | SiteDuplex | managed    | online       | complete      | in-sync |
+----+------------+------------+--------------+---------------+---------+

#Check the logs for the progress 
[sysadmin@controller-0 ~(keystone_admin)]$ tailf /var/log/dcmanager/ansible/SiteDuplex_playbook_output.log

#On the subcloud which is rehomed
[sysadmin@controller-0 ~(keystone_admin)]$ system host-unlock controller-1

#Wait for controller-0 to be up and running
[sysadmin@controller-0 ~(keystone_admin)]$ system host-swact controller-0
[sysadmin@controller-0 ~(keystone_admin)]$ system host-lock controller-0
[sysadmin@controller-0 ~(keystone_admin)]$ system host-unlock controller-0
# Wait for the controller-0 to be online and enabled state
[sysadmin@controller-1 ~(keystone_admin)]$ system host-swact controller-1

#On the Old system controller from where the subcloud have to be moved
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud delete SiteDuplex

#On the system cotroller where the subcloud is migrated 
[sysadmin@controller-0 ~(keystone_admin)]$ source /etc/platform/openrc 

# Check if the subcloud is insync state
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud show SiteDuplex
+-----------------------------+-------------------------------------------+
| Field                       | Value                                     |
+-----------------------------+-------------------------------------------+
| id                          | 2                                         |
| name                        | SiteDuplex                                |
| description                 | Simplex setup for siteA                   |
| location                    | OTEL                                      |
| software_version            | 21.12                                     |
| management                  | managed                                   |
| availability                | online                                    |
| deploy_status               | complete                                  |
| management_subnet           | 11.11.11.32/28                            |
| management_start_ip         | 11.11.11.34                               |
| management_end_ip           | 11.11.11.46                               |
| management_gateway_ip       | 11.11.11.33                               |
| systemcontroller_gateway_ip | 11.11.11.9                                |
| group_id                    | 1                                         |
| created_at                  | 2022-05-06 14:23:03.896687                |
| updated_at                  | 2022-05-10 12:08:46.007035                |
| dc-cert_sync_status         | in-sync                                   |
| firmware_sync_status        | in-sync                                   |
| identity_sync_status        | in-sync                                   |
| kubernetes_sync_status      | in-sync                                   |
| kube-rootca_sync_status     | in-sync                                   |
| load_sync_status            | in-sync                                   |
| patching_sync_status        | in-sync                                   |
| platform_sync_status        | in-sync                                   |
+-----------------------------+-------------------------------------------+
```


1. Migrate subcloud using automation


**Procedure and Results**

```bash
#connect to the duplex active controller and lock the nodes:
#====================================================================
#         SYSTEM: duplex
#====================================================================

controller-0:~$ source /etc/platform/openrc
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list 
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

[sysadmin@controller-0 ~(keystone_admin)]$ system host-lock controller-1

[sysadmin@controller-0 ~(keystone_admin)]$ system host-list 
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | locked         | disabled    | online       |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

# connect to the host central site and unmanage the duplex subcloud:
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud list 
+----+-------------+------------+--------------+---------------+---------+
| id | name        | management | availability | deploy status | sync    |
+----+-------------+------------+--------------+---------------+---------+
| 34 | SiteDuplex  | managed    | online       | complete      | in-sync |
| 35 | SiteSimplex | unmanaged  | offline      | complete      | unknown |
+----+-------------+------------+--------------+---------------+---------+

[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud unmanage SiteDuplex
+-----------------------------+-------------------------------------------+
| Field                       | Value                                     |
+-----------------------------+-------------------------------------------+
| id                          | 34                                        |
| name                        | SiteDuplex                                |
| description                 | Simplex setup for siteA                   |
| location                    | OTEL                                      |
| software_version            | 21.12                                     |
| management                  | unmanaged                                 |
| availability                | online                                    |
| deploy_status               | complete                                  |
| management_subnet           | 11.11.11.32/28                            |
| management_start_ip         | 11.11.11.34                               |
| management_end_ip           | 11.11.11.46                               |
| management_gateway_ip       | 11.11.11.33                               |
| systemcontroller_gateway_ip | 11.11.11.1                                |
| group_id                    | 1                                         |
| created_at                  | 2022-05-18T11:41:30.936840                |
| updated_at                  | 2022-05-23T15:15:03.838695                |
+-----------------------------+-------------------------------------------+

# On the new CaaS manager copy the following files:
- bootstrap.yaml
- install-values.yaml
- deployment-config.yaml
# All the following steps are executed on the NEW CaaS manager
# Modify the files:
# deployment-config.yaml - make sure the administrative state is correct
[sysadmin@controller-0 ~(keystone_admin)]$ grep  "administrativeState" -B3 deployment-config-SiteDuplex.yaml 
  name: controller-0-profile
  namespace: deployment
spec:
  administrativeState: unlocked
--
  name: controller-1-profile
  namespace: deployment
spec:
  administrativeState: locked
--
  name: worker-0-profile
  namespace: deployment
spec:
  administrativeState: unlocked
--
  name: worker-1-profile
  namespace: deployment
spec:
  administrativeState: unlocked
  
# Make sure the bmc password is set
[sysadmin@controller-0 ~(keystone_admin)]$ grep -e "bmc-" -B6 deployment-config-SiteDuplex.yaml 
apiVersion: v1
data:
  password: "RGVsbDBTUyE="
  username: cm9vdA==
kind: Secret
metadata:
  name: bmc-secret


# Make sure the license information is added:
[sysadmin@controller-0 ~(keystone_admin)]$ grep content deployment-config-SiteDuplex.yaml -A 6 -B3
---
apiVersion: v1
data:
  content: IyBXaW5kIFJpdmVyIFByb2R1Y3QgQWN0aXZhdGlvbiBGaWxlIChpbnN0YWxsLnR4dCkKIyBJc3N1ZWQgZm9yIGhvc3Q6IDxEZWxsPiA8RGVsbD4gPEFueT4KIyBMaWNlbnNlIG51bWJlcihzKTogNjgwMTUyCiMgSXNzdWVkIG9uOiAyNy1qYW4tMjAyMiAwOTo1MDo1MAojCiMgTm90ZTogdGhpcyBsaWNlbnNlIGlzIGdlbmVyYXRlZCBjdW11bGF0aXZlbHkgZm9yIGFsbAojIFdpbmQgUml2ZXIgc29mdHdhcmUgbWFuYWdlZCBieSB0aGlzIGhvc3QuCgojIDEuIEZsZXhMTSBsaWNlbnNlIGZpbGU6CiMgQmVnaW46IFNlcnZlciBsaWNlbnNlICAtLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBTZXJpYWwgTnVtYmVyOiA2ODAxNTItRGVsbC1HNFdEQzlDUEVLCgpQQUNLQUdFIFdSQ1BfQ09OVEFJTkVSX1BLRyB3cnNkIDIxIDAwNDY1REZDRUI5QiBcCglDT01QT05FTlRTPVdSQ1BfQ09OVEFJTkVSOjIxLjEyIE9QVElPTlM9U1VJVEUgXAoJU0lHTj0yNTAwQzhCMjRFRDAKSU5DUkVNRU5UIFdSQ1BfQ09OVEFJTkVSX1BLRyB3cnNkIDIxIHBlcm1hbmVudCB1bmNvdW50ZWQgNkVGNTQ4RUJDRkNDIFwKCVZFTkRPUl9TVFJJTkc9PGxuPjY4MDE1MjwvbG4+PHBzPjIyMTMtNDM8L3BzPiBIT1NUSUQ9QU5ZIFwKCUlTU1VFRD0yNy1qYW4tMjAyMiBTTj1zZXJpYWwtRGVsbC1MVjJJV0FVTEVCIFNUQVJUPTI3LWphbi0yMDIyIFwKCVNJR049NzQxQ0ZEQTRFRDA2Cg==
kind: Secret
metadata:
  name: system-license
  namespace: deployment
type: Opaque
---


# Change the bootstrap.yml file:

# Get the docker sysinv login from the target central site
[sysadmin@controller-0 ~(keystone_admin)]$ keyring get sysinv services
la9qwFz=W95DKAB=
*Replace the password in the bootstrap.yml file with the one just optained.

# Make sure that you have the docker additional images section updated in the bootstrap.yml file

# Migrate the subcloud
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud add --migrate --bootstrap-address 10.10.1.27 --bootstrap-values dx-bootstrap-config.yaml --install-values dx-install-config.yaml --sysadmin-password 'Dell2022!' --bmc-password Dell0SS!
+-----------------------------+-------------------------------------------+
| Field                       | Value                                     |
+-----------------------------+-------------------------------------------+
| id                          | 5                                         |
| name                        | SiteDuplex                                |
| description                 | Simplex setup for siteA                   |
| location                    | OTEL                                      |
| software_version            | 21.12                                     |
| management                  | unmanaged                                 |
| availability                | offline                                   |
| deploy_status               | not-deployed                              |
| management_subnet           | 11.11.11.32/28                            |
| management_start_ip         | 11.11.11.34                               |
| management_end_ip           | 11.11.11.46                               |
| management_gateway_ip       | 11.11.11.33                               |
| systemcontroller_gateway_ip | 11.11.11.9                                |
| group_id                    | 1                                         |
| created_at                  | 2022-05-23 15:37:46.377883                |
| updated_at                  | None                                      |
+-----------------------------+-------------------------------------------+

[sysadmin@controller-0 ~(keystone_admin)]$ tailf /var/log/dcmanager/ansible/SiteDuplex_playbook_output.log 
PLAY RECAP *********************************************************************
duplex                 : ok=55   changed=44   unreachable=0    failed=0   

Monday 23 May 2022  15:42:14 +0000 (0:00:03.016)       0:04:14.981 ************ 
=============================================================================== 
rehome-subcloud/update-keystone-data : Update docker registry credentials - 105.38s
rehome-subcloud/update-keystone-data : Apply puppet subcloud rehome manifest -- 26.08s
rehome-subcloud/update-keystone-data : Update keystone passwords ------- 20.88s
rehome-subcloud/update-sc-cert : Applying puppet runtime manifest ------ 13.95s
rehome-subcloud/update-network-config : Add new system-controller network -- 11.61s
rehome-subcloud/update-keystone-data : Wait until keystone is restarted -- 11.36s
rehome-subcloud/update-network-config : Add new system-controller OAM network -- 10.97s
rehome-subcloud/update-sc-cert : Remove sc-cert namespace if exists ----- 5.71s
rehome-subcloud/update-keystone-data : Store service passwords in keyring --- 4.20s
rehome-subcloud/update-keystone-data : Update services passwords in hieradata --- 3.12s
rehome-subcloud/check-services-status : Check all services are enabled-active --- 3.02s
rehome-subcloud/update-network-config : Get previous system controller network uuid --- 2.83s
rehome-subcloud/update-network-config : Add system controller subnet ---- 2.71s
rehome-subcloud/prepare-env : Get existing docker no_proxy -------------- 2.52s
rehome-subcloud/update-network-config : Delete previous system controller subnet --- 2.50s
rehome-subcloud/update-network-config : Add system controller OAM subnet --- 2.30s
rehome-subcloud/prepare-env : Get management interface of controller-1 if the subcloud is not simplex --- 2.18s
rehome-subcloud/update-network-config : Get previous system controller OAM network uuid --- 2.12s
rehome-subcloud/prepare-env : Get management interface of controller-0 --- 2.11s
rehome-subcloud/update-network-config : Check existing host route in controller-0 --- 2.08s


# Connect to the OLD CaaS Manager from where the subcloud was migrated and delete it
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud list
+----+-------------+------------+--------------+---------------+---------+
| id | name        | management | availability | deploy status | sync    |
+----+-------------+------------+--------------+---------------+---------+
| 34 | SiteDuplex  | unmanaged  | offline      | complete      | unknown |
+----+-------------+------------+--------------+---------------+---------+

[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud delete SiteDuplex
[sysadmin@controller-0 ~(keystone_admin)]$ 

# Connect back to the NEW CaaS Manager central controller and check the status:
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud list
+----+------------+------------+--------------+---------------+---------+
| id | name       | management | availability | deploy status | sync    |
+----+------------+------------+--------------+---------------+---------+
|  5 | SiteDuplex | unmanaged  | offline      | complete      | unknown |
+----+------------+------------+--------------+---------------+---------+

# Check the route list to the subcloud:
[sysadmin@controller-0 ~(keystone_admin)]$ system host-route-list controller-0
+--------------------------------------+--------+-------------+--------+------------+--------+
| uuid                                 | ifname | network     | prefix | gateway    | metric |
+--------------------------------------+--------+-------------+--------+------------+--------+
| a0914b12-75c9-4bf5-8662-fd3c87f4fd3e | mgmt0  | 11.11.11.32 | 28     | 11.11.11.9 | 1      |
+--------------------------------------+--------+-------------+--------+------------+--------+
[sysadmin@controller-0 ~(keystone_admin)]$ system host-route-list controller-1
+--------------------------------------+--------+-------------+--------+------------+--------+
| uuid                                 | ifname | network     | prefix | gateway    | metric |
+--------------------------------------+--------+-------------+--------+------------+--------+
| caa554f3-a2b2-4f5c-9e63-46157260304d | mgmt0  | 11.11.11.32 | 28     | 11.11.11.9 | 1      |
+--------------------------------------+--------+-------------+--------+------------+--------+

# Connect on the duplex subcloud controller-0 and unlock the nodes
====================================================================
         SYSTEM: SiteDuplex
====================================================================

#source the environment
controller-0:~$ source /etc/platform/openrc

# Check the system application list:
[sysadmin@controller-0 ~(keystone_admin)]$ system application-list 
+--------------------------+----------+-----------------------------------+----------------------------------------+----------+-----------+
| application              | version  | manifest name                     | manifest file                          | status   | progress  |
+--------------------------+----------+-----------------------------------+----------------------------------------+----------+-----------+
| cert-manager             | 21.12-28 | cert-manager-manifest             | certmanager-manifest.yaml              | applied  | completed |
| nginx-ingress-controller | 21.12-18 | nginx-ingress-controller-manifest | nginx_ingress_controller_manifest.yaml | applied  | completed |
| oidc-auth-apps           | 21.12-61 | oidc-auth-manifest                | manifest.yaml                          | uploaded | completed |
| platform-integ-apps      | 21.12-44 | platform-integration-manifest     | manifest.yaml                          | applied  | completed |
| rook-ceph-apps           | 1.0-14   | rook-ceph-manifest                | manifest.yaml                          | uploaded | completed |
+--------------------------+----------+-----------------------------------+----------------------------------------+----------+-----------+

# Check the hosts
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list 
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | locked         | disabled    | online       |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

[sysadmin@controller-0 ~(keystone_admin)]$ system host-unlock controller-1

# After controller-1 is back online and available perform the swact
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

[sysadmin@controller-0 ~(keystone_admin)]$ system host-swact controller-0

# After you swact connect to controller-1 and lock unlock the remaining nodes if needed and mandatory lock unlock controller-0
# Wait for 5-7 mintues for the two controllers to sync
[sysadmin@controller-1 ~(keystone_admin)]$ system host-lock controller-0

#wait for the node to become locked:
[sysadmin@controller-1 ~(keystone_admin)]$ system host-list
+----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | locked         | disabled    | online       |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
| 11 | worker-1     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

#Unlock controller-0
[sysadmin@controller-1 ~(keystone_admin)]$ system host-unlock controller-0

#After controller-0 is back online the controller can be swact back
[sysadmin@controller-0 ~(keystone_admin)]$ system host-swact controller-1

#On the NEW CaaS Manager wait for the subcloud to become online run
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud manage SiteDuplex

#Wait for 5-7 minutes for the controllers to sync and check
[sysadmin@controller-0 ~(keystone_admin)]$ dcmanager subcloud list
+----+-------------+------------+--------------+---------------+---------+
| id | name        | management | availability | deploy status | sync    |
+----+-------------+------------+--------------+---------------+---------+
| 5  | SiteDuplex  | managed    | online       | complete      | in-sync |
+----+-------------+------------+--------------+---------------+---------+


```

### 3.2.30 Verify system interfaces

**Expected Results**
1. **OAM** network should be assigned to the proper interface. ( Only on the controllers)
2. **MGMT** network should be assigned to the proper interface.
3. **PXEBOOT** network should be assigned to the proper interface.
4. **ClusterHost** network should be assigned to the proper interface.

**Procedure and Results**

```bash
# Check if all the networks are assigned to the respective interfaces.
for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system interface-network-list $host;done

controller-0
#####
+--------------+--------------------------------------+--------------+--------------+
| hostname     | uuid                                 | ifname       | network_name |
+--------------+--------------------------------------+--------------+--------------+
| controller-0 | 2d9c450b-00fc-4331-8095-673027fbe10e | pxeboot0     | pxeboot      |
| controller-0 | 6ea0dac5-d290-45af-9a15-6e914508b617 | oam0         | oam          |
| controller-0 | c63c2403-b465-4fc2-95b4-357a85ce637f | clusterhost0 | cluster-host |
| controller-0 | f7bbb516-1531-4792-aef8-e50b15f51e0e | mgmt0        | mgmt         |
+--------------+--------------------------------------+--------------+--------------+
controller-1
#####
+--------------+--------------------------------------+--------------+--------------+
| hostname     | uuid                                 | ifname       | network_name |
+--------------+--------------------------------------+--------------+--------------+
| controller-1 | 3c140691-2448-4ab2-b814-f9dc19d37944 | mgmt0        | mgmt         |
| controller-1 | 512ce3c4-fd95-4d6d-8998-47a17bb4fc41 | clusterhost0 | cluster-host |
| controller-1 | 5f56d8e9-6915-4180-8cb4-bd63c1afa1c7 | oam0         | oam          |
| controller-1 | d1d536a7-70d8-4453-8775-3db301bc4067 | pxeboot0     | pxeboot      |
+--------------+--------------------------------------+--------------+--------------+
worker-0
#####
+----------+--------------------------------------+--------------+--------------+
| hostname | uuid                                 | ifname       | network_name |
+----------+--------------------------------------+--------------+--------------+
| worker-0 | 2874797c-e785-4f42-98f6-6fe337b3748c | mgmt0        | mgmt         |
| worker-0 | abe96783-e87a-4c76-a972-dd36a43e82f4 | clusterhost0 | cluster-host |
| worker-0 | f1b18004-25ee-44c2-a446-59f1c2d0ef81 | pxeboot0     | pxeboot      |
+----------+--------------------------------------+--------------+--------------+
worker-1
#####
+----------+--------------------------------------+--------------+--------------+
| hostname | uuid                                 | ifname       | network_name |
+----------+--------------------------------------+--------------+--------------+
| worker-1 | 9705f460-ee93-4b2c-8624-1bb7a4e5802d | pxeboot0     | pxeboot      |
| worker-1 | a8203ab1-50bd-4145-a327-11a211d81e40 | mgmt0        | mgmt         |
| worker-1 | cb6f929c-ac8b-4c43-9d1c-58270dfcb0eb | clusterhost0 | cluster-host |
+----------+--------------------------------------+--------------+--------------+
```

**NOTE:**
**1. Controllers should have the OAM,MGMT,PXEBOOT, CLUSTERHOST networks.**
**2. Workers should have PXEBOOT, MGMT and CLUSTERHOST networks**
	
### 3.2.27 Reboot an unlocked node

**Expected Results**

Unlocked node should reject a reboot request

**Procedure and Results**

```bash
# Reboot the nodes that are in unlocked stated
for host in $(system host-list | grep -v id | awk '{print $4}'); do echo $host; echo "#####";system host-reboot $host;done

controller-0
#####
Can not 'Reboot' an 'unlocked' host controller-0; Please 'Lock' first
controller-1
#####
Can not 'Reboot' an 'unlocked' host controller-1; Please 'Lock' first
worker-0
#####
Can not 'Reboot' an 'unlocked' host worker-0; Please 'Lock' first
worker-1
#####
Can not 'Reboot' an 'unlocked' host worker-1; Please 'Lock' first
```



### 3.2.28 Verify production and content of Performance Counters, verify the Cloud Platform does performance monitoring to trigger alarms

**Expected Results**

Demonstrate the Cloud Platform performance monitoring mechanism (collectd).

**Procedure and Results**

```bash
# Open a parallel session and create a file that will use most of the disk space                   
[sysadmin@controller-0 ~(keystone_admin)]$ dd if=/dev/zero of=/home/sysadmin/test.file bs=1024M count=7                                                                                                    
7+0 records in                                                                                  
7+0 records out                                                                                
7516192768 bytes (7.5 GB) copied, 16.1491 s, 465 MB/s 

[sysadmin@controller-0 ~(keystone_admin)]$ df -a | grep sda                                     
/dev/sda4                         20027216 17657880   1328952  94% /                            
/dev/sda4                         20027216 17657880   1328952  94% /usr/local/kubernetes/curren 
t/stage2                                                                                        
/dev/sda4                         20027216 17657880   1328952  94% /usr/local/kubernetes/curren 
t/stage1                                                                                        
/dev/sda1                         30106488    45080  28509024   1% /opt/platform-backup         
/dev/sda3                           487634   115348    342590  26% /boot                        
/dev/sda2                           307016    10352    296664   4% /boot/efi                    


#follow the collectd log for the output
[sysadmin@controller-0 ~(keystone_admin)]$ tailf /var/log/collectd.log
2022-06-08T13:06:06.040 controller-0 collectd[110955]: info alarm notifier reading: 88.17 % usage - /
2022-06-08T13:06:06.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (1:0) False
2022-06-08T13:06:36.041 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (2:0) False
2022-06-08T13:07:06.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (3:0) False
2022-06-08T13:07:36.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (4:0) False
2022-06-08T13:07:36.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (5:0) False
2022-06-08T13:08:06.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (6:0) False
2022-06-08T13:09:06.330 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (7:0) True
2022-06-08T13:09:06.372 controller-0 collectd[110955]: info alarm notifier set alarm 100.104:warning /:host=controller-0.filesystem=/ value:88.17
2022-06-08T13:10:36.040 controller-0 collectd[110955]: info alarm notifier reading: 88.17 % usage - /

[sysadmin@controller-0 ~(keystone_admin)]$ fm alarm-list                                        
+-------+--------------------------------------------+---------------+----------+-------------+ 
| Alarm | Reason Text                                | Entity ID     | Severity | Time Stamp  | 
| ID    |                                            |               |          |             | 
+-------+--------------------------------------------+---------------+----------+-------------+ 
| 100.  | File System threshold exceeded ; threshold | host=         | major    | 2022-06-08T | 
| 104   | 80.00%, actual 88.17%                      | controller-0. |          | 13:09:06.   | 
|       |                                            | filesystem=/  |          | 331012      | 
|       |                                            |               |          |             | 
+-------+--------------------------------------------+---------------+----------+-------------+ 
[sysadmin@controller-0 ~(keystone_admin)]$ rm test.file

```


### 3.2.29 Verify existence and content of log files

**Expected Results**

Check if  the logs files are being generated.

**Procedure and Results**

```bash
# check the logs in the /var/log directory.
cd /var/log/
ls -lrt

drwx------.  2 root     root         4096 Oct 30  2018 audit
drwxr-xr-x.  2 root     root         4096 Dec 13  2018 glusterfs
drwx------.  2 root     root         4096 Oct  1  2020 httpd
drwxr-xr-x.  2 ntp      ntp          4096 Jan 10 08:00 ntpstats
drwxr-x---.  2 lighttpd lighttpd     4096 Jan 10 08:32 lighttpd
drwxr-x---.  2 root     root         4096 Jan 10 08:49 radosgw
drwxr-xr-x.  2 root     root         4096 Jan 10 08:53 openvswitch
drwx------.  2 root     root        16384 Apr 27 12:54 lost+found
-rw-------.  1 root     utmp            0 Apr 27 12:56 btmp
drwx------.  3 root     root         4096 Apr 27 12:57 samba
drwx------.  4 root     root         4096 Apr 27 12:57 libvirt
-rw-r--r--.  1 root     root          193 Apr 27 12:59 grubby_prune_debug
drwxr-xr-x.  2 root     root         4096 Apr 27 13:02 anaconda
drwxr-xr-x.  2 root     root         4096 Apr 27 13:02 rhsm
drwxr-xr-x   2 root     root         4096 Apr 27 13:05 crash
-rw-r--r--   1 root     root            0 Apr 27 13:05 lighttpd-access.log
drwxr-xr-x.  2 root     root         4096 Apr 27 13:05 tuned
-rw-r-----   1 root     root            0 Apr 27 13:05 patching-api.log
-rw-r--r--   1 root     root            0 Apr 27 13:05 sm-trap.log
-rw-r-----   1 root     root          106 Apr 27 18:48 horizon.log
drwxr-x---.  2 keystone keystone     4096 Apr 27 18:52 keystone
drwxr-xr-x   3 root     root         4096 Apr 27 18:52 calico
-rw-r--r--   1 root     root          286 Apr 27 18:53 lighttpd-error.log
-rw-------   1 root     root       120908 Apr 27 19:00 dmesg.old
drwxr-x---.  2 apache   apache       4096 Apr 27 19:03 horizon
drwxrwx--T.  2 root     root         4096 Apr 27 20:31 ceph
drwxr-x---.  2 root     root         4096 Apr 27 20:31 rabbitmq
drwxr-xr-x.  2 root     root         4096 Apr 27 20:31 dcdbsync
drwxr-xr-x.  2 root     root         4096 Apr 27 20:31 dcorch
drwxr-xr-x.  3 root     root         4096 Apr 27 20:31 dcmanager
drwxr-xr-x.  2 root     root         4096 Apr 28 00:00 sa
drwxr-x---.  2 barbican barbican     4096 Apr 28 00:50 barbican
-rw-r-----   1 root     root       850113 Apr 28 03:05 daemon-ocf.log.2.gz
-rw-r--r--   1 root     root          126 Apr 28 05:53 sm-shutdown.log
-rw-------   1 root     root       120222 Apr 28 05:56 dmesg
-rw-r-----   1 root     root        26521 Apr 28 05:57 patching.log
-rw-------   1 root     root        21965 Apr 28 05:57 grubby
-rw-r-----   1 root     root        44098 Apr 28 05:58 guestServer.log
-rw-r-----   1 root     root        42311 Apr 28 05:58 lmond.log
-rw-r-----   1 root     root        41212 Apr 28 05:58 hostwd.log
-rw-r-----   1 root     root        39838 Apr 28 05:58 mtclogd.log
drwxr-x---.  8 puppet   puppet       4096 Apr 28 06:04 puppet
-rw-r-----   1 root     root       528155 Apr 28 06:07 mtcAgent_event.log
-rw-r-----   1 root     root       865020 Apr 28 10:20 daemon-ocf.log.1.gz
-rw-r-----   1 root     root         5870 Apr 28 10:20 syslog
-rw-r--r--   1 root     root       201730 Apr 28 12:05 hawkey.log
-rw-r--r--   1 root     root      7175828 Apr 28 13:43 multus.log
drwxr-xr-x  15 root     root         4096 Apr 28 13:43 pods
-rw-r-----   1 root     root       133212 Apr 28 14:02 hbsClient.log
-rw-r--r--   1 root     root        21051 Apr 28 14:04 mgr-restful-plugin.log
-rw-r--r--   1 root     root         2862 Apr 28 14:05 dnf.rpm.log
-rw-r--r--   1 root     root       334445 Apr 28 14:05 dnf.librepo.log
-rw-r--r--   1 root     root        80227 Apr 28 14:05 dnf.log
drwxr-xr-x   2 root     root         4096 Apr 28 14:08 containers
-rw-------.  1 root     root      2715264 Apr 28 14:08 tallylog
-rw-r--r--.  1 root     root     12388684 Apr 28 14:08 lastlog
-rw-r-----   1 root     root          891 Apr 28 14:08 nfv-vim-api.log
-rw-r-----   1 root     root          891 Apr 28 14:08 nfv-vim-webserver.log
-rw-r-----   1 root     root         5278 Apr 28 14:09 hwmond_api.log
-rw-r-----   1 root     root        64276 Apr 28 14:09 hwmond.log
-rw-r-----   1 root     root        56009 Apr 28 14:09 platform.log
-rw-r-----   1 root     root       120433 Apr 28 14:09 mtcalarmd.log
-rw-r-----   1 root     root        68658 Apr 28 14:09 mtcClient.log
-rw-r--r--   1 root     root        84861 Apr 28 14:09 sm-customer.alarm
-rw-r-----   1 root     root       276091 Apr 28 14:09 fm-event.log
-rw-r-----   1 root     root       296692 Apr 28 14:09 mtcAgent.log
-rw-r-----   1 root     root       100478 Apr 28 14:09 sysinv-api.log
-rw-r-----   1 root     root       375154 Apr 28 14:09 mtcAgent_api.log
-rw-r--r--   1 root     root       422166 Apr 28 14:09 sm-scheduler.log
-rw-r-----   1 root     root        93000 Apr 28 14:09 cert-mon.log
-rw-r-----   1 root     root        93510 Apr 28 14:09 cert-alarm.log
-rw-r-----   1 root     root        51574 Apr 28 14:10 cron.log
-rw-r-----   1 root     root       106660 Apr 28 14:10 pmond.log
-rw-r-----   1 root     root      8226924 Apr 28 14:11 containerd.log
-rw-r-----   1 root     root       242983 Apr 28 14:11 openstack.log
-rw-r-----   1 root     root       638010 Apr 28 14:11 user.log
-rw-r-----   1 root     root       672209 Apr 28 14:12 haproxy.log
-rw-r-----   1 root     root      1382917 Apr 28 14:12 sysinv.log
-rw-------   1 root     root       524729 Apr 28 14:12 fm-manager.log
-rw-r-----   1 root     root      2099795 Apr 28 14:12 collectd.log
-rw-r--r--   1 root     root      1105203 Apr 28 14:12 ceph-manager.log
-rw-rw-r--.  1 root     utmp        38784 Apr 28 14:12 wtmp
-rw-r-----   1 root     root      1606898 Apr 28 14:13 hbsAgent.log
-rw-r-----   1 root     root       652826 Apr 28 14:13 fsmond.log
-rw-r-----   1 root     root       207066 Apr 28 14:13 postgres.log
-rw-r-----   1 root     root      1989396 Apr 28 14:13 kern.log
-rw-r-----   1 root     root       774856 Apr 28 14:13 nfv-vim.log
-rw-r-----   1 root     root      3959577 Apr 28 14:13 daemon.log
-rw-r-----   1 root     root       248410 Apr 28 14:13 auth.log
-rw-r-----   1 root     root      6190369 Apr 28 14:13 daemon-ocf.log
-rw-r-----   1 root     root      2981965 Apr 28 14:13 sm.log
-rw-r--r--   1 root     root       667691 Apr 28 14:13 sm-customer.log
-rw-------   1 root     root       128578 Apr 28 14:13 bash.log

#sample output of counters 
[sysadmin@controller-0 ~(keystone_admin)]$ tailf /var/log/collectd.log
2022-06-08T13:06:06.040 controller-0 collectd[110955]: info alarm notifier reading: 88.17 % usage - /
2022-06-08T13:06:06.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (1:0) False
2022-06-08T13:06:36.041 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (2:0) False
2022-06-08T13:07:06.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (3:0) False
2022-06-08T13:07:36.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (4:0) False
2022-06-08T13:08:06.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (5:0) False
2022-06-08T13:08:36.040 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (6:0) False
2022-06-08T13:09:06.330 controller-0 collectd[110955]: info alarm notifier File System host=controller-0.filesystem=/ debounce 'okay -> warning' (88.17) (7:0) True
2022-06-08T13:09:06.372 controller-0 collectd[110955]: info alarm notifier set alarm 100.104:warning /:host=controller-0.filesystem=/ value:88.17
2022-06-08T13:10:36.040 controller-0 collectd[110955]: info alarm notifier reading: 88.17 % usage - /

```

**NOTE: The output may vary depending on the node**

### 3.2.30 View CaaS Licence

**Expected Results**

License should be applied for the CaaS Platform

**Procedure and Results**
```bash
 system license-show 

 # Wind River Product Activation File (install.txt)
# Issued for host: <Dell> <Dell> <Any>
# License number(s): 680152
# Issued on: 27-jan-2022 09:50:50
#
# Note: this license is generated cumulatively for all
# Wind River software managed by this host.

# 1. FlexLM license file:
# Begin: Server license  ---------------------
# Serial Number: 680152-Dell-G4WDC9CPEK

PACKAGE WRCP_CONTAINER_PKG wrsd 21 00465DFCEB9B \
	COMPONENTS=WRCP_CONTAINER:21.12 OPTIONS=SUITE \
	SIGN=2500C8B24ED0
INCREMENT WRCP_CONTAINER_PKG wrsd 21 permanent uncounted 6EF548EBCFCC \
	VENDOR_STRING=<ln>680152</ln><ps>2213-43</ps> HOSTID=ANY \
	ISSUED=27-jan-2022 SN=serial-Dell-LV2IWAULEB START=27-jan-2022 \
	SIGN=741CFDA4ED06
 ```

### 3.2.31 View online help

**Expected Results**

All required Personnel are able to access the online support portal for the the cloud platforms

```bash
[support](https://support2.windriver.com/)
```

### 3.2.32 Verify data export

**Expected Results**

Get system data using the platform REST-API

**Procedure and Results**

```bash
NOTE: If https is enabled the address command should point to the puplic https endpoint active on port 5000/6385
For https use https:// with -k; for http use http:/ without -k. 

[sysadmin@controller-0 ~(keystone_admin)]$ system show | grep https
| https_enabled          | True                                 |
[sysadmin@controller-0 ~(keystone_admin)]$ openstack endpoint list | grep 5000
| 65efbea29fd44499a57af8962a2867cd | RegionOne        | keystone     | identity        | True    | public    | https://10.10.1.2:5000/v3    |
| 7872f1490dfd4ca49c41a1575d96f61f | RegionOne        | keystone     | identity        | True    | internal  | http://11.11.11.2:5000/v3    |
| 03a390c6a4e9430589e62261ca17d9ab | SystemController | keystone     | identity        | True    | internal  | http://11.11.11.2:25000/v3   |
| 1fe47a590e8b437ab66de47f758ece66 | SystemController | keystone     | identity        | True    | public    | https://10.10.1.2:25000/v3   |
[sysadmin@controller-0 ~(keystone_admin)]$ openstack endpoint list | grep 6385
| fdccfb52e87642c39efa8e007ef063ba | RegionOne        | sysinv       | platform        | True    | internal  | http://11.11.11.2:6385/v1    |
| ad03e7b87d034ef2b7249d1792d22806 | SystemController | sysinv       | platform        | True    | internal  | http://11.11.11.2:26385/v1   |
| b2e5ca822a9745ff8071c39628af3d57 | RegionOne        | sysinv       | platform        | True    | public    | https://10.10.1.2:6385/v1    |
| 5804243360934c99bbb97c7c2f9597f6 | SystemController | sysinv       | platform        | True    | public    | https://10.10.1.2:26385/v1   |
#https
curl -i -k -H "Content-Type: application/json" -d '{"auth":{"identity":{"methods":["password"],"password":{"user":{"name":"admin","domain":{"id":"default"},"password":"Dell0SS!"}}}, "scope": {"project": {"name": "admin", "domain": {"id": "default"}}}}}' https://10.10.1.2:5000/v3/auth/tokens --silent | grep "X-Subject-Token" | awk '{print $2}'
gAAAAABiuzFkap5AuYyXZES28NnMuJIrmRGrJP0_p7bfljCmjIivHttJvyHW044LIv5AlN-CDQnMqWkyRh16dz31dbzwypaRcjiRcfxV_iw9z-HIODooRyR_GhE7IUdvaFrvA2Nett_WMIW44-xotiN9TA9rr7gYe1w82RrM-bBkajYItm1djbI

TOKEN=gAAAAABiuzFkap5AuYyXZES28NnMuJIrmRGrJP0_p7bfljCmjIivHttJvyHW044LIv5AlN-CDQnMqWkyRh16dz31dbzwypaRcjiRcfxV_iw9z-HIODooRyR_GhE7IUdvaFrvA2Nett_WMIW44-xotiN9TA9rr7gYe1w82RrM-bBkajYItm1djbI

# curl the hosts api and chek if the host list is recieved as the response. Use the token in the previous step in the header
[sysadmin@controller-0 ~(keystone_admin)]$ curl -i -k https://10.10.1.2:6385/v1/ihosts/ -X GET -H "Content-Type: application/json" -H "X-Auth-Token: $TOKEN" --silent| tail -n 1| python -m json.tool
{
    "ihosts": [
        {
            "action": "none",
            "administrative": "unlocked",
            "availability": "available",
            "bm_ip": "192.168.110.13",
            "bm_type": "dynamic",
            "bm_username": "root",
            "boot_device": "/dev/disk/by-path/pci-0000:65:00.0-scsi-0:3:110:0",
            "capabilities": {
                "Personality": "Controller-Active",
                "stor_function": "monitor"
            },
            "clock_synchronization": "ntp",
            "config_applied": "106307a1-0840-4183-8093-b10dceae55ef",
            "config_status": null,
            "config_target": "106307a1-0840-4183-8093-b10dceae55ef",
            "console": "tty0",
            "created_at": "2022-03-04T13:59:15.413528+00:00",
            "device_image_update": null,
            "hostname": "controller-0",
            "id": 1,
            "ihost_action": "unlock",
            "install_output": "text",
            "install_state": null,
            "install_state_info": null,
            "inv_state": "inventoried",
            "invprovision": "provisioned",
            "iscsi_initiator_name": "iqn.1994-05.com.redhat:3be51fb5a70",
            "isystem_uuid": "59b02829-217a-4041-b83d-6e2f3ef294e8",
            "links": [
                {
                    "href": "https://10.10.1.2:6385/v1/ihosts/cfa807ea-955e-40d6-a481-5c3e32b48744",
                    "rel": "self"
                },
                {
                    "href": "https://10.10.1.2:6385/ihosts/cfa807ea-955e-40d6-a481-5c3e32b48744",
                    "rel": "bookmark"
                }
            ],
            "location": {},
            "mgmt_ip": "11.11.11.3",
            "mgmt_mac": "b4:96:91:bc:32:b2",
            "mtce_info": "{bmc_protocol:redfish}",
            "operational": "enabled",
            "peers": null,
            "personality": "controller",
            "reboot_needed": false,
            "reserved": "False",
            "rootfs_device": "/dev/disk/by-path/pci-0000:65:00.0-scsi-0:3:110:0",
            "serialid": null,
            "software_load": "21.12",
            "subfunction_avail": "available",
            "subfunction_oper": "enabled",
            "subfunctions": "controller,worker",
            "target_load": "21.12",
            "task": "",
            "tboot": "false",
            "ttys_dcd": null,
            "updated_at": "2022-06-28T16:52:25.821193+00:00",
            "uptime": 1147664,
            "uuid": "cfa807ea-955e-40d6-a481-5c3e32b48744",
            "vim_progress_status": "services-enabled"
        },
        {
            "action": "none",
            "administrative": "unlocked",
            "availability": "available",
            "bm_ip": "192.168.110.7",
            "bm_type": "dynamic",
            "bm_username": "root",
            "boot_device": "/dev/sdc",
            "capabilities": {
                "Personality": "Controller-Standby",
                "stor_function": "monitor"
            },
            "clock_synchronization": "ntp",
            "config_applied": "032dd639-2741-4efa-afec-869079551c1c",
            "config_status": null,
            "config_target": "032dd639-2741-4efa-afec-869079551c1c",
            "console": "tty0",
            "created_at": "2022-03-04T16:59:52.961211+00:00",
            "device_image_update": null,
            "hostname": "controller-1",
            "id": 4,
            "ihost_action": "unlock",
            "install_output": "text",
            "install_state": "completed+",
            "install_state_info": null,
            "inv_state": "inventoried",
            "invprovision": "provisioned",
            "iscsi_initiator_name": "iqn.1994-05.com.redhat:79f74c28283c",
            "isystem_uuid": "59b02829-217a-4041-b83d-6e2f3ef294e8",
            "links": [
                {
                    "href": "https://10.10.1.2:6385/v1/ihosts/fe83fa01-81f9-411b-96c5-977a99f21e62",
                    "rel": "self"
                },
                {
                    "href": "https://10.10.1.2:6385/ihosts/fe83fa01-81f9-411b-96c5-977a99f21e62",
                    "rel": "bookmark"
                }
            ],
            "location": {
                "locn": ""
            },
            "mgmt_ip": "11.11.11.4",
            "mgmt_mac": "b8:ce:f6:10:c9:bc",
            "mtce_info": "{bmc_protocol:redfish}",
            "operational": "enabled",
            "peers": null,
            "personality": "controller",
            "reboot_needed": false,
            "reserved": "False",
            "rootfs_device": "/dev/sdc",
            "serialid": null,
            "software_load": "21.12",
            "subfunction_avail": "available",
            "subfunction_oper": "enabled",
            "subfunctions": "controller,worker",
            "target_load": "21.12",
            "task": "",
            "tboot": "false",
            "ttys_dcd": "False",
            "updated_at": "2022-06-28T16:52:49.045569+00:00",
            "uptime": 1146863,
            "uuid": "fe83fa01-81f9-411b-96c5-977a99f21e62",
            "vim_progress_status": "services-enabled"
        }
    ]
}

```

### 3.2.33 Verify remote console access

**Expected Results**

Successfully login to the CaaS nodes using SSH remotely

**Procedure and Results**

```bash
ssh sysadmin@<floating-ip>

Release 21.12
------------------------------------------------------------------------
W A R N I N G *** W A R N I N G *** W A R N I N G *** W A R N I N G ***
------------------------------------------------------------------------
THIS IS A PRIVATE COMPUTER SYSTEM.
This computer system including all related equipment, network devices
(specifically including Internet access), are provided only for authorized use.
All computer systems may be monitored for all lawful purposes, including to
ensure that their use is authorized, for management of the system, to
facilitate protection against unauthorized access, and to verify security
procedures, survivability and operational security. Monitoring includes active
attacks by authorized personnel and their entities to test or verify the
security of the system. During monitoring, information may be examined,
recorded, copied and used for authorized purposes. All information including
personal information, placed on or sent over this system may be monitored. Uses
of this system, authorized or unauthorized, constitutes consent to monitoring
of this system. Unauthorized use may subject you to criminal prosecution.
Evidence of any such unauthorized use collected during monitoring may be used
for administrative, criminal or other adverse action. Use of this system
constitutes consent to monitoring for these purposes.

X11 forwarding request failed on channel 0
Last login: Wed May 25 17:14:30 2022 from 192.168.133.2
/etc/motd.d/00-header:

WARNING: Unauthorized access to this system is forbidden and will be
prosecuted by law. By accessing this system, you agree that your
actions may be monitored if unauthorized usage is suspected.

[sysadmin@controller-0 ~(keystone_admin)]$

ssh sysadmin@<controller-0-ip>

Release 21.12
------------------------------------------------------------------------
W A R N I N G *** W A R N I N G *** W A R N I N G *** W A R N I N G ***
------------------------------------------------------------------------
THIS IS A PRIVATE COMPUTER SYSTEM.
This computer system including all related equipment, network devices
(specifically including Internet access), are provided only for authorized use.
All computer systems may be monitored for all lawful purposes, including to
ensure that their use is authorized, for management of the system, to
facilitate protection against unauthorized access, and to verify security
procedures, survivability and operational security. Monitoring includes active
attacks by authorized personnel and their entities to test or verify the
security of the system. During monitoring, information may be examined,
recorded, copied and used for authorized purposes. All information including
personal information, placed on or sent over this system may be monitored. Uses
of this system, authorized or unauthorized, constitutes consent to monitoring
of this system. Unauthorized use may subject you to criminal prosecution.
Evidence of any such unauthorized use collected during monitoring may be used
for administrative, criminal or other adverse action. Use of this system
constitutes consent to monitoring for these purposes.

X11 forwarding request failed on channel 0
Last login: Wed May 25 17:14:30 2022 from 192.168.133.2
/etc/motd.d/00-header:

WARNING: Unauthorized access to this system is forbidden and will be
prosecuted by law. By accessing this system, you agree that your
actions may be monitored if unauthorized usage is suspected.

[sysadmin@controller-0 ~(keystone_admin)]$

ssh sysadmin@<controller-1-ip>

Release 21.12
------------------------------------------------------------------------
W A R N I N G *** W A R N I N G *** W A R N I N G *** W A R N I N G ***
------------------------------------------------------------------------
THIS IS A PRIVATE COMPUTER SYSTEM.
This computer system including all related equipment, network devices
(specifically including Internet access), are provided only for authorized use.
All computer systems may be monitored for all lawful purposes, including to
ensure that their use is authorized, for management of the system, to
facilitate protection against unauthorized access, and to verify security
procedures, survivability and operational security. Monitoring includes active
attacks by authorized personnel and their entities to test or verify the
security of the system. During monitoring, information may be examined,
recorded, copied and used for authorized purposes. All information including
personal information, placed on or sent over this system may be monitored. Uses
of this system, authorized or unauthorized, constitutes consent to monitoring
of this system. Unauthorized use may subject you to criminal prosecution.
Evidence of any such unauthorized use collected during monitoring may be used
for administrative, criminal or other adverse action. Use of this system
constitutes consent to monitoring for these purposes.

X11 forwarding request failed on channel 0
Last login: Wed May 25 17:14:30 2022 from 192.168.133.2
/etc/motd.d/00-header:

WARNING: Unauthorized access to this system is forbidden and will be
prosecuted by law. By accessing this system, you agree that your
actions may be monitored if unauthorized usage is suspected.

[sysadmin@controller-1 ~(keystone_admin)]$


```

### 3.2.34 Verify self-healing behaviour

**Expected Results**

Poweroff the active controller from the BMC and see if the system is able to recover to the standby node.

**Procedure and Results**

**NOTE: Check the Active Controller, This test case assumes that controller-0 is active**

```bash
# login to the active controller using OAM floating-ip
# you should be logged in to controller-0
# source the environment
# Check the nodes status

 [sysadmin@controller-0]$ source /etc/platform/openrc
 [sysadmin@controller0 ~(keystone_admin)]$ system host-list
 +----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

# Poweroff controller-0 immediately from the BMC console/BIOS or unplug the power cable
# you need to start a new ssh session to the OAM floating-ip
# this time you should be logged in on controller-1 , because it will be the active controller now.
# Check the nodes and services
# controller-0 should be offline 
# all the platform pods and services should now be running on controller-1.

 [sysadmin@controller-1]$ source /etc/platform/openrc
 [sysadmin@controller-1 ~(keystone_admin)]$ system host-list
 +----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | disabled    | offline      |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

[sysadmin@controller-0 ~(keystone_admin)]$ fm alarm-list
+----------+--------------------------------------------------------------------------------------------------------------------------+------------------------------------+----------+-----------------------+
| Alarm ID | Reason Text                                                                                                              | Entity ID                          | Severity | Time Stamp            |
+----------+--------------------------------------------------------------------------------------------------------------------------+------------------------------------+----------+-----------------------+
| 400.005  | Communication failure detected with peer over port vlan301 on host controller-0                                          | host=controller-0.network=mgmt     | major    | 2022-06-28T19:13:24.  |
|          |                                                                                                                          |                                    |          | 931849                |
|          |                                                                                                                          |                                    |          |                       |
| 400.005  | Communication failure detected with peer over port vlan12 on host controller-0                                           | host=controller-0.network=oam      | major    | 2022-06-28T19:13:24.  |
|          |                                                                                                                          |                                    |          | 926594                |
|          |                                                                                                                          |                                    |          |                       |
| 400.005  | Communication failure detected with peer over port vlan311 on host controller-0                                          | host=controller-0.network=cluster- | major    | 2022-06-28T19:13:24.  |
|          |                                                                                                                          | host                               |          | 680412                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group oam-services loss of redundancy; expected 1 standby member but no standby members available                | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=oam-services         |          | 791922                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group controller-services loss of redundancy; expected 1 standby member but no standby members available         | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=controller-services  |          | 790152                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group cloud-services loss of redundancy; expected 1 standby member but no standby members available              | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=cloud-services       |          | 788037                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group vim-services loss of redundancy; expected 1 standby member but no standby members available                | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=vim-services         |          | 745610                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group patching-services loss of redundancy; expected 1 standby member but no standby members available           | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=patching-services    |          | 743624                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group directory-services loss of redundancy; expected 2 active members but only 1 active member available        | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=directory-services   |          | 722161                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group web-services loss of redundancy; expected 2 active members but only 1 active member available              | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=web-services         |          | 680051                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group storage-services loss of redundancy; expected 2 active members but only 1 active member available          | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=storage-services     |          | 678176                |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group storage-monitoring-services loss of redundancy; expected 1 standby member but no standby members available | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=storage-monitoring-  |          | 676099                |
|          |                                                                                                                          | services                           |          |                       |
|          |                                                                                                                          |                                    |          |                       |
| 400.002  | Service group distributed-cloud-services loss of redundancy; expected 1 standby member but no standby members available  | service_domain=controller.         | major    | 2022-06-28T19:10:43.  |
|          |                                                                                                                          | service_group=distributed-cloud-   |          | 633325                |
|          |                                                                                                                          | services                           |          |                       |
|          |                                                                                                                          |                                    |          |                       |
| 400.003  | Evaluation license key will expire on 19-aug-2022; there are 52 days remaining in this evaluation                        | host=controller-0                  | minor    | 2022-06-28T08:25:44.  |
|          |                                                                                                                          |                                    |          | 409089                |
|          |                                                                                                                          |                                    |          |                       |
| 400.003  | Evaluation license key will expire on 19-aug-2022; there are 52 days remaining in this evaluation                        | host=controller-1                  | minor    | 2022-06-28T00:07:10.  |
|          |                                                                                                                          |                                    |          | 277490                |
|          |                                                                                                                          |                                    |          |                       |
+----------+--------------------------------------------------------------------------------------------------------------------------+------------------------------------+----------+-----------------------+


[sysadmin@controller-1 ~(keystone_admin)]$ system host-show controller-1 | grep capabilities 

| capabilities          | {u'stor_function': u'monitor', u'Personality': u'Controller-Active'} |

# Check the services status on controller-1
 [sysadmin@controller-1 ~(keystone_admin)]$  sudo sm-dump

 -Service_Groups------------------------------------------------------------------------
oam-services                     active               active
controller-services              active               active
cloud-services                   active               active
patching-services                active               active
directory-services               active               active
web-services                     active               active
storage-services                 active               active
storage-monitoring-services      active               active
vim-services                     active               active
distributed-cloud-services       active               active
---------------------------------------------------------------------------------------

-Services------------------------------------------------------------------------------
oam-ip                           enabled-active       enabled-active
management-ip                    enabled-active       enabled-active
drbd-pg                          enabled-active       enabled-active
drbd-rabbit                      enabled-active       enabled-active
drbd-platform                    enabled-active       enabled-active
pg-fs                            enabled-active       enabled-active
rabbit-fs                        enabled-active       enabled-active
nfs-mgmt                         enabled-active       enabled-active
platform-fs                      enabled-active       enabled-active
postgres                         enabled-active       enabled-active
rabbit                           enabled-active       enabled-active
platform-export-fs               enabled-active       enabled-active
platform-nfs-ip                  enabled-active       enabled-active
sysinv-inv                       enabled-active       enabled-active
sysinv-conductor                 enabled-active       enabled-active
mtc-agent                        enabled-active       enabled-active
hw-mon                           enabled-active       enabled-active
dnsmasq                          enabled-active       enabled-active
fm-mgr                           enabled-active       enabled-active
keystone                         enabled-active       enabled-active
lighttpd                         enabled-active       enabled-active
patch-alarm-manager              enabled-active       enabled-active
mgr-restful-plugin               enabled-active       enabled-active
ceph-manager                     enabled-active       enabled-active
vim                              enabled-active       enabled-active
vim-api                          enabled-active       enabled-active
vim-webserver                    enabled-active       enabled-active
haproxy                          enabled-active       enabled-active
pxeboot-ip                       enabled-active       enabled-active
drbd-extension                   enabled-active       enabled-active
extension-fs                     enabled-active       enabled-active
extension-export-fs              enabled-active       enabled-active
etcd                             enabled-active       enabled-active
drbd-etcd                        enabled-active       enabled-active
etcd-fs                          enabled-active       enabled-active
barbican-api                     enabled-active       enabled-active
barbican-keystone-listener       enabled-active       enabled-active
barbican-worker                  enabled-active       enabled-active
cluster-host-ip                  enabled-active       enabled-active
dcdbsync-api                     enabled-active       enabled-active
docker-distribution              enabled-active       enabled-active
dockerdistribution-fs            enabled-active       enabled-active
drbd-dockerdistribution          enabled-active       enabled-active
ceph-mon                         enabled-active       enabled-active
cephmon-fs                       enabled-active       enabled-active
drbd-cephmon                     enabled-active       enabled-active
ceph-osd                         enabled-active       enabled-active
helmrepository-fs                enabled-active       enabled-active
registry-token-server            enabled-active       enabled-active
cert-mon                         enabled-active       enabled-active
device-image-fs                  enabled-active       enabled-active
cert-alarm                       enabled-active       enabled-active
------------------------------------------------------------------------------

# Check the Alarms.
# we should see lot of redundancy alarms related to controller-0 and platform networking.
 [sysadmin@controller-1 ~(keystone_admin)]$ fm alarm-list # empty result means there are no alarms


# Power-on controller-0 and wait until it is unlocked, enabled and available.
 [sysadmin@controller-1 ~(keystone_admin)]$  watch system host-list
 +----+--------------+-------------+----------------+-------------+--------------+
| id | hostname     | personality | administrative | operational | availability |
+----+--------------+-------------+----------------+-------------+--------------+
| 1  | controller-0 | controller  | unlocked       | enabled     | available    |
| 2  | controller-1 | controller  | unlocked       | enabled     | available    |
| 9  | worker-0     | worker      | unlocked       | enabled     | available    |
+----+--------------+-------------+----------------+-------------+--------------+

# the controller-0 is the standby controller now.
sysadmin@controller-1 ~(keystone_admin)]$ system host-show controller-1 | grep capabilities 

| capabilities          | {u'stor_function': u'monitor', u'Personality': u'Controller-Active'} |

sysadmin@controller-1 ~(keystone_admin)]$ system host-show controller-0 | grep capabilities 

| capabilities          | {u'stor_function': u'monitor', u'Personality': u'Controller-standby'} |} |

# Check the Alarms.
# All the Alarms related to controller-0 and platform networking should be cleared.

 ```
**NOTE The controller power down should come up and should show as unlocked and enabled in host-list**

### 3.2.35 Verify system health after deployment

**Expected Results**

The system is in healthy state after the installation

**Procedure and Results**

```bash
# Login to active controller using floating-ip
# Source the environment
# Check the system health
sysadmin@controller-1]$ source /etc/platform/openrc
sysadmin@controller-1~(keystone_admin)]$ system health-query
System Health:
All hosts are provisioned: [OK]
All hosts are unlocked/enabled: [OK]
All hosts have current configurations: [OK]
All hosts are patch current: [OK]
Ceph Storage Healthy: [OK]
No alarms: [OK]
All kubernetes nodes are ready: [OK]
All kubernetes control plane pods are ready: [OK]

# Check the status of all the services in the sm.
sysadmin@controller-1~(keystone_admin)]$ sudo sm-dump

-Service_Groups------------------------------------------------------------------------
oam-services                     active               active
controller-services              active               active
cloud-services                   active               active
patching-services                active               active
directory-services               active               active
web-services                     active               active
storage-services                 active               active
storage-monitoring-services      active               active
vim-services                     active               active
distributed-cloud-services       active               active
---------------------------------------------------------------------------------------

-Services------------------------------------------------------------------------------
oam-ip                           enabled-active       enabled-active
management-ip                    enabled-active       enabled-active
drbd-pg                          enabled-active       enabled-active
drbd-rabbit                      enabled-active       enabled-active
drbd-platform                    enabled-active       enabled-active
pg-fs                            enabled-active       enabled-active
rabbit-fs                        enabled-active       enabled-active
nfs-mgmt                         enabled-active       enabled-active
platform-fs                      enabled-active       enabled-active
postgres                         enabled-active       enabled-active
rabbit                           enabled-active       enabled-active
platform-export-fs               enabled-active       enabled-active
platform-nfs-ip                  enabled-active       enabled-active
sysinv-inv                       enabled-active       enabled-active
sysinv-conductor                 enabled-active       enabled-active
mtc-agent                        enabled-active       enabled-active
hw-mon                           enabled-active       enabled-active
dnsmasq                          enabled-active       enabled-active
fm-mgr                           enabled-active       enabled-active
keystone                         enabled-active       enabled-active
lighttpd                         enabled-active       enabled-active
patch-alarm-manager              enabled-active       enabled-active
mgr-restful-plugin               enabled-active       enabled-active
ceph-manager                     enabled-active       enabled-active
vim                              enabled-active       enabled-active
vim-api                          enabled-active       enabled-active
vim-webserver                    enabled-active       enabled-active
haproxy                          enabled-active       enabled-active
pxeboot-ip                       enabled-active       enabled-active
drbd-extension                   enabled-active       enabled-active
extension-fs                     enabled-active       enabled-active
extension-export-fs              enabled-active       enabled-active
etcd                             enabled-active       enabled-active
drbd-etcd                        enabled-active       enabled-active
etcd-fs                          enabled-active       enabled-active
barbican-api                     enabled-active       enabled-active
barbican-keystone-listener       enabled-active       enabled-active
barbican-worker                  enabled-active       enabled-active
cluster-host-ip                  enabled-active       enabled-active
dcdbsync-api                     enabled-active       enabled-active
docker-distribution              enabled-active       enabled-active
dockerdistribution-fs            enabled-active       enabled-active
drbd-dockerdistribution          enabled-active       enabled-active
ceph-mon                         enabled-active       enabled-active
cephmon-fs                       enabled-active       enabled-active
drbd-cephmon                     enabled-active       enabled-active
ceph-osd                         enabled-active       enabled-active
helmrepository-fs                enabled-active       enabled-active
registry-token-server            enabled-active       enabled-active
cert-mon                         enabled-active       enabled-active
device-image-fs                  enabled-active       enabled-active
cert-alarm                       enabled-active       enabled-active
------------------------------------------------------------------------------
```

### 3.2.36 Record the CaaS Platform installation time

**Expected Results**
We will expect different results, depending on Network connectivity between the sites and nodes.
We expect the installation time be between:
- 30 - 60 minutes for a AIO simplex 
- 60 - 120 miuntes for other site types

ZTP:
- 1h AIO Simplex
- 2h - 2H30m AIO Duplex (can increase slightly depending on the number of workers)
NOTE: for ZTP the nodes are installed and fully configured with the previously exported settings.


```bash
- 30 - 60 minutes for a AIO simplex 
- 60 - 120 miuntes for other site types
```

### 3.4.1 Basic Calico CNI functionality test on Cloud Platform node

**Expected Results**

1. Bring up two pods.
2. Ping each other.

**Procedure and Results**

```bash
# files needed
#	- pod images: 
#		- busybox 
#	- pod creation yaml file

#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document

# Create a manifest file for launching the pods for the testcase and create the pods.
[sysadmin@controller-0 ~(keystone_admin)]$ cat <EOF> calico.yml
apiVersion: v1
kind: Pod
metadata:
    name: calico-1
spec:
    imagePullSecrets:
    - name: registry-creds
    containers:
    - name: calico-1
      image: registry.local:9001/ps_emea/busybox:22.06
      command: ['sh','-c']
      args: ['while true;do sleep 10;done;']
---
apiVersion: v1
kind: Pod
metadata:
    name: calico-2
spec:
    imagePullSecrets:
    - name: registry-creds
    containers:
    - name: calico-2
      image: registry.local:9001/ps_emea/busybox:22.06
      command: ['sh','-c']
      args: ['while true;do sleep 10;done;']
EOF
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl apply -f calico.yml

# Check if the pods are up and running without any issue
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl get pods -o wide | grep calico

calico-1                              1/1     Running   0          20s    172.16.43.42     worker-0       <none>           <none>
calico-2                              1/1     Running   0          20s    172.16.43.43     worker-0       <none>           <none>


# Get the Ip address of each pods and try ping each other and verify if it works.

[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec  calico-1 -- ping -c 2 172.16.43.43
PING 172.16.43.43 (172.16.43.43): 56 data bytes
64 bytes from 172.16.43.43: seq=0 ttl=63 time=0.095 ms
64 bytes from 172.16.43.43: seq=1 ttl=63 time=0.044 ms
--- 172.16.43.43 ping statistics ---
2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max = 0.044/0.069/0.095 ms


[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec  calico-2 -- ping -c 2 172.16.43.42
PING 172.16.43.42 (172.16.43.42): 56 data bytes
64 bytes from 172.16.43.42: seq=0 ttl=63 time=0.061 ms
64 bytes from 172.16.43.42: seq=1 ttl=63 time=0.032 ms

--- 172.16.43.42 ping statistics ---
2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max = 0.032/0.046/0.061 ms


[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec  calico-2 -- traceroute 172.16.166.154

traceroute to 172.16.166.154 (172.16.166.154), 30 hops max, 46 byte packets
 1  worker-0 (11.11.11.43)  0.003 ms  0.001 ms  0.001 ms
 2  192-168-206-3.kubernetes.default.svc.cluster.local (192.168.206.3)  0.258 ms  0.266 ms  0.248 ms
 3  172.16.166.154 (172.16.166.154)  0.296 ms  0.302 ms  0.312 ms

[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec  calico-2 -- ip route
default via 169.254.1.1 dev eth0
169.254.1.1 dev eth0 scope link
```

### 3.4.2 Verify the Egress rule for Egress Network Policies:

**Expected Results**

1. NetworkPolicy is created for test1 namespace.
2. All the traffic to BMC network from the pods on test1 namespace will be blocked and dropped.

**Procedure and Results**
```bash
# files needed
#	- pod images: 
#		- centos 
#	- pod creation yaml file

#download and copy the image to the subcloud active controller(version can be different)
#load/tag/push the image to the subcloud registry 
#create a kubernetes secret - steps available APPENDIX-end of the document

# Create two namespaces
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl create namespace test1
namespace/test1 created

[sysadmin@controller-0 ~(keystone_admin)]$ kubectl create namespace test2
namespace/test2 created

# Create secrets in both the namespaces for the kuberentes to pull the images from local registry
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl create secret docker-registry registry-creds --docker-username=sysinv --docker-password=$(keyring get sysinv services) --docker-server=registry.local:9001 -n test1
secret/registry-creds created


[sysadmin@controller-0 ~(keystone_admin)]$ kubectl create secret docker-registry registry-creds --docker-username=sysinv --docker-password=$(keyring get sysinv services) --docker-server=registry.local:9001 -n test2
secret/registry-creds created

# Create the file which contains the network policy 
[sysadmin@controller-0 ~(keystone_admin)]$ vim namespaces_test_policy.yml 
apiVersion: crd.projectcalico.org/v1
kind: NetworkPolicy
metadata:
  name: deny-egress-bmc
  namespace: test1
spec:
  types:
    - Egress
  egress:
    - action: Deny
      destination:
        nets:
        - 192.168.110.0/24
    - action: Allow
      destination:
        nets:
          - 0.0.0.0/0
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-claim1
  namespace: test1
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: cephfs
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod1
  namespace: test1
spec:
  imagePullSecrets:
    - name: registry-creds
  containers:
   - name: test-pod
     image: registry.local:9001/ps_emea/centos:22.06.0
     volumeMounts:
       - name: ceph-volume
         mountPath: /mnt
     command: ["/bin/sh","-c", "--"]
     args: ["while true; do sleep 10; done;"]
  volumes:
    - name: ceph-volume
      persistentVolumeClaim:
        claimName: test-claim1
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-claim2
  namespace: test2
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: cephfs
---
apiVersion: v1
kind: Pod
metadata:
  name: test-pod2
  namespace: test2
spec:
  imagePullSecrets:
    - name: registry-creds
  containers:
   - name: test-pod
     image: registry.local:9001/ps_emea/centos:22.06.0
     volumeMounts:
       - name: ceph-volume
         mountPath: /mnt
     command: ["/bin/sh","-c", "--"]
     args: ["while true; do sleep 10; done;"]
  volumes:
    - name: ceph-volume
      persistentVolumeClaim:
        claimName: test-claim2
---

# Create the networkpolicy, pods in both the namespaces.
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl apply -f namespaces_test_policy.yml 
networkpolicy.crd.projectcalico.org/deny-egress-bmc created

# Check if the resources all the resources are up.
NAME        READY   STATUS    RESTARTS   AGE
test-pod1   1/1     Running   0          76s

NAME          STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
test-claim1   Bound    pvc-19a5c737-30db-467a-80f3-55df319b8fd0   1Gi        RWO            cephfs         76s

NAME        READY   STATUS    RESTARTS   AGE
test-pod2   1/1     Running   0          76s

NAME          STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
test-claim2   Bound    pvc-346cd5aa-d5e7-46e6-994a-64f97486a132   1Gi        RWO            cephfs         77s

# The BMC network access traffics will be blocked for all the pods on namespace test1.
# Pods on netspace test2 will still have connectivity to the BMC network
# Ping will be used for connectivity test.
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec -it test-pod1 -n test1 -- /bin/bash -c "ping 192.168.110.35 -c 3;exit"
PING 192.168.110.35 (192.168.110.35) 56(84) bytes of data.

--- 192.168.110.35 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 2041ms
command terminated with exit code 1

# Make sure that pods on other namespaces (test2) have still access to the BMC network
[sysadmin@controller-0 ~(keystone_admin)]$ kubectl exec -it test-pod2 -n test2 -- /bin/bash -c "ping 192.168.110.35 -c 3;exit"
PING 192.168.110.35 (192.168.110.35) 56(84) bytes of data.
64 bytes from 192.168.110.35: icmp_seq=1 ttl=62 time=0.675 ms
64 bytes from 192.168.110.35: icmp_seq=2 ttl=62 time=0.687 ms
64 bytes from 192.168.110.35: icmp_seq=3 ttl=62 time=0.660 ms

--- 192.168.110.35 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2083ms
rtt min/avg/max/mdev = 0.660/0.674/0.687/0.011 ms
```


### 3.2.37 CaaS Manager Backup/Restore

**Description**
Describe and verify the backup and recovery procedure/process for the CaaS manager.  

There are 3 recovery cases: 

    Recover a faulty controller using another healthy controller node. 
    Recover a faulty site from scratch using deployment manager 
    Recover a faulty site using remote ansible restore command 

All the above cases will be covered. 

**Expected Results** 

    Backup:  

The following files are created and moved to a safe location: 

    Deployment configuration yaml files 
    Hosts.xml 
    localhost tar.gz files 
    Certificates  

    Recovery:  

    The faulty controller will be re-installed and recovered using the active controller 
    The backed-up files and ZTP automation will be used to recover the whole CaaS-Manager site. 
    The ansible recovery command will be used to restore the backup files and system 
    
**Execution and procedure: 


```bash
#Backup  

Make sure there is at least 10G of free disk space in /opt/backups 
Files needed  
- backup tar files 
- hosts.xml 
- deployment-config.yaml 
- deploy tool 
- localhost-backup.yaml 

#The deploy tool available for download from delivers.windriver.com (always use the one as per the installed patch on the platform)  
#generate the deployment-config.yaml file from the active controller as admin 
[sysadmin@controller-0 ~(keystone_admin)]$ ./deploy build -n deployment -s caasmanager --minimal-config 

#expected output 
building deployment for system "caasmanager" in namespace "deployment" 
building namespace configuration 
building system configuration 
...filtering system attributes 
building system endpoint secret configuration 
building system license secret configuration 
building certificate secret configurations 
building data network configurations 
building platform network configurations
building PTP instance configurations 
building PTP interface configurations
building host and profile configurations 
...Building host configuration for "controller-0" 
...Building host profile configuration for "controller-0" 
...Running profile filters for "controller-0-profile" 
...Building host configuration for "controller-1" 
...Building host profile configuration for "controller-1" 
...Running profile filters for "controller-1-profile" 
re-running profile filters for second pass 
...Running profile filters for "controller-0-profile" 
...Running profile filters for "controller-1-profile" 
simplifying profile configurations 
done. 
Warning: The generated deployment configuration contains kubernetes 
  Secrets that must be manually edited to add information that is not 
  retrievable from the system.  For example, any BMC Secrets must be 
  edited to add the password and any SSL Secrets must be edited to add 
  the certificate and key information.  Any such information must be 
  added in base64 encoded format. 
[sysadmin@controller-0 ~(keystone_admin)]$ ls | grep deployment 
deployment-config.yaml 
[sysadmin@controller-0 ~(keystone_admin)]$  

#add the bmc password encrypted in the deployment-config.yaml file 
[sysadmin@controller-0 ~(keystone_admin)]$ BMC_PWD=password 
[sysadmin@controller-0 ~(keystone_admin)]$ echo $(echo -n "${BMC_PWD}" | base64 -w0) 
cGFzc3dvcmQ= 

#edit the deployment-config.yaml file 
[sysadmin@controller-0 ~(keystone_admin)]$ vim deployment-config.yaml 
#edit the section: 
--- 
apiVersion: v1 
data: 
  password: "" 
  username: YWRtaW4= 
kind: Secret 
metadata: 
  name: bmc-secret 
  namespace: deployment 
type: kubernetes.io/basic-auth 
--- 
#add the password 
--- 
apiVersion: v1 
data: 
  password: "cGFzc3dvcmQ=" 
  username: YWRtaW4= 
kind: Secret 
metadata: 
  name: bmc-secret 
  namespace: deployment 
type: kubernetes.io/basic-auth 
--- 
#save the file and copy it to a safe location  
#create the backup playbook yaml file under /home/sysadmin 
#[sysadmin@controller-0 ~(keystone_admin)]$ cat << EOF > localhost-backup.yaml 
#> --- 
#> ansible_become_pass: "<admin_password>" 
#> admin_password: "<admin_password>" 
#> backup_user_local_registry: "true" 
#> ... 
#> EOF 
[sysadmin@controller-0 ~(keystone_admin)]$ ls | grep backup 
localhost-backup.yaml 
#execute the backup playbook file in a screen session: 
[sysadmin@controller-0 ~(keystone_admin)]$ screen -S backup 
[sysadmin@controller-0 ~(keystone_admin)]$ ansible-playbook /usr/share/ansible/stx-ansible/playbooks/backup.yml 
#expected execution time ~10 minutes 
#the tar file will be generated under /opt/backups on controller-0 
NOTE: The content of the disks will not be saved, the data that is not saved outside the formatted controller will be lost. 
The restoration will occur only for the platform services and applications. 
Example: all the data saved in /opt/backups/ in controller-1 will not be restored unless the data was previously moved. 
#expected output: 
PLAY RECAP ********************************************************************************************************************************************************************************************************************************* 
localhost                  : ok=128  changed=60   unreachable=0    failed=0    
Tuesday 21 June 2022  09:18:19 +0200 (0:00:00.021)       0:06:52.170 **********  
===============================================================================  
backup/backup-system : Create a tgz archive for dc-vault backup ------------------------------------------------------------------------------------------------------------------------------------------------------------------- 158.13s 
backup/backup-system : Create a tgz archive for platform backup ------------------------------------------------------------------------------------------------------------------------------------------------------------------- 114.34s 
backup/backup-system : Notify applications that backup succeeded ------------------------------------------------------------------------------------------------------------------------------------------------------------------- 65.93s 
backup/backup-system : Create the override backup file ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 3.65s 
common/push-docker-images : Get the k8s_registry barbican secret if it's authenticated ---------------------------------------------------------------------------------------------------------------------------------------------- 3.46s 
common/push-docker-images : Get the docker_registry barbican secret if it's authenticated ------------------------------------------------------------------------------------------------------------------------------------------- 3.06s 
common/push-docker-images : Get the quay_registry barbican secret if it's authenticated --------------------------------------------------------------------------------------------------------------------------------------------- 3.01s 
backup/backup-system : Check the size (in KiB) of directories that will be backed up for platform ----------------------------------------------------------------------------------------------------------------------------------- 3.00s 
common/push-docker-images : Get the elastic_registry barbican secret if it's authenticated ------------------------------------------------------------------------------------------------------------------------------------------ 3.00s 
common/push-docker-images : Get the gcr_registry barbican secret if it's authenticated ---------------------------------------------------------------------------------------------------------------------------------------------- 2.98s 
common/push-docker-images : Get the ghcr_registry barbican secret if it's authenticated --------------------------------------------------------------------------------------------------------------------------------------------- 2.96s 
backup/backup-system : Get etcd endpoints ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.59s 
common/push-docker-images : Query the docker_registry ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.55s 
backup/prepare-env : Check if it is the active controller --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.53s 
common/push-docker-images : Query the quay_registry --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.53s 
common/push-docker-images : Query the gcr_registry ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.53s 
common/push-docker-images : Query the ghcr_registry --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.49s 
common/push-docker-images : Query the elastic_registry ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 2.49s 
backup/backup-system : Get openstack application status ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.48s 
common/push-docker-images : Query the k8s_registry ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.48s 
[sysadmin@controller-0 ~(keystone_admin)]$ 

#check the files 
[sysadmin@controller-0 ~(keystone_admin)]$ ls -lrth /opt/backups/ | grep backup
-rw-r--r-- 1 root     root          1,8G iun 27 09:16 localhost_docker_local_registry_backup_2022_06_27_09_15_01.tgz
-rw-r--r-- 1 root     root          2,4G iun 27 09:19 localhost_platform_backup_2022_06_27_09_15_01.tgz
-rw-r--r-- 1 root     root           146 iun 27 09:19 localhost_dc_vault_backup_2022_06_27_09_15_01.tgz

# move these files to a safe location 
#generate the host.xml export file 
#from the active controller connect as admin 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-bulk-export  
Export successfully to ./hosts.xml 
[sysadmin@controller-0 ~(keystone_admin)]$ ls | grep xml 
hosts.xml 

####Restore: 
    Recover one controller from the active controller 
Restore controller: 
NOTE: The content of the disks will not be restored, the data that is not saved outside the formatted controller will be lost. 
The restoration will occur only for the platform services and applications. 
Example: all the data saved in /opt/backups/ in controller-1 will not be restored unless the data was previously moved. 

#connect on the active controller as admin and check the hosts 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list  
+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | enabled     | available    | 
+----+--------------+-------------+----------------+-------------+--------------+ 
#ssh to controller-1 and format the node 
[sysadmin@controller-0 ~(keystone_admin)]$ ssh controller-1 
#execute the wipe disk command 
controller-1:~$ sudo wipedisk 
Password:  
This will result in the loss of all data on the hard drives and 
will require this node to be re-installed. 
The following disks will be wiped: 
    /dev/sda 
    /dev/sda5 
  
Are you absolutely sure? [y/n] y 
Type 'wipediskscompletely' to confirm: wipediskscompletely 

#power off controller-1 
#check the status from the active controller 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list  
+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | disabled    | offline      | 
+----+--------------+-------------+----------------+-------------+--------------+ 
[sysadmin@controller-0 ~(keystone_admin)]$ fm alarm-list  
+----------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------+----------+-----------------------+ 
| Alarm ID | Reason Text                                                                                                           | Entity ID                            | Severity | Time Stamp            | 
+----------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------+----------+-----------------------+ 
| 200.009  | controller-1 experienced a persistent critical 'Cluster-host Network' communication failure.                          | host=controller-1.network=Cluster-   | critical | 2022-06-21T14:54:17.  | 
|          |                                                                                                                       | host                                 |          | 054527                | 
|          |                                                                                                                       |                                      |          |                       | 
| 400.005  | Communication failure detected with peer over port vlan311 on host controller-0                                       | host=controller-0.network=cluster-   | major    | 2022-06-21T14:54:17.  | 
|          |                                                                                                                       | host                                 |          | 054047                | 
|          |                                                                                                                       |                                      |          |                       | 
| 200.004  | controller-1 experienced a service-affecting failure. Auto-recovery in progress. Manual Lock and Unlock may be        | host=controller-1                    | critical | 2022-06-21T14:54:17.  | 
|          | required if auto-recovery is unsuccessful.                                                                            |                                      |          | 013786                | 
|          |                                                                                                                       |                                      |          |                       | 
| 200.005  | controller-1 experienced a persistent critical 'Management Network' communication failure.                            | host=controller-1.network=Management | critical | 2022-06-21T14:54:17.  | 
|          |                                                                                                                       |                                      |          | 010487                | 
|          |                                                                                                                       |                                      |          |                       | 
| 400.005  | Communication failure detected with peer over port vlan301 on host controller-0                                       | host=controller-0.network=mgmt       | major    | 2022-06-21T14:54:17.  | 
|          |                                                                                                                       |                                      |          | 010436                | 
|          |                                                                                                                       |                                      |          |                       | 
| 400.005  | Communication failure detected with peer over port vlan12 on host controller-0                                        | host=controller-0.network=oam        | major    | 2022-06-21T14:54:16.  | 
|          |                                                                                                                       |                                      |          | 938165                | 
|          |                                                                                                                       |                                      |          |                       | 
| 800.001  | Storage Alarm Condition: HEALTH_WARN. Please check 'ceph -s' for more details.                                        | cluster=06b60984-e3e6-4e3d-          | warning  | 2022-06-21T14:10:09.  | 
|          |                                                                                                                       | b8e2-ddad0d18dbb1                    |          | 674138                | 
|          |                                                                                                                       |                                      |          |                       | 
+----------+-----------------------------------------------------------------------------------------------------------------------+--------------------------------------+----------+-----------------------+ 

#lock the faulty controller 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-lock controller-1 
+-----------------------+--------------------------------------+ 
| Property              | Value                                | 
+-----------------------+--------------------------------------+ 
| action                | none                                 | 
| administrative        | unlocked                             | 
| availability          | offline                              | 
| bm_ip                 | 128.224.210.12                       | 
| bm_type               | dynamic                              | 
| bm_username           | admin                                | 
| boot_device           | /dev/sda                             | 
| capabilities          | {u'stor_function': u'monitor'}       | 
| clock_synchronization | ntp                                  | 
| config_applied        | 773d4990-c725-4481-a022-961a50f4bef4 | 
| config_status         | None                                 | 
| config_target         | 773d4990-c725-4481-a022-961a50f4bef4 | 
| console               |                                      | 
| created_at            | 2022-06-20T15:16:49.688655+00:00     | 
| device_image_update   | None                                 | 
| hostname              | controller-1                         | 
| id                    | 2                                    | 
| install_output        | graphical                            | 
| install_state         | completed                            | 
| install_state_info    | None                                 | 
| inv_state             | inventoried                          | 
| invprovision          | provisioned                          | 
| location              | {}                                   | 
| mgmt_ip               | 192.168.30.22                        | 
| mgmt_mac              | 00:1e:67:62:ec:e7                    | 
| operational           | disabled                             | 
| personality           | controller                           | 
| reboot_needed         | False                                | 
| reserved              | False                                | 
| rootfs_device         | /dev/sda                             | 
| serialid              | None                                 | 
| software_load         | 21.12                                | 
| task                  | Locking                              | 
| tboot                 | false                                | 
| ttys_dcd              | None                                 | 
| updated_at            | 2022-06-21T14:55:40.335108+00:00     | 
| uptime                | 0                                    | 
| uuid                  | dc3ccf46-16ed-48d3-b9fd-cfd2a308da94 | 
| vim_progress_status   | services-enabled                     | 
+-----------------------+--------------------------------------+ 
# reinstall the controller 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-reinstall controller-1 
+-----------------------+--------------------------------------+ 
| Property              | Value                                | 
+-----------------------+--------------------------------------+ 
| action                | none                                 | 
| administrative        | locked                               | 
| availability          | offline                              | 
| bm_ip                 | 128.224.210.12                       | 
| bm_type               | dynamic                              | 
| bm_username           | admin                                | 
| boot_device           | /dev/sda                             | 
| capabilities          | {u'stor_function': u'monitor'}       | 
| clock_synchronization | ntp                                  | 
| config_applied        | 773d4990-c725-4481-a022-961a50f4bef4 | 
| config_status         | None                                 | 
| config_target         | 773d4990-c725-4481-a022-961a50f4bef4 | 
| console               |                                      | 
| created_at            | 2022-06-20T15:16:49.688655+00:00     | 
| device_image_update   | None                                 | 
| hostname              | controller-1                         | 
| id                    | 2                                    | 
| install_output        | graphical                            | 
| install_state         | completed                            | 
| install_state_info    | None                                 | 
| inv_state             | reinstalling                         | 
| invprovision          | provisioned                          | 
| location              | {}                                   | 
| mgmt_ip               | 192.168.30.22                        | 
| mgmt_mac              | 00:1e:67:62:ec:e7                    | 
| operational           | disabled                             | 
| personality           | controller                           | 
| reboot_needed         | False                                | 
| reserved              | False                                | 
| rootfs_device         | /dev/sda                             | 
| serialid              | None                                 | 
| software_load         | 21.12                                | 
| task                  | Reinstalling                         | 
| tboot                 | false                                | 
| ttys_dcd              | None                                 | 
| updated_at            | 2022-06-21T14:56:42.373449+00:00     | 
| uptime                | 0                                    | 
| uuid                  | dc3ccf46-16ed-48d3-b9fd-cfd2a308da94 | 
| vim_progress_status   | services-disabled                    | 
+-----------------------+--------------------------------------+ 

#follow the progress from the console/logs as the node will be automatically booted via pxe-boot. 
#wait for the process to complete 
#observe that after the installation the node will be online and locked 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list  
+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | locked         | disabled    | online       | 
+----+--------------+-------------+----------------+-------------+--------------+ 
#observe that the configuration for the controller is still present on the platform: 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-if-list controller-1 
+--------------------------------------+-------------+----------+----------+---------+-----------+---------------+------------------------------------+------------+ 
| uuid                                 | name        | class    | type     | vlan id | ports     | uses i/f      | used by i/f                        | attributes | 
+--------------------------------------+-------------+----------+----------+---------+-----------+---------------+------------------------------------+------------+ 
| 083a8bc3-1942-4c1c-bb44-83e4ee41c162 | pxeboot0    | platform | ethernet | None    | [u'eno1'] | []            | [u'clusterhost', u'mgmt0', u'oam'] | MTU=1500   | 
| 1956ec06-54b0-4d06-9aa1-f27a83b9b5dc | mgmt0       | platform | vlan     | 301     | []        | [u'pxeboot0'] | []                                 | MTU=1500   | 
| 6fb376af-2a48-46eb-a1c8-82446fc8f67f | clusterhost | platform | vlan     | 311     | []        | [u'pxeboot0'] | []                                 | MTU=1500   | 
| c8e3f5e4-bfc2-405e-a9a3-674a41e8769b | oam         | platform | vlan     | 12      | []        | [u'pxeboot0'] | []                                 | MTU=1500   | 
+--------------------------------------+-------------+----------+----------+---------+-----------+---------------+------------------------------------+------------+ 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-disk-list controller-1 
+--------------------------------------+-----------+---------+---------+-------+------------+-----+-------------+-----------------------------------------------------------------+ 
| uuid                                 | device_no | device_ | device_ | size_ | available_ | rpm | serial_id   | device_path                                                     | 
|                                      | de        | num     | type    | gib   | gib        |     |             |                                                                 | 
+--------------------------------------+-----------+---------+---------+-------+------------+-----+-------------+-----------------------------------------------------------------+ 
| 699240a3-76ee-4352-b442-a2cc10fcfe11 | /dev/sda  | 2048    | SSD     | 1117. | 0.0        | N/A | PHWA610500V | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6762ece7000-lun-0 | 
|                                      |           |         |         | 813   |            |     | H1P2JGN     |                                                                 | 
|                                      |           |         |         |       |            |     |             |                                                                 | 
| 92f22429-c35b-486c-ad50-0f6f79e3e166 | /dev/sdb  | 2064    | SSD     | 465.  | 465.758    | N/A | S62BNF0R963 | /dev/disk/by-path/pci-0000:03:00.0-sas-0x5001e6762ece7001-lun-0 | 
|                                      |           |         |         | 761   |            |     | 470R        |                                                                 | 
|                                      |           |         |         |       |            |     |             |                                                                 | 
+--------------------------------------+-----------+---------+---------+-------+------------+-----+-------------+-----------------------------------------------------------------+ 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-fs-list controller-1 
+--------------------------------------+---------+-------------+----------------+ 
| UUID                                 | FS Name | Size in GiB | Logical Volume | 
+--------------------------------------+---------+-------------+----------------+ 
| 622d0489-aae3-44f7-b103-6f4f3a1fd364 | backup  | 400         | backup-lv      | 
| e5f59d47-e559-4873-9251-89fb2fe7c95f | docker  | 100         | docker-lv      | 
| 90ea0ce1-cc40-4543-b957-ccd49010cf99 | kubelet | 100         | kubelet-lv     | 
| b98fe447-5e07-45f7-b2b5-5143d839d602 | scratch | 100         | scratch-lv     | 
+--------------------------------------+---------+-------------+----------------+ 
#given the node is already configured, the only remaining step is to unlock the node 
#wait for the node to reboot and to be reconfigured 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-unlock controller-1 
+-----------------------+--------------------------------------+ 
| Property              | Value                                | 
+-----------------------+--------------------------------------+ 
| action                | none                                 | 
| administrative        | locked                               | 
| availability          | online                               | 
| bm_ip                 | 128.224.210.12                       | 
| bm_type               | dynamic                              | 
| bm_username           | admin                                | 
| boot_device           | /dev/sda                             | 
| capabilities          | {u'stor_function': u'monitor'}       | 
| clock_synchronization | ntp                                  | 
| config_applied        | 773d4990-c725-4481-a022-961a50f4bef4 | 
| config_status         | None                                 | 
| config_target         | 773d4990-c725-4481-a022-961a50f4bef4 | 
| console               |                                      | 
| created_at            | 2022-06-20T15:16:49.688655+00:00     | 
| device_image_update   | None                                 | 
| hostname              | controller-1                         | 
| id                    | 2                                    | 
| install_output        | graphical                            | 
| install_state         | completed                            | 
| install_state_info    | None                                 | 
| inv_state             | inventoried                          | 
| invprovision          | provisioned                          | 
| location              | {}                                   | 
| mgmt_ip               | 192.168.30.22                        | 
| mgmt_mac              | 00:1e:67:62:ec:e7                    | 
| operational           | disabled                             | 
| personality           | controller                           | 
| reboot_needed         | False                                | 
| reserved              | False                                | 
| rootfs_device         | /dev/sda                             | 
| serialid              | None                                 | 
| software_load         | 21.12                                | 
| task                  | Unlocking                            | 
| tboot                 | false                                | 
| ttys_dcd              | None                                 | 
| updated_at            | 2022-06-21T15:17:59.749977+00:00     | 
| uptime                | 297                                  | 
| uuid                  | dc3ccf46-16ed-48d3-b9fd-cfd2a308da94 | 
| vim_progress_status   | services-disabled                    | 
+-----------------------+--------------------------------------+ 
#confirm the node is online and that there are no other alarms 
[sysadmin@controller-0 ~(keystone_admin)]$ system host-list  
+----+--------------+-------------+----------------+-------------+--------------+ 
| id | hostname     | personality | administrative | operational | availability | 
+----+--------------+-------------+----------------+-------------+--------------+ 
| 1  | controller-0 | controller  | unlocked       | enabled     | available    | 
| 2  | controller-1 | controller  | unlocked       | enabled     | available    | 
+----+--------------+-------------+----------------+-------------+--------------+ 
[sysadmin@controller-0 ~(keystone_admin)]$ fm alarm-list 
 
[sysadmin@controller-0 ~(keystone_admin)]$  

###############Restore controllers after CasS nodes failure  
# use the ZTP steps for reinstallation of the nodes. 
#Required files for CaaS manager restoration 
#   localhost_docker_local_registry_backup_2022_06_27_09_15_01.tgz  
#   localhost_platform_backup_2022_06_27_09_15_01.tgz 
#   localhost_dc_vault_backup_2022_06_27_09_15_01.tgz  
#Transfer the files on the active controller 

Expected Results 

Backup: 
The following files are created and moved to a safe location: 
    Deployment configuration yaml file 
    Hosts.xml 
    localhost tar.gz files  
    Deployment config file 
    Hosts.xml 
    Tar files 

Recovery:  
    The faulty controller-1 will be re-installed and recovered using another healthy controller 
    before restoring - controller is in failed state  
    after restoring  - controller is online and active
    The backed-up files and ZTP automation will be used to recover the whole CaaS-Manager site. 
NOTE ZTP steps/actions on chapter 8 
###RESTORE CaaS Manager
#Required files:
#	- backup tar.gz files
#		- localhost_docker_local_registry_backup.tgz  
#		- localhost_platform_backup.tgz 
#		- localhost_dc_vault_backup.tgz 
#	- localhost.yaml
#	- windriver iso
#	- windriver iso signature
#	- local harbor certificate

#Steps and procedures
	1. boot the iso and install the controller node as per standard procedure
	2. configure the network and dns for the node
	3. transfer the restore required files to the node in /opt/platofm-backup
	4. run the restore platform playbook
		localhost:~$ screen -S restore
		~(keystone_admin)]$ ansible-playbook /usr/share/ansible/stx-ansible/playbooks/restore_platform.yml -e 'initial_backup_dir=/opt/platform-backup/wr ansible_become_pass="River2022!" admin_password="River2022!" backup_filename=localhost_platform_backup_2022_06_27_09_15_01.tgz wipe_ceph_osds=false'
Expected result:
PLAY RECAP *********************************************************************************************************************************************************************************************************************************
localhost                  : ok=483  changed=265  unreachable=0    failed=0   

Monday 27 June 2022  14:28:23 +0200 (0:00:00.343)       0:48:03.636 *********** 
=============================================================================== 
bootstrap/apply-manifest : Applying puppet bootstrap manifest --------------------------------------------------------------------------------------------------------------------------------------------------------------------- 301.47s
bootstrap/persist-config : Wait for service endpoints reconfiguration to complete ------------------------------------------------------------------------------------------------------------------------------------------------- 298.75s
bootstrap/bringup-essential-services : Wait for 120 seconds to ensure kube-system pods are all started ---------------------------------------------------------------------------------------------------------------------------- 120.33s
bootstrap/persist-config : Wait for sysinv inventory ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 57.27s
bootstrap/persist-config : Saving config in sysinv database ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 45.08s
bootstrap/apply-manifest : Extract apiserver-keys from /etc/kubernetes/pki --------------------------------------------------------------------------------------------------------------------------------------------------------- 36.43s
restore-platform/restore-more-data : Restore armada manifests and extension filesystem --------------------------------------------------------------------------------------------------------------------------------------------- 36.23s
bootstrap/bringup-essential-services : Wait for 30 seconds to ensure deployments have time to scale back up ------------------------------------------------------------------------------------------------------------------------ 30.26s
bootstrap/bringup-bootstrap-applications : pause ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 30.04s
restore-platform/prepare-env : Copy the backup tarball to /scratch if the file is already on-box ----------------------------------------------------------------------------------------------------------------------------------- 24.56s
bootstrap/bringup-essential-services : Initializing Kubernetes master -------------------------------------------------------------------------------------------------------------------------------------------------------------- 24.04s
restore-platform/restore-sw-patches : Apply patches -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 22.96s
bootstrap/persist-config : Find old registry secrets in Barbican ------------------------------------------------------------------------------------------------------------------------------------------------------------------- 22.43s
bootstrap/persist-config : Wait for system controller database configuration to complete ------------------------------------------------------------------------------------------------------------------------------------------- 19.24s
bootstrap/bringup-essential-services : Restore Helm charts if the host is bootstrapped in restore mode ----------------------------------------------------------------------------------------------------------------------------- 18.29s
bootstrap/bringup-essential-services : Restore encryption provider config ---------------------------------------------------------------------------------------------------------------------------------------------------------- 18.26s
bootstrap/bringup-essential-services : restore /etc/hosts file --------------------------------------------------------------------------------------------------------------------------------------------------------------------- 18.25s
bootstrap/apply-manifest : Prefetch static and system hieradata -------------------------------------------------------------------------------------------------------------------------------------------------------------------- 18.25s
bootstrap/apply-manifest : Check if apiserver-keys are present in the backup tarball ----------------------------------------------------------------------------------------------------------------------------------------------- 18.24s
bootstrap/prepare-env : Extract ssl_ca certifcate from backup archive -------------------------------------------------------------------------------------------------------------------------------------------------------------- 18.23s

#Restore the images if needed
ansible-playbook /usr/share/ansible/stx-ansible/playbooks/restore_user_images.yml -e 'initial_backup_dir=/opt/platform-backup/wr backup_filename=localhost_docker_local_registry_backup_2022_06_27_09_15_01.tgz ansible_become_pass="River2022!"'

Expected result:
PLAY RECAP *********************************************************************************************************************************************************************************************************************************
localhost                  : ok=18   changed=8    unreachable=0    failed=0   

Monday 27 June 2022  14:39:51 +0200 (0:00:00.192)       0:01:02.282 *********** 
=============================================================================== 
restore-user-images/restore-local-registry-images : Import docker images ----------------------------------------------------------------------------------------------------------------------------------------------------------- 27.85s
restore-user-images/prepare-env : Copy the backup tarball to /scratch if the file is already on-box -------------------------------------------------------------------------------------------------------------------------------- 17.76s
restore-user-images/restore-local-registry-images : Push to local registry if any image tagged as such ------------------------------------------------------------------------------------------------------------------------------ 4.67s
backup-restore/validate-input : Check if backup file exists ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 4.24s
restore-user-images/restore-local-registry-images : Check that backup archive exists ------------------------------------------------------------------------------------------------------------------------------------------------ 4.16s
common/prepare-env : stat ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.74s
restore-user-images/prepare-env : Create /etc/platform/.restore_user_images_in_progress flag file ----------------------------------------------------------------------------------------------------------------------------------- 0.39s
restore-user-images/restore-local-registry-images : Get image list to push to local registry ---------------------------------------------------------------------------------------------------------------------------------------- 0.37s
backup-restore/prepare-env : Retrieve software version number ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.31s
restore-user-images/prepare-env : Check if restoring user images is already in progress --------------------------------------------------------------------------------------------------------------------------------------------- 0.22s
backup-restore/prepare-env : Check archive dir -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.20s
restore-user-images/restore-local-registry-images : Remove the /etc/platform/.restore_user_images_in_progress file ------------------------------------------------------------------------------------------------------------------ 0.19s
backup-restore/prepare-env : Retrieve system type ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.19s
common/prepare-env : include_vars --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.08s
restore-user-images/restore-local-registry-images : debug --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.05s
backup-restore/prepare-env : Set software version fact ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 0.04s
backup-restore/validate-input : Set default target where backup tarball inspection takes place -------------------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Set the initial_backup_dir to /opt/platform-backup if not specified and backup file is on the host -------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Fail if backup_filename is not defined or set ------------------------------------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Fail if the backup file is off-box and initial_backup_dir is not specified -------------------------------------------------------------------------------------------------------------------------- 0.03s

#Unlock the node and restore the dc_vault
#restore the dc-vault for the CaaS Manager
ansible-playbook /usr/share/ansible/stx-ansible/playbooks/restore_dc_vault.yml -e 'initial_backup_dir=/opt/platform-backup/wr backup_filename=localhost_dc_vault_backup_2022_06_27_09_15_01.tgz ansible_become_pass="River2022!"'

PLAY RECAP *********************************************************************************************************************************************************************************************************************************
localhost                  : ok=11   changed=4    unreachable=0    failed=0   

Monday 27 June 2022  14:42:09 +0200 (0:00:00.033)       0:00:05.714 *********** 
=============================================================================== 
restore-dc-vault/prepare-env : Check if controller is unlocked ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- 2.92s
common/prepare-env : stat ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------0.73s
backup-restore/prepare-env : Retrieve software version number ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.29s
backup-restore/validate-input : Check if backup file exists ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.24s
backup-restore/prepare-env : Check archive dir -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.17s
backup-restore/prepare-env : Retrieve system type ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.16s
restore-dc-vault/prepare-env : Check if the system is a DC controller --------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.16s
restore-dc-vault/prepare-env : Check if restoring dc vault is already in progress --------------------------------------------------------------------------------------------------------------------------------------------------- 0.16s
common/prepare-env : include_vars --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.08s
restore-dc-vault/prepare-env : Fail if controller is not unlocked ------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/prepare-env : Set software version fact ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 0.03s
backup-restore/validate-input : Fail if backup file does not exist on the target ---------------------------------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Set default target where backup tarball inspection takes place -------------------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Set the initial_backup_dir to /opt/platform-backup if not specified and backup file is on the host -------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Fail if the backup file is off-box and initial_backup_dir is not specified -------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Fail if backup_filename is not defined or set ------------------------------------------------------------------------------------------------------------------------------------------------------- 0.03s
backup-restore/validate-input : Update target if backup data are off-box ------------------------------------------------------------------------------------------------------------------------------------------------------------ 0.03s
common/prepare-env : Gather remote SSH public key ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.03s
common/prepare-env : Fail if host is unreachable ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ 0.03s
common/prepare-env : debug ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 0.03s

#Reinstall controller-1 using the pxe-boot procedure.
#After controller-1 is installed the output should be:
~(keystone_admin)]$ system host-list
+----+-------------+------------+---------------+-----------+------------+
| id | hostname    | personality| administrative|operational|availability|
+----+-------------+------------+---------------+-----------+------------+
| 1  | controller-0| controller | unlocked      |enabled    |available   |
| 2  | controller-1| controller | unlocked      |enabled    |available   |
+----+-------------+------------+---------------+-----------+------------+

Postrequisites

Passwords for local user accounts must be restored manually since they are not included as part of the backup and restore procedures.
After restoring a Distributed Cloud subcloud, you need to bring it back to the managed state on the Central Cloud (SystemController), by using the following commands:
    $ source /etc/platform/openrc
    ~(keystone_admin)]$ dcmanager subcloud manage simplex

```

## APPENDIX

### Load/tag/push docker image

**Procedure**
```bash
# transfer the container image you want to use to the active subcloud controller
# after the image is transfered load the tar file into the local registry
[sysadmin@controller-0 wr(keystone_admin)]$ sudo docker load registry.local:9001 < cyclictest.latest.tar.gz
Loaded image: cyclictest:latest
# if needed tag the image you loaded using sudo docker tag 
[sysadmin@controller-0 wr(keystone_admin)]$sudo docker tag cyclictest:latest registry.local:9001/ps_emea/cyclictest:v2.1
# push the image to the subcloud registry
[sysadmin@controller-0 wr(keystone_admin)]$sudo docker push registry.local:9001/ps_emea/cyclictest:v2.1
The push refers to repository [registry.local:9001/ps_emea/cyclictest]
3a22bf3c204b: Pushed 
v2.0: digest: sha256:c3395acac076bb7fc1278f76b699b0a6dbb966d9c9f546b75bb4b3225c9d0610 size: 2211
# using sudo docker images check the status of your image
[sysadmin@controller-0 ~(keystone_admin)]$ sudo docker images | grep cyclic
registry.local:9001/ps_emea/cyclictest                 v2.1                97288a7c80d9        7 days ago          2.35GB

```

### Create a kubernetes secret


**Procedure**
```bash
# create a kubernetes secret named registry-cred for docker login on registry.local:9001 for the default namespace
# if you want to create a secret for a different namespace change the commad instead of default to use your namespace
controller-0:/opt/backups/wr$ kubectl create secret docker-registry registry-creds --docker-username=sysinv --docker-password=$(keyring get sysinv services) --docker-server=registry.local:9001 -n default

secret/registry-creds created

```
