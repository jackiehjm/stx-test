from pytest import fixture, mark, skip
from utils.tis_log import LOG
from utils import cli, table_parser
from keywords import host_helper, system_helper
from consts.auth import Tenant

@mark.caas
def test_system_interface():
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        for entry in system_helper.get_host_list_data():
            LOG.tc_step("Verifying if all required platform interfaces are present on {}".format(entry['hostname']))
            table_ = table_parser.table(cli.system('interface-network-list {}'.format(entry['hostname']), ssh_client=con_ssh, auth_info=Tenant.get('admin_platform'))[1])
            if_name = table_parser.get_values(table_, target_header="ifname")
            network_name = table_parser.get_values(table_, target_header="network_name")
            ctrl_with_pxeboot =  ['pxeboot', 'oam', 'cluster-host', 'mgmt']
            ctrl_without_pxeboot =  [ 'oam', 'cluster-host', 'mgmt']
            worker_with_pxeboot = ['pxeboot', 'cluster-host', 'mgmt']
            worker_without_pxeboot = ['cluster-host', 'mgmt']
            if system_helper.is_aio_duplex(con_ssh):
                if entry['personality'] == "controller":
                    assert set(network_name) == set(ctrl_with_pxeboot), "{} system interfaces not correctly configured, check if following networks exist {}".format(entry['hostname'], ctrl_ntwrk)
                elif entry['personality'] == "worker":
                    assert set(network_name) == set(worker_with_pxeboot) or set(network_name) == set(worker_without_pxeboot), "{} system interfaces not correctly configured, check if following networks exist {}".format(entry['hostname'], worker_ntwrk)
                else:
                    LOG.error("Personality not set correctly for host {}".format(entry['hostname']))
            else:
                assert set(network_name) == set(ctrl_without_pxeboot)  or set(network_name) == set(ctrl_with_pxeboot), "{} system interfaces not correctly configured, check if following networks exist {}".format(entry['hostname'], ctrl_ntwrk)
