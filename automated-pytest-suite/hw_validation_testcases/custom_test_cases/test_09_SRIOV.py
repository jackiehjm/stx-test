import pytest
import time
import yaml
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant
from utils import cli
import subprocess
from consts.proj_vars import ProjVar

HWV_CONFIG = ProjVar.get_var('HWV_CONFIG')
SRIOV_NIC_C0 = HWV_CONFIG['sriov_nic_c0']

def check_skip():
    if system_helper.is_aio_duplex():
        skip("Duplex system detected")
    if SRIOV_NIC_C0 == "NoNIC":
        skip("No NIC configured for SRIOV")

@mark.hw_validation 
def test_sriov_server(request):
    check_skip()

@mark.hw_validation 
def test_sriov_client(request):
    check_skip()

@mark.hw_validation 
def test_sriov_iperf_pods(request):
    check_skip()

    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh: 
        LOG.tc_step("Preparing Interfaces and Pods")
        home_dir = HostLinuxUser.get_home()
        host_helper.lock_host(host)
        time.sleep(5)

        Iperf_Server = "utils/test_files/Test9_sriov-iperfserver-validation.yaml"
        Iperf_Client = "utils/test_files/Test9_sriov-iperfclient-validation.yaml" 
        Iperf_Test = "utils/test_files/Test9_iperf3.py" 
        Interfaces = "utils/test_files/Test9_and_10_Find_Interfaces.py"
        LOG.tc_step("Finding SR-IOV capable interfaces")
        common.scp_from_localhost_to_active_controller(source_path= Interfaces, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_and_10_Find_Interfaces.py")
        rows = output.strip().split('\n')
        LOG.tc_step("Interface 1 is " + rows[0])
        LOG.tc_step("Interface 2 is " + rows[1])
        speed = con_ssh.exec_sudo_cmd("ethtool " + rows[0] + " | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'") #Comment this line if entering interfaces manually.
        con_ssh.exec_cmd("system datanetwork-add physnet0 vlan")
   #     con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov0 -c pci-sriov -N 12 controller-0 ens2f2 --vf-driver=netdevice")  #Uncomment this line if entering interfaces manually. Update interface to be used.
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov0 -c pci-sriov -N 12 controller-0 " + rows[0] + " --vf-driver=netdevice")  #Comment this line if entering interfaces manually.
        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-0 sriov00 vf sriov0 -N 2 --vf-driver=netdevice")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-0 sriov00 physnet0")
        con_ssh.exec_cmd("system host-memory-modify controller-0 -1G 10 0")
        con_ssh.exec_cmd("system datanetwork-add physnet1 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov1 -c pci-sriov -N 12 controller-0 " + rows[1] + " --vf-driver=netdevice") #Comment this line if entering interfaces manually.
      #  con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov1 -c pci-sriov -N 12 controller-0 ens1f2 --vf-driver=netdevice") #Uncomment this line if entering interfaces manually. Update interface to be used.
        con_ssh.exec_cmd("system host-if-add -c pci-sriov controller-0 sriov01 vf sriov1 -N 2 --vf-driver=netdevice")
        con_ssh.exec_cmd("system interface-datanetwork-assign controller-0 sriov01 physnet1")
        con_ssh.exec_cmd("system host-label-assign controller-0 sriovdp=enabled")
        con_ssh.exec_cmd("system host-label-assign controller-0 kube-cpu-mgr-policy=static")
        time.sleep(60)

        host_helper.unlock_host(host)
        time.sleep(20)
        common.scp_from_localhost_to_active_controller(source_path= Iperf_Server, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test9_sriov-iperfserver-validation.yaml")
        time.sleep(10)
        common.scp_from_localhost_to_active_controller(source_path= Iperf_Client, dest_path=home_dir)
        con_ssh.exec_cmd("kubectl create -f Test9_sriov-iperfclient-validation.yaml")
        time.sleep(10)
        LOG.tc_step("Installing iperf3 on Server and Client Pods")
        con_ssh.exec_cmd("kubectl exec -it iperf-server -- yum install -y iperf3")
        time.sleep(30)
        con_ssh.exec_cmd("kubectl exec -it iperf-client -- yum install -y iperf3")
        time.sleep(30)

        LOG.tc_step("Executing iperf3 test")
        common.scp_from_localhost_to_active_controller(source_path= Iperf_Test, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_iperf3.py")
        final_output = output.strip().split('\n')
        bandwidth = final_output[-1]
#        speed = con_ssh.exec_sudo_cmd("ethtool ens1f2 | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'") # Uncomment this line if entering interfaces manually. Define specific interface to be used.

        con_ssh.exec_cmd("kubectl delete -f Test9_sriov-iperfclient-validation.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test9_sriov-iperfserver-validation.yaml")
        con_ssh.exec_cmd("rm Test9_sriov-iperfserver-validation.yaml")
        con_ssh.exec_cmd("rm Test9_sriov-iperfclient-validation.yaml")
        con_ssh.exec_cmd("rm Test9_and_10_Find_Interfaces.py")
        con_ssh.exec_cmd("rm Test9_iperf3.py")
        LOG.tc_step("Link Speed is " + str(speed[1]) + " Mbits/s.")
        LOG.tc_step("iPerf Bandwidth is " + bandwidth + " Gbits/sec.")
        performance = (float(bandwidth)/float(speed[1])) * 100
        LOG.tc_step("Performance is " + str(performance))
        assert (performance >= 90), "Test Failed"

