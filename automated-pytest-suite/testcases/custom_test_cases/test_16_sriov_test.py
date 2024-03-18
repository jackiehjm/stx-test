import yaml

from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common,ping_helper, kube_helper, host_helper, system_helper,network_helper, traffic_helper
from utils import cli, table_parser
import json
import os
import shutil
import re
import time
from consts.auth import Tenant, HostLinuxUser

hosts=system_helper.get_hypervisors(operational="enabled", availability="available")

@mark.caas
@mark.latency
@mark.parametrize('host', hosts)
def test_sriov_net_plugin(host, request):
    LOG.tc_step("Checking system health")
    output, _ = system_helper.get_system_health_query()
    assert output == 0, "System not in healthy state, exiting tests"

    LOG.tc_step("Retrieving the active controller from the lab")
    active_ctrl=system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        host_status = system_helper.get_host_values(host, ('availability', 'operational'), con_ssh=con_ssh,
                                                    auth_info=Tenant.get('admin_platform'))
        assert host_status[0] == "available" and host_status[
            1] == "enabled", "Host {} not in available and operational state, marking the test as failed".format(host)

        request.addfinalizer(lambda: time.sleep(180))
        LOG.tc_step('Select an already existing sriov net device ')
        ret = False
        try:
            code, sriov_list = cli.system("host-if-list {} --nowrap |grep sriov |grep vf ".format(host),
                                      ssh_client=con_ssh)
            ret = True
        except:
            pass
        assert ret, "sriov vf is not not enabled"
        sriov = common.parse_table_to_dict(sriov_list, 9, 0, 1)
        LOG.info("sriov items {}".format(sriov.items()))
        netdevice = ""
        for i, ifname in sriov.items():
            code, sriov_list = cli.system("host-if-show {} {} |grep sriov_vf_driver".format(host, i),
                                          ssh_client=con_ssh)
            if 'netdevice' in sriov_list:

                table_ = table_parser.table(
                 cli.system('host-if-show {} {}'.format(host, i), ssh_client=con_ssh, auth_info=Tenant.get('admin_platform'))[1])
                table_ = table_parser.filter_table(table_, Property='sriov_numvfs')
                numofvfs = table_parser.get_values(table_, 'Value', strict=False)[0]
                LOG.info("numofvfs {}".format(numofvfs))
                if int(numofvfs) >= 2:
                    netdevice = ifname
                    break
                else:
                    continue
                LOG.info("netdevice {}".format(netdevice))
                break
        assert netdevice != "", "There is no netdevice present associated with sriov interface"
        #if netdevice == "":
        #    skip('There is no netdevice present associated with sriov interface')
        yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/sriov_net_plugin_test.yaml"
        yaml_file = open(yaml_file).read()
        yaml_file = yaml_file.split("---")
        yamls = []
        for file in yaml_file:
            yaml_out = yaml.load(file, Loader=yaml.FullLoader)
            yamls.append(yaml_out)
        yamls = filter(None, yamls)
        pods = []
        nads={}
        c=0
        os.mkdir("test_yamls")
        request.addfinalizer(lambda: shutil.rmtree("test_yamls"))
        for yamldata in yamls:
            if yamldata["kind"] == "Pod":
                pods.append(yamldata)
            if yamldata["kind"] == "NetworkAttachmentDefinition":
                nads[c] = [yamldata["metadata"]["name"],
                           json.loads(yamldata["spec"]["config"]).get("ipam").get("addresses")[0].get("address")]
                LOG.info("nads is {}".format(nads[c]))
                c+=1
                nad_yaml="test_yamls/"+yamldata["metadata"]["name"] + ".yaml"
                yamldata["metadata"]["annotations"]["k8s.v1.cni.cncf.io/resourceName"] = "intel.com/pci_sriov_net_{}".format(netdevice)
                with open(nad_yaml, "w+") as file:
                    yaml.dump(yamldata, file, default_flow_style=False)
                assert kube_helper.create_and_verify_network_attachment(request, nad_yaml, yamldata["metadata"]["name"],
                                                                 con_ssh=con_ssh), "Failed to create NetworkAttachmentDefinition".format(yamldata["metadata"]["name"])
        for pod in pods:
            pod_name=pod["metadata"]["name"]
            LOG.tc_step("Creating pod : {}".format(pod_name))
            if pod_name == "test-pod-sriov":
                pod["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks"] = "sriov-static-pod"
                pod['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_{}'.format(netdevice)] =  pod['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']
                del pod ['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']

                pod["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_{}".format(netdevice)] = pod["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]
                del pod["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]

                pod["spec"]["nodeName"] = host
            if pod_name == "test-pod-sriov2":
                pod["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks"] = "sriov-static-pod2"
                pod['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_{}'.format(netdevice)] =  pod['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']
                del pod ['spec']['containers'][0]['resources']['requests']['intel.com/pci_sriov_net_dpdk']

                pod["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_{}".format(netdevice)] = pod["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]
                del pod["spec"]["containers"][0]["resources"]["limits"]["intel.com/pci_sriov_net_dpdk"]

                pod["spec"]["nodeName"] = host
            pod_yaml="test_yamls/" + pod_name + ".yaml"
            with open(pod_yaml, "w+") as file:
                yaml.dump(pod, file, default_flow_style=False)
            assert kube_helper.create_and_verify_pod(request, con_ssh, pod_yaml,
                                                         pod_name), "Pod {} creation failed".format(pod_name)
        pod_name=[pod['metadata']['name'] for pod in pods]
        for i in range(0,len(pods)):
            LOG.tc_step("Ping from pod {} to pod {}".format(pod_name[i], pod_name[abs(i-1)]))
            out = con_ssh.exec_cmd(
                    cmd="kubectl exec {} -- ping {} -c 6".format(pod_name[i], nads[abs(i - 1)][1].split("/")[0]),
                    get_exit_code=False, expect_timeout=30)
            packet_loss = -1
            LOG.info("Output {}".format(out))
            for stat in out:
                if "loss" in str(stat):
                    packet_loss = int([x for x in stat.split('\n') if x.find('packet loss') != -1][0].split('%')[0].split(' ')[-1])
            assert packet_loss == 0, "Ping encountered packet loss of {}".format(packet_loss)
            LOG.info("ping results, packet loss is {}%,### ".format(packet_loss))
            _, out = con_ssh.exec_cmd(cmd="kubectl exec {} -- env |grep PCI_SRIOV_NET".format(pod_name[i]),
                                          get_exit_code=False)
            LOG.info("PCI Sriov present: ".format(out.split("=")[0]))
            assert out.split("=")[1].count(":") == 2, "PCI_SRIOV_NET not present"


