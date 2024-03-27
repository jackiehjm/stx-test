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
import re

HWV_CONFIG = ProjVar.get_var('HWV_CONFIG')
SRIOV_NIC_C0 = HWV_CONFIG['sriov_nic_c0']
SRIOV_NIC_C1 = HWV_CONFIG['sriov_nic_c1']

SRIOV_C0 = "controller-0"
SRIOV_C1 = "controller-1"

def find_virtfn_number(string):
    pattern = r"virtfn(\d+)"
    match = re.search(pattern, string)
    if match:
        return int(match.group(1))
    else:
        return None

def get_cpu_list(string):
    """
    get cpu list from ranges like 1-5, 8, 10
    """

    cpu_list = []
    ranges_and_numbers = string.split(',')
    for entry in ranges_and_numbers:
        if "-" in entry:
            start, end = map(int, entry.split('-'))
            cpu_list.extend(range(start, end + 1))
        else:
            cpu_list.append(int(entry))
    return cpu_list

def get_vf_pci(con_ssh, podname):
    """
    get vf pci id in the pod.
    """
    cmd_vf_pci = "kubectl exec -it %s -- env | grep PCI" % podname
    _, output = con_ssh.exec_cmd(cmd_vf_pci)
    vf_pci = output.split("=")[1]
    return vf_pci

@mark.hw_validation
def test_dpdk_swact_c0(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    active, standby = system_helper.get_active_standby_controllers()
    if active == SRIOV_C0:
        host_helper.swact_host(SRIOV_C0)
        time.sleep(120)

@mark.hw_validation
def test_dpdk_pktgen(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    with host_helper.ssh_to_host(hostname=SRIOV_C1) as con_ssh: 
        LOG.tc_step("Preparing Interfaces for pktgen")
        home_dir = HostLinuxUser.get_home()
       
        host_helper.lock_host(SRIOV_C0)   
        time.sleep(5)

        con_ssh.exec_cmd("system host-if-delete %s sriov00" % SRIOV_C0)
        con_ssh.exec_cmd("system host-if-modify -c none %s sriov0" % SRIOV_C0)
        con_ssh.exec_cmd("system datanetwork-add physnet4 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov4 -c pci-sriov -N 12 %s %s --vf-driver=vfio" % (SRIOV_C0, SRIOV_NIC_C0))
        con_ssh.exec_cmd("system host-if-add -c pci-sriov %s sriov04 vf sriov4 -N 5 --vf-driver=vfio" % SRIOV_C0)
        con_ssh.exec_cmd("system interface-datanetwork-assign %s sriov04 physnet4" % SRIOV_C0)
        con_ssh.exec_cmd("system host-memory-modify %s -1G 11 0" % SRIOV_C0)
        con_ssh.exec_cmd("system host-label-assign %s sriovdp=enabled" % SRIOV_C0)
        con_ssh.exec_cmd("system host-label-assign %s kube-cpu-mgr-policy=static" % SRIOV_C0)
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 16 %s" % SRIOV_C0)
        time.sleep(60)

        host_helper.unlock_host(SRIOV_C0)
        time.sleep(30)

@mark.hw_validation
def test_dpdk_swact_c1(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    host_helper.swact_host(SRIOV_C1)
    time.sleep(120)

@mark.hw_validation
def test_dpdk_testpmd(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    with host_helper.ssh_to_host(hostname=SRIOV_C0) as con_ssh: 
        LOG.tc_step("Preparing Interfaces for testpmd")
        home_dir = HostLinuxUser.get_home()
       
        host_helper.lock_host(SRIOV_C1)   
        time.sleep(5)

        con_ssh.exec_cmd("system host-if-delete %s sriov01" % SRIOV_C1)
        con_ssh.exec_cmd("system host-if-modify -c none %s sriov1" % SRIOV_C1)
        con_ssh.exec_cmd("system datanetwork-add physnet5 vlan")
        con_ssh.exec_cmd("system host-if-modify -m 1500 -n sriov5 -c pci-sriov -N 12 %s %s --vf-driver=vfio" % (SRIOV_C1, SRIOV_NIC_C1))

        con_ssh.exec_cmd("system host-if-add -c pci-sriov %s sriov05 vf sriov5 -N 5 --vf-driver=vfio" % SRIOV_C1)
        con_ssh.exec_cmd("system interface-datanetwork-assign %s sriov05 physnet5" % SRIOV_C1)
        con_ssh.exec_cmd("system host-memory-modify %s -1G 11 0" % SRIOV_C1)
        con_ssh.exec_cmd("system host-label-assign %s sriovdp=enabled" % SRIOV_C1)
        con_ssh.exec_cmd("system host-label-assign %s kube-cpu-mgr-policy=static" % SRIOV_C1)
        con_ssh.exec_cmd("system host-cpu-modify -f application-isolated -p0 16 %s" % SRIOV_C1)
        time.sleep(60)

        host_helper.unlock_host(SRIOV_C1)
        time.sleep(30)

@mark.hw_validation
def test_dpdk_pods(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    active = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=active) as con_ssh:
        home_dir = HostLinuxUser.get_home()

        pktgen = "utils/test_files/Test10_dpdk-pktgen-vfio.yaml"
        testpmd = "utils/test_files/Test10_dpdk-testpmd-vfio.yaml" 
        dpdk_expect = "utils/test_files/Test10_expect.expect"
        dpdk_subprocess = "utils/test_files/Test10_subprocess.py"

        common.scp_from_localhost_to_active_controller(source_path=dpdk_expect, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path=dpdk_subprocess, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path=pktgen, dest_path=home_dir)
        common.scp_from_localhost_to_active_controller(source_path=testpmd, dest_path=home_dir)

        con_ssh.exec_cmd("kubectl create -f Test10_dpdk-pktgen-vfio.yaml")
        time.sleep(10)

        con_ssh.exec_cmd("kubectl create -f Test10_dpdk-testpmd-vfio.yaml")
        time.sleep(60)

        _, output_pktgen = con_ssh.exec_cmd("kubectl get pods|grep dpdk-pktgen")
        _, output_testpmd = con_ssh.exec_cmd("kubectl get pods|grep dpdk-testpmd")

        assert ("Running" in output_pktgen), "Test Failed: the pod pktgen is not running"
        assert ("Running" in output_testpmd), "Test Failed: the pod testpmd is not running"

@mark.hw_validation
def test_dpdk_vf_pktgen(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    with host_helper.ssh_to_host(hostname=SRIOV_C0) as con_ssh:
        vf_pci = get_vf_pci(con_ssh, "dpdk-pktgen")

        cmd_vf_path = "ls -l /sys/class/net/%s/device/virtfn*|grep %s" % (SRIOV_NIC_C0, vf_pci)
        _, vf_path = con_ssh.exec_cmd(cmd_vf_path)

        vf_num = find_virtfn_number(vf_path)
        cmd_vf_set_mac = "ip link set %s vf %s mac 9e:fd:e6:dd:44:44" % (SRIOV_NIC_C0, vf_num)
        code, output = con_ssh.exec_sudo_cmd(cmd_vf_set_mac)

        assert code == 0, "Test Failed"


@mark.hw_validation
def test_dpdk_vf_testpmd(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    with host_helper.ssh_to_host(hostname=SRIOV_C1) as con_ssh:
        vf_pci = get_vf_pci(con_ssh, "dpdk-testpmd")

        cmd_vf_path = "ls -l /sys/class/net/%s/device/virtfn*|grep %s" % (SRIOV_NIC_C1, vf_pci)
        _, vf_path = con_ssh.exec_cmd(cmd_vf_path)

        vf_num = find_virtfn_number(vf_path)
        cmd_vf_set_mac = "ip link set %s vf %s mac 9e:fd:e6:dd:55:55" % (SRIOV_NIC_C1, vf_num)
        code, output = con_ssh.exec_sudo_cmd(cmd_vf_set_mac)

        assert code == 0, "Test Failed"

@mark.hw_validation
def test_dpdk_check(request):
    if system_helper.is_aio_simplex():
        skip("Simplex system detected")

    active = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=active) as con_ssh:
        home_dir = HostLinuxUser.get_home()

        code, taskset_pktgen = con_ssh.exec_cmd("kubectl exec -it dpdk-pktgen -- taskset -pc 1")
        affinity_pktgen = taskset_pktgen.strip().split(' ')[5]

        code, taskset_testpmd = con_ssh.exec_cmd("kubectl exec -it dpdk-testpmd -- taskset -pc 1")
        affinity_testpmd = taskset_testpmd.strip().split(' ')[5]

        
        LOG.tc_step("Cores assigned for pktgen are " + affinity_pktgen)
        LOG.tc_step("Cores assigned for testpmd are  " + affinity_testpmd) 

        con_ssh.exec_cmd("chmod +x Test10_expect.expect")
        affinity_pktgen_list = get_cpu_list(affinity_pktgen) 
        vf_pci_pktgen = get_vf_pci(con_ssh, "dpdk-pktgen")
        vf_pci_testpmd = get_vf_pci(con_ssh, "dpdk-testpmd")

        con_ssh.exec_cmd("sed -i 's/pktgen_affinity/"+affinity_pktgen+"/' Test10_expect.expect")
        con_ssh.exec_cmd("sed -i 's/testpmd_affinity/"+affinity_testpmd+"/' Test10_subprocess.py")

        con_ssh.exec_cmd("sed -i 's/pktgen_PCI/"+vf_pci_pktgen+"/' Test10_expect.expect")
        con_ssh.exec_cmd("sed -i 's/2ndCPUpktgen/"+str(affinity_pktgen_list[1])+".0/' Test10_expect.expect")
        con_ssh.exec_cmd("sed -i 's/testpmd_PCI/"+vf_pci_testpmd+"/' Test10_subprocess.py")

        code, output = con_ssh.exec_cmd("python3 Test10_subprocess.py")
        bandwidth = output.strip().split('\n')
        LOG.tc_step("Rx Bandwidth is: " + bandwidth[0])
        LOG.tc_step("Tx Bandwidth is: " + bandwidth[1])
        speed = con_ssh.exec_sudo_cmd("ethtool %s | awk -F'[ :]' '/Speed:/ {gsub(/[^0-9.]/,\"\",$3); print $3}'" % SRIOV_NIC_C1)
        performance_rx = (float(bandwidth[0])/float(speed[1])) / 10000
        LOG.tc_step("Rx Performance is " + str(performance_rx))
        performance_tx = (float(bandwidth[1])/float(speed[1])) / 10000
        LOG.tc_step("Tx Performance is " + str(performance_tx))

        con_ssh.exec_cmd("kubectl delete -f Test10_dpdk-pktgen-vfio.yaml")
        con_ssh.exec_cmd("kubectl delete -f Test10_dpdk-testpmd-vfio.yaml")
        con_ssh.exec_cmd("rm Test10_*")

        assert (performance_rx >= 90), "Test Failed"
        assert (performance_tx >= 90), "Test Failed"
