import pytest
import time
import yaml
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant
from utils import cli
import subprocess

@mark.hw_validation
def test_sriov_interfaces(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh: 
        LOG.tc_step("Preparing Interfaces and Pods")
        home_dir = HostLinuxUser.get_home()
        standby = system_helper.get_standby_controller_name()
        # Comment this section if two interfaces are enabled and ready for SRIOV on this controller. If unsure enter interface name manually.
        ''' 
        dpdk_interfaces = "utils/test_files/Test9_and_10_Find_Interfaces.py"
        common.scp_from_localhost_to_active_controller(source_path= dpdk_interfaces, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_and_10_Find_Interfaces.py")
        rows_dpdk = output.strip().split('\n')
        '''
        # Comment this section if two interfaces are enabled and ready for SRIOV on this controller. If unsure enter interface name manually.         
        
        host_helper.lock_host(standby)   
        con_ssh.exec_cmd("system host-if-delete 2 sriov00")
        con_ssh.exec_cmd("system host-if-delete 2 sriov01")
        con_ssh.exec_cmd("system host-if-modify -c none 2 sriov0")
        con_ssh.exec_cmd("system host-if-modify -c none 2 sriov1")
        con_ssh.exec_cmd("system datanetwork-add physnet4 vlan")
      #  con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov4 -c pci-sriov -N 12 controller-1 " + rows_dpdk[0] + " --vf-driver=vfio")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov4 -c pci-sriov -N 12 controller-1 ens1f1 --vf-driver=vfio") # Define specific interface to be used if not using script to find Interface. Comment above line if entering manually
        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-1 sriov04 vf sriov4 -N 5 --vf-driver=vfio")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-1 sriov04 physnet4")
        con_ssh.exec_cmd("system host-memory-modify controller-1 -1G 11 0")
        con_ssh.exec_cmd("system datanetwork-add physnet5 vlan")
      #  con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov5 -c pci-sriov -N 12 controller-1 " + rows_dpdk[1] + " --vf-driver=vfio")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov5 -c pci-sriov -N 12 controller-1 ens2f1 --vf-driver=vfio") # Define specific interface to be used if not using script to find Interface. Comment above line if entering manually.

       # speed = con_ssh.exec_sudo_cmd("ethtool " + rows[0] + " | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'") #Comment this line if entering interfaces manually .
        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-1 sriov05 vf sriov5 -N 5 --vf-driver=vfio")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-1 sriov05 physnet5")
        con_ssh.exec_cmd("system host-label-assign controller-1 sriovdp=enabled")
        con_ssh.exec_cmd("system host-label-assign controller-1 kube-cpu-mgr-policy=static")
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 16 controller-1")
        time.sleep(60)
        host_helper.unlock_host(standby)
        con_ssh.exec_cmd("system host-swact "+host)
        time.sleep(60)

@mark.hw_validation
def test_dpdk_part2(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        home_dir = HostLinuxUser.get_home()

        pktgen = "utils/test_files/Test10_dpdk-pktgen-vfio.yaml"
        testpmd = "utils/test_files/Test10_dpdk-testpmd-vfio.yaml" 
        dpdk_test = "utils/test_files/Test10_DPDK.py"
        dpdk_expect = "utils/test_files/Test10_expect.expect"
        dpdk_subprocess = "utils/test_files/Test10_subprocess.py"

        common.scp_from_localhost_to_active_controller(source_path= dpdk_test, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path= dpdk_expect, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path= dpdk_subprocess, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path= pktgen, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test10_dpdk-pktgen-vfio.yaml")
        time.sleep(10)

        common.scp_from_localhost_to_active_controller(source_path= testpmd, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test10_dpdk-testpmd-vfio.yaml")
        time.sleep(10)
        LOG.tc_step("Getting PCI Devices")
        code, output = con_ssh.exec_cmd("python3 Test10_DPDK.py")
        values = output.strip().split('\n')
        con_ssh.exec_sudo_cmd(values[4])
        con_ssh.exec_sudo_cmd(values[5])
        code, taskset_pktgen = con_ssh.exec_cmd("kubectl exec -it dpdk-pktgen -- taskset -pc 1")
        affinity_pktgen = taskset_pktgen.strip().split(' ')
        code, taskset_testpmd = con_ssh.exec_cmd("kubectl exec -it dpdk-testpmd -- taskset -pc 1")
        affinity_testpmd = taskset_testpmd.strip().split(' ')
        LOG.tc_step("Cores assigned for pktgen are " + affinity_pktgen[5])
        LOG.tc_step("Cores assigned for testpmd are  " + affinity_testpmd[5]) 

        con_ssh.exec_cmd("chmod +x Test10_expect.expect")
        cores = affinity_pktgen[5]
        affinity_list = cores.split(',')
        print("using cores: "+affinity_list[1])
        con_ssh.exec_cmd("sed -i 's/pktgen_affinity/"+affinity_pktgen[5]+"/' Test10_expect.expect")
        con_ssh.exec_cmd("sed -i 's/testpmd_affinity/"+affinity_testpmd[5]+"/' Test10_subprocess.py")
        con_ssh.exec_cmd("sed -i 's/pktgen_PCI/"+values[6]+"/' Test10_expect.expect")
        con_ssh.exec_cmd("sed -i 's/2ndCPUpktgen/"+affinity_list[1]+".0/' Test10_expect.expect")
        con_ssh.exec_cmd("sed -i 's/testpmd_PCI/"+values[7]+"/' Test10_subprocess.py")
        code, output = con_ssh.exec_cmd("python3 Test10_subprocess.py")
        bandwidth = output.strip().split('\n')
        LOG.tc_step("Rx Bandwidth is: " +bandwidth[0])
        LOG.tc_step("Tx Bandwidth is: " +bandwidth[1])
        speed = con_ssh.exec_sudo_cmd("ethtool ens1f1 | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'") # Uncomment this line if entering interfaces manually. Define specific interface to be used.
        performance_rx = (float(bandwidth[0])/float(speed[1])) / 10000
        LOG.tc_step("Rx Performance is " + str(performance_rx))
        performance_tx = (float(bandwidth[1])/float(speed[1])) / 10000
        LOG.tc_step("Tx Performance is " + str(performance_tx))
        con_ssh.exec_cmd("kubectl delete -f Test10_dpdk-pktgen-vfio.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test10_dpdk-testpmd-vfio.yaml")
        con_ssh.exec_cmd("rm Test10_*")
        assert (performance_rx >= 90), "Test Failed"
        assert (performance_tx >= 90), "Test Failed"
