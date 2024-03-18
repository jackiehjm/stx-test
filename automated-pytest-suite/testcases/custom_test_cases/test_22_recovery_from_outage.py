from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import common, kube_helper, host_helper, system_helper
import time
@mark.caas
def test_recovery_from_outage(request):
    host=system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Running the cli command to get Kube pods")
        pods=kube_helper.get_pods(field=('NAME', 'STATUS'), namespace="kube-system",con_ssh=con_ssh)
        running_pods=[]
        for x in pods:
            if x[1]=="Running" and host in x[0]:
                running_pods.append(x[0])
        LOG.tc_step("Delete pods with names containing {}".format(host))
        LOG.debug("Deleting pods :{}".format(running_pods))
        kube_helper.delete_resources(resource_names=running_pods, resource_types='pod',post_check=False,
                         namespace="kube-system", con_ssh=con_ssh, fail_ok=False,check_both_controllers=False)

        LOG.tc_step("Check if pods {} came up automatically after deletion".format(running_pods))
        ret,_=kube_helper.wait_for_pods_status(pod_names=running_pods, namespace="kube-system",timeout=60, fail_ok=False, con_ssh=con_ssh)
        assert ret , "PODs didn't came up as a part of self healing"

