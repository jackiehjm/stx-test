import yaml

from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import HostLinuxUser, Tenant

hosts=system_helper.get_hypervisors(operational="enabled", availability="available")

@mark.caas
@mark.parametrize('host', hosts)
def test_02_acc_card_config(host, request):
    LOG.tc_step("Checking system health")
    output, _ = system_helper.get_system_health_query()
    assert output == 0, "System not in healthy state, exiting tests"

    LOG.tc_step("Retrieving the active controller from the lab")
    active_ctrl = system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=active_ctrl) as con_ssh:
        host_status = system_helper.get_host_values(host, ('availability', 'operational'), con_ssh=con_ssh,
                                                    auth_info=Tenant.get('admin_platform'))
        assert host_status[0] == "available" and host_status[
            1] == "enabled", "Host {} not in available and operational state, marking the test as failed".format(host)

        yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/acc-test.yaml"
        home_dir = HostLinuxUser.get_home()
        common.scp_from_localhost_to_active_controller(yaml_file, dest_path=home_dir)
        file = yaml_file.split("/")[-1]
        arg_str = ' {}/{}'.format(home_dir,file)
        
        yaml_dict = common.get_yaml_data(yaml_file)
        pod_name = yaml_dict['metadata']['name']
        yaml_dict["spec"]["nodeName"] = host
        pod_yaml = file
        with open(pod_yaml, "w+") as file:
            yaml.dump(yaml_dict, file, default_flow_style=False)

        
        LOG.tc_step("Creating Pod {}".format(pod_name))
        assert kube_helper.create_and_verify_pod(request, con_ssh, pod_yaml, pod_name), "Pod {} creation failed".format(
            pod_name)

        LOG.tc_step("Checking if acceleration card is properly configured")
        code, output = kube_helper.exec_kube_cmd(sub_cmd='exec', args="-it {} -n default -- sh -c \"env | grep PCI\"".format(pod_name), con_ssh=con_ssh)
        pattern = r'\b([0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}.\d{1}\S*)'
        intel_acc = "PCIDEVICE_INTEL_COM_INTEL_ACC100_FEC"
        match = [pattern, intel_acc]
        assert list(filter(lambda x:  x in output, match)), "Acceleration card configuration is not correct"


