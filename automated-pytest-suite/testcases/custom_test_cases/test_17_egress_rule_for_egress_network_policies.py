from pytest import mark
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper, traffic_helper
from consts.auth import HostLinuxUser

@mark.caas
def test_egress_rule_for_egress_network_policies(request):
    LOG.info("Verify the Egress rule for Egress Network Policies")
    pod_name = "test-pod1"
    LOG.info("Deploying pod {} with centos image".format(pod_name))
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        yaml_file = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/test_pod.yaml"
        home_dir = HostLinuxUser.get_home()
        common.scp_from_localhost_to_active_controller(yaml_file, dest_path=home_dir)
        file = yaml_file.split("/")[-1]
        arg_str = ' {}/{}'.format(home_dir,file)
        LOG.tc_step("kubectl apply {}, and check {} Pod is created and running".format(yaml_file, pod_name))
        request.addfinalizer(lambda: con_ssh.exec_cmd("rm -rf {}/{}".format(home_dir, file)))
        request.addfinalizer(lambda: kube_helper.delete_resources(resource_names=pod_name,resource_types="pod" ,con_ssh=con_ssh,check_both_controllers=False))
        assert kube_helper.apply_pod(arg_str, pod_name, con_ssh=con_ssh), "Pod creation {} failed".format(pod_name)
   
        pod_ip = kube_helper.get_deployed_pod_ip(request, pod_name=pod_name, con_ssh=con_ssh)
        yaml_path = "/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/"
        yaml_file = "egress_rule.yaml"
        yaml_out = "egress_out.yaml"
        LOG.info("Read the yaml file from for Network Policy")
        yaml_dict = common.get_yaml_data(yaml_path + yaml_file)

        idrac_ip_subnet = kube_helper.get_idrac_ip_network_range(con_ssh=con_ssh)
        yaml_dict['spec']['egress'][0]['destination']['nets'][0] = idrac_ip_subnet
        common.write_yaml_data_to_file(yaml_dict, yaml_out, directory="/usr/wrcptestsuite/automated-pytest-suite/utils/test_files")
        networkpolicy = "deny-egress-bmc"
        ret=kube_helper.create_and_verify_network_policy(request, yaml_path + yaml_out, networkpolicy, con_ssh=con_ssh)
        assert ret == True, "Creating Network Policy {} failed".format(networkpolicy)
        bmc_gw_ip, _ = system_helper.get_idrac_ip_and_subnet(con_ssh=con_ssh)
    
        LOG.tc_step("Verifying traffic from pod to bmc, traffic should be blocked")
        kube_command = "kubectl exec -it {} --".format(pod_name)
        out_data= traffic_helper.verify_traffic_after_creating_network_policy(kube_command, bmc_gw_ip, con_ssh=con_ssh)
        LOG.info("Packet loss is {}".format(out_data[0]['packet_loss']))
        assert out_data[0]['packet_loss'] == 100, "Verification of NetworkPolicy to drop traffic from Pod to IDRAC IP is failed : {}".format(pod_name) 

        LOG.tc_step("Verifying traffic from pod to OAM IPs, traffic should flow")
        if system_helper.is_aio_duplex(con_ssh=con_ssh):
            oam_ip =  system_helper.get_oam_ip("oam_c0_ip", con_ssh=con_ssh)
        else:
            oam_ip = system_helper.get_oam_ip("oam_ip", con_ssh=con_ssh)
        out_data= traffic_helper.verify_traffic_after_creating_network_policy(kube_command, oam_ip, con_ssh=con_ssh)
        assert out_data[0]['packet_loss'] == 0, "Verification of NetworkPolicy to allow traffic from Pod to OAM IP is failed : {}".format(pod_name)
