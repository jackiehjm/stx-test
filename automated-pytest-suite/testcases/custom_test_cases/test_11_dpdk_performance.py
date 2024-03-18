import re
import time
from pytest import mark
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper, \
    container_helper, keystone_helper
from consts.auth import Tenant, HostLinuxUser
import yaml
from utils import cli, table_parser
import json
import os
import shutil
from consts.auth import Tenant, HostLinuxUser

hosts=system_helper.get_hypervisors(operational="enabled", availability="available")

pktgen_yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/pktgen.yaml"
testpmd_yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/testpmd.yaml"

def update_dpdk_pod_yaml(host, con_ssh, request):
    ret = False
    try:
        code, sriov_list = cli.system("host-if-list {} --nowrap |grep sriov |grep vf ".format(host),
                                      ssh_client=con_ssh)
        ret = True
    except:
        pass
    assert ret, "sriov vf is not not enabled"
    sriov = common.parse_table_to_dict(sriov_list, 9, 0, 1)
    vfio_driver = ""
    for i, ifname in sriov.items():
        table_ = table_parser.table(cli.system("host-if-show {} {}".format(host, i),
                                               ssh_client=con_ssh, auth_info=Tenant.get('admin_platform'))[1])
        table_sriov_numvfs = table_parser.filter_table(table_, Property='{}'.format('sriov_numvfs'))
        table_sriov_vf_driver = table_parser.filter_table(table_, Property='{}'.format('sriov_vf_driver'))
        sriov_numvfs = table_parser.get_values(table_sriov_numvfs, 'Value', strict=False)[0]
        sriov_vf_driver = table_parser.get_values(table_sriov_vf_driver, 'Value', strict=False)[0]
        if host == "controller-0" or host == "controller-1":
            if sriov_vf_driver == "vfio" and int(sriov_numvfs) >= 3 :
                vfio_driver = ifname
                break
            else:
                continue
        else:
            if sriov_vf_driver == "vfio":
                vfio_driver = ifname
                break
            else:
                continue
    assert vfio_driver != "", "There is no vfio_driver present associated with sriov interface"
    yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/mfvfio.yaml"

    yaml_file = open(yaml_file).read()
    yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)
    request.addfinalizer(lambda: shutil.rmtree("test_yamls"))
    os.mkdir("test_yamls")

    nad_yaml = "test_yamls/" + yaml_data["metadata"]["name"] + ".yaml"
    yaml_data["metadata"]["annotations"]["k8s.v1.cni.cncf.io/resourceName"] = "intel.com/pci_sriov_net_{}".format(
        vfio_driver)
    with open(nad_yaml, "w+") as file:
        yaml.dump(yaml_data, file, default_flow_style=False)
    assert kube_helper.create_and_verify_network_attachment(request, nad_yaml, yaml_data["metadata"]["name"],
                                                            con_ssh=con_ssh), "Failed to create NetworkAttachmentDefinition".format(
        yaml_data["metadata"]["name"])

    yaml_file = open(pktgen_yaml_file).read()
    yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)

    yaml_data["spec"]["nodeName"] = host

    yaml_data['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_{}'.format(vfio_driver)] = \
    yaml_data['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']
    del yaml_data['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']

    yaml_data["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_{}".format(vfio_driver)] = \
    yaml_data["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]
    del yaml_data["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]

    pktgen_pod = yaml_data["metadata"]["name"]
    pktgen_pod_yaml = "test_yamls/" + pktgen_pod + ".yaml"
    with open(pktgen_pod_yaml, "w+") as file:
        yaml.dump(yaml_data, file, default_flow_style=False)

    yaml_file = open(testpmd_yaml_file).read()
    yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)

    yaml_data["spec"]["nodeName"] = host

    yaml_data['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_{}'.format(vfio_driver)] = \
    yaml_data['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']
    del yaml_data['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']

    yaml_data["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_{}".format(vfio_driver)] = \
    yaml_data["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]
    del yaml_data["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]

    testpmd_pod = yaml_data["metadata"]["name"]
    testpmd_pod_yaml = "test_yamls/" + testpmd_pod + ".yaml"
    with open(testpmd_pod_yaml, "w+") as file:
        yaml.dump(yaml_data, file, default_flow_style=False)
    return pktgen_pod, pktgen_pod_yaml, testpmd_pod, testpmd_pod_yaml


def create_pod_from_yaml(request, con_ssh, pod_yaml, pod_name):
    assert kube_helper.create_and_verify_pod(request, con_ssh, pod_yaml,
                                             pod_name), "Pod {} creation failed".format(pod_name)


def fetch_config_from_pktgen_pod(pktgen_pod, con_ssh):
    code, output = kube_helper.exec_kube_cmd(sub_cmd='exec',
                                             args="-it {} -n default -- sh -c \"taskset -pc 1\"".format(pktgen_pod),
                                             con_ssh=con_ssh)
    matcher = re.compile(r'pid 1\'s current affinity list: (\d+),(\d+)')
    match = matcher.search(output)
    cpu1, cpu2 = match.groups()
    code, output = kube_helper.exec_kube_cmd(sub_cmd='exec',
                                             args="-it {} -n default -- sh -c \"env | grep PCI\"".format(pktgen_pod),
                                             con_ssh=con_ssh)
    intel_acc_matcher = re.compile(r'\b(0{0,4}:\d{2}:\d{2}.\d:?\w*)')
    match = intel_acc_matcher.search(output)
    pci_addr = match.groups()[0]
    return cpu1, cpu2, pci_addr

def start_pktgen(con_ssh, cpu1, cpu2, pci_addr, pktgen_pod):
    original_prompt = con_ssh.get_prompt()
    con_ssh.set_prompt(r'Pktgen:/>')
    change_to_build_dir = "cd /opt/pktgen-dpdk-pktgen-20.11.3/Builddir/app"
    start_pktgen = "./pktgen -l {},{} n 3 -w {} --proc-type auto --socket-mem 1024 --file-prefix pg --  -P -m \"{}.0\" --crc-strip".format(
        cpu1, cpu2, pci_addr, cpu2)
    _, output = con_ssh.exec_cmd(
        "kubectl exec -it {} -n default -- sh -c \"{}; {}\"".format(pktgen_pod, change_to_build_dir, start_pktgen),
        get_exit_code=False)
    return output

def start_testpmd(active_ctrl, testpmd_pod, src_mac):
    with host_helper.ssh_to_host(hostname=active_ctrl) as testpmd_ssh:
        code, output = kube_helper.exec_kube_cmd(sub_cmd='exec',
                                                 args="-it {} -n default -- sh -c \"taskset -pc 1\"".format(
                                                     testpmd_pod), con_ssh=testpmd_ssh)
        matcher = re.compile(r'pid 1\'s current affinity list: (\d+),(\d+)')
        match = matcher.search(output)
        cpu1, cpu2 = match.groups()
        code, output = kube_helper.exec_kube_cmd(sub_cmd='exec',
                                                 args="-it {} -n default -- sh -c \"env | grep PCI\"".format(
                                                     testpmd_pod), con_ssh=testpmd_ssh)
        intel_acc_matcher = re.compile(r'\b(0{0,4}:\d{2}:\d{2}.\d:?\w*)')
        match = intel_acc_matcher.search(output)
        pci_addr = match.groups()[0]

        testpmd_start = "/opt/dpdk-20.11/build/app/dpdk-testpmd --socket-mem 1024 -l {},{} -w {} --file-prefix=testpmd_ -- --forward-mode=mac --auto-start --stats-period 1 --eth-peer=0,\"{}\"".format(
            cpu1, cpu2, pci_addr, src_mac)
        original_prompt = testpmd_ssh.get_prompt()
        testpmd_ssh.set_prompt(r'(.*?)')

        LOG.tc_step("Starting DPDK-Testpmd application")
        _, output = testpmd_ssh.exec_cmd(
            "kubectl exec {} -n default -- sh -c \"{} > testpmd_op.txt &\"".format(testpmd_pod, testpmd_start),
            get_exit_code=False)
        time.sleep(3)
        testpmd_ssh.send_control()
        testpmd_ssh.set_prompt(original_prompt)
        testpmd_ssh.expect(timeout=10)
        _, file_content = testpmd_ssh.exec_cmd(
            "kubectl exec {} -n default -- sh -c \"head -25 testpmd_op.txt \"".format(testpmd_pod))
        matcher = re.compile(r'(?:[0-9a-fA-F]:?){12}')
        dst_mac = re.findall(matcher, file_content)[0]
        return dst_mac


@mark.caas
@mark.parametrize('host', hosts)
def test_dpdk_performance(host, request):
    LOG.tc_step("Checking system health")
    output, _ = system_helper.get_system_health_query()
    assert output == 0, "System not in healthy state, exiting tests"

    LOG.tc_step("Retrieving the active controller from the lab")
    active_ctrl=system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        original_prompt = con_ssh.get_prompt()
        host_status = system_helper.get_host_values(host, ('availability', 'operational'), con_ssh=con_ssh,
                                                    auth_info=Tenant.get('admin_platform'))
        assert host_status[0] == "available" and host_status[1] == "enabled", "Host {} not in available and operational state, marking the test as failed".format(host)

        LOG.tc_step('Selecting a sriov vfio driver with num of vfs more than 3')
        pktgen_pod, pktgen_pod_yaml, testpmd_pod, testpmd_pod_yaml = update_dpdk_pod_yaml(host, con_ssh, request)

        LOG.tc_step("Creating Pktgen pod")
        create_pod_from_yaml(request, con_ssh, pktgen_pod_yaml, pktgen_pod)

        if host == "controller-0" or host == "controller-1":
            LOG.tc_step("Creating TestPMD pod")
            create_pod_from_yaml(request, con_ssh, testpmd_pod_yaml, testpmd_pod)

        LOG.tc_step("Fetching configuration values from the Pktgen pod")
        cpu1, cpu2, pci_addr = fetch_config_from_pktgen_pod(pktgen_pod, con_ssh)

        if "worker" in host:
            con_ssh.set_prompt(original_prompt)
            _, output = con_ssh.exec_cmd("quit", get_exit_code=False)
            assert pci_addr, "VFIO PCI address not present on the pod for host {}, marking the test as failed".format(host)
            return 

        LOG.tc_step("Starting Pktgen application")
        output = start_pktgen(con_ssh, cpu1, cpu2, pci_addr, pktgen_pod)
        
        if "No response or return failure" in output:
            LOG.info("Did not get a clean start for Pktgen app for the first time,"
                      "\nPerforming cleanup and re-starting the test.")
            if host == "controller-0" or host == "controller-1":
                matcher = re.compile(r'(?:[0-9a-fA-F]:?){12}')
                src_mac = re.findall(matcher, output)[0]
                con_ssh.exec_cmd("page main", get_exit_code=False)
                con_ssh.set_prompt(original_prompt)
                _, output = con_ssh.exec_cmd("quit", get_exit_code=False)

                LOG.tc_step("Fetching configuration values from Testpmd pod")
                dst_mac = start_testpmd(active_ctrl, testpmd_pod, src_mac)

            LOG.tc_step("Deleting Pktgen and/or Testpmd pods")
            con_ssh.exec_cmd("page main", get_exit_code=False)
            con_ssh.set_prompt(original_prompt)
            _, output = con_ssh.exec_cmd("quit", get_exit_code=False)

            con_ssh.exec_cmd(cmd="kubectl delete pod {}".format(pktgen_pod))
            if host == "controller-0" or host == "controller-1":
                con_ssh.exec_cmd(cmd="kubectl delete pod {}".format(testpmd_pod))

            LOG.info("Re-creating Pktgen and/or Testpmd pods")
            LOG.tc_step("Creating Pktgen pod")
            create_pod_from_yaml(request, con_ssh, pktgen_pod_yaml, pktgen_pod)

            if host == "controller-0" or host == "controller-1":
                LOG.tc_step("Creating TestPMD pod")
                create_pod_from_yaml(request, con_ssh, testpmd_pod_yaml, testpmd_pod)

            LOG.tc_step("Fetching configuration values from the Pktgen pod")
            cpu1, cpu2, pci_addr = fetch_config_from_pktgen_pod(pktgen_pod, con_ssh)
            if "worker" in host:
                con_ssh.set_prompt(original_prompt)
                _, output = con_ssh.exec_cmd("quit", get_exit_code=False)
                assert pci_addr, "VFIO PCI address not present on the pod for host {}, marking the test as failed".format(host)
            if host == "controller-0" or host == "controller-1":
                LOG.tc_step("Starting Pktgen application")
                output = start_pktgen(con_ssh, cpu1, cpu2, pci_addr, pktgen_pod)
        LOG.info("Pktgen app started correctly, continuing...")
        matcher = re.compile(r'(?:[0-9a-fA-F]:?){12}')
        src_mac = re.findall(matcher, output)[0]
        con_ssh.exec_cmd("page main", get_exit_code=False)
        con_ssh.set_prompt(original_prompt)
        _, output = con_ssh.exec_cmd("quit", get_exit_code=False)
            
        if host == "controller-0" or host == "controller-1":
            LOG.tc_step("Fetching configuration values from Testpmd pod")
            dst_mac = start_testpmd(active_ctrl, testpmd_pod, src_mac)
    
            LOG.tc_step("Starting Pktgen application and sending traffic to TestPMD pod")
    
            def quit_pktgen():
                LOG.info("Exiting from pktgen")
                con_ssh.set_prompt(original_prompt)
                _, output = con_ssh.exec_cmd("quit", get_exit_code=False)
            request.addfinalizer(quit_pktgen)
    
            try:
                LOG.tc_step("Fetching configuration values from the Pktgen pod")
                cpu1, cpu2, pci_addr = fetch_config_from_pktgen_pod(pktgen_pod, con_ssh)
    
                LOG.tc_step("Starting Pktgen application")
                output = start_pktgen(con_ssh, cpu1, cpu2, pci_addr, pktgen_pod)
                assert "No response or return failure" not in output, "Pktgen application failed to start even the second time, marking the test as failed"
                _, _ = con_ssh.exec_cmd("set 0 dst mac {}".format(dst_mac), get_exit_code=False)
                _, _ = con_ssh.exec_cmd("set 0 size 1024", get_exit_code=False)
                _, _ = con_ssh.exec_cmd("set 0 rate 40%", get_exit_code=False)
                _, _ = con_ssh.exec_cmd("start 0", get_exit_code=False)
                time.sleep(2)
    
                LOG.tc_step("Running traffic for 30 seconds and observing stats")
                ansi_escape_regex = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                prev_pkts_max_rx_1 = 0
                for i in range(6):
                    LOG.info("Iteration {}".format(i))
                    output = con_ssh.get_raw_output("page main", get_exit_code=False)
                    parsed_op = ansi_escape_regex.sub('', output)
                    LOG.info("Parsed output of 'page main' {}".format(parsed_op))
                    stats = re.findall(r'\d+/\d+', parsed_op[-100:])
                    pkts_max_rx = stats[0]
                    mbit_rx_tx = stats[2]
                    rx, tx = re.findall(r'(\d+)', mbit_rx_tx)
                    pkts_max_rx_1, _ = re.findall(r'(\d+)', pkts_max_rx)
                    assert int(rx) >= 0.99 * int(tx), "Packet loss observed. Rx is very low compared to transmitted."
                    assert int(pkts_max_rx_1) >= prev_pkts_max_rx_1, "Pkts/s Max/Rx not being updated constantly"
                    prev_pkts_max_rx_1 = int(pkts_max_rx_1)
                    time.sleep(5)
            except Exception as e:
                LOG.error("Exception {}".format(e))
                con_ssh.set_prompt(original_prompt)
                _, output = con_ssh.exec_cmd("quit", get_exit_code=False)
                raise e

