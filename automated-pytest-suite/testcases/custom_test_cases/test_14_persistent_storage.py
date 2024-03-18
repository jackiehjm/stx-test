import yaml

from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
from consts.auth import  HostLinuxUser, Tenant

hosts=system_helper.get_hypervisors(operational="enabled", availability="available")

@mark.caas
@mark.parametrize('host', hosts)
def test_persistent_storage(host, request):
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

        yaml_file="/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/pv_claim_1.yaml"
        yaml_dict = common.get_yaml_data(yaml_file)
        pvc_name = yaml_dict['metadata']['name']
        LOG.tc_step('kubectl apply {}, and check {} Persistent Volume Claim is created and '
                    'running'.format(yaml_file, pvc_name))
        kube_helper.apply_and_check_pvc(request,yaml_file, resource_name=pvc_name, con_ssh=con_ssh, timeout=30 ,interval=10                                               ), "PVC creation {} failed".format(pvc_name)

        yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/pv_pod.yaml"
        file = yaml_file.split("/")[-1]
        home_dir = HostLinuxUser.get_home()
        arg_str = ' {}/{}'.format(home_dir,file)
        yaml_dict = common.get_yaml_data(yaml_file)
        pod_name = yaml_dict['metadata']['name']
        yaml_dict["spec"]["nodeName"] = host
        pod_yaml = "pv_pod.yaml"
        with open(pod_yaml, "w+") as file:
            yaml.dump(yaml_dict, file, default_flow_style=False)

        LOG.tc_step('kubectl apply {}, and check {} Pod is created and running'.format(pod_yaml, pod_name))
        assert kube_helper.create_and_verify_pod(request, con_ssh, pod_yaml, pod_name), "Pod {} creation failed".format(
            pod_name)

        mount_dir = yaml_dict['spec']['containers'][0]['volumeMounts'][0]['mountPath']
        filename = "{}/testfile".format(mount_dir)
        contents = "TEST_FILE"
        LOG.tc_step("Writing a file in Pod {}".format(pod_name))
        ret = kube_helper.create_file_in_a_pod(request, filename, pod_name, contents, con_ssh=con_ssh)
        assert contents in ret, "Writing {} failed".format(filename)

        LOG.tc_step("Deleting Pod {} and creating it again".format(pod_name))
        assert kube_helper.delete_resources(resource_names=pod_name, con_ssh=con_ssh), "Pod {} deletion failed".format(pod_name)
        assert kube_helper.apply_pod(arg_str, pod_name, con_ssh=con_ssh), "Pod re-creation {} failed".format(pod_name)
        LOG.tc_step("Checking file {} in  new pod -  {}".format(filename, pod_name))
        ret = kube_helper.create_file_in_a_pod(request, filename, pod_name, contents, create=False, con_ssh=con_ssh)
        assert contents in ret, "Persistence of {} failed".format(filename)

