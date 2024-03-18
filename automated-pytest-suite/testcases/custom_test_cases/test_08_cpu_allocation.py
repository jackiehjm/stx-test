from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli
from keywords import host_helper, system_helper
from consts.auth import Tenant

@mark.caas
def test_cpu_allocation():
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        for entry in system_helper.get_host_list_data():
            LOG.tc_step("Verifying the number of CPU consumed by {}".format(entry))
            value = int(cli.system('host-cpu-list {}  | grep Platform | wc -l'.format(entry['hostname']), ssh_client=con_ssh, auth_info=Tenant.get('admin_platform'))[1])
            LOG.info("CPU core used by {} is {}".format(entry, value))
            if entry['personality'] == "controller":
                assert value == 4, "CPU allocation incorrect for controller"
            elif entry['personality'] == "worker":
                assert  value == 2, "CPU allocation incorrect for worker"
            else:
                LOG.error("Node's personality is not set correclty")


