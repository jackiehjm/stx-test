import pytest
import time
import yaml
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant
from utils import cli
import subprocess

# Comment this section if standby controller has the SRIOV interfaces to test
'''
@mark.hw_validation
def test_1_3_swact(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    first_active = host
    first_standby = system_helper.get_standby_controller_name()
    LOG.tc_step("First Active is "+ first_active)
    LOG.tc_step("First Standby is "+ first_standby)
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Issuing swact command")
        con_ssh.exec_cmd("system host-swact "+host)
        time.sleep(60)
'''
# End of comment, if standby controller has the SRIOV interfaces to test


@mark.hw_validation
def test_sriov_interfaces(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh: 
        LOG.tc_step("Preparing Interfaces and Pods")
        home_dir = HostLinuxUser.get_home()
        standby = system_helper.get_standby_controller_name()
        host_helper.lock_host(standby)
        time.sleep(5)
        '''
# Comment this section and define interfaces manually if two interfaces are not enabled and ready for SRIOV on this controller. If unsure enter interface name manually, uncommeting the two lines below and using the appropriate interface name.
        Interfaces = "utils/test_files/Test9_and_10_Find_Interfaces.py" 
        LOG.tc_step("Finding SR-IOV capable interfaces")
        common.scp_from_localhost_to_active_controller(source_path= Interfaces, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_and_10_Find_Interfaces.py")
        rows = output.strip().split('\n')
        LOG.tc_step("Code equals " + str(code))
        LOG.tc_step("Output equals " + str(output))
        LOG.tc_step("Interface 1 is " + rows[0])
        LOG.tc_step("Interface 2 is " + rows[1])
        speed = con_ssh.exec_sudo_cmd("ethtool " + rows[0] + " | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'") #Uncomment this line if you have uncommented the section above.
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov0 -c pci-sriov -N 12 controller-1 " + rows[0] + " --vf-driver=netdevice")

# Comment this section and define interfaces manually if two interfaces are not enabled and ready for SRIOV on this controller. If unsure enter interface name manually, uncommeting the two lines below and using the appropriate interface name.
        '''
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov0 -c pci-sriov -N 12 controller-1 ens1f1 --vf-driver=netdevice") # Define specific interface to be used if not using script to find Interface

        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-1 sriov00 vf sriov0 -N 2 --vf-driver=netdevice")
        con_ssh.exec_cmd("system datanetwork-add physnet0 vlan")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-1 sriov00 physnet0")
        con_ssh.exec_cmd("system host-memory-modify controller-1 -1G 10 0")
        con_ssh.exec_cmd("system datanetwork-add physnet1 vlan")

#        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov1 -c pci-sriov -N 12 controller-1 " + rows[1] + " --vf-driver=netdevice") #Uncomment this line if you have uncommented the section above.
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov1 -c pci-sriov -N 12 controller-1 ens2f1 --vf-driver=netdevice") # Define specific interface to be used if not using script to find Interface.

        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-1 sriov01 vf sriov1 -N 2 --vf-driver=netdevice")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-1 sriov01 physnet1")
        con_ssh.exec_cmd("system host-label-assign controller-1 sriovdp=enabled")
        con_ssh.exec_cmd("system host-label-assign controller-1 kube-cpu-mgr-policy=static")
        host_helper.unlock_host(standby)
        time.sleep(20)
        con_ssh.exec_cmd("system host-swact "+host)
        time.sleep(60)
        return speed #Comment this line if entering interfaces manually

@mark.hw_validation
def test_sriov_interfaces_part2(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        home_dir = HostLinuxUser.get_home()
        Iperf_Server = "utils/test_files/Test9_sriov-iperfserver-validation.yaml"
        Iperf_Client = "utils/test_files/Test9_sriov-iperfclient-validation.yaml" 
        Iperf_Test = "utils/test_files/Test9_iperf3.py" 
        common.scp_from_localhost_to_active_controller(source_path= Iperf_Server, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test9_sriov-iperfserver-validation.yaml")
        time.sleep(30)
        common.scp_from_localhost_to_active_controller(source_path= Iperf_Client, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test9_sriov-iperfclient-validation.yaml")
        time.sleep(30)
        LOG.tc_step("Installing iperf3 on Server and Client Pods")
        con_ssh.exec_cmd("kubectl exec -it iperf-server -- yum install -y iperf3")
        time.sleep(30)
        con_ssh.exec_cmd("kubectl exec -it iperf-client -- yum install -y iperf3")
        time.sleep(30)
        LOG.tc_step("Executing iperf3 test")
        common.scp_from_localhost_to_active_controller(source_path= Iperf_Test, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_iperf3.py")
        final_output = output.strip().split('\n')
        LOG.tc_step("Bandwidth is " + final_output[-1])
        bandwidth = final_output[-1]

        speed = con_ssh.exec_sudo_cmd("ethtool ens1f1 | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'") # Uncomment this line if entering interfaces manually. Define specific interface to be used.

        LOG.tc_step("Link Speed is " + str(speed[1]) + " Mbits/s.")
        LOG.tc_step("iPerf Bandwidth is " + bandwidth + " Gbits/sec.")
        performance = (float(bandwidth)/float(speed[1])) * 100
        LOG.tc_step("Performance is " + str(performance))
        con_ssh.exec_cmd("kubectl delete -f Test9_sriov-iperfclient-validation.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test9_sriov-iperfclient-validation.yaml")
        con_ssh.exec_cmd("rm Test9_*")
        assert (performance >= 90), "Test Failed"

