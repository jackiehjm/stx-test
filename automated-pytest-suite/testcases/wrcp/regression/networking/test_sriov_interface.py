import json
import random

from pytest import fixture, mark, param, skip

from consts.auth import HostLinuxUser
from consts.proj_vars import ProjVar
from keywords import common, dc_helper, host_helper, kube_helper, system_helper
from testcases.wrcp.regression.security import utils
from utils.tis_log import LOG

SYSTEM_DIR = HostLinuxUser.get_home()
TEST_FILES = "testcases/wrcp/regression/networking/test_files/sriov"
PCI_CLASSES = 'pci-sriov'
INTF_FIELDS = [
    'ifname',
    'ifclass',
    'iftype',
    'ports',
    'uses',
    'sriov_numvfs',
    'sriov_vf_driver',
    'vlan_id',
    'uuid',
    'used_by',
    'max_tx_rate',
    'imtu',
]
SRIOV_IF = 'sriov0'
PLATFORM_INTFS = ['pxeboot0', 'oam0', 'cluster0', 'mgmt0']


@fixture(scope="module")
def get_lab_utils(request):
    """
    Fixture to return the con_ssh,auth_info,region,fip of the lab
    Returns:
        con_ssh,auth_info,region,fip
    """
    region = "RegionOne"
    if ProjVar.get_var('IS_DC'):
        # Fow now only subcloud in DC is configured with sriov, this should be modified if any
        # interface is configured with sriov at central cloud
        region = ProjVar.get_var('PRIMARY_SUBCLOUD')
    con_ssh, auth_info = dc_helper.get_region_con_auth(region)
    fip = common.get_lab_fip(region=region, bracket_for_ipv6=True)
    return con_ssh, auth_info, region, fip


@mark.dc_sriov
@mark.container_platform
class TestSriov:
    vf_intf = "test_intf"
    new_sriov_intf = 'sriov425'
    namespace = "pvtest"
    data_network = 'testnetwork'
    pci_device = "PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_{}".format(data_network.upper())

    @fixture(scope='class')
    def ensure_sriov_configured(self, request, get_lab_utils):
        """
        Fixture to ensure that sriov is configured on the system
        Args:
            get_lab_utils (fixture)
        """
        (
            request.cls.con_ssh,
            request.cls.auth_info,
            request.cls.region,
            request.cls.fip,
        ) = get_lab_utils

        hosts = system_helper.get_hosts(con_ssh=self.con_ssh, auth_info=self.auth_info)

        request.cls.aio_simplex = system_helper.is_aio_simplex(
            con_ssh=self.con_ssh, auth_info=self.auth_info
        )

        LOG.fixture_step("{}:Get the hosts configured with sriov interface".format(self.region))
        # The sriov interface is comprised of class type 'pci-sriov' and if_type 'ethernet'
        request.cls.hosts_sriov_intfs = host_helper.get_hosts_interfaces_info(
            hosts,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            kwargs_for_get_host_interfaces={'net_type': PCI_CLASSES, 'if_type': 'ethernet'},
            kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True},
        )

        if not self.hosts_sriov_intfs:
            skip('No sriov interfaces are configured on any host on this lab system')

    @fixture(scope='class')
    def ensure_host(self, request):
        """secure the host to perform the tests"""
        request.cls.host = system_helper.get_active_controller_name(
            con_ssh=self.con_ssh, auth_info=self.auth_info
        )

        if system_helper.is_aio_duplex(con_ssh=self.con_ssh, auth_info=self.auth_info):
            request.cls.host = system_helper.get_standby_controller_name(
                con_ssh=self.con_ssh, auth_info=self.auth_info
            )

        if not self.aio_simplex and not system_helper.is_aio_duplex(
            con_ssh=self.con_ssh, auth_info=self.auth_info
        ):
            # Currently on a standard system, only compute nodes are configured with sriov
            for compute_node in system_helper.get_computes(
                con_ssh=self.con_ssh, auth_info=self.auth_info
            ):
                if compute_node in self.hosts_sriov_intfs:
                    request.cls.host = compute_node
                    break

        if request.cls.host not in self.hosts_sriov_intfs:
            skip("The selected host '{}' is not configured with sriov")

    @fixture(scope='class')
    def ensure_sriov(self, request):
        """Pick the base sriov interface to perform the test"""
        keys_view = list(self.hosts_sriov_intfs[self.host].keys())
        if SRIOV_IF in keys_view:
            request.cls.sriov_intf = SRIOV_IF
        else:
            request.cls.sriov_intf = random.choice(keys_view)

        port = self.hosts_sriov_intfs[self.host][self.sriov_intf]['ports'][-1]
        request.cls.sriov_port = host_helper.get_port_property_values(port, self.host)[port]

        LOG.info("Ensure '{}' port is Up".format(port))
        assert (
            self.sriov_port['operstate'] == 'up'
        ), "operstate of sriov '{}' is not up, check the underlying port '{}' status".format(
            self.sriov_intf, self.sriov_port
        )

    def get_cmd_output_in_json(self, host, cmd):
        """
        Function to return the output in json format
        Args:
            host (str): host to check the command
            cmd (str): cmd to execute on the host
        Returns:
            ret (json)
        """
        ret = {}
        with host_helper.ssh_to_host(host, con_ssh=self.con_ssh) as host_ssh:
            code, output = host_ssh.exec_sudo_cmd(cmd)
        if code == 0:
            ret = json.loads(output)
        return ret

    def verify_ip_link_show_vf(self, host, port, vf_list, vlan_id=None, max_tx_rate=None):
        """
        Function to validate the vf paramters using "ip link show <port> | grep vf id"
        Args:
            host (str): host to check the command
            port (str): underlying physical port of sriov interface
            vf_list (list): list of vf's to verify
            vlan_id (str): vlan id
            max_tx_rate (str): max_tx_rate of the vf
        """
        with host_helper.ssh_to_host(host, con_ssh=self.con_ssh) as host_ssh:
            for vf_id in vf_list:
                cmd = "ip link show {} | grep 'vf {}'".format(port, vf_id)
                _, out = host_ssh.exec_sudo_cmd(cmd)
                out = utils.strip_ansi_codes(out)
                if vlan_id:
                    assert vlan_id in out, "Expected vlan '{}' not present in '{}'".format(
                        vlan_id, out
                    )
                if max_tx_rate:
                    assert max_tx_rate in out, "Expected tx_rate '{}' not present in '{}'".format(
                        max_tx_rate, out
                    )

    def get_data_network_vf_ids(self, host, data_network):
        """
        Function to return the vf's list
        Args:
            host (str): host to check the command
            datanetwork (str): datanetwork of which vf's interface assigned
        Returns:
            vf_list (list): returns the vf's list
        """
        cmd = 'cat /etc/pcidp/config.json;echo'
        resource_name = "pci_sriov_net_{}".format(data_network)
        vf_list = []
        resources = self.get_cmd_output_in_json(host, cmd)
        for resource in resources["resourceList"]:
            if resource["resourceName"] == resource_name:
                pf_names = resource["selectors"]["pfNames"][-1]
                assert pf_names, "Expected pfnames not found"
                vf_list = pf_names.split('#')[-1].split(',')
        return vf_list

    def verify_system_vf_intf_value(self, host, intf_name, obj):
        """
        Verifies the vf interface values using system commands
        Args:
            host(str): host
            intf_name(str): vf test interface
            key (str): attr of the interface
            exp_val (str): expected value of the key
        """
        # verify the interface exist on the node
        host_intf = host_helper.get_hosts_interfaces_info(
            host,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            kwargs_for_get_host_interfaces={'name': intf_name},
            kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True},
        )

        assert host_intf, "Expected interface {} is not found on the host".format(intf_name)

        # verify the interface value is expected as configured
        for key, exp_val in obj.items():
            assert (
                host_intf[host][intf_name][key] == exp_val
            ), "expected value {} is not equal to actual {}".format(
                exp_val, host_intf[host][intf_name][key]
            )

    def get_avaliable_rate_limit(self, host):
        """
        This method calculates the avaliable rate-limit on the port
        Args:
            host(str): host
        Returns:
            returns the available rate limit
        """

        # On a SRIOV interface, 90% bw is allocated to vf's and 10% to pf's interface
        total_vfs_bw = round(self.sriov_port['speed'] * 0.9)

        # The vf interface is comprised of class type 'pci-sriov' and if_type 'vf'
        vf_intfs = host_helper.get_hosts_interfaces_info(
            host,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            kwargs_for_get_host_interfaces={'net_type': PCI_CLASSES, 'if_type': 'vf'},
            kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True},
        )

        used_vfs_bw = 0
        if host in vf_intfs.keys():
            for value in vf_intfs[host].values():
                if value['max_tx_rate'] is not None:
                    used_vfs_bw = value['sriov_numvfs'] * value['max_tx_rate'] + used_vfs_bw

        assert (
            total_vfs_bw > used_vfs_bw
        ), "Used vf's bw '{}' should not be greater than '{}'".format(used_vfs_bw, total_vfs_bw)
        return total_vfs_bw - used_vfs_bw

    def mtu_error(self, val1, val2):
        """
        Method to return the MTU semantic check error
        """
        msg = 'Interface MTU ({}) cannot be larger than MTU of underlying interface ({})'.format(
            val1, val2
        )
        return msg

    def max_tx_limit_error(self, val1):
        """
        Method to return the rate-limit semantic check error
        """
        msg = (
            'Configured (max_tx_rate*sriov_numvfs) exceeds available link speed bandwidth: {} Mbps.'
            .format(val1)
        )
        return msg

    def verify_pci_device_in_pod(self):
        """
        Method to check the pci device on the pod
        """
        pods = kube_helper.get_resources(namespace=self.namespace, con_ssh=self.con_ssh)
        LOG.tc_step("{}:Verify that {} exist on the pod".format(self.region, self.pci_device))
        _, out = kube_helper.exec_cmd_in_container(
            cmd="printenv | grep {}".format(self.pci_device),
            pod=pods[-1],
            namespace=self.namespace,
            con_ssh=self.con_ssh,
        )
        assert out, "The {} doesn't exist on the pod".format(self.pci_device)


@mark.usefixtures('ensure_sriov_configured', 'ensure_host', 'ensure_sriov')
class TestSriovInterface(TestSriov):
    """
    Feature epic: TCPG-308
    """

    intfs = [('vfio', 'test_vf'), ('netdevice', 'test_net'), ('ethernet', 'test_eth')]

    @fixture(scope='class')
    def delete_test_intf(self, request):
        """
        Fixture to delete the vf test interface in the teardown
        Returns:
            host (str): returns the host
        """

        def teardown():
            vf_interfaces = host_helper.get_host_interfaces(
                self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
            )

            exiting_test_intfs = [intf for _, intf in self.intfs if intf in vf_interfaces]

            if exiting_test_intfs:
                # lock the host
                LOG.fixture_step("{}:Lock the host {}".format(self.region, self.host))
                host_helper.lock_host(
                    host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
                )

                for test_intf in exiting_test_intfs:
                    LOG.fixture_step(
                        "{}:Delete the vf '{}' test interface".format(self.region, test_intf)
                    )
                    host_helper.delete_host_interface(
                        self.host,
                        test_intf,
                        con_ssh=self.con_ssh,
                        auth_info=self.auth_info,
                        lock_unlock=False,
                    )

                # unlock the host
                LOG.fixture_step("{}:Unlock the host {}".format(self.region, self.host))
                host_helper.unlock_host(
                    host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
                )

        request.addfinalizer(teardown)

    @mark.p2
    @mark.parametrize('sriov_vf_driver,test_intf', intfs)
    def test_sriov_vf_interface(self, delete_test_intf, sriov_vf_driver, test_intf):
        sriov_vf_count = 2
        # Get the mtu configured for SRIOVIF
        sriov_mtu = self.hosts_sriov_intfs[self.host][self.sriov_intf]['imtu']

        # lock the host
        LOG.tc_step("{}:Lock the host {}".format(self.region, self.host))
        host_helper.lock_host(host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info)

        # add the host interface
        if sriov_vf_driver == 'ethernet':
            LOG.tc_step(
                "{}:Create the ethernet interface {} on the host {}".format(
                    self.region, test_intf, self.host
                )
            )
            host_helper.add_host_interface(
                self.host,
                test_intf,
                [],
                mtu=sriov_mtu,
                if_class='platform',
                parent_sriov_vf=self.sriov_intf,
                lock_unlock=False,
                sub_intf_type=sriov_vf_driver,
            )

        else:
            LOG.tc_step(
                "{}:Create the vf interface {} on the host {}".format(
                    self.region, test_intf, self.host
                )
            )
            host_helper.add_host_interface(
                self.host,
                test_intf,
                [],
                mtu=sriov_mtu,
                if_class='pci-sriov',
                sriov_vf_count=sriov_vf_count,
                sriov_vf_driver=sriov_vf_driver,
                parent_sriov_vf=self.sriov_intf,
                lock_unlock=False,
            )

        # verify the interface is created with configured mtu
        LOG.tc_step(
            "{}:Verify that vf interface {} is created on the host {}".format(
                self.region, test_intf, self.host
            )
        )
        self.verify_system_vf_intf_value(self.host, test_intf, {'imtu': sriov_mtu})

        # perform this check only if sriov_mtu less 9216 frame size
        if sriov_mtu < 9216:
            new_mtu = sriov_mtu + 1
            exp_msg = self.mtu_error(new_mtu, sriov_mtu)
            # modify the interface mtu to greater then sriov and expect it to fail
            LOG.tc_step(
                "{}:Verify that modifying the vf interface mtu {} greater than base sriov "
                "interface's mtu {} throws an error".format(self.region, new_mtu, sriov_mtu)
            )
            code, msg = host_helper.modify_host_interface(
                self.host,
                test_intf,
                mtu=sriov_mtu + 1,
                con_ssh=self.con_ssh,
                auth_info=self.auth_info,
                lock_unlock=False,
                fail_ok=True,
            )

            assert (
                code == 1 and msg == exp_msg
            ), "Expected rtn_code,msg {}:{} not equal to actual {}:{}".format(1, exp_msg, code, msg)

        # perform modify interface mtu
        new_mtu = sriov_mtu - 1
        LOG.tc_step("{}:Modify the vf interface mtu to {}".format(self.region, new_mtu))
        host_helper.modify_host_interface(
            self.host,
            test_intf,
            mtu=new_mtu,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            lock_unlock=False,
        )

        # verify the interface is modified
        LOG.tc_step("{}:Verify that vf interface mtu modified to {}".format(self.region, new_mtu))
        self.verify_system_vf_intf_value(self.host, test_intf, {'imtu': new_mtu})

        if sriov_vf_driver != 'ethernet':
            # Modify interface --max-tx-rate
            avail_rate_limit = self.get_avaliable_rate_limit(self.host)
            max_tx_rate = 100
            exp_msg = self.max_tx_limit_error(avail_rate_limit)

            # Now try to configure max-tx-rate greater than avaliable rate limit should throw an
            # error
            LOG.tc_step(
                "{}:Verify that modifying the vf interface rate-limit {} greater than the "
                "available rate-limit {} throws an error".format(
                    self.region, max_tx_rate + avail_rate_limit, avail_rate_limit
                )
            )
            code, msg = host_helper.modify_host_interface(
                self.host,
                test_intf,
                max_tx_rate=max_tx_rate + avail_rate_limit,
                con_ssh=self.con_ssh,
                auth_info=self.auth_info,
                lock_unlock=False,
                fail_ok=True,
            )

            assert (
                code == 1 and msg == exp_msg
            ), "Expected rtn_code,msg {}:'{}' not equal to actual {}:'{}'".format(
                1, exp_msg, code, msg
            )

            # Now try to configure max-tx-rate equal to or less than avaliable rate-limit should
            # accept it
            LOG.tc_step(
                "{}:Modify the vf interface rate-limit to {}".format(self.region, max_tx_rate)
            )
            host_helper.modify_host_interface(
                self.host,
                test_intf,
                max_tx_rate=max_tx_rate,
                con_ssh=self.con_ssh,
                auth_info=self.auth_info,
                lock_unlock=False,
                fail_ok=True,
            )

            # verify the configured interface max-tx-rate
            LOG.tc_step(
                "{}:Verify the vf interface rate-limit is modified to {}".format(
                    self.region, max_tx_rate
                )
            )
            self.verify_system_vf_intf_value(self.host, test_intf, {'max_tx_rate': max_tx_rate})

        # unlock the host
        LOG.tc_step("{}:Unlock the host {}".format(self.region, self.host))
        host_helper.unlock_host(host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info)

        if sriov_vf_driver != 'ethernet':
            # verify the changes after the host unlock
            LOG.tc_step(
                "{}:Verify that vf interface mtu,rate-limit modified to {}".format(
                    self.region, max_tx_rate
                )
            )
            self.verify_system_vf_intf_value(self.host, test_intf, {'max_tx_rate': max_tx_rate})

        LOG.tc_step("{}:Verify that vf interface mtu modified to {}".format(self.region, new_mtu))
        self.verify_system_vf_intf_value(self.host, test_intf, {'imtu': new_mtu})

    @fixture(scope='function')
    def create_vf_intf_for_pod_assignment(self, request):
        """
        This test verifies vf interface's paramaters by assigning to a pod
        Steps:
            - Lock the host
            - Create the vf interface on the host
            - Verify that vf interface is created on the host
            - Verify that modifying vf' interface mtu greater than base sriov interface throws an
            error
            - Modify the vf interface mtu
            - Verify the vf interface mtu
        Returns:
           returns host, max_tx_rate
        """
        vf_type = request.param
        sriov_mtu = self.hosts_sriov_intfs[self.host][self.sriov_intf]['imtu']
        sriov_vf_count = 1

        avail_rate_limit = self.get_avaliable_rate_limit(self.host)
        max_tx_rate = round(avail_rate_limit / sriov_vf_count)

        def teardown():
            LOG.fixture_step("{}:Delete the {} namespace".format(self.region, self.namespace))
            kube_helper.delete_resources(
                resource_names=self.namespace,
                resource_types="namespace",
                con_ssh=self.con_ssh,
                ignore_not_found="True",
            )

            stand_by = system_helper.get_standby_controller_name(
                con_ssh=self.con_ssh, auth_info=self.auth_info
            )

            controllers = system_helper.get_controllers(
                con_ssh=self.con_ssh, auth_info=self.auth_info
            )
            if not self.aio_simplex and self.host in controllers and self.host != stand_by:
                host_helper.swact_host(con_ssh=self.con_ssh, auth_info=self.auth_info)

            vf_interfaces = host_helper.get_host_interfaces(
                self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
            )

            exiting_test_intfs = [
                intf for intf in [self.new_sriov_intf, self.vf_intf] if intf in vf_interfaces
            ]

            if exiting_test_intfs:
                # lock the host
                LOG.fixture_step("{}:Lock the host {}".format(self.region, self.host))
                host_helper.lock_host(
                    host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
                )

                # delete the test sriov interface
                if self.new_sriov_intf in exiting_test_intfs:
                    LOG.fixture_step(
                        "{}:Delete the interface '{}'".format(self.region, self.new_sriov_intf)
                    )
                    host_helper.modify_host_interface(
                        self.host,
                        self.new_sriov_intf,
                        con_ssh=self.con_ssh,
                        auth_info=self.auth_info,
                        if_class='none',
                        lock_unlock=False,
                    )

                # delete the test vf interface
                if self.vf_intf in exiting_test_intfs:
                    LOG.fixture_step(
                        "{}:Delete the test interface {}".format(self.region, self.vf_intf)
                    )
                    host_helper.delete_host_interface(
                        self.host,
                        self.vf_intf,
                        con_ssh=self.con_ssh,
                        lock_unlock=False,
                        auth_info=self.auth_info,
                    )

                # unlock the host
                LOG.fixture_step("{}:Unlock the host {}".format(self.region, self.host))
                host_helper.unlock_host(
                    host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
                )

            uuid = system_helper.get_data_network_values(
                self.data_network, con_ssh=self.con_ssh, auth_info=self.auth_info
            )
            if uuid:
                # delete the test network
                LOG.fixture_step(
                    "{}:Delete the data network {}".format(self.region, self.data_network)
                )
                system_helper.delete_data_network(
                    uuid, con_ssh=self.con_ssh, auth_info=self.auth_info
                )

        request.addfinalizer(teardown)

        # create data network "test-network"
        LOG.fixture_step("{}:Create the data network {}".format(self.region, self.data_network))
        system_helper.create_data_network(
            self.data_network, mtu=sriov_mtu, con_ssh=self.con_ssh, auth_info=self.auth_info
        )

        # lock the host
        LOG.fixture_step("{}:Lock the host {}".format(self.region, self.host))
        host_helper.lock_host(host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info)

        # add the host vf interface with vf cound 2 with rate-limit
        LOG.fixture_step("{}:Create the test interface {}".format(self.region, self.vf_intf))
        host_helper.add_host_interface(
            self.host,
            self.vf_intf,
            [],
            mtu=sriov_mtu,
            if_class='pci-sriov',
            sriov_vf_count=sriov_vf_count,
            sriov_vf_driver=vf_type,
            max_tx_rate=max_tx_rate,
            parent_sriov_vf=self.sriov_intf,
            lock_unlock=False,
        )

        LOG.fixture_step(
            "{}:Verify mtu,rate-limit of the test interface {}".format(self.region, self.vf_intf)
        )
        self.verify_system_vf_intf_value(
            self.host, self.vf_intf, {'imtu': sriov_mtu, 'max_tx_rate': max_tx_rate}
        )

        # assign 'test_intf' to "test-network"
        LOG.fixture_step(
            "{}:Assign the test interface {} to data network {}".format(
                self.region, self.vf_intf, self.data_network
            )
        )
        host_helper.assign_interface_datanetwork(
            self.host,
            self.vf_intf,
            self.data_network,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
        )

        # Unlock the host
        LOG.fixture_step("{}:Unlock the host {}".format(self.region, self.host))
        host_helper.unlock_host(host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info)

        LOG.fixture_step("{}:Create {} namespace".format(self.region, self.namespace))
        kube_helper.create_namespace(self.namespace, con_ssh=self.con_ssh)

        return max_tx_rate

    def get_no_of_reboots(self):
        """Helper method to return the last reboot list of the host"""
        with host_helper.ssh_to_host(self.host, con_ssh=self.con_ssh) as host_ssh:
            _, out = host_ssh.exec_sudo_cmd('last reboot')
            return len(out.splitlines())

    def get_unused_port(self):
        """Helper method to return the unused port on the system"""
        intfs = host_helper.get_hosts_interfaces_info(
            self.host,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            kwargs_for_get_host_interfaces={
                'net_type': 'None',
                'if_type': 'ethernet',
                'show_all': True,
            },
            kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True},
        )
        if intfs:
            ports_dict = host_helper.get_port_property_values(
                list(intfs[self.host].keys()), self.host
            )
            for port, val in ports_dict.items():
                if val['operstate'] == 'down':
                    return port
        return None

    @mark.parametrize(
        'create_vf_intf_for_pod_assignment, pod_yaml',
        [
            param("netdevice", "vlan_2351.yaml", marks=[mark.p2]),
            param("vfio", "vlan_2352.yaml", marks=[mark.p2]),
        ],
        indirect=["create_vf_intf_for_pod_assignment"],
    )
    def test_sriov_vf_assignment_to_pod(self, create_vf_intf_for_pod_assignment, pod_yaml):
        """
        Test to verify the vf parameters after assigning to pod
        Setup:
            - Lock the host
            - Create the vf interface on the host
            - Verify that vf interface is created on the host
            - Verify that modifying vf' interface mtu greater than base sriov interface throws an
            error
            - Modify the vf interface mtu
            - Verify the vf interface mtu
        Steps:
            - Apply the pod yaml
            - Verify that pod is in running state
            - Verify the vlan_id and rate-limit config on the vf interface
            - Initiate swact
            - Verify the vlan_id and rate-limit config on the vf interface
            - Reboot the controller
            - lock the host
            - modify the base sriov interface
            - Check the host is rebooted only once
            - Verify the vlan_id and rate-limit config on the vf interface
        Teardown:
            - Delete the pod
            - Delete the test interface
            - Delete the data network
            - Delete the namespace
        """
        max_tx_rate = create_vf_intf_for_pod_assignment
        file_path = "{}/{}".format(TEST_FILES, pod_yaml)
        vlan_id = pod_yaml[5:9]

        # get the underlying sriov physical port
        port = self.hosts_sriov_intfs[self.host][self.sriov_intf]['ports'][-1]

        common.scp_from_localhost_to_active_controller(
            source_path=file_path,
            dest_path=SYSTEM_DIR,
            floating_ip=common.get_lab_fip(region=self.region, bracket_for_ipv6=True),
        )

        LOG.tc_step("{}:Apply the {} pod yaml".format(self.region, pod_yaml))
        kube_helper.apply_resource("{}/{}".format(SYSTEM_DIR, pod_yaml), con_ssh=self.con_ssh)

        def verify():
            LOG.tc_step("{}:Verify that pod is in running state".format(self.region))
            kube_helper.wait_for_pods_status(namespace=self.namespace, con_ssh=self.con_ssh)

            # get the vf's of data network
            vf_list = self.get_data_network_vf_ids(self.host, self.data_network)

            assert vf_list, "vf's are not shown in datanetwork resource list"

            LOG.tc_step(
                "{}:Verify the vlan_id and rate-limit config on the vf interface".format(
                    self.region
                )
            )
            self.verify_ip_link_show_vf(self.host, port, vf_list, vlan_id, str(max_tx_rate))

            # Verify pci device on the pod
            self.verify_pci_device_in_pod()

        verify()

        if not self.aio_simplex:
            LOG.tc_step("Initiate swact on cc")
            host_helper.swact_host(con_ssh=self.con_ssh, auth_info=self.auth_info)

        verify()

        LOG.tc_step("Reboot the controller")
        host_helper.reboot_hosts(
            hostnames=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info
        )

        verify()

        # Adding the bug scenario CGTS-23734, modifying the sriov while the pod is running with
        # one of the vf interfaces

        # Number of reboots before modification
        no_of_reboots = self.get_no_of_reboots()

        # lock the host
        LOG.tc_step("{}:Lock the host {}".format(self.region, self.host))
        host_helper.lock_host(host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info)

        # Modify the base sriov interface
        # Try vf number change on sriov
        LOG.tc_step(
            "{}:Try modify {} interface vf number change".format(self.region, self.sriov_intf)
        )
        vf_count = self.hosts_sriov_intfs[self.host][self.sriov_intf]['sriov_numvfs'] - 1

        host_helper.modify_host_interface(
            self.host,
            self.sriov_intf,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            sriov_vf_count=vf_count,
            lock_unlock=False,
        )

        # Unlock the host
        LOG.tc_step("{}:Unlock the host {}".format(self.region, self.host))
        utils.wait_for_expected_exit_code(
            host_helper.unlock_host,
            expected_rc=0,
            host=self.host,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            fail_ok=True,
        )

        # Number of reboots after modification
        no_of_latest_reboots = self.get_no_of_reboots()

        assert (
            no_of_latest_reboots - no_of_reboots == 1
        ), "System should only reboot once after sriov interface modify unlock"

        verify()

    @fixture(scope='function')
    def ensure_port(self, request):
        """
        Fixture to skip the test if no free port is available
        Return:
            port
        """
        port = self.get_unused_port()

        if not port:
            skip("No usable port available to run this test")

        return port

    @mark.p2
    @mark.parametrize(
        'create_vf_intf_for_pod_assignment, pod_yaml',
        [("vfio", "vlan_2352.yaml")],
        indirect=["create_vf_intf_for_pod_assignment"],
    )
    def test_create_sriov_when_pod_running_on_a_vf_intf_on_other_sriov(
        self, ensure_port, create_vf_intf_for_pod_assignment, pod_yaml
    ):
        """
        This test covers the JIRA scenario CGTS-23359
        Setup:
            - Lock the host
            - Create the vf interface on the host
            - Verify that vf interface is created on the host
            - Verify that modifying vf' interface mtu greater than base sriov interface throws an
            error
            - Modify the vf interface mtu
            - Verify the vf interface mtu
        Steps:
            - Apply the pod yaml
            - Verify the pod is in running state
            - Create another sriov interface
        Teardown:
            - Delete the new sriov interface
            - Delete the pod
            - Delete the test interface
            - Delete the data network
            - Delete the namespace
        """
        new_sriov_port = ensure_port
        file_path = "{}/{}".format(TEST_FILES, pod_yaml)

        common.scp_from_localhost_to_active_controller(
            source_path=file_path,
            dest_path=SYSTEM_DIR,
            floating_ip=common.get_lab_fip(region=self.region, bracket_for_ipv6=True),
        )

        LOG.tc_step("{}:Apply the {} pod yaml".format(self.region, pod_yaml))
        kube_helper.apply_resource("{}/{}".format(SYSTEM_DIR, pod_yaml), con_ssh=self.con_ssh)

        LOG.tc_step("{}:Verify that pod is in running state".format(self.region))
        kube_helper.wait_for_pods_status(namespace=self.namespace, con_ssh=self.con_ssh)

        # lock the host
        LOG.tc_step("{}:Lock the host {}".format(self.region, self.host))
        host_helper.lock_host(host=self.host, con_ssh=self.con_ssh, auth_info=self.auth_info)

        # Try to create another sriov interface
        LOG.tc_step(
            "{}:create another sriov '{}' interface on port '{}'".format(
                self.region, self.new_sriov_intf, new_sriov_port
            )
        )
        # Get total number of virtual functions for selected interface
        sriov_total_vf_count_on_port = host_helper.get_host_port_values(
            host=self.host, port=new_sriov_port, fields="sriov_totalvfs", con_ssh=self.con_ssh
        )

        sriov_expected_vf_count_on_host = str(sriov_total_vf_count_on_port[0])
        host_helper.modify_host_interface(
            self.host,
            new_sriov_port,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            sriov_vf_count=sriov_expected_vf_count_on_host,
            new_if_name=self.new_sriov_intf,
            if_class='pci-sriov',
            sriov_vf_driver='netdevice',
            lock_unlock=False,
        )

        # Unlock the host
        LOG.tc_step("{}:Unlock the host {}".format(self.region, self.host))
        utils.wait_for_expected_exit_code(
            host_helper.unlock_host,
            expected_rc=0,
            host=self.host,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            fail_ok=True,
        )


@mark.usefixtures('ensure_sriov_configured', 'ensure_host', 'ensure_sriov')
class TestSriovInterfaceModify(TestSriov):
    """
    Feature epic: TCPG-374
    """

    lock_msg = "Host must be locked."

    @fixture(scope='function')
    def ensure_aio_sx(self, request):
        """
        Fixture function to skip the tests if not AIO-SX
        """
        if not self.aio_simplex:
            skip("These tests are applicable to only on AIO-SX")

    @fixture(scope='function')
    def ensure_aio_system(self, request):
        """
        Fixture function to skip the tests if AIO-SX
        """
        if self.aio_simplex:
            skip("These tests are applicable to only non AIO-SX")

    def verify(self, interface, **kwargs):
        """
        Method to verify the semantic check msg on the system
        Args:
            interface (str): name of the interface
        """
        code, msg = host_helper.modify_host_interface(
            self.host,
            interface,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
            lock_unlock=False,
            fail_ok=True,
            **kwargs,
        )

        assert (
            code == 1 and msg == self.lock_msg
        ), "Expected rtn_code,msg {}:{} not equal to actual {}:{}".format(
            1, self.lock_msg, code, msg
        )

    @mark.p2
    def test_modify_sriov_interface_is_rejected_without_lock(self):
        """
        Test to verify the sriov interface modification is rejected on all system types
        Args:
            ensure_aio_sx (fixture)
        Steps:
            - Try modifying the sriov interface mtu
            - Try modifying the sriov class
            - Try modifying the sriov vf count
        """
        # Get the mtu configured for SRIOVIF
        sriov_mtu = self.hosts_sriov_intfs[self.host][self.sriov_intf]['imtu'] - 1

        # Check to change the sriov interface class
        LOG.tc_step(
            "{}:Try modify {} interface mtu to {}".format(self.region, self.sriov_intf, sriov_mtu)
        )
        self.verify(self.sriov_intf, mtu=sriov_mtu)

        # Check to change the sriov interface class
        LOG.tc_step("{}:Try modify {} interface class to none".format(self.region, self.sriov_intf))
        self.verify(self.sriov_intf, if_class='none')

        # Try vf number change on sriov
        LOG.tc_step(
            "{}:Try modify {} interface vf number change".format(self.region, self.sriov_intf)
        )
        vf_count = self.hosts_sriov_intfs[self.host][self.sriov_intf]['sriov_numvfs'] - 1
        self.verify(self.sriov_intf, sriov_vf_count=vf_count)

    @mark.p2
    @mark.parametrize('vf_driver_type', ['vfio', 'netdevice'])
    def test_sriov_vf_interface_add_is_rejected_on_non_sx(self, ensure_aio_system, vf_driver_type):
        """
        This is negative test to check vf interface-add rejected on non-sx systems without
        lock/unlock
        Steps:
            - Create the vf interface and expect it to fail
        """
        sriov_vf_count = 2
        avail_rate_limit = self.get_avaliable_rate_limit(self.host)
        max_tx_rate = round(avail_rate_limit / sriov_vf_count)

        # Get the mtu configured for SRIOVIF
        sriov_mtu = self.hosts_sriov_intfs[self.host][self.sriov_intf]['imtu']

        # add the host interface
        LOG.tc_step(
            "{}:Create the vf interface {} on the host {} and expect it to reject".format(
                self.region, self.vf_intf, self.host
            )
        )
        code, msg = host_helper.add_host_interface(
            self.host,
            self.vf_intf,
            [],
            mtu=sriov_mtu,
            if_class='pci-sriov',
            sriov_vf_count=sriov_vf_count,
            sriov_vf_driver=vf_driver_type,
            max_tx_rate=max_tx_rate,
            parent_sriov_vf=self.sriov_intf,
            lock_unlock=False,
            fail_ok=True,
        )

        assert (
            code == 1 and msg == self.lock_msg
        ), "Expected rtn_code,msg {}:{} not equal to actual {}:{}".format(
            1, self.lock_msg, code, msg
        )

    @fixture(scope='function')
    def delete_test_intf(self, request):
        """
        Fixture to delete the vf test interface in the teardown
        Steps:
            - Delete the vf test interface
        """

        def teardown():
            host_intf = host_helper.get_hosts_interfaces_info(
                self.host,
                con_ssh=self.con_ssh,
                auth_info=self.auth_info,
                kwargs_for_get_host_interfaces={'name': self.vf_intf},
                kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True},
            )
            if host_intf:
                LOG.fixture_step(
                    "{}:Delete the vf '{}' test interface".format(self.region, self.vf_intf)
                )
                host_helper.delete_host_interface(
                    self.host,
                    self.vf_intf,
                    con_ssh=self.con_ssh,
                    auth_info=self.auth_info,
                    lock_unlock=False,
                )

        request.addfinalizer(teardown)

    @mark.p2
    @mark.lab_simplex
    @mark.parametrize('vf_driver_type', ['vfio', 'netdevice'])
    def test_sriov_vf_interface_is_added_without_lock_on_sx(
        self, ensure_aio_sx, delete_test_intf, vf_driver_type
    ):
        """
        Test to add vf interface and modify
        Steps:
            - Create the vf interface
            - Verify that vf interface is created
            - Try modifying the vf interface and expect the err msg
        Teardown:
            - Delete the vf test interface
        """
        sriov_vf_count = 2
        avail_rate_limit = self.get_avaliable_rate_limit(self.host)
        max_tx_rate = round(avail_rate_limit / sriov_vf_count)

        # Get the mtu configured for SRIOVIF
        sriov_mtu = self.hosts_sriov_intfs[self.host][self.sriov_intf]['imtu']

        # add the host interface
        LOG.tc_step(
            "{}:Create the vf interface {} on the host {}".format(
                self.region, self.vf_intf, self.host
            )
        )
        host_helper.add_host_interface(
            self.host,
            self.vf_intf,
            [],
            mtu=sriov_mtu,
            if_class='pci-sriov',
            sriov_vf_count=sriov_vf_count,
            sriov_vf_driver=vf_driver_type,
            max_tx_rate=max_tx_rate,
            parent_sriov_vf=self.sriov_intf,
            lock_unlock=False,
        )

        # verify the Vf interface is created on the host
        LOG.tc_step(
            "{}:Verify that vf interface {} is created on the host {}".format(
                self.region, self.vf_intf, self.host
            )
        )
        self.verify_system_vf_intf_value(
            self.host, self.vf_intf, {'imtu': sriov_mtu, 'max_tx_rate': max_tx_rate}
        )

        self.verify(self.vf_intf, mtu=sriov_mtu - 1)
        self.verify(self.vf_intf, max_tx_rate=max_tx_rate - 1)
        if vf_driver_type == 'vfio':
            self.verify(self.vf_intf, sriov_vf_driver='netdevice')
        else:
            self.verify(self.vf_intf, sriov_vf_driver=vf_driver_type)

    @fixture(scope='function')
    def create_vf_intf(self, request):
        """
        Fixture to create vf test interface,assign to data network
        Steps:
            - Create the data network
            - Create the test interface
            - Verify mtu,rate-limit of the test interface
            - Assign the test interface to data network
            - create namespace
            - Delete the namespace
            - Get the interface-data-network uuid
            - Remove the interface from the data-network
            - Delete the test interface
            - Delete the data-network
        """
        sriov_mtu = self.hosts_sriov_intfs[self.host][self.sriov_intf]['imtu']
        sriov_vf_count = 1
        avail_rate_limit = self.get_avaliable_rate_limit(self.host)
        max_tx_rate = round(avail_rate_limit / sriov_vf_count)

        def teardown():
            LOG.fixture_step("{}:Delete the {} namespace".format(self.region, self.namespace))
            kube_helper.delete_resources(
                resource_names=self.namespace,
                resource_types="namespace",
                con_ssh=self.con_ssh,
                ignore_not_found="True",
            )

            # Get the test interface
            host_intf = host_helper.get_hosts_interfaces_info(
                self.host,
                con_ssh=self.con_ssh,
                auth_info=self.auth_info,
                kwargs_for_get_host_interfaces={'name': self.vf_intf},
                kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True},
            )

            if host_intf:
                # get the uuid of the datanetwork-interface
                LOG.fixture_step(
                    "{}:Get the {} interface data-network-uuid".format(self.region, self.vf_intf)
                )
                datanetwork_intf_uuid = host_helper.get_host_datanetworks(
                    self.host,
                    self.vf_intf,
                    field='uuid',
                    con_ssh=self.con_ssh,
                    auth_info=self.auth_info,
                )

                # remove the vf interface from the data network
                if datanetwork_intf_uuid:
                    LOG.fixture_step(
                        "{}:Remove the {} from data-network".format(self.region, self.vf_intf)
                    )
                    host_helper.remove_interface_datanetwork(
                        datanetwork_intf_uuid, con_ssh=self.con_ssh, auth_info=self.auth_info
                    )

                LOG.fixture_step(
                    "{}:Delete the test interface {}".format(self.region, self.vf_intf)
                )
                host_helper.delete_host_interface(
                    self.host,
                    self.vf_intf,
                    con_ssh=self.con_ssh,
                    auth_info=self.auth_info,
                    lock_unlock=False,
                )

            data_network_uuid = system_helper.get_data_network_values(
                self.data_network, con_ssh=self.con_ssh, auth_info=self.auth_info
            )
            if data_network_uuid:
                # delete the test network
                LOG.fixture_step(
                    "{}:Delete the data network {}".format(self.region, self.data_network)
                )
                system_helper.delete_data_network(
                    data_network_uuid, con_ssh=self.con_ssh, auth_info=self.auth_info
                )

        request.addfinalizer(teardown)

        # create data network "test-network"
        LOG.fixture_step("{}:Create the data network {}".format(self.region, self.data_network))
        system_helper.create_data_network(
            self.data_network, mtu=sriov_mtu, con_ssh=self.con_ssh, auth_info=self.auth_info
        )

        # add the host vf interface with vf cound 2 with rate-limit
        LOG.fixture_step("{}:Create the test interface {}".format(self.region, self.vf_intf))
        host_helper.add_host_interface(
            self.host,
            self.vf_intf,
            [],
            mtu=sriov_mtu,
            if_class='pci-sriov',
            sriov_vf_count=sriov_vf_count,
            sriov_vf_driver='netdevice',
            max_tx_rate=max_tx_rate,
            parent_sriov_vf=self.sriov_intf,
            lock_unlock=False,
        )

        LOG.fixture_step(
            "{}:Verify mtu,rate-limit of the test interface {}".format(self.region, self.vf_intf)
        )
        self.verify_system_vf_intf_value(
            self.host, self.vf_intf, {'imtu': sriov_mtu, 'max_tx_rate': max_tx_rate}
        )

        # assign 'test_intf' to "test-network"
        LOG.fixture_step(
            "{}:Assign the test interface {} to data network {}".format(
                self.region, self.vf_intf, self.data_network
            )
        )
        host_helper.assign_interface_datanetwork(
            self.host,
            self.vf_intf,
            self.data_network,
            con_ssh=self.con_ssh,
            auth_info=self.auth_info,
        )

        LOG.fixture_step("{}:Create {} namespace".format(self.region, self.namespace))
        kube_helper.create_namespace(self.namespace, con_ssh=self.con_ssh)

        return max_tx_rate

    @mark.p2
    @mark.lab_simplex
    def test_sriov_vf_intf_assignment_to_pod(self, ensure_aio_sx, create_vf_intf):
        """
        Test vf assignment to the pod
        Args:
            create_vf_intf (fixture)
        Setup:
            - Create the data network
            - Create the test interface
            - Verify mtu,rate-limit of the test interface
            - Assign the test interface to data network
            - create namespace
        Steps:
            - Apply the pod yaml
            - Verify that pod is in running state
            - Verify the vlan_id and rate-limit config on the vf interface
        Teardown:
            - Delete the namespace
            - Get the interface-data-network uuid
            - Remove the interface from the data-network
            - Delete the test interface
            - Delete the data-network
        """
        max_tx_rate = create_vf_intf
        pod_yaml = "vlan_2351.yaml"
        file_path = "{}/{}".format(TEST_FILES, pod_yaml)
        vlan_id = pod_yaml[5:9]

        # get the underlying sriov physical port
        port = self.hosts_sriov_intfs[self.host][self.sriov_intf]['ports'][-1]

        common.scp_from_localhost_to_active_controller(
            source_path=file_path,
            dest_path=SYSTEM_DIR,
            floating_ip=common.get_lab_fip(region=self.region, bracket_for_ipv6=True),
        )

        LOG.tc_step("{}:Apply the {} pod yaml".format(self.region, pod_yaml))
        kube_helper.apply_resource("{}/{}".format(SYSTEM_DIR, pod_yaml), con_ssh=self.con_ssh)

        LOG.tc_step("{}:Verify that pod is in running state".format(self.region))
        kube_helper.wait_for_pods_status(namespace=self.namespace, con_ssh=self.con_ssh)

        # get the vf's of data network
        vf_list = self.get_data_network_vf_ids(self.host, self.data_network)

        assert vf_list, "vf's are not shown in datanetwork resource list"

        LOG.tc_step(
            "{}:Verify the vlan_id and rate-limit config on the vf interface".format(self.region)
        )
        self.verify_ip_link_show_vf(self.host, port, vf_list, vlan_id, str(max_tx_rate))

        # Verify pci device on the pod
        self.verify_pci_device_in_pod()

