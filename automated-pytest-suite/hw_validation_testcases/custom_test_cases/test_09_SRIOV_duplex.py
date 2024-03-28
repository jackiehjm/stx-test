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
SRIOV_NIC_C1 = HWV_CONFIG['sriov_nic_c1']

SRIOV_C0 = "controller-0"
SRIOV_C1 = "controller-1"

def check_skip():
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")
    if SRIOV_NIC_C0 == "NoNIC":
        skip("No NIC configured on Controller-0 for SRIOV")
    if SRIOV_NIC_C1 == "NoNIC":
        skip("No NIC configured on Controller-1 for SRIOV")

@mark.hw_validation
def test_sriov_swact_c1(request):
    check_skip()

    active, standby = system_helper.get_active_standby_controllers()
    if active == SRIOV_C1:
        host_helper.swact_host(SRIOV_C1)
        time.sleep(120)

@mark.hw_validation
def test_sriov_client(request):
    check_skip()

    with host_helper.ssh_to_host(hostname=SRIOV_C0) as con_ssh: 
        LOG.tc_step("Preparing Interfaces for iperf client")
        home_dir = HostLinuxUser.get_home()

        host_helper.lock_host(SRIOV_C1)
        time.sleep(5)

        con_ssh.exec_cmd("system datanetwork-add physnet1 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov1 -c pci-sriov -N 12 %s %s --vf-driver=netdevice" % (SRIOV_C1, SRIOV_NIC_C1)) 
        con_ssh.exec_cmd("system host-if-add -c pci-sriov %s sriov01 vf sriov1 -N 2 --vf-driver=netdevice" % SRIOV_C1)
        con_ssh.exec_cmd("system interface-datanetwork-assign %s sriov01 physnet1" % SRIOV_C1)
        con_ssh.exec_cmd("system host-memory-modify %s -1G 10 0" % SRIOV_C1)
        con_ssh.exec_cmd("system host-label-assign %s sriovdp=enabled" % SRIOV_C1)
        con_ssh.exec_cmd("system host-label-assign %s kube-cpu-mgr-policy=static" % SRIOV_C1)

        host_helper.unlock_host(SRIOV_C1)
        time.sleep(20)

@mark.hw_validation
def test_sriov_swact_c0(request):
    check_skip()

    host_helper.swact_host(SRIOV_C0)
    time.sleep(120)

@mark.hw_validation
def test_sriov_server(request):
    check_skip()

    with host_helper.ssh_to_host(hostname=SRIOV_C1) as con_ssh: 
        LOG.tc_step("Preparing Interfaces for iperf server")
        home_dir = HostLinuxUser.get_home()

        host_helper.lock_host(SRIOV_C0)
        time.sleep(5)

        con_ssh.exec_cmd("system datanetwork-add physnet0 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov0 -c pci-sriov -N 12 %s %s --vf-driver=netdevice" % (SRIOV_C0, SRIOV_NIC_C0))
        con_ssh.exec_cmd("system host-if-add -c pci-sriov %s sriov00 vf sriov0 -N 2 --vf-driver=netdevice" % SRIOV_C0)
        con_ssh.exec_cmd("system interface-datanetwork-assign %s sriov00 physnet0" % SRIOV_C0)
        con_ssh.exec_cmd("system host-memory-modify %s -1G 10 0" % SRIOV_C0)
        con_ssh.exec_cmd("system host-label-assign %s sriovdp=enabled" % SRIOV_C0)
        con_ssh.exec_cmd("system host-label-assign %s kube-cpu-mgr-policy=static" % SRIOV_C0)

        host_helper.unlock_host(SRIOV_C0)
        time.sleep(20)

@mark.hw_validation
def test_sriov_iperf_pods(request):
    check_skip()

    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        home_dir = HostLinuxUser.get_home()
        Iperf_Server = "utils/test_files/Test9_sriov-iperfserver-validation.yaml"
        Iperf_Client = "utils/test_files/Test9_sriov-iperfclient-validation.yaml" 
        Iperf_Test = "utils/test_files/Test9_iperf3.py" 
        common.scp_from_localhost_to_active_controller(source_path=Iperf_Server, dest_path=home_dir)

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
        common.scp_from_localhost_to_active_controller(source_path=Iperf_Test, dest_path=home_dir)
        code, output = con_ssh.exec_cmd("python3 Test9_iperf3.py")
        final_output = output.strip().split('\n')
        LOG.tc_step("Bandwidth is " + final_output[-1])
        bandwidth = final_output[-1]

        speed = con_ssh.exec_sudo_cmd("ethtool %s | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'" % SRIOV_NIC_C1)

        LOG.tc_step("Link Speed is " + str(speed[1]) + " Mbits/s.")
        LOG.tc_step("iPerf Bandwidth is " + bandwidth + " Gbits/sec.")
        performance = (float(bandwidth)/float(speed[1])) * 100
        LOG.tc_step("Performance is " + str(performance))
        con_ssh.exec_cmd("kubectl delete -f Test9_sriov-iperfclient-validation.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test9_sriov-iperfserver-validation.yaml")
        con_ssh.exec_cmd("rm Test9_*")
        assert (performance >= 90), "Test Failed"

