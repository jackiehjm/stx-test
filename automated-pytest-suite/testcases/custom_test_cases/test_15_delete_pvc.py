from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper

@mark.caas
def test_delete_pvc(request):
    host=system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        yaml_file ="/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/pv-volume.yaml"
        yaml_dict = common.get_yaml_data(yaml_file)
        pv_name = yaml_dict['metadata']['name']
        LOG.tc_step('kubectl apply {}, and check {} Persistent volume is created and '
                    'running'.format(yaml_file, pv_name))
        kube_helper.apply_and_check_pv(request ,yaml_file, resource_name=pv_name, con_ssh=con_ssh ,timeout=30
                                       ,interval=10)

        yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/pv-claim.yaml"
        yaml_dict = common.get_yaml_data(yaml_file)
        pvc_name = yaml_dict['metadata']['name']
        LOG.tc_step('kubectl apply {}, and check {} Persistent volume Claim is created and '
                    'running'.format(yaml_file, pvc_name))
        kube_helper.apply_and_check_pvc(request, yaml_file, resource_name=pvc_name, con_ssh=con_ssh, timeout=30,
                                        interval=10)
