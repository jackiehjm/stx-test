#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast
import inspect
import ipaddress
import re
import time

import yaml

from consts.cli_errs import InterfaceErr
from consts.proj_vars import ProjVar
from consts.stx import PodStatus
from framework.runner.system_info.os.os_manager import OSManager
from framework.runner.system_info.os.os_types import OSTypes
from keywords import (
    container_helper,
    host_helper,
    kube_helper,
    network_helper,
    sriov_helper,
    storage_helper,
    system_helper,
)
from keywords.general import file_utilities
from pytest import fail, fixture, mark, param, skip
from testfixtures.recover_hosts import HostsToRecover
from utils import cli, exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG

CALICOCTL_IMAGE = 'quay.io/calico/ctl:v3.2.8'
CALICOCTL_PODNAME = 'calicoctl'
CUMULUS_REGISTRY = 'admin-2.cumulus.wrs.com:30093'
DPDK_HUGEPAGE_REQD = 2
DPDK_POD_CPUS_REQD = 2
DPDK_POD_IMAGE = 'networking/mlx-dpdk:latest'
DPDK_TESTPMD_PATH = '/opt/bin/testpmd'
INTERFACE_CLASS_PCI_SRIOV = 'pci-sriov'
INTERFACE_DELETION_WAIT = 10
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
INTERFACE_TYPE_VF = 'vf'
IPV4_VERSION = 4
IPV6_VERSION = 6
KUBE_CPU_MGR_POLICY_LABEL = 'kube-cpu-mgr-policy'
KUBE_TOPOLOGY_MGR_POLICY_LABEL = 'kube-topology-mgr-policy'
LOCAL_REGISTRY = 'registry.local:9001'
MTU = 1500
POD_IMAGE = {"netdevice": 'centos/tools', "dpdk": f'{CUMULUS_REGISTRY}/' + DPDK_POD_IMAGE}
POD_INTERFACE = 'PCIDEVICE_INTEL_COM_PCI_SRIOV_NET_{}'
POD_TYPE_DPDK = 'dpdk'
POD_TYPE_NETDEVICE = 'netdevice'
SRIOVDP_ANNOTATION_PREFIX = 'intel.com/pci_sriov_net_'
SRIOVDP_LABEL = 'sriovdp'
TEST_DATA_IF = "tdata"
TEST_SRIOV_INTERFACE = "tsriov"
VF_DRIVER_NETDEVICE = 'netdevice'
VF_DRIVER_NETDEVICES = [VF_DRIVER_NETDEVICE, 'None']
VF_DRIVER_VFIO = 'vfio'
VF_DRIVER_VFIOS = [VF_DRIVER_VFIO]
IMAGES_TO_PULL = [DPDK_POD_IMAGE, CALICOCTL_IMAGE]


class PodCpu:
    @classmethod
    def execute_cmd(cls, cmd, pod_name, namespace='default'):
        """
        Executes the given command and captures the output
        Args:
            cmd (str): cmd to execute
            pod_name (str): name of pod to execute command
            namespace (str): namespace, default value is "default"

        Returns: output of command
        """
        code, output = kube_helper.exec_cmd_in_container(cmd, pod=pod_name, namespace=namespace)
        return code, output

    @classmethod
    def get_pod_cpus(cls, pod_name, namespace='default'):
        """
        Get the CPUs assigned to a pod
        Args:
            pod_name (str): The name of the pod to get cpus
            namespace (str): namespace, default value is "default"

        Return cpu_list (list): A list of CPUs assigned to the pod
        """
        cpu_list = list()
        cmd = "cat /sys/fs/cgroup/cpuset/cpuset.cpus"

        code, output = cls.execute_cmd(cmd, pod_name, namespace=namespace)

        if code == 0:
            cpu_list = re.split('[-,]', output)

        return cpu_list

    @classmethod
    def get_cpus_info(cls, pod_name, cpus, namespace='default', filter_name='physical id'):
        """
        Get the cpus information on a given pod using /proc/cpuinfo
        Args:
            pod_name (str): The name of the pod to get cpu information.
            cpus (str) (list): cpu's ID to get its information.
            namespace (str): namespace, default value is "default".
            filter_name (str): name of field to be captured and get the information.

        Return (dict): physical id corresponding to each processor
        """
        cpu_info = dict()
        cpu_info_regex = r"processor\s*:\s*(\d+).*?{}\s*:\s*(\d+)".format(filter_name)
        cmd = "cat /proc/cpuinfo"

        if isinstance(cpus, str):
            cpus = [cpus]

        code, output = cls.execute_cmd(cmd, pod_name, namespace=namespace)
        if code == 0:
            regex_matches = re.findall(cpu_info_regex, output, re.DOTALL)
            for match in regex_matches:
                cpu_id = match[0]
                if cpu_id in cpus:
                    cpu_info[cpu_id] = match[1]

        return cpu_info


class TestPmd(PodCpu):
    @classmethod
    def get_socket_memory(cls, pod_name, cpus):
        """
        This method provides needed memory for testpdm API based on physical id of each cpu

        if both cpus are on physical-id=0 then 512,0 is the memory which is needed.
        if both cpus are on physical-id=1 then 0,512 is the memory which is needed.
        if cpus are on two different numas then 512,512 is the memory which is needed.
        Args:
            pod_name (str): The name of pod to get memory needed for testpmd API
            cpus (list): A list of CPUs allocated to pod
        Return (str): memory needed to pass to testpdm. 512,0 or 0,512 or 512,512.
        """
        cpu_physical_id_info = cls.get_cpus_info(pod_name, cpus)

        assert len(cpu_physical_id_info) == len(
            cpus
        ), 'CPU physical info is {} and expected cpus is {}'.format(
            cpu_physical_id_info.keys(), cpus
        )

        for cpu in cpus:
            assert (
                cpu_physical_id_info[cpu] == '0' or cpu_physical_id_info[cpu] == '1'
            ), "numas expected to be 0 or 1 for cpu: {} on pod {}".format(cpu, pod_name)

        first_cpu, second_cpu = cpus
        if cpu_physical_id_info[first_cpu] != cpu_physical_id_info[second_cpu]:
            socket_memory = "512,512"
        elif cpu_physical_id_info[first_cpu] == '0':
            socket_memory = "512,0"
        else:
            socket_memory = "0,512"

        return socket_memory

    @classmethod
    def start_testpmd(cls, podname, cpulist, devicelist, peerlist, mode='rxonly', stats_period='2'):
        """
        Start the testpmd application in a pod
        Args:
            podname (str): The name of the pod to start the application on
            cpulist (list): A list of CPUs the application will use
            devicelist (list): A list of devices the application will use
            peerlist (list): A list of mac addresses of the peer
                            (sender/receiver)
            mode (str): The forwarding mode of the application
            stats_period (int): The number of seconds between outputting
                                results
        """
        assert len(cpulist) == 2
        assert len(peerlist) == len(devicelist)

        socket_memory = cls.get_socket_memory(podname, cpulist)
        cmd = 'bash -c "{} --lcores 0@{},{} --socket-mem {} --legacy-mem '.format(
            DPDK_TESTPMD_PATH, cpulist[0], cpulist[1], socket_memory
        )
        for device in devicelist:
            cmd += '-w {} '.format(device['pci_address'])

        cmd += '-- '

        for idx, peer in enumerate(peerlist):
            cmd += '--eth-peer={},{} '.format(idx, peer)

        cmd += '-a --forward-mode={} --stats-period {} '.format(mode, stats_period)
        cmd += '> /tmp/output.txt 2> error.txt &"'

        LOG.tc_step(
            "Try to start testpmd application in pod {} with command {}".format(podname, cmd)
        )
        kube_helper.exec_cmd_in_container(
            cmd, pod=podname, namespace='default', stdin=None, tty=None, fail_ok=True
        )

        # Give it time to initialize and start polling
        time.sleep(30)

    @classmethod
    def stop_testpmd(cls, podname):
        """
        Stop the testpmd application in a pod
        Args:
            podname (str): The name of the pod to stop the application on
        """
        cmd = 'pkill testpmd'
        LOG.tc_step(
            "Try to stop testpmd application in pod {} with command {}".format(podname, cmd)
        )
        kube_helper.exec_cmd_in_container(
            cmd, pod=podname, namespace='default', stdin=None, tty=None, fail_ok=True
        )

    @classmethod
    def verify_testpmd(cls, podname):
        """
        Stop the testpmd application in a pod
        Args:
            podname (str): The name of the pod to stop the application on
        """
        cmd = 'pgrep testpmd'
        LOG.tc_step(
            "Try to verify testpmd application in pod {} is running with command {}".format(
                podname, cmd
            )
        )
        code, output = kube_helper.exec_cmd_in_container(
            cmd, pod=podname, namespace='default', stdin=None, tty=None, fail_ok=True
        )

        return code, output

    @classmethod
    def collect_testpmd_stat(cls, podname, statid='RX-packets'):
        """
        Collect testpmd statistics
        Args:
            podname (str): The name of the pod the application is
                           running on
            statid (str): The statistic name to look for
        Returns (dict): A dictionary of statistics:
                        {port_num (str): stat value (int) ... }
        """
        cmd = 'cat /tmp/output.txt'
        code, output = kube_helper.exec_cmd_in_container(cmd, pod=podname, namespace='default')

        port_stats = {}
        output = output.splitlines()
        for idx, line in enumerate(output):
            info = line.split()

            # The stats report for and individual port can be identified
            # by the presence of a series of '####' characters
            if len(info) >= 5 and '####' in info[0]:
                port_num = int(info[5])
                if port_num not in port_stats:
                    port_stats[port_num] = 0

                for stat_line in output[idx:]:
                    stat = stat_line.split()
                    if len(stat) > 2 and statid in stat[0]:
                        pkts = int(stat[1])
                        if pkts > port_stats[port_num]:
                            port_stats[port_num] = pkts
                        break
        return port_stats


class Host:
    @classmethod
    def get_host_labels_to_recover(cls, initial_hosts_labels, new_hosts_labels):
        """
        This method find the labels to be removed and added back based on
        initial labels and new labels on each host.
        Args:
            initial_hosts_labels (dict): A dictionary of labels on each host
                                        {"compute-0": {
                                            "sriov": "enabled",
                                            "kube-topology-mgr-policy": "best-effort"}}
            new_hosts_labels (dict): A dictionary of new labels on each host
                                        {"compute-0": {
                                            "kube-cpu-mgr-policy": "static",
                                            kube-topology-mgr-policy": "restricted"}}
        Returns (dict) (dict): Returns two dictionaries to remove and add back labels.
                                remove_host_labels: {"compute-0": ["kube-cpu-mgr-policy"]}
                                add_back_host_labels: {"compute-0":
                                {"kube-topology-mgr-policy": "best-effort"}}
        """
        remove_host_labels = dict()
        add_back_host_labels = dict()
        for host, new_labels_dict in new_hosts_labels.items():
            remove_host_labels[host] = list()
            add_back_host_labels[host] = dict()
            for new_label, new_label_value in new_labels_dict.items():
                if new_label in initial_hosts_labels[host]:
                    if new_label_value != initial_hosts_labels[host][new_label]:
                        add_back_host_labels[host].update(
                            {new_label: initial_hosts_labels[host][new_label]}
                        )
                else:
                    remove_host_labels[host].append(new_label)

        return remove_host_labels, add_back_host_labels

    @classmethod
    def assign_host_labels(
        cls, hosts_labels, overwrite=False, scope='class', log_type="fixture_step", depth=1
    ):
        """
        Assign labels to hosts
        Args:
            hosts_labels (dict): dictionary of host and its corresponding labels and their values
                {
                    "compute-0": {"sriov": "enabled", "kube-cpu-mgr-policy": "static"},
                    "controller-0": {"kube-topology-mgr-policy": "restricted"}
                 }
            overwrite (bool): whether or not to overwrite
            scope (class|function|module): scope to recover host lock
            log_type (tc_step, fixture_step): different type of log from class
                                                                TisLogger in tis_log.py
            depth (int): depth of log to print in output
        """

        log_function = eval("LOG.{}".format(log_type))

        for host, labels in hosts_labels.items():
            if labels:
                HostsToRecover.add(host, scope=scope)
                log_function("Setting {} label on {}".format(labels, host), depth=depth)
                host_helper.assign_host_labels(host, labels=labels, overwrite=overwrite)
                HostsToRecover.remove(host, scope=scope)

    @classmethod
    def remove_host_labels(cls, hosts_labels, scope='function', log_type="fixture_step", depth=1):
        """
        Remove labels from hosts
        Args:
            hosts_labels (dict): dictionary of host and its corresponding labels to be removed
                {
                    "compute-0": ["sriov", "kube-cpu-mgr-policy"]
                    "controller-0": ["kube-topology-mgr-policy"]
                 }
            scope (class|function|module): scope to recover host
            log_type (tc_step, fixture_step): different type of log from class
                                                                TisLogger in tis_log.py
            depth (int): depth of log to print in output
        """
        log_function = eval("LOG.{}".format(log_type))

        for host, labels in hosts_labels.items():
            if labels:
                HostsToRecover.add(host, scope=scope)
                log_function("Removing {} label from {}".format(labels, host), depth=depth)
                host_helper.remove_host_labels(host, labels)
                HostsToRecover.remove(host, scope=scope)


class SRIOV:
    @classmethod
    def get_max_num_vfs(
        cls, data_network_capacity, sriov_configs, pod_type, if_class=INTERFACE_CLASS_PCI_SRIOV
    ):
        """
        Based on the data-network capacity and pod_type, it finds the maximum number of vfs
        Args:
            data_network_capacity (dict): The system's SR-IOV device plugin datan-etwork capacity.
            sriov_configs (dict): The system's SR-IOV interface configuration.
            pod_type (str): The pod type (netdevice / DPDK).
            if_class (str): The interface class (pci-sriov / pci-passthrough).

        Returns (int): maximum number of vfs capacity based on pod_type.
        """

        vf_capacity_list = []
        for sriov_config in sriov_configs:
            host_name = sriov_config['host']
            host_interfaces = sriov_config['interfaces']
            for host_interface in host_interfaces:
                if host_interface['class'] == if_class:
                    if pod_type == POD_TYPE_DPDK:
                        if host_interface['is_mellanox']:
                            if host_interface['vf_driver'] in VF_DRIVER_VFIOS:
                                continue
                        else:
                            if host_interface['vf_driver'] in VF_DRIVER_NETDEVICES:
                                continue
                    elif pod_type == POD_TYPE_NETDEVICE:
                        if host_interface['vf_driver'] in VF_DRIVER_VFIOS:
                            continue

                    for data_network in host_interface['datanetworks']:
                        data_network = sriov_helper.normalize_datanetwork_name(data_network)
                        if data_network_capacity[host_name].get('data_network', False):
                            capacity = data_network_capacity[host_name][data_network]
                            vf_capacity_list.append(int(capacity))

        if vf_capacity_list:
            return max(vf_capacity_list)
        else:
            return 0

    @classmethod
    def get_sriov_interface_num_vfs(cls, sriov_configs):
        """
        Get number of configured sriov vfs for each interface on each host.
        Args:
            sriov_configs: A list of SR-IOV config dictionaries:
            [{host: (str), interfaces: (list)}..]

        Returns (dict): dictionary of hosts and interfaces with corresponding number of vfs
                        {"controller-0": {"sriov0": "64"},
                        "compute-0": {"sriov1": "32":, "sriov0": 64}}}
        """
        interface_vfs_dict = dict()
        for sriov_config in sriov_configs:
            host = sriov_config["host"]
            interfaces = sriov_config["interfaces"]
            interface_vfs_dict[host] = dict()
            for interface in interfaces:
                interface_name = interface.get("name")
                sriov_numvfs = host_helper.get_host_interface_values(
                    host, interface_name, "sriov_numvfs"
                )[0]
                interface_vfs_dict[host].update({interface_name: sriov_numvfs})
        return interface_vfs_dict

    @classmethod
    def create_sriov_daemonset(
        cls,
        host,
        net_defs,
        daemonset_name=None,
        container_name=None,
        pod_type="netdevice",
        label_name="daemonset_sriov",
        file_path=None,
        namespace='default',
        image='centos/tools',
        ip_version=IPV4_VERSION,
        default_ipv6_pool=False,
    ):
        """
        Create a DaemonSet Object on host
        Args:
            host (str): THe name of host to create DaemonSet on that.
            net_defs (list): The list of network attachment definitions.
            daemonset_name (str): The Name of DaemonSet.
            container_name (str): The name of pod.
            pod_type (str): The type of pod to create (netdevice or dpdk).
            label_name (str): The labels to assign to DaemonSet and pod.
            file_path (str): The path to the file which Yaml file is there.
            namespace (str): The namespace to create DaemonSet.
            image (str): The image to use for creating pod.
            ip_version (str): The ip version of interfaces to allocated to pod.
            default_ipv6_pool (bool): use the default ipv6 pool or not

        Returns (name of DaemonSet (str), pods created (dict))
        """
        pods = list()
        testname = inspect.currentframe().f_back.f_code.co_name

        if container_name is None:
            container_name = "container-{}".format(testname.lower().replace("_", "-"))
        if daemonset_name is None:
            daemonset_name = "daemonset-{}".format(testname.lower().replace("_", "-"))
        if file_path is None:
            file_path = "/tmp/daemon_set_{}.yaml".format(daemonset_name)

        daemonset_name = sriov_helper.create_daemoset_pod_yaml(
            daemonset_name,
            container_name,
            net_defs,
            pod_type=pod_type,
            host=host,
            file_path=file_path,
            label_name=label_name,
            ip_version=ip_version,
            namespace=namespace,
            image=image,
            default_ipv6_pool=default_ipv6_pool,
        )

        LOG.tc_minor_step("Create DaemonSet {} on host {}".format(daemonset_name, host))

        kube_helper.apply_resource(file_path=file_path)

        LOG.tc_minor_step("Check status of POD {}".format(daemonset_name))

        _, actual_status = kube_helper.wait_for_pods_status(
            partial_names=daemonset_name, namespace=namespace
        )

        for actual_pod_name, actual_pod_status in actual_status.items():
            if pod_type == POD_TYPE_NETDEVICE:
                ipinfo = get_ipaddrs(actual_pod_name, ip_version=ip_version)
            else:
                ipinfo = []
            pods.append({'name': actual_pod_name, 'ip': ipinfo})

        return daemonset_name, pods

    @classmethod
    def verify_daemonset_status(
        cls,
        daemonset_name,
        expected_daemonset_values,
        fields=['NAME', 'DESIRED', 'CURRENT', 'READY', 'AVAILABLE', 'NODE SELECTOR', "CONTAINERS"],
        namespace="default",
        timeout=360,
        check_interval=10,
        **kwargs,
    ):
        """
        Verify different fields of DaemonSet in kubectl get daemonset <>
        Args:
            daemonset_name (str): The name of DaemonSet
            expected_daemonset_values (list): The list of tuples for expected value of each field.
            fields (list): The list of fields to be verified.
            namespace (str): The name space that DaemonSet is created.
            timeout (str): The time out to finish trying verifying fields
            if the expected values is not the same as actual values.
            check_interval (str): The sleep time between each interval of checking the values.
            *kwargs: Additional key/value

        Returns ((bool) verification status , (list) list of actual values)
        """
        LOG.info("Verify the status of DaemonSet {}".format(daemonset_name))
        end_time = time.time() + timeout
        while time.time() < end_time:
            actual_daemonset_values = kube_helper.get_resources(
                field=fields,
                resource_names=daemonset_name,
                namespace=namespace,
                resource_type='daemonsets',
                **kwargs,
            )
            if actual_daemonset_values == expected_daemonset_values:
                LOG.info(
                    "DaemonSet {}'s values are matching with expected values".format(daemonset_name)
                )
                return True, actual_daemonset_values

            LOG.info("Wait for {} before checking again DaemonSet status".format(daemonset_name))
            time.sleep(check_interval)

        LOG.warning(
            "DaemonSet {} actual values do not match with expected values".format(daemonset_name)
        )
        return False, actual_daemonset_values

    @classmethod
    def get_sriov_hosts_datanetwork(
        self, vfs, pod_type, num_hosts, pods_per_host, sriov_config, datanetwork_capacity
    ):
        """
        This method finds hosts and data-networks which satisfy sr-iov requirments
        Args:
            vfs (int): Number of vfs
            pod_type (str): type of pod (netdevice, dpdk)
            num_hosts (int): number of hosts
            pods_per_host (int): number of pods to be created on each host
            sriov_config (dict): SRIOV configuration returned from prepare_host
            datanetwork_capacity (dict): sriov node capacity returned from sriov_node_capacity

        Returns (tuple): Data networks and hosts available based on sriov requested
        """
        LOG.tc_step(
            "Try to find data-network and hosts with capacity vfs: {} for pod type: {}".format(
                vfs, pod_type
            )
        )
        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            pod_type,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork:
            skip('no data network exists with capacity for {} SR-IOV vfio VFs'.format(vfs))

        if not hosts:
            skip(
                'no host exists with capacity for {} SR-IOV vfio VFs and {} 1G hugpages'.format(
                    vfs, DPDK_HUGEPAGE_REQD
                )
            )
        LOG.info(
            "Data-Networks: {} and hosts: {} have capacity SRI-IOV vfs: {} for pod type {}".format(
                datanetwork, hosts, vfs, pod_type
            )
        )
        if num_hosts < len(hosts):
            LOG.info(
                "Hosts: {} are capable of creating pod with vfs: {}, and "
                "host {} is selected to have pod".format(hosts, vfs, hosts[-num_hosts:])
            )
            hosts = hosts[-num_hosts:]

        return datanetwork, hosts

    @classmethod
    def verify_allocated_vfs(cls, host, expected_values):
        """
        Verify the number of allocated sriov vfs to be the same as expected ones

        Args:
            host (str): name of host where the pods are created
            expected_values (dict): Dictionary of datanetworks with corresponding
            expected request and limit values

        Return (None)
        """
        data_networks = list(expected_values.keys())
        allocated_sriov_vfs = sriov_helper.get_node_sriov_allocated_resources(host, data_networks)
        assert (
            allocated_sriov_vfs == expected_values
        ), "Allocated sriov resource is not the same as expected values"


@fixture(scope='module')
def pull_and_push_external_to_local():
    """
    Pull docker image from external repository and push to registry.local.
    """
    con_ssh = ControllerClient.get_active_controller()

    for image in IMAGES_TO_PULL:
        target_name = '{}/{}'.format(LOCAL_REGISTRY, image)
        container_helper.login_to_docker(registry=LOCAL_REGISTRY, con_ssh=con_ssh)

        LOG.fixture_step(f'Pull {image} image from {LOCAL_REGISTRY} repository')
        rc, image_id = container_helper.pull_docker_image(
            name=target_name, fail_ok=True, con_ssh=con_ssh, timeout=600
        )
        if rc == 1:
            LOG.info(f'Docker image {image} does not exist on {LOCAL_REGISTRY}')
            LOG.fixture_step(f'Pull {image} image from external repository')

            name = image
            if image == DPDK_POD_IMAGE:
                name = f'{CUMULUS_REGISTRY}/{image}'

            rc, image_id = container_helper.pull_docker_image(
                name=name, fail_ok=True, con_ssh=con_ssh, timeout=600
            )
            assert rc == 0, f'Pull {name} image from external repository failed'

            LOG.fixture_step('Tag image with local registry')
            container_helper.tag_docker_image(
                source_image=image_id, target_name=target_name, con_ssh=con_ssh
            )

            LOG.fixture_step('Login to local docker registry')
            container_helper.push_docker_image((target_name), con_ssh=con_ssh)
        else:
            LOG.info(f"Image {image} present in local registry ")


@fixture(scope='module')
def prepare_host(request):
    """
    Discover the SR-IOV interface configuration of the system and
    ensure that the sriovdp label is applied.
    Args:
        request: The fixture request

    Returns (list): A list of SR-IOV config dictionaries:
                    [{host: (str), interfaces: (list)}..]
    """
    host_initial_labels = dict()
    new_hosts_labels = dict()
    sriovdp_label = {SRIOVDP_LABEL: 'enabled'}

    sriov_configs = sriov_helper.get_sriov_config()
    if not sriov_configs:
        skip('no capable SR-IOV interfaces')

    LOG.fixture_step("Getting Initial Labels on SR-IOV hosts")
    # Get Initial labels on each host, to be used later to recover the labels
    for config in sriov_configs:
        host = config['host']
        LOG.fixture_step("Getting Initial Labels on host: {}".format(host), depth=1)
        host_initial_labels[host] = host_helper.get_host_labels_info(host)
        new_hosts_labels[host] = sriovdp_label

    LOG.fixture_step("Add host's labels: {}".format(new_hosts_labels))
    Host.assign_host_labels(new_hosts_labels, overwrite=True)

    def revert_host():
        """
        Restore the labels
        """

        remove_host_labels, add_back_host_labels = Host.get_host_labels_to_recover(
            host_initial_labels, new_hosts_labels
        )
        LOG.fixture_step("Remove host's labels: {}".format(remove_host_labels))
        Host.remove_host_labels(remove_host_labels)

        if add_back_host_labels:
            LOG.fixture_step("Add host's labels back: {}".format(add_back_host_labels))
            Host.assign_host_labels(add_back_host_labels, overwrite=True)

    request.addfinalizer(revert_host)
    return sriov_configs


@fixture(scope='module', autouse=True)
def sriov_node_capacity(request, prepare_host):
    """
    Get the SR-IOV device plugin capacity (number of vfs available)
    on each datanetwork in the system.
    Args:
        request: The fixture request
        prepare_host: The prepare_host fixture

    Returns (dict): A dictionary of nodes with their SR-IOV device plugin
                    discovered virtual functions.
                    {node_name: {datanetwork_name: num_vfs}, ...}

    """
    return sriov_helper.get_sriov_node_capacity()


@fixture(scope='function')
def prepare_test_interfaces(request, get_base_interface_info):
    """
    This fixture creates child vf sriov interfaces and NADs for test purposes

    Args:
        - request(fixture)
        - get_base_interface_info(function fixture)

    Returns:
        - host, nads(str, tuple(dict)):
    """
    LOG.fixture_step('Check system datanetworks')
    datanetworks = system_helper.get_data_networks()
    if len(datanetworks) < 2:
        skip('Not enough datanetworks configured on system: {}'.format(datanetworks))

    sriov_vf_driver, host, parent_if, parent_datanetwork = get_base_interface_info
    test_if = TEST_SRIOV_INTERFACE

    LOG.fixture_step('Lock {}'.format(host))
    host_helper.lock_host(host, swact=True)

    LOG.fixture_step('Create 3 child sriov interfaces over {}'.format(parent_if))
    test_interfaces = add_sriov_interfaces(
        host,
        test_if,
        parent_if,
        interface_count=3,
        sriov_vf_driver=sriov_vf_driver,
        alt_driver=True,
    )

    LOG.fixture_step('Create test datanetwork')
    _, test_datanetwork = system_helper.create_data_network('test_datanetwork', field='name')
    datanetwork_uuid = system_helper.get_data_network_values(test_datanetwork)

    LOG.fixture_step(
        'Assign {} interface to {} datanetwork'.format(test_interfaces[0], test_datanetwork)
    )
    host_helper.assign_interface_datanetwork(host, test_interfaces[0], test_datanetwork)

    LOG.fixture_step('Unlock {}'.format(host))
    host_helper.unlock_host(host)

    def cleanup():
        LOG.fixture_step('Lock {}'.format(host))
        host_helper.lock_host(host)

        for interface in test_interfaces:
            LOG.fixture_step('Delete {} interface'.format(interface))
            host_helper.delete_host_interface(host, interface, lock_unlock=False)

        LOG.fixture_step('Delete {} datanetwork'.format(test_datanetwork))
        system_helper.delete_data_network(datanetwork_uuid)

        LOG.fixture_step('Unlock {}'.format(host))
        host_helper.unlock_host(host)

    request.addfinalizer(cleanup)
    return host, datanetworks, test_datanetwork, parent_datanetwork


@fixture(scope='function')
def prepare_data_interface(request, get_base_interface_info):
    """
    This fixture creates a data class interface for test purposes

    Args:
        - request

    Steps:
        - Lock target host
        - Create data class interface over first available port

    Returns:
        - host(str), data_interface(str): target host, created data class interface
    """
    _, host, _, _ = get_base_interface_info
    if not host:
        skip('Standby controller is in bad state, perform manual check before running any tests')

    LOG.fixture_step('Lock {}'.format(host))
    host_helper.lock_host(host)
    host_ports = host_helper.get_host_ports(host)
    host_interfaces = host_helper.get_hosts_interfaces_info(
        host, kwargs_for_get_host_interface_values={'fields': INTF_FIELDS, 'rtn_dict': True}
    )[host]

    used_ports = [
        host_interfaces[interface]['ports'][0]
        for interface in host_interfaces
        if host_interfaces[interface]['ports']
    ]

    available_ports = list(set(host_ports) - set(used_ports))
    if not available_ports:
        skip('No available ports on {}'.format(host))
    port = available_ports[0]

    LOG.fixture_step('Create data class interface over {} port'.format(port))
    data_interface = TEST_DATA_IF
    host_helper.modify_host_interface(
        host,
        '',
        mtu=1500,
        if_class='data',
        lock_unlock=False,
        port=port,
        new_if_name=data_interface,
    )

    def delete_data_interface():
        LOG.fixture_step('Deleting created data interface {}'.format(data_interface))
        host_helper.modify_host_interface(host, data_interface, if_class='none')

    request.addfinalizer(delete_data_interface)
    return host, data_interface


@fixture(scope='function')
def get_base_interface_info(request, prepare_host):
    """
    This fixture retrieves the first sriov interface from system sriov config
    set by 'prepare_host' fixture before test execution in order to avoid code
    duplication as mentioned info is required by several TCs

    Args:
        - request(fixture object):
        - prepare_host(module fixture):

    Returns:
        - sriov_vf_driver, host, parent_if: (str, str, str)
    """
    sriov_vf_driver = prepare_host[0]['interfaces'][0]['vf_driver']
    if sriov_vf_driver == 'None':
        sriov_vf_driver = 'netdevice'
    host = prepare_host[0]['host']
    parent_if = prepare_host[0]['interfaces'][0]['name']
    parent_datanetwork = prepare_host[0]['interfaces'][0]['datanetworks'][0]
    swact = system_helper.is_active_controller(host) and system_helper.is_aio_duplex()

    # check host-lock will be possible and not rejected due to ceph minimum monitors up
    if host in storage_helper.get_ceph_mons():
        health, reasons = storage_helper.get_ceph_state()
        if health != 'HEALTH_OK':
            for reason in reasons:
                if 'mons down' in reason:
                    mons_up = int(reason.split(' ', 1)[0][-1]) - int(reason.split(' ', 1)[0][0])
                    if mons_up < 3 and host in reason:
                        host = prepare_host[1]['host'] if len(prepare_host) > 1 else None

    if not host:
        msg = (
            'Available host {} cannot be locked as It is one of 2 min required Ceph monitors up'
            'please check ceph monitors manually before running SRIOV TCs: {}'.format(host, reason)
        )
        skip(msg)

    def revert_swact():
        host_helper.swact_host(system_helper.get_active_controller_name())

    if swact:
        request.addfinalizer(revert_swact)

    return sriov_vf_driver, host, parent_if, parent_datanetwork


def add_sriov_interfaces(
    host, interface, parent_sriov_vf, sriov_vf_driver, interface_count=1, alt_driver=False
):
    """
    This method creates a given number of child vf sriov interfaces
    according to specific args

    Args:
        - host(str): host to create the interfaces in
        - interface(str): name for new interface/s
        - parent_sriov_vf(str): parent sriov interface
        - sriov_vf_driver(str): parent sriov interface driver
        - interface_count(int): number of interfaces to be created
        - alt_driver(bool): wether to iterate on parent and non parent driver for
                            new interfaces
    Returns:
        - new_interfaces(list(str)): list of created interfaces
    """
    non_parent_driver = (
        VF_DRIVER_VFIO if sriov_vf_driver == VF_DRIVER_NETDEVICE else VF_DRIVER_NETDEVICE
    )
    new_interfaces = []
    failed_interfaces = []
    for i in range(interface_count):
        vf_driver = sriov_vf_driver if (not i % 2) and alt_driver else non_parent_driver
        new_interface = interface + str(i) if interface_count != 1 else interface
        LOG.info(
            'Adding {} child interface with {} driver and {} as parent interface'.format(
                new_interface, vf_driver, parent_sriov_vf
            )
        )
        rc, out = host_helper.add_host_interface(
            host,
            new_interface,
            '',
            mtu=MTU,
            parent_sriov_vf=parent_sriov_vf,
            if_class=INTERFACE_CLASS_PCI_SRIOV,
            sriov_vf_count=1,
            lock_unlock=False,
            sriov_vf_driver=vf_driver,
            fail_ok=True,
        )
        if rc != 0:
            failed_interfaces.append((new_interface, out))
        else:
            new_interfaces.append(new_interface)
    msg = 'Failed to create {} interfaces on {}'.format(failed_interfaces, host)
    assert not failed_interfaces, msg

    return new_interfaces


def get_sriov_network(vf_idx, ip_version):
    """
    Get the network CIDR to be used for each VF
    Args:
        vf_idx: The VF index
        ip_version: The IP version

    Returns:
        An IPv4Network or IPv6Network object - The V4/V6 network to use
    """
    if ip_version == IPV4_VERSION:
        net = ipaddress.ip_network('192.168.{}.0/24'.format(vf_idx), strict=False)
    elif ip_version == IPV6_VERSION:
        net = ipaddress.ip_network('2626:{}::/64'.format(vf_idx))
    else:
        raise ValueError("Invalid ip_version {} is given".format(ip_version))
    return net


def create_calicoctl_pod(podname):
    """
    Create an pod containing the calicoctl application
    calicoctl is a utility similar to kubectl that is used to configure
    calico.  It is primarily used in this test suite to setup separate
    IP pools that are used on the SR-IOV interfaces so that connectivity
    tests are guaranteed to use the correct interface (otherwise, the
    SR-IOV interfaces would be on the same subnet as the default
    network interface).  At this point in time we do not include
    the calicoctl application on the system itself.
    Args:
        podname (str): The name of the calicoctl pod
    """
    # Based on: https://docs.projectcalico.org/v3.2/getting-started/kubernetes/installation/
    # hosted/kubernetes-datastore/calicoctl.yaml

    service_account_config = {
        'apiVersion': 'v1',
        'kind': 'ServiceAccount',
        'metadata': {'name': podname, 'namespace': 'kube-system'},
    }

    filename = '/tmp/calicoctl_sa.yaml'
    content = yaml.dump(service_account_config, default_flow_style=False)
    file_utilities.create_file(filename, content)
    LOG.tc_step("Try to create calicoctl service account {}".format(podname))
    kube_helper.apply_resource(filename)

    cluster_role_config = {
        'apiVersion': 'rbac.authorization.k8s.io/v1',
        'kind': 'ClusterRole',
        'metadata': {'name': podname},
        'rules': [
            {
                'apiGroups': [""],
                'resources': ['namespaces', 'nodes'],
                'verbs': ['get', 'list', 'update'],
            },
            {'apiGroups': [""], 'resources': ['pods', 'serviceaccounts'], 'verbs': ['get', 'list']},
            {'apiGroups': [""], 'resources': ['pods/status'], 'verbs': ['update']},
            {
                'apiGroups': ["crd.projectcalico.org"],
                'resources': [
                    'bgppeers',
                    'bgpconfigurations',
                    'clusterinformations',
                    'felixconfigurations',
                    'globalnetworkpolicies',
                    'globalnetworksets',
                    'ippools',
                    'networkpolicies',
                    'hostendpoints',
                ],
                'verbs': ['create', 'get', 'list', 'update', 'delete'],
            },
        ],
    }

    filename = '/tmp/calicoctl_cr.yaml'
    content = yaml.dump(cluster_role_config, default_flow_style=False)
    file_utilities.create_file(filename, content)
    LOG.tc_step("Try to create calicoctl cluster role {}".format(podname))
    kube_helper.apply_resource(filename)

    cluster_role_binding_config = {
        'apiVersion': 'rbac.authorization.k8s.io/v1',
        'kind': 'ClusterRoleBinding',
        'metadata': {'name': podname},
        'roleRef': {
            'apiGroup': 'rbac.authorization.k8s.io',
            'kind': 'ClusterRole',
            'name': podname,
        },
        'subjects': [{'kind': 'ServiceAccount', 'name': podname, 'namespace': 'kube-system'}],
    }

    filename = '/tmp/calicoctl_crb.yaml'
    content = yaml.dump(cluster_role_binding_config, default_flow_style=False)
    file_utilities.create_file(filename, content)
    LOG.tc_step("Try to create calicoctl cluster role binding {}".format(podname))
    kube_helper.apply_resource(filename)

    pod_config = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {'name': podname, 'namespace': 'kube-system'},
        'spec': {
            'nodeSelector': {'beta.kubernetes.io/os': 'linux'},
            'hostNetwork': True,
            'serviceAccountName': podname,
            'containers': [
                {
                    'name': podname,
                    'image': CALICOCTL_IMAGE,
                    'command': ['/bin/sh', '-c', 'while true; do sleep 3600; done'],
                    'env': [{'name': 'DATASTORE_TYPE', 'value': 'kubernetes'}],
                }
            ],
            'imagePullSecrets': [{'name': 'default-registry-key'}],
        },
    }

    filename = '/tmp/calicoctl_pod.yaml'
    content = yaml.dump(pod_config, default_flow_style=False)
    file_utilities.create_file(filename, content)
    LOG.tc_step("Try to create calicoctl pod {}".format(podname))
    kube_helper.apply_resource(filename)
    LOG.info("Check for {} pod Running".format(podname))
    kube_helper.wait_for_pods_status(
        pod_names=podname, namespace='kube-system', status=PodStatus.RUNNING
    )


def create_calico_ippool(podname, poolname, cidr):
    """
    Create a calico IP Pool
    Args:
        podname (str): The name of the calicoctl pod that will use the IP pool
        poolname (str): The name for the IP pool
        cidr (str): The IP address and prefix of the IP pool

    Returns (tuple): (exit code (int), command output (str))
    """
    con_ssh = ControllerClient.get_active_controller()

    # IPv6 pools require an ipipMode of 'Never'
    config = {
        'apiVersion': 'projectcalico.org/v3',
        'kind': 'IPPool',
        'metadata': {'name': poolname},
        'spec': {'cidr': cidr, 'ipipMode': 'Never', 'natOutgoing': True},
    }

    filename = '/tmp/calicoctl-ippool-{}.yaml'.format(poolname)
    content = yaml.dump(config, default_flow_style=False)

    LOG.tc_step("Try to create calicoctl IP pool config file {}".format(filename))
    file_utilities.create_file(filename, content)

    # Copy the IP pool .yaml file to the calicoctl pod
    LOG.tc_step("Try to create copy the calicoctl IP pool config file to pod {}".format(podname))
    cmd = 'kubectl cp {} -n kube-system {}:{}'.format(filename, podname, filename)
    code, output = con_ssh.exec_cmd(cmd, fail_ok=True)
    if code > 0:
        # Occasionally the kubectl commands will fail on the calicoctl pod.
        # Needs investigating, but for now we will work around this by retrying
        # a number of times.
        for i in range(1, 10):
            time.sleep(1)
            code, output = con_ssh.exec_cmd(cmd, fail_ok=True)
            if code == 0:
                # Finally passed
                break
        else:
            return code, output

    # Apply the IP pool .yaml in the calicoctl pod
    LOG.tc_step("Try to create the calicoctl IP pool {} on pod {}".format(poolname, podname))
    cmd = 'calicoctl apply -f {}'.format(filename)
    code, output = kube_helper.exec_cmd_in_container(
        cmd, pod=podname, stdin=True, namespace='kube-system'
    )

    if code > 0:
        for i in range(1, 10):
            time.sleep(1)
            code, output = kube_helper.exec_cmd_in_container(
                cmd, pod=podname, stdin=True, namespace='kube-system'
            )
            if code == 0:
                break
        else:
            return code, output

    return code, output


def delete_calico_ippool(podname, poolname):
    """
    Delete a calico IP Pool
    Args:
        podname (str): The name of the calicoctl pod that will use the IP pool
        poolname (str): The name for the IP pool
    """
    LOG.tc_step("Try to delete the calicoctl IP pool {} from {}".format(poolname, podname))
    cmd = 'calicoctl delete ippool {}'.format(poolname)
    kube_helper.exec_cmd_in_container(
        cmd, pod=podname, stdin=True, tty=True, namespace='kube-system'
    )


def get_calico_ippool_name(datanetwork, vf_idx):
    """
    Get a standardized Calico pool name
    Args:
        datanetwork (str): The datanetwork for the pool
        vf_idx (int): The VF number

    Returns (str): The Calico pool name
    """
    # poolname must only have alphanumeric characters, '-', and '.'
    return 'sriov-pool-{}-vf{}'.format(datanetwork, vf_idx).lower().replace("_", "-")


def create_calico_ippools(datanetwork, num_vfs, ip_version=IPV4_VERSION):
    """
    Create calico pools for a datanetwork
    Args:
        datanetwork (str): The datanetwork for the pool
        num_vfs (int): The number of VFs on the datanetwork
        ip_version (int): The IP version

    Returns (list): The created Calico IP pools
    """

    ippools = []

    for idx in range(0, num_vfs):
        poolname = get_calico_ippool_name(datanetwork, idx + 1)
        cidr = get_sriov_network(idx + 1, ip_version)
        code, output = create_calico_ippool(CALICOCTL_PODNAME, poolname, str(cidr))
        if code == 0:
            ippools.append(poolname)

    return ippools


def get_calico_ipam_config(cidr, poolname):
    """
    Create an IPAM config for the calico-ipam CNI plugin
    Args:
        cidr (IPv4Network or IPv6Network object): Classless inter-domain routing (ip/prefix)
        poolname (str): The name of the IP pool to use

    Returns ipam_config (dict): A host-local compatible ipam config dictionary
    """
    ipam_config = {"\"type\"": "\"calico-ipam\"", "\"subnet\"": "\"{}\"".format(str(cidr))}

    if cidr.version == IPV4_VERSION:
        ipam_config["\"assign_ipv4\""] = "\"true\""
        ipam_config["\"ipv4_pools\""] = "[\"{}\"]".format(poolname)
    elif cidr.version == IPV6_VERSION:
        ipam_config["\"assign_ipv6\""] = "\"true\""
        ipam_config["\"assign_ipv4\""] = "\"false\""
        ipam_config["\"ipv6_pools\""] = "[\"{}\"]".format(poolname)
    return ipam_config


def get_static_ipam_config(address):
    """
    Get a properly formatted config for static IPAM
    Args:
        address (str): The IPv4/IPv6 address to assign

    Returns ipam_config (dict): A static compatible ipam config dictionary
    """
    ipam_config = {
        "\"type\"": "\"static\"",
        "\"addresses\"": [{"\"address\"": "\"{}\"".format(address)}],
    }
    return ipam_config


def get_dhcp_ipam_config():
    """
    Get a properly formatted config for dhcp IPAM

    Returns ipam_config (dict): A dhcp compatible ipam config dictionary
    """
    ipam_config = {"\"type\"": "\"dhcp\""}
    return ipam_config


def start_dhcp_daemons(hosts):
    """
    Start the DHCP daemon required when using a DHCP IPAM
    Args:
        hosts (list): The hosts to start the daemon on

    """
    for host in hosts:
        with host_helper.ssh_to_host(host) as host_ssh:
            cmd = 'rm -f /run/cni/dhcp.sock'
            host_ssh.exec_sudo_cmd(cmd)

            LOG.tc_step("Try to start DHCP daemon on {}".format(host))
            cmd = 'setsid /opt/cni/bin/ daemon >/dev/null 2>&1 &'
            host_ssh.exec_sudo_cmd(cmd)


def stop_dhcp_daemons(hosts):
    """
    Stop the DHCP daemons
    Args:
        hosts (list): The hosts to stop the daemon on

    """
    for host in hosts:
        with host_helper.ssh_to_host(host) as host_ssh:
            LOG.tc_step("Try to stop DHCP daemon on {}".format(host))
            cmd = 'pkill dhcp'
            host_ssh.exec_sudo_cmd(cmd)


def create_dhcp_pod(podname, datanetwork, network):
    """
    Create a pod to act as a DHCP server
    Args:
        podname (str): The name of the DHCP pod to create
        datanetwork (str): The datanetwork of the DHCP interface
        network (str): The network CIDR to use to assign addresses from
    """
    nadname = podname
    dhcp_address = ipaddress.ip_interface(
        '{}/{}'.format(ipaddress.ip_interface(network).ip + 1, network.prefixlen)
    )
    dhcp_ipam = get_static_ipam_config(str(dhcp_address))
    filename = sriov_helper.create_network_attachment_definition(
        nadname, datanetwork, ipam=dhcp_ipam, spoofchk="off", trust="on"
    )

    range_start = str(dhcp_address.ip + 2)
    range_end = str(dhcp_address.ip + 100)

    LOG.tc_step("Try to create network attachment definition {}".format(podname))
    kube_helper.apply_resource(filename)

    pod_config = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': 'pod-{}'.format(podname),
            'annotations': {'k8s.v1.cni.cncf.io/networks': '{}'.format(nadname)},
        },
        'spec': {
            'containers': [
                {
                    'name': 'pod-{}'.format(podname),
                    'image': 'andyshinn/dnsmasq:2.72',
                    'imagePullPolicy': 'IfNotPresent',
                    'command': [
                        "dnsmasq",
                        "--log-dhcp",
                        "-p0",
                        "-k",
                        "-i",
                        "net1",
                        "-l",
                        "/tmp/leasefile.dhcp",
                        "--log-facility",
                        "/tmp/dhcp.log",
                        "--dhcp-range",
                        "{},{},5m".format(range_start, range_end),
                    ],
                    'ports': [
                        {'name': 'dhcp-67', 'containerPort': 67, 'protocol': 'UDP'},
                        {'name': 'dhcp-68', 'containerPort': 68, 'protocol': 'UDP'},
                    ],
                    'volumeMounts': [{'name': 'etcdnsmasqd', 'mountPath': '/etc/dnsmasq.d'}],
                    'securityContext': {'capabilities': {'add': ["NET_ADMIN"]}},
                    'resources': {
                        'requests': {'intel.com/pci_sriov_net_{}'.format(datanetwork): 1},
                        'limits': {'intel.com/pci_sriov_net_{}'.format(datanetwork): 1},
                    },
                }
            ],
            'volumes': [{'name': 'etcdnsmasqd', 'hostPath': {'path': '/etc/dnsmasq.d'}}],
            'dnsPolicy': 'Default',
        },
    }

    filename = '/tmp/dhcp-pod.yaml'
    content = yaml.dump(pod_config, default_flow_style=False)
    file_utilities.create_file(filename, content)
    LOG.tc_step("Try to create DHCP pod {}".format(podname))
    kube_helper.apply_resource(filename)


def create_network_attachment_definitions(
    hosts,
    vfs,
    datanetwork,
    cni_type='sriov',
    ipam_type=None,
    ip_version=IPV4_VERSION,
    user_ipam_config=None,
):
    """
    Create a network attachment definitions
    Args:
        hosts (lists): A list of hosts that pods using the network attachment
                       definition can be scheduled on.
        vfs (int): The number of vfs in each pod
        datanetwork (str): The datanetwork of the network attachment definition
        cni_type (str): The CNI type of the network attachment definition
        ipam_type (str): The IPAM type to use in the network attachment
                        definition
        ip_version (int): The IP version to use in the network attachment
                          definition (4/6)
        user_ipam_config (dict): The ipam configuration dictionary

    Returns (list): A list dicts containing information about each created
                    network attachment definition.
    """
    testname = inspect.currentframe().f_back.f_code.co_name

    netdefs = []
    for host_idx, host in enumerate(hosts):
        for idx in range(0, vfs):
            nadname = (
                '{}-{}-{}-vf{}'.format(testname, host, datanetwork, idx + 1)
                .lower()
                .replace("_", "-")
            )
            exists = [nad['name'] for nad in netdefs if nad['name'] == nadname]
            if exists:
                continue

            cidr = get_sriov_network(idx + 1, ip_version)

            if user_ipam_config is None:
                if ipam_type == 'calico-ipam':
                    poolname = get_calico_ippool_name(datanetwork, idx + 1)
                    ipam_config = get_calico_ipam_config(cidr, poolname)
                elif ipam_type == 'dhcp':
                    ipam_config = get_dhcp_ipam_config()
                elif ipam_type == 'host-local':
                    ipam_config = sriov_helper.get_host_local_ipam_config(
                        host_idx, len(hosts), cidr, ip_version
                    )
                else:
                    ipam_config = None
            else:
                ipam_config = user_ipam_config

            filename = sriov_helper.create_network_attachment_definition(
                nadname,
                datanetwork,
                cni_type=cni_type,
                ipam=ipam_config,
                spoofchk="off",
                trust="on",
            )

            LOG.tc_minor_step("Try to create network attachment definition {}".format(nadname))
            kube_helper.apply_resource(filename)
            nad_config = {'name': nadname, 'datanetwork': datanetwork, 'vfs': 1, 'host': host}
            netdefs.append(nad_config)
    return netdefs


def create_netdevice_pod_yaml(
    filename, podname, netdefs, host=None, ip_version=IPV4_VERSION, default_ipv6_pool=True
):
    """
    Create a pod .yaml file on the active controller based on a netdevice
    (kernel interface) application
    Args:
        filename (str): The absolute path to the file to create
        podname (str): The name of the pod
        netdefs (list): The list of network attachment definitions
        host (str): The host to place the pod on
        ip_version (int): The IP version of the default pod network
        default_ipv6_pool (bool): Use default-ipv6-pool or not

    Returns (exit code (int), command output (str))
    """
    podname = sriov_helper.normalize_metadata_name(podname)

    networks = ""
    datanetworks = {}

    netdefs = [netdef for netdef in netdefs if host == netdef['host']]

    for idx, netdef in enumerate(netdefs):
        if idx > 0:
            networks += ","
        nad_name = netdef['name']
        vfs = netdef['vfs']
        datanetwork = netdef['datanetwork']
        networks += ",".join([nad_name for i in range(vfs)])
        if datanetwork not in datanetworks.keys():
            datanetworks[datanetwork] = vfs
        else:
            datanetworks[datanetwork] += vfs

    config = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': podname,
            'annotations': {'k8s.v1.cni.cncf.io/networks': '{}'.format(networks)},
        },
        'spec': {
            'containers': [
                {
                    'name': podname,
                    'image': 'centos/tools',
                    'imagePullPolicy': 'IfNotPresent',
                    'command': ['/bin/bash', '-c', '--'],
                    'args': ['while true; do sleep 300000; done;'],
                    'securityContext': {
                        'capabilities': {'add': ["IPC_LOCK", "NET_ADMIN", "NET_RAW"]}
                    },
                    'resources': {'requests': {}, 'limits': {}},
                }
            ]
        },
    }
    for datanetwork in datanetworks.keys():
        vfs = datanetworks[datanetwork]
        config['spec']['containers'][0]['resources']['requests'].update(
            {'intel.com/pci_sriov_net_{}'.format(datanetwork): vfs}
        )
        config['spec']['containers'][0]['resources']['limits'].update(
            {'intel.com/pci_sriov_net_{}'.format(datanetwork): vfs}
        )
    if host is not None:
        config['spec'].update({'nodeSelector': {'kubernetes.io/hostname': host}})
    if ip_version == IPV4_VERSION:
        config['metadata']['annotations'].update(
            {'cni.projectcalico.org/ipv4pools': '\"[\\"default-ipv4-ippool\\"]\"'}
        )
    elif ip_version == IPV6_VERSION and default_ipv6_pool:
        config['metadata']['annotations'].update(
            {'cni.projectcalico.org/ipv6pools': '\"[\\"default-ipv6-ippool\\"]\"'}
        )
    content = yaml.dump(config, default_flow_style=False)

    return file_utilities.create_file(filename, content)


def create_dpdk_pod_yaml(
    filename, podname, netdefs, host=None, ip_version=None, default_ipv6_pool=True
):
    """
    Create a pod .yaml file on the active controller based on a DPDK
    application
    Args:
        filename (str): The absolute path to the file to create
        podname (str): The name of the pod
        netdefs (list): The list of network attachment definitions
        host (str): The host to place the pod on
        ip_version (int): The IP version of the default pod network
        default_ipv6_pool (bool): use the default ipv6 pool or not

    Returns (exit code (int), command output (str))
    """
    podname = sriov_helper.normalize_metadata_name(podname)

    networks = ""
    datanetworks = {}

    netdefs = [netdef for netdef in netdefs if host == netdef['host']]

    for idx, netdef in enumerate(netdefs):
        if idx > 0:
            networks += ","
        nad_name = netdef['name']
        vfs = netdef['vfs']
        datanetwork = netdef['datanetwork']
        networks += ",".join([nad_name for i in range(vfs)])
        if datanetwork not in datanetworks.keys():
            datanetworks[datanetwork] = vfs
        else:
            datanetworks[datanetwork] += vfs

    config = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': podname,
            'annotations': {'k8s.v1.cni.cncf.io/networks': '{}'.format(networks)},
        },
        'spec': {
            'restartPolicy': 'Always',
            'containers': [
                {
                    'name': podname,
                    'image': f'{CUMULUS_REGISTRY}/' + DPDK_POD_IMAGE,
                    'command': ["/bin/bash", "-ec", "sleep infinity"],
                    'imagePullPolicy': 'IfNotPresent',
                    'stdin': True,
                    'tty': True,
                    'volumeMounts': [{'mountPath': '/mnt/huge-1048576kB', 'name': 'hugepage'}],
                    'securityContext': {
                        'capabilities': {'add': ["IPC_LOCK", "NET_ADMIN", "NET_RAW"]}
                    },
                    'resources': {
                        'requests': {'memory': '3Gi', 'cpu': DPDK_POD_CPUS_REQD},
                        'limits': {
                            'hugepages-1Gi': '2Gi',
                            'memory': '3Gi',
                            'cpu': DPDK_POD_CPUS_REQD,
                        },
                    },
                }
            ],
            'volumes': [{'name': 'hugepage', 'emptyDir': {'medium': 'HugePages'}}],
        },
    }

    for datanetwork in datanetworks.keys():
        vfs = datanetworks[datanetwork]
        config['spec']['containers'][0]['resources']['requests'].update(
            {'intel.com/pci_sriov_net_{}'.format(datanetwork): vfs}
        )
        config['spec']['containers'][0]['resources']['limits'].update(
            {'intel.com/pci_sriov_net_{}'.format(datanetwork): vfs}
        )
    if host is not None:
        config['spec'].update({'nodeSelector': {'kubernetes.io/hostname': host}})
    if ip_version == IPV4_VERSION:
        config['metadata']['annotations'].update(
            {'cni.projectcalico.org/ipv4pools': '\"[\\"default-ipv4-ippool\\"]\"'}
        )
    elif ip_version == IPV6_VERSION and default_ipv6_pool:
        config['metadata']['annotations'].update(
            {'cni.projectcalico.org/ipv6pools': '\"[\\"default-ipv6-ippool\\"]\"'}
        )
    content = yaml.dump(config, default_flow_style=False)

    return file_utilities.create_file(filename, content)


def create_netdevice_pod(
    podname, netdefs, host=None, ip_version=IPV4_VERSION, default_ipv6_pool=True
):
    """
    Create a pod .yaml file on the active controller based on a netdevice
    (kernel interface) application
    Args:
        podname (str): The name of the pod
        netdefs (list): The list of network attachment definitions
        host (str): The host to place the pod on
        ip_version (int): The IP version of the pod's default network
        default_ipv6_pool (bool): whether to use default-ipv6-pool or not

    Returns filename (str)
    """
    filename = '/tmp/pod-{}.yaml'.format(podname)
    create_netdevice_pod_yaml(
        filename,
        podname,
        netdefs,
        host=host,
        ip_version=ip_version,
        default_ipv6_pool=default_ipv6_pool,
    )
    return filename


def create_dpdk_pod(podname, netdefs, host=None, ip_version=None, default_ipv6_pool=True):
    """
    Create a pod .yaml file on the active controller based on a DPDK
    application
    Args:
        podname (str): The name of the pod
        netdefs (list): The list of network attachment definitions
        host (str): The host to place the pod on
        ip_version (int): The IP version of the pod's default network
        default_ipv6_pool (bool): use the default ipv6 pool or not

    Returns filename (str)
    """
    filename = '/tmp/pod-{}.yaml'.format(podname)
    create_dpdk_pod_yaml(
        filename,
        podname,
        netdefs,
        host=host,
        ip_version=ip_version,
        default_ipv6_pool=default_ipv6_pool,
    )
    return filename


def _get_resources(con_ssh=None):
    """
    Get SR-IOV related kubernetes resources
    Args:
        con_ssh: the current ssh connection to the active controller

    Returns (tuple): (default pods (list), system pods (list),
                      network attachment definitions (list),
                      Calico IP pools (list))
    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    default_pods = kube_helper.get_resources(
        field='NAME', resource_type='pod', namespace='default', con_ssh=con_ssh
    )

    system_pods = kube_helper.get_resources(
        field='NAME', resource_type='pod', namespace='kube-system', con_ssh=con_ssh
    )

    nads = kube_helper.get_resources(
        field='NAME', resource_type='net-attach-def', namespace='default', con_ssh=con_ssh
    )

    daemon_sets = kube_helper.get_resources(
        field='NAME', resource_type='daemonsets', namespace='default', con_ssh=con_ssh
    )

    deployment_pods = kube_helper.get_resources(
        field='NAME', resource_type='deployment', namespace='default', con_ssh=con_ssh
    )

    ippools = []
    if CALICOCTL_PODNAME in system_pods:
        cmd = 'calicoctl get ippools'
        code, output = kube_helper.exec_cmd_in_container(
            cmd, pod=CALICOCTL_PODNAME, stdin=True, namespace='kube-system', fail_ok=True
        )
        if code > 0:
            for i in range(1, 10):
                time.sleep(1)
                code, output = kube_helper.exec_cmd_in_container(
                    cmd, pod=CALICOCTL_PODNAME, stdin=True, namespace='kube-system', fail_ok=True
                )
                if code == 0:
                    break

        if code == 0:
            for line in output.splitlines():
                info = line.split()
                if len(info) > 0:
                    ippools.append(info[0])

    return default_pods, system_pods, nads, ippools, daemon_sets, deployment_pods


def _get_system_resources(hosts=None):
    """
    This method get the datanetwork and interface of on each host.
    Args:
        hosts (list): The list of hosts to get interfaces.

    Returns (tuple): (datanetwork's uuid (list),
                      interfaces of eahc host (dict))
    """
    host_interfaces = {}

    if not hosts:
        hosts = system_helper.get_hosts()

    datanetworks = system_helper.get_data_networks(field='uuid')
    for host in hosts:
        host_interfaces[host] = host_helper.get_host_interfaces(host)

    return datanetworks, host_interfaces


@fixture(scope='function')
def prepare_system_resources(request, prepare_host):
    """
    Discover datanetwork and host-interfaces resources and
    revert system back to initial state in teardown.
    Args:
        request: The fixture request
        prepare_host: The configuration of all SR-IOV enabled interfaces in the system

    Returns: None
    """
    sriov_configs = prepare_host
    init_host_interfaces = {}
    hosts = []

    for sriov_config in sriov_configs:
        hosts.append(sriov_config['host'])

    init_datanetwork_uuids, init_host_interfaces = _get_system_resources(hosts=hosts)

    def revert_system_resources():
        """
        This is teardown to revert configured datanetwork and interfaces on each host
        during testcase execution.
        """

        datanetwork_uuids, host_interfaces = _get_system_resources(hosts=hosts)

        for host, interfaces in host_interfaces.items():
            cleanup_host_interfaces = list(set(interfaces) - set(init_host_interfaces[host]))

            if cleanup_host_interfaces:
                for cleanup_host_interface in cleanup_host_interfaces:
                    LOG.fixture_step(
                        "Try to remove interfaces {} on host {}".format(
                            host, cleanup_host_interfaces
                        )
                    )
                    host_helper.delete_host_interface(host, cleanup_host_interface)

        cleanup_datanetworks_uuid = list(set(datanetwork_uuids) - set(init_datanetwork_uuids))
        if cleanup_datanetworks_uuid:
            LOG.fixture_step('datanetworks to cleanup: {}'.format(cleanup_datanetworks_uuid))
            for cleanup_datanetwork_uuid in cleanup_datanetworks_uuid:
                system_helper.delete_data_network(cleanup_datanetwork_uuid)

    request.addfinalizer(revert_system_resources)


@fixture(scope='function')
def prepare_resources(request):
    """
    Discover SR-IOV related kubernetes resources
    Args:
        request: The fixture request

    Returns (tuple): (default pods (list), system pods (list),
                      network attachment definitions (list),
                      Calico IP pools (list), DaemonSet (list))
    """
    con_ssh = ControllerClient.get_active_controller()

    (
        init_d_pods,
        init_s_pods,
        init_nads,
        init_ippools,
        init_daemon_sets,
        init_deployment_pods,
    ) = _get_resources(con_ssh)

    def revert_resources():
        """
        Remove any created SR-IOV related kubernetes resources
        """
        default_pods, system_pods, nads, ippools, daemon_sets, deployment_pods = _get_resources(
            con_ssh
        )

        cleanup_default_pods = [pod for pod in default_pods if pod not in init_d_pods]
        cleanup_system_pods = [pod for pod in system_pods if CALICOCTL_PODNAME == pod]
        cleanup_nads = [nad for nad in nads if nad not in init_nads]
        cleanup_ippools = [pool for pool in ippools if 'sriov' in pool]
        cleanup_daemon_sets = [
            daemon_set for daemon_set in daemon_sets if daemon_set not in init_daemon_sets
        ]
        cleanup_deployment_pods = [
            deployment_pod
            for deployment_pod in deployment_pods
            if deployment_pod not in init_deployment_pods
        ]

        LOG.info("DaemonSets to clean up: {}".format(cleanup_daemon_sets))
        LOG.info("pods to cleanup: %r", cleanup_default_pods + cleanup_system_pods)
        LOG.info("network attachment definitions to cleanup: %r", cleanup_nads)
        LOG.info("ippools to cleanup: %r", cleanup_ippools)

        if cleanup_deployment_pods:
            LOG.fixture_step("Clean-up Deployments")
            for deployment_pod in cleanup_deployment_pods:
                if "sriov" in deployment_pod:
                    LOG.fixture_step("Delete {} Deployment".format(deployment_pod), depth=1)
                    kube_helper.delete_resources(
                        resource_names=deployment_pod,
                        resource_types="deployment",
                        namespace='default',
                        check_both_controllers=False,
                        fail_ok=True,
                    )

        if cleanup_daemon_sets:
            LOG.fixture_step("Clean-up DaemonSets")
            for daemon_set in cleanup_daemon_sets:
                if 'sriov' in daemon_set:
                    LOG.fixture_step("Try to delete {} DaemonSet".format(daemon_set), depth=1)
                    kube_helper.delete_resources(
                        resource_names=daemon_set,
                        resource_types="daemonset",
                        namespace='default',
                        check_both_controllers=False,
                        fail_ok=True,
                    )

        if cleanup_default_pods:
            LOG.fixture_step("Clean-up PODs")
            for pod in cleanup_default_pods:
                if 'sriov' in pod:
                    LOG.fixture_step("Try to delete {} pod".format(pod), depth=1)
                    kube_helper.delete_resources(
                        resource_names=pod,
                        namespace='default',
                        check_both_controllers=False,
                        fail_ok=True,
                    )

        if cleanup_nads:
            LOG.fixture_step("Clean-up Network Attachment Definition")
            for netdef in cleanup_nads:
                if 'sriov' in netdef:
                    LOG.fixture_step(
                        "Try to delete {} network attachment definition".format(netdef), depth=1
                    )
                    kube_helper.delete_resources(
                        resource_names=netdef,
                        resource_types='net-attach-def',
                        fail_ok=True,
                        namespace='default',
                    )

        if cleanup_ippools:
            LOG.fixture_step("Clean-up Calico IP POOLs")
            for ippool in cleanup_ippools:
                LOG.fixture_step("Try to delete calico IP pool {}".format(ippool), depth=1)
                cmd = 'calicoctl delete ippool {}'.format(ippool)
                kube_helper.exec_cmd_in_container(
                    cmd,
                    pod=CALICOCTL_PODNAME,
                    stdin=True,
                    tty=True,
                    fail_ok=True,
                    namespace='kube-system',
                )

        if cleanup_system_pods:
            LOG.fixture_step("Clean-up system PODs")
            for pod in cleanup_system_pods:
                LOG.fixture_step("Try to delete pod {}".format(CALICOCTL_PODNAME), depth=1)
                kube_helper.delete_resources(
                    resource_names=pod,
                    namespace='kube-system',
                    check_both_controllers=False,
                    fail_ok=True,
                )

    request.addfinalizer(revert_resources)
    return init_d_pods, init_s_pods, init_nads, init_ippools, init_daemon_sets


def create_sriov_pods(
    hosts, netdefs, pod_type, ip_version=IPV4_VERSION, user_podname=None, default_ipv6_pool=True
):
    """
    Create pods on each specified host
    Args:
        hosts (list): The list of hosts to create pods on
        netdefs (list): The list of network attachment definitions
        pod_type (str): The type of pod to create (netdevice / DPDK)
        ip_version (int): The IP version of the pod's default network
        user_podname (dict): Dictionary of name of pod on each host
        default_ipv6_pool (bool): use default-ipv6-pool or not

    Returns pods (list): A list of created pods:
                         ([{name: podname, ip: ipinfo},..])
    """
    # testname is the calling function
    testname = inspect.currentframe().f_back.f_code.co_name

    pods = []
    for idx, host in enumerate(hosts):
        if user_podname is None:
            podname = '{}-{}'.format(testname.lower().replace("_", "-"), idx)
        else:
            podname = user_podname[host]

        if pod_type == POD_TYPE_NETDEVICE:
            filename = create_netdevice_pod(
                podname,
                netdefs,
                host=host,
                ip_version=ip_version,
                default_ipv6_pool=default_ipv6_pool,
            )
        else:
            filename = create_dpdk_pod(
                podname,
                netdefs,
                host=host,
                ip_version=ip_version,
                default_ipv6_pool=default_ipv6_pool,
            )

        LOG.tc_minor_step("Try to create pod {} on host {}".format(podname, host))

        kube_helper.apply_pod(file_path=filename, pod_name=podname, check_both_controllers=False)

        # Retrieve and store IP address information
        if pod_type == POD_TYPE_NETDEVICE:
            ipinfo = get_ipaddrs(podname, ip_version=ip_version)
        else:
            ipinfo = []
        pods.append({'name': podname, 'ip': ipinfo})
    return pods


def check_system_compatibility(
    num_hosts, pods_per_host, num_vfs, ifclass, pod_type, sriov_config, datanetwork_capacity
):
    """
    Based on the system's SR-IOV interface and datanetwork configuration,
    get a datanetwork and list of hosts that satisfies the requirements
    on the number of VFs, interface class, and pod type (netdevice / DPDK)
    Args:
        num_vfs (int): The number VFs the datanetwork should support
        num_hosts (int): The number of hosts supporting the datanetwork
        ifclass (str): The interface class (pci-sriov / pci-passthrough)
        pod_type (str): The pod type (netdevice / DPDK)
        sriov_config (dict): The system's SR-IOV inteface configuration
        datanetwork_capacity (dict): The system's SR-IOV device plugin
                                     datanetwork capacity

    Returns (tuple):
            (datanetwork (str), hosts (list))
    """
    # Find the full set of datanetworks configured on all hosts
    hosts = [x['host'] for x in sriov_config]
    datanetworks = []
    for host in hosts:
        datanetworks += datanetwork_capacity[host]
    datanetworks = set(datanetworks)

    # Find compatible datanetworks across all hosts that satisfy the number
    # of VFs, ifclass, and VF driver requested
    compatible_datanetworks = {}
    for config in sriov_config:
        host = config['host']
        interfaces = config['interfaces']
        compatible_datanetworks[host] = []
        for interface in interfaces:
            if interface['class'] != ifclass:
                continue
            if pod_type == POD_TYPE_DPDK:
                if interface['is_mellanox']:
                    if interface['vf_driver'] in VF_DRIVER_VFIOS:
                        continue
                else:
                    if interface['vf_driver'] in VF_DRIVER_NETDEVICES:
                        continue
            elif pod_type == POD_TYPE_NETDEVICE:
                if interface['vf_driver'] in VF_DRIVER_VFIOS:
                    continue

            for datanetwork in interface['datanetworks']:
                datanetwork = sriov_helper.normalize_datanetwork_name(datanetwork)
                if datanetwork_capacity[host].get('datanetwork', False):
                    capacity = datanetwork_capacity[host][datanetwork]
                else:
                    capacity = 0
                if capacity >= num_vfs * pods_per_host:
                    compatible_datanetworks[host].append(datanetwork)

    # For every compatible datanetwork, create a list of hosts that are
    # configured for this datanetwork
    compatible_hosts = {}
    for datanetwork in datanetworks:
        compatible_hosts.update({datanetwork: []})
        for host in compatible_datanetworks.keys():
            if datanetwork in compatible_datanetworks[host]:
                if pod_type == POD_TYPE_DPDK:
                    mempages_1g = host_helper.get_host_memories(host, headers=('app_hp_total_1G',))
                    mem = 0
                    for proc in mempages_1g:
                        mem += mempages_1g[proc][0]
                    if mem < DPDK_HUGEPAGE_REQD * pods_per_host:
                        continue
                compatible_hosts[datanetwork].append(host)

    # Pick the first datanetwork that satisfies the number of nics and number
    # of host requirements
    for datanetwork in compatible_hosts.keys():
        hosts = compatible_hosts[datanetwork]
        if len(hosts) >= num_hosts:
            return datanetwork, compatible_hosts[datanetwork]

    return None, None


def get_ipaddrs(podname, interface=None, ip_version=IPV4_VERSION):
    """
    Get the IP address info for SR-IOV interfaces in a pod
    Args:
        podname (str): The name of the pod to check
        interface (str): The name of the interface to check
        ip_version (int): The IP version of address on the SR-IOV interfaces

    Returns iplist (list): A list of SR-IOV interface IP address information
    """
    iplist = []
    if ip_version == IPV4_VERSION:
        cmd = 'ip -o -br addr list '
    elif ip_version == IPV6_VERSION:
        cmd = 'ip -6 -o -br addr list '
    if interface:
        cmd += 'dev {}'.format(interface)

    code, output = kube_helper.exec_cmd_in_container(cmd, pod=podname, namespace='default')

    for line in output.splitlines():
        info = line.split()

        if len(info) >= 3:
            interface = info[0]
            if 'net' not in interface:
                # Additional SR-IOV interfaces in a pod are named with net[N]
                continue

            ip, prefix = info[2].split('/', 1)
            ipinfo = {'name': interface, 'ip': ip, 'prefix': prefix}
            iplist.append(ipinfo)

    return iplist


@mark.container_platform
class TestSriovDpdk:
    @fixture(scope='class')
    def prepare_tests(self, request):
        """
        Discover the SR-IOV interface configuration of the system and
        ensure that the appropriate labels are applied.
        Args:
            request: The fixture request

        Returns (list): A list of SR-IOV config dictionaries:
                        [{host: (str), interfaces: (list)}..]
        """
        host_initial_labels = dict()
        new_hosts_labels = dict()
        kube_labels = {
            KUBE_CPU_MGR_POLICY_LABEL: 'static',
            KUBE_TOPOLOGY_MGR_POLICY_LABEL: 'restricted',
        }

        sriov_configs = sriov_helper.get_sriov_config()
        if not sriov_configs:
            skip('no capable SR-IOV interfaces')

        LOG.fixture_step("Getting Initial Labels on hosts")
        # Get Initial labels on each host, to be used later to recover the labels
        for config in sriov_configs:
            host = config['host']
            LOG.fixture_step("Getting Initial Labels on host: {}".format(host), depth=1)
            host_initial_labels[host] = host_helper.get_host_labels_info(host)
            new_hosts_labels[host] = kube_labels

        LOG.fixture_step("Add host's labels: {}".format(new_hosts_labels))
        Host.assign_host_labels(new_hosts_labels, overwrite=True)

        def revert_tests():
            """Restore the labels."""

            remove_host_labels, add_back_host_labels = Host.get_host_labels_to_recover(
                host_initial_labels, new_hosts_labels
            )

            LOG.fixture_step("Remove host's labels: {}".format(remove_host_labels))
            Host.remove_host_labels(remove_host_labels)
            if add_back_host_labels:
                LOG.fixture_step("Add host's labels back: {}".format(add_back_host_labels))
                Host.assign_host_labels(add_back_host_labels, overwrite=True)

        request.addfinalizer(revert_tests)
        return sriov_configs

    @mark.dc_sriov
    @mark.parametrize(
        'vfs',
        [
            param(1, marks=[mark.patch_testing, mark.p2]),
            param(2, marks=[mark.p2]),
            param('max', marks=[mark.p2]),
        ],
    )
    def test_sriovdp_dpdk_single_pod(
        self,
        vfs,
        prepare_host,
        sriov_node_capacity,
        pull_and_push_external_to_local,
        prepare_resources,
        prepare_tests,
    ):
        """
        Test creation of a pod with DPDK SR-IOV interfaces
        Args:
            vfs (int): Number VFs to give to a pod
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
            prepare_tests: class fixture

        Setups:
            - Set Labels KUBE_CPU_MGR_POLICY_LABEL and KUBE_TOPOLOGY_MGR_POLICY_LABEL
              to compute nodes
            - Find a datanetwork to use for SR-IOV VFs

        Test Steps:
            - Create a network attachment definition for the SR-IOV VFs
            - Create a pod with SR-IOV DPDK devices on each host
            - Verify the number of VFs (PCI devices) in the pod
            - Delete the pods
            - Delete the network attachment definition

        TearDown:
            - Revert labels on configured hosts

        """
        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        num_hosts = 1
        pods_per_host = 1
        pods = []
        netdefs = []

        ip_version = IPV6_VERSION if ProjVar.get_var('IPV6_OAM') else IPV4_VERSION

        vfs = (
            vfs
            if vfs != 'max'
            else SRIOV.get_max_num_vfs(datanetwork_capacity, sriov_config, POD_TYPE_DPDK)
        )
        LOG.info("Number of vfs are going to be used is {}".format(vfs))

        LOG.tc_step(
            "Try to find data-network and hosts with capacity vfs: {} for pod type: {}".format(
                vfs, POD_TYPE_DPDK
            )
        )
        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_DPDK,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork:
            skip(
                'no data network exists with capacity for {} SR-IOV {} VFs'.format(
                    vfs, POD_TYPE_DPDK
                )
            )

        if not hosts:
            skip(
                'no host exists with capacity for {} SR-IOV {} VFs and {} 1G hugpages'.format(
                    vfs, POD_TYPE_DPDK, DPDK_HUGEPAGE_REQD
                )
            )
        LOG.info(
            "Data-Networks: {} and hosts: {} have capacity SRI-IOV vfs: {} for pod type {}".format(
                datanetwork, hosts, vfs, POD_TYPE_DPDK
            )
        )

        if num_hosts < len(hosts):
            LOG.info(
                "Hosts: {} are capable of creating pod with vfs: {}, and "
                "host {} is selected to have pod".format(hosts, vfs, hosts[-num_hosts:])
            )
            hosts = hosts[-num_hosts:]

        LOG.tc_step(
            "Try to create Network Attachment Definitions on hosts: {} "
            "for SR-IOV vfs: {} using Data Networks: {}".format(hosts, vfs, datanetwork)
        )
        # Create network attachment definitions with SR-IOV as the CNI type
        netdefs = create_network_attachment_definitions(hosts, vfs, datanetwork)

        LOG.tc_step(
            "Try to create pod {} with vfs: {} on host: {}".format(POD_TYPE_DPDK, vfs, hosts)
        )
        # Create pods that use the network attachment definitions
        pods = create_sriov_pods(hosts, netdefs, pod_type=POD_TYPE_DPDK, ip_version=ip_version)

        LOG.tc_step("Verify the number of SR-IOV interfaces in pods {}".format(pods))
        # Verify the number of SR-IOV interfaces in the pod
        for pod in pods:
            LOG.tc_minor_step(
                "Verify the number of SR-IOV interfaces in pod {} to be {}".format(pod["name"], vfs)
            )
            podname = pod['name']
            devices = sriov_helper.get_pod_pci_device_info(podname)
            dpdk_devices = []
            for device in devices:
                for driver in ['vfio', 'mlx']:
                    if driver in device['driver']:
                        dpdk_devices.append(device)

            assert len(devices) == vfs
            assert len(dpdk_devices) == vfs

        with host_helper.ssh_to_host(hosts[0]) as host_ssh:
            LOG.tc_step("Verify spoof to be off and trust is on")
            cmd = "ip link | grep 'spoof checking off, link-state auto, trust on'"
            _, output = host_ssh.exec_cmd(cmd)
            assert (
                len(output.splitlines()) == vfs
            ), "Expected to see {} vfs with spoof checking off, link-state auto, trust on".format(
                vfs
            )

    @mark.dc_sriov
    @mark.lab_sriov
    @mark.parametrize(
        ('num_hosts', 'num_vfs'),
        [
            param(1, 1, marks=[mark.patch_testing, mark.p1]),
            param(1, 2, marks=[mark.patch_testing, mark.p1]),
            param(2, 1, marks=[mark.p1]),
            param(2, 2, marks=[mark.p1]),
        ],
    )
    def test_sriovdp_dpdk_connectivity(
        self,
        prepare_host,
        num_hosts,
        num_vfs,
        sriov_node_capacity,
        pull_and_push_external_to_local,
        prepare_resources,
        prepare_tests,
    ):
        """
        Test connectivity between SR-IOV interfaces in a pod with DPDK

        Args:
            prepare_host: module fixture
            num_hosts: the number of hosts to place pods on
            num_vfs: the number of VFs to test in each pod
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
            prepare_tests: class fixture

        Setups:
            - Set Labels KUBE_CPU_MGR_POLICY_LABEL and KUBE_TOPOLOGY_MGR_POLICY_LABEL
                  to compute nodes
            - Find a datanetwork to use for SR-IOV VFs

        Test Steps:
            - Create network attachment definitions for the SR-IOV VFs
            - Create sending and receiving pods with SR-IOV DPDK devices
            - Verify the number of VFs (PCI devices) in the pod
            - Run traffic between the sending pod and all receiving pods
            - Collect and verify the traffic statistics
            - Delete the pods
            - Delete the network attachment definitions

        TearDown:
            - Revert labels on configured hosts
        """

        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        pods_per_host = 2 if num_hosts == 1 else 1

        vfs = num_vfs
        pods = []

        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_DPDK,
            sriov_config,
            datanetwork_capacity,
        )
        if not datanetwork:
            skip('no data network exists with capacity for {} SR-IOV vfio VFs'.format(vfs))

        if not hosts:
            skip(
                'no host exists with capacity for {} SR-IOV vfio VFs and {} 1G hugpages'.format(
                    vfs, DPDK_HUGEPAGE_REQD
                )
            )

        if num_hosts == 1:
            # Ensure the two connectivity pods are created on the same host
            hosts = [hosts[0], hosts[0]]
        elif num_hosts < len(hosts):
            hosts = hosts[-num_hosts:]

        # Create the network attachment definition spec(s) for the receiver(s)
        rx_netdefs = []
        for host_idx, host in enumerate(hosts[1:]):
            netdefs = []
            for vf in range(1, num_vfs + 1):
                nadname = 'test-sriovdp-connectivity-rx-vf{}'.format(vf)
                rx_mac = 'fa:6e:b4:01:{:02X}:{:02X}'.format(host_idx + 1, vf)
                filename = sriov_helper.create_network_attachment_definition(
                    nadname, datanetwork, mac=rx_mac, spoofchk="off", trust="on"
                )
                netdefs.append(
                    {
                        'name': nadname,
                        'datanetwork': datanetwork,
                        'filename': filename,
                        'vfs': 1,
                        'host': host,
                        'mac': rx_mac,
                    }
                )

            # Create the pod spec for the receiver
            podname = 'test-sriovdp-connectivity-rx'
            filename = create_dpdk_pod(podname, netdefs, host=hosts[1])
            pods.append(
                {
                    'podname': podname,
                    'filename': filename,
                    'host': host,
                    'netdefs': netdefs,
                    'type': 'rx',
                }
            )
            rx_netdefs += netdefs

        # Create the network attachment definition spec for the sender
        tx_netdefs = []
        for vf in range(1, num_vfs + 1):
            nadname = 'test-sriovdp-connectivity-tx-vf{}'.format(vf)
            tx_mac = 'fa:6e:b4:02:01:{:02X}'.format(vf)
            filename = sriov_helper.create_network_attachment_definition(
                nadname, datanetwork, mac=tx_mac, spoofchk="off", trust="on"
            )
            tx_netdefs.append(
                {
                    'name': nadname,
                    'datanetwork': datanetwork,
                    'filename': filename,
                    'vfs': 1,
                    'host': hosts[0],
                    'mac': tx_mac,
                }
            )

        # Create the pod spec for the sender
        podname = 'test-sriovdp-connectivity-tx'
        filename = create_dpdk_pod(podname, tx_netdefs, host=hosts[0])
        tx_pod = {
            'podname': podname,
            'filename': filename,
            'host': hosts[0],
            'netdefs': tx_netdefs,
            'type': 'tx',
        }
        pods.append(tx_pod)

        # Create the network attachment definitions
        netdefs = tx_netdefs + rx_netdefs
        for netdef in netdefs:
            LOG.tc_step("Try to create network attachment definition {}".format(netdef['name']))
            kube_helper.apply_resource(netdef['filename'])

        # Create the pods and verify the number of SR-IOV interfaces
        for pod in pods:
            LOG.tc_step("Try to create pod {} on host {}".format(pod['podname'], pod['host']))
            kube_helper.apply_pod(
                file_path=pod['filename'], pod_name=pod['podname'], check_both_controllers=False
            )

            devices = sriov_helper.get_pod_pci_device_info(pod['podname'])
            assert len(devices) == sum(map(lambda x: x['vfs'], pod['netdefs']))

            cpus = PodCpu.get_pod_cpus(pod['podname'])
            assert len(cpus) == DPDK_POD_CPUS_REQD

        # Run testpmd from the sender to all of the receivers
        # and collect stats
        for pod in pods:
            if pod['type'] == 'tx':
                continue
            rx_pod = pod

            rx_cpus = PodCpu.get_pod_cpus(rx_pod['podname'])
            peerlist = [tx['mac'] for tx in tx_pod['netdefs']]
            rx_devices = sriov_helper.get_pod_pci_device_info(rx_pod['podname'])
            TestPmd.start_testpmd(rx_pod['podname'], rx_cpus, rx_devices, peerlist)
            code, output = TestPmd.verify_testpmd(rx_pod['podname'])
            assert code == 0

            tx_cpus = PodCpu.get_pod_cpus(tx_pod['podname'])
            peerlist = [rx['mac'] for rx in rx_pod['netdefs']]
            tx_devices = sriov_helper.get_pod_pci_device_info(tx_pod['podname'])
            TestPmd.start_testpmd(tx_pod['podname'], tx_cpus, tx_devices, peerlist, mode='txonly')
            code, output = TestPmd.verify_testpmd(tx_pod['podname'])
            assert code == 0

            LOG.tc_step("Pausing 60 seconds to run traffic and collect stats")
            time.sleep(60)

            TestPmd.stop_testpmd(tx_pod['podname'])
            TestPmd.stop_testpmd(rx_pod['podname'])

            rx_stats = TestPmd.collect_testpmd_stat(rx_pod['podname'], statid='RX-packets')
            tx_stats = TestPmd.collect_testpmd_stat(tx_pod['podname'], statid='TX-packets')

            LOG.info("Port rx stats: %r", rx_stats)
            LOG.info("Port tx stats: %r", tx_stats)

            # Do not try to match exactly the sent / received stats.
            #
            # This test is really just ensuring that a DPDK application in a
            # pod is able to launch and send / receive traffic, rather than
            # testing the DPDK application itself.
            #
            # There can be several reasons for the received stats to
            # not exactly match the sent stats:
            #
            # - testpmd outputs stats to a file at intervals, but the sender
            #   / receiver are started at different times
            #
            # - In a multi-vf test, the single polling core may have to service
            #   multiple ports with the sender transmitting as fast as
            #   possible.
            #
            # - The tests typically use VFs from a single NIC, with the
            #   sender trying to blast traffic as fast as possible on each NIC.
            #
            # Assert that we have a reasonable amount of traffic successfully
            # sent / received and that it cannot be a result of random traffic
            # on the network.
            if len(rx_stats) != num_vfs:
                fail('Failed to get testpmd receive stats for all ports')
            if len(tx_stats) != num_vfs:
                fail('Failed to get testpmd transmit stats for all ports')
            for stat in rx_stats.keys():
                assert rx_stats[stat] > 10000
            for stat in tx_stats.keys():
                assert tx_stats[stat] > 10000


@mark.container_platform
class TestSriovNetdevice:
    @mark.parametrize(
        ('vfs', 'num_lock_unlock_reboot', 'lock_reboot'),
        [
            (
                param(
                    1,
                    1,
                    "lock/unlock",
                    marks=mark.priorities('platform_nightly', 'dc_sriov', 'p2'),
                )
            ),
            param('max', 1, "lock/unlock", marks=mark.priorities('p2')),
            param(1, 1, "reboot", marks=mark.priorities('dc_sriov', 'p2')),
            param('max', 1, "reboot", marks=mark.priorities('p2')),
        ],
    )
    def test_sriovdp_netdev_single_pod(
        self,
        vfs,
        num_lock_unlock_reboot,
        lock_reboot,
        prepare_host,
        sriov_node_capacity,
        prepare_resources,
        pull_and_push_external_to_local,
    ):
        """
        Test creation of a pod with netdevice SR-IOV interfaces
        Args:
            vfs (int): Number VFs to give to a pod
            num_lock_unlock_reboot (int): Number of times to lock/unlock host
            lock_reboot (str): Do lock/unlock or reboot the host
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
            pull_and_push_external_to_local: function fixture
        Setups:
            - Find a datanetwork to use for SR-IOV VFs

        Test Steps:
            - Create a network attachment definition for the SR-IOV VFs
            - Create a pod with SR-IOV netdevice NICs on each host
            - If restart-on-reboot is True
                - Lock/unlock host
            - Verify if pod is in Running State
            - if restart-on-reboot is True
                - Verify if DiemonSet has expected values
            - Verify the number of VFs (NICs) in the pod
            - Delete the pods
            - Delete the network attachment definition

        """
        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        num_hosts = 1
        pods_per_host = 1
        ipam_type = 'calico-ipam'
        pods = []
        netdefs = []

        if ProjVar.get_var('IPV6_OAM'):
            ip_version = IPV6_VERSION
        else:
            ip_version = IPV4_VERSION

        vfs = (
            vfs
            if vfs != 'max'
            else SRIOV.get_max_num_vfs(datanetwork_capacity, sriov_config, POD_TYPE_NETDEVICE)
        )
        LOG.info("Number of vfs are going to be used is {}".format(vfs))

        LOG.tc_step(
            "Try to find data-network and hosts with capacity vfs: {} for pod type: {}".format(
                vfs, POD_TYPE_NETDEVICE
            )
        )
        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_NETDEVICE,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork:
            skip('no data network exists with capacity for {} SR-IOV netdevice VFs'.format(vfs))

        if not hosts:
            skip('no host exists with capacity for {} SR-IOV netdevice VFs'.format(vfs))
        LOG.info(
            "Data-Networks: {} and hosts: {} have capacity SRI-IOV vfs: {} for pod type {}".format(
                datanetwork, hosts, vfs, POD_TYPE_NETDEVICE
            )
        )

        if num_hosts < len(hosts):
            LOG.info(
                "Hosts: {} are capable of creating pod with vfs: {} and, "
                "host {} is selected to have pod".format(hosts, vfs, hosts[-num_hosts:])
            )
            hosts = hosts[-num_hosts:]

        LOG.tc_step(
            "Try to create Network Attachment Definitions on hosts: {} "
            "for SR-IOV vfs: {} using Data Networks: {}".format(hosts, vfs, datanetwork)
        )

        if ipam_type == 'calico-ipam' and ip_version == IPV6_VERSION:
            # Launch a pod with the calicoctl application so that separate
            # IP pools can be created
            create_calicoctl_pod(CALICOCTL_PODNAME)
            ippools = create_calico_ippools(datanetwork, vfs, ip_version)
            if len(ippools) != vfs:
                raise exceptions.SriovdpError(
                    "Unexpected number of IP pools: {}. Expected: {}".format(len(ippools), vfs)
                )

        # Create network attachment definitions with SR-IOV as the CNI type
        if ip_version == IPV6_VERSION:
            netdefs = create_network_attachment_definitions(
                hosts, vfs, datanetwork, ipam_type=ipam_type, ip_version=ip_version
            )
        else:
            netdefs = create_network_attachment_definitions(
                hosts, vfs, datanetwork, user_ipam_config={"\"type\"": "\"{}\"".format(ipam_type)}
            )

        LOG.tc_step("Try to create DaemonSet with pod template with netdevice as vfio driver")
        daemonset_name, pods = SRIOV.create_sriov_daemonset(
            host=hosts[0], net_defs=netdefs, ip_version=ip_version
        )
        daemonset_fields = ['NAME', 'DESIRED', 'READY', 'AVAILABLE', 'NODE SELECTOR']
        expected_daemonset_values = [
            (daemonset_name, '1', '1', '1', "kubernetes.io/hostname={}".format(hosts[0]))
        ]
        LOG.tc_step(
            "Verify DaemonSet {} with expected values {} for fields {}".format(
                daemonset_name, expected_daemonset_values, daemonset_fields
            )
        )
        daemon_set_status, actual_daemonset_values = SRIOV.verify_daemonset_status(
            daemonset_name, expected_daemonset_values, fields=daemonset_fields
        )
        assert daemon_set_status, "DaemonSet {} did not reach status {} for fields {}".format(
            daemonset_name, expected_daemonset_values, daemonset_fields
        )

        for lock_unlock_reboot_iteration in range(0, num_lock_unlock_reboot + 1):
            LOG.tc_step("Verify SRIOV's interfaces allocated in pods")
            for pod in pods:
                pod_sriov_interfaces_verification_error = list()

                pod_name = pod["name"]
                LOG.tc_minor_step(
                    "Verify the SRIOV interface information in pod {} "
                    "and its state to be UP".format(pod_name)
                )
                pod_sriov_interfaces = sriov_helper.get_pod_interfaces(pod_name, filter_name="net")
                LOG.info(
                    "interface(s) {} (is/are) allocated to pod {}".format(
                        list(pod_sriov_interfaces.keys()), pod_name
                    )
                )
                for (
                    pod_sriov_interface_name,
                    pod_sriov_interface_info,
                ) in pod_sriov_interfaces.items():
                    pod_sriov_interface_state = pod_sriov_interface_info["state"]
                    if pod_sriov_interface_state != "UP":
                        LOG.error(
                            "Interface {} in pod is {} which is not expected as UP".format(
                                pod_sriov_interface_name, pod_sriov_interface_state
                            )
                        )
                        pod_sriov_interfaces_verification_error.append(pod_sriov_interface_name)

                assert (
                    len(list(pod_sriov_interfaces.keys())) == vfs
                ), "Number of allocated SRIOV interfaces in pod {} is not {}!!!".format(
                    pod_name, vfs
                )

                assert (
                    pod_sriov_interfaces_verification_error == []
                ), "Interfaces {} are not UP!!!".format(pod_sriov_interfaces_verification_error)

            LOG.tc_step("Verify the number of SR-IOV interfaces in each pods")
            # Verify the number of SR-IOV interfaces in the pod
            for pod in pods:
                podname = pod['name']
                LOG.tc_minor_step(
                    "Verify the number of SR-IOV interfaces in pod {} to be {}".format(
                        pod["name"], vfs
                    )
                )
                devices = sriov_helper.get_pod_pci_device_info(podname)
                net_devices = []
                for device in devices:
                    if device['ifname'] is not None:
                        net_devices.append(device)

                assert len(devices) == vfs
                assert len(net_devices) == vfs

            if lock_unlock_reboot_iteration != num_lock_unlock_reboot:
                LOG.tc_step(
                    "{} Host {}, iteration: {}".format(
                        lock_reboot, hosts[0], lock_unlock_reboot_iteration + 1
                    )
                )
                LOG.tc_minor_step("{} host {}".format(lock_reboot, hosts[0]))
                HostsToRecover.add(hosts[0])
                if lock_reboot == "reboot":
                    host_helper.reboot_hosts(hosts[0])
                else:
                    host_helper.lock_host(hosts[0], swact=True)
                    LOG.info("Sleep for 30 sec before unlock the host")
                    time.sleep(30)
                    host_helper.unlock_host(hosts[0])
                HostsToRecover.remove(hosts[0])

                LOG.tc_minor_step(
                    "Check status of POD {} after {} host {}".format(
                        lock_reboot, daemonset_name, hosts[0]
                    )
                )

                # After reboot or lock/unlock the pod name will be changed,
                # so here we are getting the correct names
                pods = list()
                _, actual_status = kube_helper.wait_for_pods_status(partial_names=daemonset_name)

                for actual_pod_name, actual_pod_status in actual_status.items():
                    LOG.info(
                        "Checking POD {} with status {} if it is in {}".format(
                            actual_pod_name, actual_pod_status, PodStatus.RUNNING
                        )
                    )
                    if actual_pod_status == PodStatus.RUNNING:
                        ipinfo = get_ipaddrs(actual_pod_name)

                        pods.append({'name': actual_pod_name, 'ip': ipinfo})

    @mark.dc_sriov
    @mark.lab_sriov
    @mark.lab_ipv4
    @mark.parametrize(
        ('num_hosts', 'vfs', 'ipam_type'),
        [
            param(1, 1, 'calico-ipam', marks=[mark.p1, mark.platform_nightly]),
            param(2, 1, 'calico-ipam', marks=[mark.p1]),
            param(2, 2, 'calico-ipam', marks=[mark.p1]),
            param(1, 1, 'host-local', marks=[mark.p1]),
            param(2, 1, 'host-local', marks=[mark.p1]),
            param(2, 2, 'host-local', marks=[mark.p1]),
            param(1, 1, 'dhcp', marks=[mark.p1]),
            param(2, 1, 'dhcp', marks=[mark.p1]),
        ],
    )
    def test_sriovdp_netdev_connectivity_ipv4(
        self,
        num_hosts,
        vfs,
        ipam_type,
        prepare_host,
        sriov_node_capacity,
        prepare_resources,
        pull_and_push_external_to_local,
    ):
        """
        Test connectivity between SR-IOV interfaces in a pod
        Args:
            num_hosts (int): Number of different hosts to test on
            vfs (int): Number of VFs per pod to test
            ipam_type (str): The IPAM type to test
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
            pull_and_push_external_to_local: function fixture
        Setups:
            - Find a datanetwork to use for SR-IOV VFs

        Test Steps:
            - Create a network attachment definition for the SR-IOV VFs
            - Create a pod with SR-IOV netdevice NICs on each host
            - Send ICMP traffic from the first pod to the other pods over
                  the SR-IOV interface(s)
            - Delete the pods
            - Delete the network attachment definition

        """
        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        default_ipv6_pool = True

        hosts = [x['host'] for x in sriov_config]
        if len(hosts) < num_hosts:
            skip(
                'not enough hosts with SR-IOV interfaces to test '
                'connectivity between {} hosts'.format(num_hosts)
            )

        ipv6_test = ProjVar.get_var('IPV6_OAM')
        if ipv6_test:
            skip('This test can only be run on IPv4')

        if num_hosts == 1:
            pods_per_host = 2
        else:
            pods_per_host = 1

        num_vfs = vfs
        if ipam_type == 'dhcp':
            # The DHCP server needs to run in SR-IOV enabled pod
            # on the same datanetwork as the connectivity pods.
            num_vfs += 1

        # Find an existing SR-IOV enabled data network that can accommodate
        # the virtual function and host requirements
        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            num_vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_NETDEVICE,
            sriov_config,
            datanetwork_capacity,
        )
        if not datanetwork:
            skip('no data network exists with capacity for {} SR-IOV netdevice VFs'.format(num_vfs))

        if ipam_type == 'calico-ipam':
            # Launch a pod with the calicoctl application so that separate
            # IP pools can be created
            create_calicoctl_pod(CALICOCTL_PODNAME)
            ippools = create_calico_ippools(datanetwork, vfs, IPV4_VERSION)

            if len(ippools) != vfs:
                raise exceptions.SriovdpError(
                    "Unexpected number of IP pools: {}. Expected: {}".format(len(ippools), vfs)
                )

        if ipam_type == 'dhcp':
            cidr = get_sriov_network(0, IPV4_VERSION)
            create_dhcp_pod('dhcp-sriov', datanetwork, cidr)
            stop_dhcp_daemons(hosts)
            start_dhcp_daemons(hosts)

        if num_hosts == 1:
            # Ensure the two connectivity pods are created on the same host
            hosts = [hosts[0], hosts[0]]
        elif num_hosts < len(hosts):
            hosts = hosts[-num_hosts:]

        LOG.tc_step(
            "Try to create Network Attachment Definitions on hosts: {} "
            "for SR-IOV vfs: {} using Data Networks: {}".format(hosts, vfs, datanetwork)
        )
        # Create network attachment definitions with SR-IOV as the CNI type
        netdefs = create_network_attachment_definitions(
            hosts, vfs, datanetwork, ipam_type=ipam_type, ip_version=IPV4_VERSION
        )

        LOG.tc_step(
            "Try to create pod {} with vfs: {} on host: {}".format(POD_TYPE_NETDEVICE, vfs, hosts)
        )

        # Create pods that use the network attachment definition
        pods = create_sriov_pods(
            hosts,
            netdefs,
            pod_type=POD_TYPE_NETDEVICE,
            ip_version=IPV4_VERSION,
            default_ipv6_pool=default_ipv6_pool,
        )

        # Verify the number of SR-IOV interfaces in each pod
        for pod in pods:
            podname = pod['name']
            devices = sriov_helper.get_pod_pci_device_info(podname)
            net_devices = []
            for device in devices:
                if device['ifname'] is not None:
                    net_devices.append(device)

            assert len(devices) == vfs
            assert len(net_devices) == vfs

        # Attempt ICMP traffic between the first pod and all other pods
        for idx, pod in enumerate(pods):
            for interface in pod['ip']:
                if ipam_type == 'calico-ipam':
                    # Until multus can support adding routes, we need to
                    # explicitly add one for the SR-IOV interfaces, as the
                    # IP prefix given by calico-ipam is /32
                    prefix = '24'
                    cidr = ipaddress.ip_network(
                        '{}/{}'.format(interface['ip'], prefix), strict=False
                    )

                    LOG.tc_step(
                        "Try to create a route to {} via {} in pod {}".format(
                            cidr, interface['name'], pod['name']
                        )
                    )
                    cmd = 'ip route add {} dev {}'.format(cidr, interface['name'])

                    kube_helper.exec_cmd_in_container(cmd, pod=pod['name'], namespace='default')
                if idx == 0:
                    continue

                ipaddr = interface['ip']

                LOG.tc_step("Try to send ICMP to {} from pod {}".format(ipaddr, pods[0]['name']))
                cmd = 'ping -c 3 {}'.format(ipaddr)

                kube_helper.exec_cmd_in_container(cmd, pod=pods[0]['name'], namespace='default')

        if ipam_type == 'dhcp':
            stop_dhcp_daemons(hosts)

    @mark.dc_sriov
    @mark.lab_sriov
    @mark.lab_ipv6
    @mark.parametrize(
        ('num_hosts', 'vfs', 'ipam_type'),
        [
            param(1, 1, 'calico-ipam', marks=[mark.p1, mark.patch_testing, mark.platform_nightly]),
            param(2, 1, 'calico-ipam', marks=[mark.p1]),
            param(2, 2, 'calico-ipam', marks=[mark.p1]),
            param(1, 1, 'host-local', marks=[mark.p1, mark.patch_testing]),
            param(2, 1, 'host-local', marks=[mark.p1]),
            param(2, 2, 'host-local', marks=[mark.p1]),
        ],
    )
    def test_sriovdp_netdev_connectivity_ipv6(
        self,
        num_hosts,
        vfs,
        ipam_type,
        prepare_host,
        sriov_node_capacity,
        prepare_resources,
        pull_and_push_external_to_local,
    ):
        """
        Test connectivity between SR-IOV interfaces in a pod
        Args:
            num_hosts (int): Number of different hosts to test on
            vfs (int): Number of VFs per pod to test
            ipam_type (str): The IPAM type to test
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
            pull_and_push_external_to_local: function fixture
        Setups:
            - Find a datanetwork to use for SR-IOV VFs

        Test Steps:
            - Create a network attachment definition for the SR-IOV VFs
            - Create a pod with SR-IOV netdevice NICs on each host
            - Send ICMP traffic from the first pod to the other pods over
                  the SR-IOV interface(s)
            - Delete the pods
            - Delete the network attachment definition

        """
        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        default_ipv6_pool = True

        hosts = [x['host'] for x in sriov_config]
        if len(hosts) < num_hosts:
            skip(
                'not enough hosts with SR-IOV interfaces to test '
                'connectivity between {} hosts'.format(num_hosts)
            )

        ipv6_test = ProjVar.get_var('IPV6_OAM')
        if not ipv6_test:
            skip('This test must run on an IPv6 Lab')

        if num_hosts == 1:
            pods_per_host = 2
        else:
            pods_per_host = 1

        num_vfs = vfs

        # Find an existing SR-IOV enabled data network that can accommodate
        # the virtual function and host requirements
        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            num_vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_NETDEVICE,
            sriov_config,
            datanetwork_capacity,
        )
        if not datanetwork:
            skip('no data network exists with capacity for {} SR-IOV netdevice VFs'.format(num_vfs))

        if ipam_type == 'calico-ipam':
            # Launch a pod with the calicoctl application so that separate
            # IP pools can be created
            create_calicoctl_pod(CALICOCTL_PODNAME)
            ippools = create_calico_ippools(datanetwork, vfs, IPV6_VERSION)

            if len(ippools) != vfs:
                raise exceptions.SriovdpError(
                    "Unexpected number of IP pools: {}. Expected: {}".format(len(ippools), vfs)
                )

        if num_hosts == 1:
            # Ensure the two connectivity pods are created on the same host
            hosts = [hosts[0], hosts[0]]
        elif num_hosts < len(hosts):
            hosts = hosts[-num_hosts:]

        LOG.tc_step(
            "Try to create Network Attachment Definitions on hosts: {} "
            "for SR-IOV vfs: {} using Data Networks: {}".format(hosts, vfs, datanetwork)
        )
        # Create network attachment definitions with SR-IOV as the CNI type
        netdefs = create_network_attachment_definitions(
            hosts, vfs, datanetwork, ipam_type=ipam_type, ip_version=IPV6_VERSION
        )

        LOG.tc_step(
            "Try to create pod {} with vfs: {} on host: {}".format(POD_TYPE_NETDEVICE, vfs, hosts)
        )
        if ipam_type == "calico-ipam":
            default_ipv6_pool = False

        # Create pods that use the network attachment definition
        pods = create_sriov_pods(
            hosts,
            netdefs,
            pod_type=POD_TYPE_NETDEVICE,
            ip_version=IPV6_VERSION,
            default_ipv6_pool=default_ipv6_pool,
        )

        # Verify the number of SR-IOV interfaces in each pod
        for pod in pods:
            podname = pod['name']
            devices = sriov_helper.get_pod_pci_device_info(podname)
            net_devices = []
            for device in devices:
                if device['ifname'] is not None:
                    net_devices.append(device)

            assert len(devices) == vfs
            assert len(net_devices) == vfs

        # Attempt ICMP traffic between the first pod and all other pods
        for idx, pod in enumerate(pods):
            for interface in pod['ip']:
                if ipam_type == 'calico-ipam':
                    # Until multus can support adding routes, we need to
                    # explicitly add one for the SR-IOV interfaces, as the
                    # IP prefix given by calico-ipam is /32
                    prefix = '64'
                    cidr = ipaddress.ip_network(
                        '{}/{}'.format(interface['ip'], prefix), strict=False
                    )

                    LOG.tc_step(
                        "Try to create a route to {} via {} in pod {}".format(
                            cidr, interface['name'], pod['name']
                        )
                    )
                    cmd = 'ip route add {} dev {}'.format(cidr, interface['name'])

                    kube_helper.exec_cmd_in_container(cmd, pod=pod['name'], namespace='default')
                if idx == 0:
                    continue

                ipaddr = interface['ip']

                LOG.tc_step("Try to send ICMP to {} from pod {}".format(ipaddr, pods[0]['name']))
                cmd = 'ping6 -c 3 {}'.format(ipaddr)

                kube_helper.exec_cmd_in_container(cmd, pod=pods[0]['name'], namespace='default')

    @mark.p2
    @mark.patch_testing
    @mark.dc_sriov
    @mark.lab_ipv6
    @mark.lab_sriov
    def test_sriovdp_netdev_ipv6_single_pod(
        self, prepare_host, sriov_node_capacity, prepare_resources
    ):
        """
        Test to create an sriov pod with netdevice driver and ipv6

        Args:
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
        Setups:
            - Find datanetwork to use for netdevice SR-IOV VFs

        Test Steps:
            - Create a ipv6 network attachment definition for the SR-IOV VFs
            - Create a pod with SR-IOV netdevice NICs on host with ipv6 address
            - Verify if pod is in Running State
            - Verify the number of VFs (NICs) in the pod
        TearDown:
            - Delete Network Attachment definition
            - Delete POD
        """
        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        num_hosts = 1
        pods_per_host = 1
        vfs = 2
        ipam_type = "host-local"
        ip_version = IPV6_VERSION

        if not ProjVar.get_var('IPV6_OAM'):
            skip("The Lab is IPv4 and will not applied to this TestCase")

        LOG.tc_step(
            "Try to find data-network and hosts with capacity vfs: {} for pod type: {}".format(
                vfs, POD_TYPE_NETDEVICE
            )
        )
        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_NETDEVICE,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork:
            skip('no data network exists with capacity for {} SR-IOV netdevice VFs'.format(vfs))

        if not hosts:
            skip('no host exists with capacity for {} SR-IOV netdevice VFs'.format(vfs))
        LOG.info(
            "Data-Networks: {} and hosts: {} have capacity SRI-IOV vfs: {} for pod type {}".format(
                datanetwork, hosts, vfs, POD_TYPE_NETDEVICE
            )
        )

        if num_hosts < len(hosts):
            LOG.info(
                "Hosts: {} are capable of creating pod with vfs: {} and, "
                "host {} is selected to have pod".format(hosts, vfs, hosts[-num_hosts:])
            )
            hosts = hosts[-num_hosts:]

        netdefs = create_network_attachment_definitions(
            hosts, vfs, datanetwork, ipam_type=ipam_type, ip_version=ip_version
        )

        LOG.tc_step(
            "Try to create pod {} with vfs: {} on host: {}".format(POD_TYPE_NETDEVICE, vfs, hosts)
        )
        # Create pods that use the network attachment definitions
        pods = create_sriov_pods(hosts, netdefs, pod_type=POD_TYPE_NETDEVICE, ip_version=ip_version)

        for pod in pods:
            pod_name = pod["name"]
            LOG.tc_minor_step(
                "Verify the SRIOV interface information in pod {} and its state to be UP".format(
                    pod_name
                )
            )

            pod_sriov_interfaces = sriov_helper.get_pod_interfaces(pod_name, filter_name="net")
            LOG.info(
                "interface(s) {} (is/are) allocated to pod {}".format(
                    list(pod_sriov_interfaces.keys()), pod_name
                )
            )
            assert (
                len(pod_sriov_interfaces.keys()) == vfs
            ), "Allocated interfaces in pod is not {}".format(vfs)

            for pod_sriov_interface_name, pod_sriov_interface_info in pod_sriov_interfaces.items():
                pod_sriov_interface_state = pod_sriov_interface_info["state"]
                assert (
                    pod_sriov_interface_state == "UP"
                ), "Interface {} in pod is {} which is not expected as UP".format(
                    pod_sriov_interface_name, pod_sriov_interface_state
                )

            LOG.tc_minor_step(
                "Verify the number of SR-IOV interfaces in pod {} to be {}".format(pod["name"], vfs)
            )
            devices = sriov_helper.get_pod_pci_device_info(pod_name)
            net_devices = []
            for device in devices:
                if device['ifname'] is not None:
                    net_devices.append(device)

            assert len(devices) == vfs
            assert len(net_devices) == vfs


@mark.container_platform
class TestSriovMixed:
    @fixture(scope='class')
    def prepare_tests(self, request):
        """
        Discover the SR-IOV interface configuration of the system and
        ensure that the appropriate labels are applied.
        Args:
            request: The fixture request

        Returns (list): A list of SR-IOV config dictionaries:
                        [{host: (str), interfaces: (list)}..]
        """
        host_initial_labels = dict()
        new_hosts_labels = dict()
        kube_labels = {
            KUBE_CPU_MGR_POLICY_LABEL: 'static',
            KUBE_TOPOLOGY_MGR_POLICY_LABEL: 'restricted',
        }

        sriov_configs = sriov_helper.get_sriov_config()
        if not sriov_configs:
            skip('no capable SR-IOV interfaces')

        # Get Initial labels on each host, to be used later to recover the labels
        for config in sriov_configs:
            host = config['host']
            LOG.fixture_step("Getting Initial Labels on host: {}".format(host))
            host_initial_labels[host] = host_helper.get_host_labels_info(host)
            new_hosts_labels[host] = kube_labels

        LOG.fixture_step("Add host's labels: {}".format(new_hosts_labels))
        Host.assign_host_labels(new_hosts_labels, overwrite=True)

        def revert_tests():
            """
            Restore the labels
            """
            remove_host_labels, add_back_host_labels = Host.get_host_labels_to_recover(
                host_initial_labels, new_hosts_labels
            )
            LOG.fixture_step("Remove host's labels: {}".format(remove_host_labels))
            Host.remove_host_labels(remove_host_labels)

            if add_back_host_labels:
                LOG.fixture_step("Add host's labels back: {}".format(add_back_host_labels))
                Host.assign_host_labels(add_back_host_labels, overwrite=True)

        request.addfinalizer(revert_tests)
        return sriov_configs

    @mark.p2
    @mark.dc_sriov
    @mark.parametrize(('dpdk_vfs', 'netdevice_vfs'), [(1, 1), (2, 2)])
    def test_sriovdp_mixed_single_pod(
        self,
        dpdk_vfs,
        netdevice_vfs,
        prepare_host,
        sriov_node_capacity,
        prepare_resources,
        prepare_tests,
        pull_and_push_external_to_local,
    ):
        """
        Test creation of a pod with multiple netdevice/dpdk based SR-IOV
        interfaces
        Args:
            dpdk_vfs (int): Number of VFs to use for DPDK operations
            netdevice_vfs (int): Number of VFs to use for netdevice operations
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_resources: module fixture
            prepare_tests: class fixture
        Setups:
            - Find a datanetwork to use for netdevice SR-IOV VFs
            - Find a datanetwork to use for DPDK SR-IOV VFs
            - Remove and delete test app if exists

        Test Steps:
            - Create a network attachment definition for the netdevice VFs
            - Create a network attachment definition for the DPDK VFs
            - Create a pod with netdevice + DPDK VFs
            - Verify the number of VFs in the pod
            - Delete the pod
            - Delete the network attachment definitions

        """
        sriov_config = prepare_host
        datanetwork_capacity = sriov_node_capacity
        num_hosts = 1
        pods_per_host = 1
        pods = []
        netdefs = []

        ip_version = IPV6_VERSION if ProjVar.get_var('IPV6_OAM') else IPV4_VERSION

        datanetwork_netdevice, hosts_netdevice = check_system_compatibility(
            num_hosts,
            pods_per_host,
            netdevice_vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_NETDEVICE,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork_netdevice:
            skip(
                'no data network exists with capacity for {} SR-IOV netdevice VFs'.format(
                    netdevice_vfs
                )
            )

        datanetwork_dpdk, hosts_dpdk = check_system_compatibility(
            num_hosts,
            pods_per_host,
            dpdk_vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_DPDK,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork_dpdk:
            skip('no data network exists with capacity for {} SR-IOV vfio VFs'.format(dpdk_vfs))

        hosts = list(set(hosts_netdevice) & set(hosts_dpdk))
        if not hosts:
            skip('no host exists with both netdevice and dpdk')

        if num_hosts < len(hosts):
            hosts = hosts[-num_hosts:]

        if datanetwork_dpdk == datanetwork_netdevice:
            LOG.tc_step(
                "Try to create Network Attachment Definitions on "
                "hosts: {} for SR-IOV vfs: {} "
                "using Data Networks: {}".format(hosts, netdevice_vfs + dpdk_vfs, datanetwork_dpdk)
            )
            netdefs = create_network_attachment_definitions(
                hosts, netdevice_vfs + dpdk_vfs, datanetwork_dpdk
            )
        else:
            LOG.tc_step(
                "Try to create Network Attachment Definitions on "
                "hosts: {} for SR-IOV vfs: {} "
                "using Data Networks: {}".format(hosts, netdevice_vfs, datanetwork_netdevice)
            )
            netdevice_netdefs = create_network_attachment_definitions(
                hosts, netdevice_vfs, datanetwork_netdevice
            )
            LOG.tc_step(
                "Try to create Network Attachment Definitions on "
                "hosts: {} for SR-IOV vfs: {} "
                "using Data Networks: {}".format(hosts, dpdk_vfs, datanetwork_dpdk)
            )
            dpdk_netdefs = create_network_attachment_definitions(hosts, dpdk_vfs, datanetwork_dpdk)
            netdefs = netdevice_netdefs + dpdk_netdefs

        LOG.tc_step("Try to create pod {} on host: {}".format(POD_TYPE_DPDK, hosts))
        # Create pods that use the network attachment definitions
        pods = create_sriov_pods(hosts, netdefs, pod_type=POD_TYPE_DPDK, ip_version=ip_version)

        # Verify the number of SR-IOV interfaces in each pod
        for pod in pods:
            podname = pod['name']
            devices = sriov_helper.get_pod_pci_device_info(podname)
            net_devices = []
            vfio_devices = []
            mlx_devices = []

            for device in devices:
                if 'mlx' in device['driver']:
                    mlx_devices.append(device)
                elif device['ifname'] is not None:
                    net_devices.append(device)
                elif 'vfio' in device['driver']:
                    vfio_devices.append(device)

            assert len(devices) == (dpdk_vfs + netdevice_vfs)
            if not mlx_devices:
                assert len(net_devices) == netdevice_vfs
                assert len(vfio_devices) == dpdk_vfs
            else:
                assert len(mlx_devices) == (dpdk_vfs + netdevice_vfs)

            for pod in pods:
                LOG.tc_step("Try to delete {} pod".format(pod['name']))
                kube_helper.delete_resources(resource_names=pod['name'])

            for netdef in netdefs:
                LOG.tc_step("Try to delete {} network attachment definition".format(netdef['name']))
                kube_helper.delete_resources(
                    resource_names=netdef['name'], resource_types='net-attach-def'
                )

    @mark.p2
    @mark.parametrize('vfs', [param(1, marks=mark.priorities('platform_nightly', 'dc_sriov'))])
    def test_sriovdp_mixed_add_vf_interface(
        self,
        vfs,
        prepare_host,
        sriov_node_capacity,
        prepare_system_resources,
        pull_and_push_external_to_local,
    ):
        """
        Test creation of a VF interface via system cmd
        Args:
            vfs (int): Number of virtual functions to assign to the new VF
                interface
            prepare_host: module fixture
            sriov_node_capacity: module fixture
            prepare_system_resources: function fixture
        Setups:
            - Choose an ethernet based pci-sriov interface to create a VF
                  interface over
            - Remove and delete test app if exists

        Test Steps:
            - lock the host
            - create a VF interface
            - create a datanetwork for the VF interface
            - assign the VF interface to the datanetwork
            - unlock the host
            - Verify the sriovdp daemon SR-IOV pools are updated to reflect the
                  new VF interface
        Teardown:
            - delete the VF interface's datanetwork
            - delete datanetwork
        """
        sriov_configs = prepare_host
        datanetwork_capacity = sriov_node_capacity
        interface_name = None
        datanetwork_name = "sriov-test-datanetwork"

        for config in sriov_configs:
            host = config['host']
            interfaces = config['interfaces']

            for interface in interfaces:
                if interface['class'] == INTERFACE_CLASS_PCI_SRIOV:
                    if interface['vf_driver'] == 'vfio':
                        break
            else:
                skip(
                    'No existing SR-IOV devices bound to VFIO; '
                    'Cannot determine whether vfio is supported or '
                    'VT-d is enabled in the BIOS'
                )

            for interface in interfaces:
                if (
                    interface['class'] == INTERFACE_CLASS_PCI_SRIOV
                    and interface['type'] == 'ethernet'
                ):
                    # Mellanox devices are always netdevice
                    if interface['is_mellanox']:
                        continue
                    if interface['vf_driver'] == 'vfio':
                        continue
                    # Make sure there's enough VFs for the VF interface
                    numvfs = interface['num_vfs']
                    if int(numvfs) <= vfs:
                        continue
                    driver = interface['vf_driver']
                    datanetworks = interface['datanetworks']
                    interface_name = interface['name']
                    break
            if interface_name:
                # Found the SR-IOV interface to use for the VF interface
                LOG.info(
                    "Interface {} will be used for VF interface on host {}".format(
                        interface_name, host
                    )
                )
                break

        if not interface_name:
            skip('no compatible ethernet SR-IOV interfaces for VF interface creation')

        old_vfs = []
        for datanetwork in datanetworks:
            datanetwork = sriov_helper.normalize_datanetwork_name(datanetwork)
            old_vfs.append(datanetwork_capacity[host][datanetwork])

        if driver in ['None', 'netdevice']:
            new_driver = 'vfio'
        else:
            new_driver = 'netdevice'
        new_interface_name = 'sriov'

        LOG.tc_step("Try to lock host {}".format(host))
        HostsToRecover.add(host, scope='function')
        host_helper.lock_host(host, swact=True)

        LOG.tc_step(
            "Try to add {} interface on host {} with driver {} on parent {} with driver {}".format(
                INTERFACE_TYPE_VF, host, new_driver, interface_name, driver
            )
        )
        host_helper.add_host_interface(
            host,
            new_interface_name,
            interface_name,
            if_type=INTERFACE_TYPE_VF,
            if_class=INTERFACE_CLASS_PCI_SRIOV,
            sriov_vf_count=vfs,
            sriov_vf_driver=new_driver,
            lock_unlock=False,
        )

        LOG.tc_step("Try to add datanetwork: {}".format(datanetwork_name))
        system_helper.create_data_network(datanetwork_name)

        LOG.tc_step(
            "Try to assign interface {} to data network {} on host {}".format(
                new_interface_name, datanetwork_name, host
            )
        )
        host_helper.assign_interface_datanetwork(host, new_interface_name, datanetwork_name)

        LOG.tc_step("Try to unlock host {}".format(host))
        host_helper.unlock_host(host)

        new_datanetwork_capacity = sriov_helper.get_sriov_node_capacity()

        new_vfs = []
        for idx, datanetwork in enumerate(datanetworks):
            datanetwork = sriov_helper.normalize_datanetwork_name(datanetwork)
            if datanetwork in datanetwork_capacity[host].keys():
                new_vfs.append(new_datanetwork_capacity[host][datanetwork])

        LOG.tc_step(
            "Try to verify the number of VFs on datanetworks belonging to {}".format(interface_name)
        )
        for idx, vf in enumerate(new_vfs):
            assert vf == (old_vfs[idx] - vfs)


@mark.dc_sriov
@mark.parametrize(
    'num_hosts',
    [
        param(1, marks=[mark.patch_testing, mark.p1]),
        param(2, marks=[mark.p1]),
    ],
)
def test_sriov_pod_to_pod_netdevice_ping_iperf(
    prepare_host,
    sriov_node_capacity,
    prepare_resources,
    num_hosts,
    pull_and_push_external_to_local,
):
    """
    Test ping/ipref pod to pod created using netdevice vf
    Args:
        prepare_host: module fixture
        sriov_node_capacity: module fixture
        prepare_system_resources: function fixture
        num_hosts: the number of hosts to place pods on

    Test Steps:
        - Find data-network compatible for netdevice and number of vfs.
        - Create Data Network Definition and attached to corresponding data-network.
        - Create pods on each host:
            - if number of hosts is one, then two pods on the host will be created.
            - if number of hosts is not one, one pod per each host will be created.
        - Verify ping from each pod to other pod successfully.
        - Verify the ipref from one pod to another pod successfully.

    TearDown:
        - Delete Network-attachment-definition
        - Delete Created pods
    """

    vfs = 1
    pods_per_host = 1 if num_hosts == 2 else 2
    sriov_config = prepare_host
    datanetwork_capacity = sriov_node_capacity

    ip_version = IPV6_VERSION if ProjVar.get_var('IPV6_OAM') else IPV4_VERSION

    LOG.tc_step(
        "Try to find data-network and hosts with capacity vfs: {} for pod type: {}".format(
            vfs, POD_TYPE_NETDEVICE
        )
    )
    datanetwork, hosts = check_system_compatibility(
        num_hosts,
        pods_per_host,
        vfs,
        INTERFACE_CLASS_PCI_SRIOV,
        POD_TYPE_NETDEVICE,
        sriov_config,
        datanetwork_capacity,
    )

    if not datanetwork:
        skip(
            'no data network exists with capacity for '
            '{} SR-IOV vfio VFs for number of hosts {}'.format(vfs, num_hosts)
        )

    if not hosts:
        skip(
            'no host exists with capacity for {} SR-IOV vfio VFs and {} 1G hugpages'.format(
                vfs, DPDK_HUGEPAGE_REQD
            )
        )

    LOG.info(
        "Data-Networks: {} and hosts: {} have capacity SRI-IOV vfs: {} for pod type {}".format(
            datanetwork, hosts, vfs, POD_TYPE_NETDEVICE
        )
    )
    if num_hosts < len(hosts):
        LOG.info(
            "Hosts: {} are capable of creating pod with vfs: {}, and "
            "host {} is selected to have pod".format(hosts, vfs, hosts[-num_hosts:])
        )
        hosts = hosts[-num_hosts:]

    if num_hosts == 1:
        pods_on_hosts = hosts * pods_per_host
    else:
        pods_on_hosts = hosts

    LOG.tc_step(
        "Try to create Network Attachment Definitions on host(s): {} "
        "for SR-IOV vf(s): {} using Data Networks: {}".format(hosts, vfs, datanetwork)
    )
    netdefs = create_network_attachment_definitions(
        pods_on_hosts, vfs, datanetwork, ipam_type='host-local', ip_version=ip_version
    )

    LOG.tc_step(
        "Try to create pod {} with vf(s): {} on host(s): {}".format(POD_TYPE_NETDEVICE, vfs, hosts)
    )
    pods = create_sriov_pods(
        pods_on_hosts, netdefs, pod_type=POD_TYPE_NETDEVICE, ip_version=ip_version
    )

    # ping and ipref from one pod to other and vice versa
    LOG.tc_step("Try to ping and ipref from one pod to other pod")
    for client_pod in pods:
        client_pod_name = client_pod["name"]
        for server_pod in pods:
            server_pod_name = server_pod["name"]
            if client_pod_name != server_pod_name:
                for server_pod_ip in server_pod["ip"]:
                    LOG.tc_minor_step(
                        "Ping from {} to {} with IP {}".format(
                            client_pod_name, client_pod_name, server_pod_ip["ip"]
                        )
                    )
                    network_helper.ping_from_pod(
                        client_pod_name, destination_ip=server_pod_ip["ip"], ip_version=ip_version
                    )

                    for client_pod_ip in client_pod["ip"]:
                        LOG.tc_minor_step(
                            "ipref from client {} with client ip {} to server {} with ip {}".format(
                                client_pod_name,
                                client_pod_ip["ip"],
                                server_pod_name,
                                server_pod_ip["ip"],
                            )
                        )
                        network_helper.iperf_pod_to_pod(
                            server_ip=server_pod_ip["ip"],
                            client_ip=client_pod_ip["ip"],
                            server_pod_name=server_pod_name,
                            client_pod_name=client_pod_name,
                        )


class TestSriovMaxVf:
    @fixture(scope='function')
    def get_initial_num_vfs(self, request, prepare_host):
        """
        Get the pre-configured SR-IOV VF's numbers
        Args:
            request: The fixture request
            prepare_host: The prepare_host fixture
        """

        sriov_configs = prepare_host
        LOG.fixture_step("Getting Initial SR-IOV vfs on each SR-IOV interface")
        initial_sriov_interface_num_vfs = SRIOV.get_sriov_interface_num_vfs(sriov_configs)

        def revert_sriov_vfs():
            """
            Restore the number of vf's on each SR-IOV interface
            """
            sriov_interface_num_vfs = SRIOV.get_sriov_interface_num_vfs(sriov_configs)

            LOG.fixture_step("Revert-back SR-IOV vfs if needed.")
            for host, sriov_interfaces_info in sriov_interface_num_vfs.items():
                host_is_locked = False
                for interface_name, num_vf in sriov_interfaces_info.items():
                    if num_vf != initial_sriov_interface_num_vfs[host][interface_name]:
                        LOG.fixture_step(
                            "Modify SR-IOV vf "
                            "of interface {} on host {} to its initial value {}".format(
                                interface_name,
                                host,
                                initial_sriov_interface_num_vfs[host][interface_name],
                            ),
                            depth=1,
                        )

                        HostsToRecover.add(host)
                        host_helper.lock_host(host, swact=True)
                        host_is_locked = True

                        host_helper.modify_host_interface(
                            host,
                            interface_name,
                            sriov_vf_count=initial_sriov_interface_num_vfs[host][interface_name],
                            lock_unlock=False,
                        )
                if host_is_locked:
                    host_helper.unlock_host(host)
                    HostsToRecover.remove(host)

        request.addfinalizer(revert_sriov_vfs)

    @mark.p2
    @mark.dc_sriov
    def test_sriovdp_exceed_max_vf(self, prepare_host, get_initial_num_vfs):
        """
        Negative Test to configure more than maximum supported VFs on netdevice/vfio drivers.
        Args:
            prepare_host: module fixture
            get_initial_num_vfs: function fixture to get initial number of configured vfs

        Test Steps:
            - Get SR-IOV interfaces configurations
            - Get the maximum capacity of number of VFs for SR-IOV interface
                - if interface is on a port (Parent): use system host-port-show <host> <port> to
                find the capacity of the port for sriov vfs.
                - if interface is a child: use system host-if-show <host> <parent-interface> to
                find the capacity of the parent interface
            - Lock the host
            - Try to configure more than maximum capacity of VF for specific interface.
            - Verify the error message to make sure modification gets rejected.

        TearDown:
            - Revert back the number of VFs on each SR-IOV interface
        """
        sriov_configs = prepare_host

        # If a lab has multiple hosts with SR-IOV capacity, in DM all configured the same,
        # therefore, picking one of them to do the test
        sriov_config = sriov_configs[0] if sriov_configs else skip('no capable SR-IOV interfaces')

        host = sriov_config["host"]
        interfaces = sriov_config["interfaces"]
        for interface in interfaces:
            ports = ast.literal_eval(interface.get("ports"))
            interface_name_used_by = ast.literal_eval(interface.get("uses"))
            interface_name = interface.get("name")
            assert (
                ports or interface_name_used_by
            ), "Interface {} is not parent neither child".format(interface_name)
            if ports:
                LOG.tc_step(
                    "Getting maximum number of VFs supported on host {} for port {}".format(
                        host, ports[0]
                    )
                )
                # Getting maximum number of sr-iov vf capacity on this port
                sriov_totalvfs = host_helper.get_host_port_values(host, ports[0], "sriov_totalvfs")[
                    0
                ]
                modified_sriov_vfs = str(int(sriov_totalvfs) + 1)
                LOG.info(
                    "Interface {} uses port {} which has maximum {} vfs".format(
                        interface_name, ports[0], sriov_totalvfs
                    )
                )
                expected_error_msg = 'The interface support a maximum of {} VFs'.format(
                    sriov_totalvfs
                )
            elif interface_name_used_by:
                LOG.tc_step(
                    "Getting maximum number of VFs supported on host {} for interface {}".format(
                        host, interface_name_used_by[0]
                    )
                )
                # Getting maximum number of sr-iov vf capacity on interface's parent
                modified_sriov_vfs = host_helper.get_host_interface_values(
                    host, interface_name_used_by[0], "sriov_numvfs"
                )[0]
                LOG.info(
                    "Interface {} uses parent {} which has maximum {} vfs".format(
                        interface_name, interface_name_used_by[0], modified_sriov_vfs
                    )
                )

                expected_error_msg = (
                    "The number of virtual functions ({}) must be less than or equal to the "
                    "available VFs".format(
                        modified_sriov_vfs,
                    )
                )

            LOG.tc_step("Lock host {} to modify interface {}".format(host, interface_name), depth=1)
            HostsToRecover.add(host)
            host_helper.lock_host(host, swact=True)

            LOG.tc_step(
                "Modify VF number of interface {} on host {} to {}".format(
                    interface_name, host, modified_sriov_vfs
                ),
                depth=1,
            )
            code, output = host_helper.modify_host_interface(
                host,
                interface_name,
                sriov_vf_count=modified_sriov_vfs,
                lock_unlock=False,
                fail_ok=True,
            )
            assert (
                code > 0 and expected_error_msg in output
            ), 'Configuring more than max {} vfs did not failed as expected'.format(
                modified_sriov_vfs
            )

        LOG.tc_step("UnLock host {}".format(host))
        host_helper.unlock_host(host)
        HostsToRecover.remove(host)


@mark.p2
@mark.dc_sriov
@mark.parametrize("pod_type", ["netdevitest_sriovdp_mixed_single_podce", "dpdk"])
def test_sriovdp_pending_pod(
    pod_type,
    prepare_host,
    sriov_node_capacity,
    prepare_resources,
    pull_and_push_external_to_local,
):
    """
    Test a new pod after the vfs reached maximum cannot be created
    Args:
        pod_type (str): Type of pod (dpdk or netdevice)
        prepare_host: The prepare_host fixture
        sriov_node_capacity: module fixture
        prepare_resources: module fixture

    Setups:
        - Set label sriovdp: enabled on hosts
        - Discover SRIOV interfaces configuration
        - Get already exsiting pods and network-attachment-definition objects in the lab

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create a pod with max-1 vfs on the host
        - Check the status of created pod to be in Running state
        - Create a pod with 1 vf on the host
        - Check the status of created pod to be in Running state
        - Create third pod with one vf on the host
        - Check the status of last created pod to make sure be in Pending state
        - Delete the second pod (pod with one vf)
        - Check the status of last pod which was in Pending state to make sure it is in Running

    TearDown:
        - Delete created pod
        - Delete created network-attachment-definition
    """

    testname = inspect.currentframe().f_code.co_name
    pods_per_host = 1
    num_hosts = 1
    sriov_config = prepare_host
    datanetwork_capacity = sriov_node_capacity
    max_vfs = SRIOV.get_max_num_vfs(datanetwork_capacity, sriov_config, pod_type)
    LOG.info("Maximum number of vfs type of {} is {}".format(pod_type, max_vfs))
    ip_version = IPV6_VERSION if ProjVar.get_var('IPV6_OAM') else IPV4_VERSION

    datanetwork, hosts = SRIOV.get_sriov_hosts_datanetwork(
        max_vfs, pod_type, num_hosts, pods_per_host, sriov_config, datanetwork_capacity
    )
    host_under_test = hosts[0]

    # Create network attachment definitions with SR-IOV as the CNI type
    nadname = "nad_{}_{}".format(testname, pod_type)
    nadname = nadname.replace("_", "-")
    filename = sriov_helper.create_network_attachment_definition(
        nadname, datanetwork, cni_type='sriov', spoofchk="off", trust="on"
    )

    LOG.tc_step("Try to create network attachment definition {}".format(nadname))
    kube_helper.apply_resource(filename)

    vfs = [max_vfs - 1, 1]
    for index in range(2):
        nad_config = {
            'name': nadname,
            'datanetwork': datanetwork,
            'vfs': vfs[index],
            'host': host_under_test,
        }
        netdefs = [nad_config]
        user_podname = {host_under_test: "{}-{}".format(testname.replace("_", "-"), index + 1)}
        LOG.tc_step(
            "Create SRIOV pod type {} with vfs: {} on host {}".format(
                pod_type, vfs[index], host_under_test
            )
        )
        create_sriov_pods(
            hosts, netdefs, pod_type=pod_type, user_podname=user_podname, ip_version=ip_version
        )

    nad_config = {'name': nadname, 'datanetwork': datanetwork, 'vfs': 1, 'host': host_under_test}
    netdefs = [nad_config]
    podname = "{}-3".format(testname.replace("_", "-"))

    if pod_type == POD_TYPE_NETDEVICE:
        filename = create_netdevice_pod(
            podname, netdefs, host=host_under_test, ip_version=ipaddress
        )
    else:
        filename = create_dpdk_pod(podname, netdefs, host=host_under_test, ip_version=ipaddress)

    LOG.tc_step(
        "Create an extra SRIOV pod type {} with vfs: 1 on host {}".format(pod_type, host_under_test)
    )
    kube_helper.apply_pod(
        file_path=filename,
        pod_name=podname,
        check_both_controllers=False,
        pod_status=PodStatus.PENDING,
    )

    LOG.info("Sleep for 15 sec to make sure Pending state is not initial status")
    time.sleep(15)
    LOG.tc_step("Check status of pod {} to be {}".format(podname, PodStatus.PENDING))
    kube_helper.wait_for_pods_status(pod_names=podname, status=PodStatus.PENDING)

    LOG.tc_step(
        "Delete pod {} on host {}".format(
            "{}-2".format(testname.replace("_", "-")), host_under_test
        )
    )
    kube_helper.delete_resources(resource_names="{}-2".format(testname.replace("_", "-")))

    LOG.tc_step(
        "Check status of pod {} after deleting {} to be {}".format(
            podname, "{}-2".format(testname.replace("_", "-")), PodStatus.RUNNING
        )
    )
    kube_helper.wait_for_pods_status(pod_names=podname, status=PodStatus.RUNNING)


@mark.dc_sriov
@mark.parametrize(
    "pod_type",
    [
        param('netdevice', marks=[mark.p2]),
        param('dpdk', marks=[mark.p2]),
    ],
)
def test_sriovdp_resource_allocation(
    pod_type,
    prepare_host,
    sriov_node_capacity,
    prepare_resources,
    pull_and_push_external_to_local,
):
    """
    Test allocated sriov resources are cleared after deleting pods

    Args:
        pod_type (str): Type of pod (dpdk or netdevice)
        prepare_host: The prepare_host fixture
        sriov_node_capacity: module fixture
        prepare_resources: module fixture

    Setups:
        - Set label sriovdp: enabled on hosts
        - Discover SRIOV interfaces configuration
        - Get already existing pods and network-attachment-definition objects in the lab

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create a pod with 1 vf on the host
        - Verify allocated sriov resources
        - Delete created pod
        - Verify allocated sriov resources

    TearDown:
        - Delete created pod
        - Delete created network-attachment-definition
    """
    testname = inspect.currentframe().f_code.co_name
    pods_per_host = 1
    num_hosts = 1
    vfs = 1
    sriov_config = prepare_host
    datanetwork_capacity = sriov_node_capacity
    ip_version = IPV6_VERSION if ProjVar.get_var('IPV6_OAM') else IPV4_VERSION

    datanetwork, hosts = SRIOV.get_sriov_hosts_datanetwork(
        vfs, pod_type, num_hosts, pods_per_host, sriov_config, datanetwork_capacity
    )

    host_under_test = hosts[0]

    # Create network attachment definitions with SR-IOV as the CNI type
    nadname = "nad_{}_{}".format(testname, pod_type)
    nadname = nadname.replace("_", "-")
    LOG.tc_step("Create NetworkAttachmentDefinition using datanetwork {}".format(datanetwork))
    filename = sriov_helper.create_network_attachment_definition(
        nadname, datanetwork, cni_type='sriov', spoofchk="off", trust="on"
    )
    kube_helper.apply_resource(filename)

    nad_config = {'name': nadname, 'datanetwork': datanetwork, 'vfs': vfs, 'host': host_under_test}
    netdefs = [nad_config]
    LOG.tc_step(
        "Create SRIOV pod type {} with vfs: {} on host {}".format(pod_type, vfs, host_under_test)
    )
    pods = create_sriov_pods(hosts, netdefs, pod_type=pod_type, ip_version=ip_version)

    LOG.tc_step("Verify number of allocated sriov resources")
    expected_sriov_allocated = {datanetwork: {"requests": vfs, "limits": vfs}}
    SRIOV.verify_allocated_vfs(hosts[0], expected_sriov_allocated)

    for pod in pods:
        pod_name = pod["name"]

        LOG.tc_step("Delete {} pod".format(pod_name))
        kube_helper.delete_resources(
            resource_names=pod_name, namespace='default', check_both_controllers=False
        )

    LOG.tc_step("Verify number of allocated sriov resources after deleting pods")
    expected_sriov_allocated = {datanetwork: {"requests": 0, "limits": 0}}
    SRIOV.verify_allocated_vfs(hosts[0], expected_sriov_allocated)


@mark.dc_sriov
@mark.lab_sriov
@mark.parametrize(
    "pod_type",
    [
        param('netdevice', marks=[mark.p2]),
        param('dpdk', marks=[mark.p2]),
    ],
)
def test_sriovdp_replicas_same_network(
    pod_type,
    prepare_host,
    sriov_node_capacity,
    prepare_resources,
    pull_and_push_external_to_local,
):
    """
    Test SRIOV pod creation on same network with two replicas with different drivers
    Args:
        pod_type (str): Type of pod (dpdk or netdevice)
        prepare_host: The prepare_host fixture
        sriov_node_capacity: module fixture
        prepare_resources: module fixture

    Setups:
        - Set label sriovdp: enabled on hosts
        - Discover SRIOV interfaces configuration
        - Get already existing pods and network-attachment-definition objects in the lab

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create a pod with 2 vf on the host with two replicas
        - Verify Status of pods to be Running
        - Verify the number of allocated sriov interface in each pod

    TearDown:
        - Delete created pod
        - Delete created network-attachment-definition
    """
    testname = f"sriovdp-replicas-same-network-{pod_type}"
    num_hosts = 1
    pods_per_host = 1
    replicas = 2
    vfs = 2
    sriov_deployment_pod_name = "sriov-pod-replicas"
    sriov_yaml_file_path = "/tmp/{}.yaml".format(testname)
    nadname = "nad-{}-{}".format(testname, pod_type)

    sriov_verifier = sriov_helper.SriovVerifiers()
    sriov_configs = prepare_host
    datanetwork_capacity = sriov_helper.get_sriov_node_capacity()

    data_networks, _ = check_system_compatibility(
        num_hosts, pods_per_host, vfs, 'pci-sriov', pod_type, sriov_configs, datanetwork_capacity
    )
    if not data_networks:
        skip(
            'No Data Network exists with capacity for {} '
            'SR-IOV {} VFs and neither dpdk VFs {}'.format(vfs, pod_type, vfs)
        )

    LOG.tc_step("Create NetworkAttachmentDefinition for {}".format(pod_type))
    ipam = sriov_helper.create_host_local_ipam_config(
        "10.56.216.0/24", routes=[{"\"dst\"": "\"0.0.0.0/0\""}], gateway="\"10.56.216.1\""
    )
    nad_file_netdevice = sriov_helper.create_network_attachment_definition(
        nadname, data_networks, ipam=ipam, datastore_type=None, kubernetes=None
    )
    kube_helper.apply_resource(nad_file_netdevice)

    nads_name = nadname
    for i in range(1, vfs):
        nads_name += ", {}".format(nadname)

    pod_deployment_dict = sriov_helper.create_sriov_deployment_yaml(
        sriov_deployment_pod_name,
        nads_name,
        POD_IMAGE[pod_type],
        data_networks,
        vfs,
        replicas=replicas,
    )
    content = yaml.dump(pod_deployment_dict, default_flow_style=False)
    file_utilities.create_file(sriov_yaml_file_path, content)
    LOG.tc_step("Create pod {}".format(sriov_deployment_pod_name))
    kube_helper.apply_resource(sriov_yaml_file_path)

    LOG.tc_step("Get created SRIOV POD's name")
    _, create_sriov_pod_name = kube_helper.wait_for_pods_status(
        partial_names=sriov_deployment_pod_name
    )

    assert (
        len(create_sriov_pod_name) == replicas
    ), "Replicas is {} but number of pods are {}, {}".format(
        replicas, len(create_sriov_pod_name), create_sriov_pod_name
    )

    LOG.tc_step("Verify status of created SRIOV PODs")
    expected_values_pod_status = dict()
    for pod_name in list(create_sriov_pod_name.keys()):
        expected_values_pod_status[pod_name] = PodStatus.RUNNING
    sriov_verifier.verify_sriov_pods_status(
        list(create_sriov_pod_name.keys()), expected_values=expected_values_pod_status
    )

    LOG.tc_step("Verify number of sriov interfaces in each pod")
    for pod_name in list(create_sriov_pod_name.keys()):
        LOG.tc_step(
            "Verify number of sriov interfaces in pod {} to be {}".format(pod_name, vfs), depth=1
        )
        sriov_verifier.verify_number_of_sriov_interface(pod_name, vfs, pod_type)


@mark.p3
def test_add_delete_vf_interface(get_base_interface_info):
    """
    This test verifies sriov vf interfaces deletion via cli

    Skip Conditions:
        - no sriov interface configured on system

    Setup:
        - get_base_interface_info: function fixture
    Steps:
        - lock target host
        - add a vf interface with just 1 VF over a pre-existing sriov configured interface
        - verify new vf interface is created
        - verify new vf interface can be deleted via 'host-if-delete'
        - unlock host
    """
    sriov_vf_driver, host, parent_if, _ = get_base_interface_info
    test_if = 'sriovtest'

    LOG.tc_step('Lock {}'.format(host))
    host_helper.lock_host(host, swact=True)

    LOG.tc_step(
        'Add {} child interface in {} with {} driver and {} as parent interface'.format(
            test_if, host, sriov_vf_driver, parent_if
        )
    )
    add_sriov_interfaces(host, test_if, parent_if, sriov_vf_driver=sriov_vf_driver)

    LOG.tc_step('Delete {} sriov interface and verify it does not exist'.format(test_if))
    host_helper.delete_host_interface(host, test_if, lock_unlock=False)
    # some seconds before checking if doesn't exist
    time.sleep(INTERFACE_DELETION_WAIT)
    msg = '{} interface still exists'.format(test_if)
    assert test_if not in host_helper.get_host_interfaces(host), msg

    LOG.tc_step('Unlock {}'.format(host))
    host_helper.unlock_host(host)


@mark.p2
def test_multiple_sriov_vf_interfaces_single_parent(prepare_resources, prepare_test_interfaces):
    """
    This test verifies multiple sriov vf interfaces can be configured over
    a single sriov parent interface and those interfaces can be provisioned
    to a pod with both netdevice and vfio networks.

    Skip Conditions:
        - no sriov interface configured on system

    Setup:
        - prepare_test_interfaces(function fixture)
            - lock target host and swact if active controller on DX system
            - add 3 vf sriov child interfaces, 2 with different driver from parent if
              and one with same driver
            - assing one of child interfaces with different driver to a datanetwork that's
              assigned to parent sriov interface
    Steps:
        - create network attachment definitions for both parent interface and the child
          interface previously assigned to datanetwork
        - create a netdevice type pod provisioned with the NADs created at TC setup
        - verify pod's interfaces are the ones provisioned
        - delete created pod
        - delete network attachment definitions
    Teardown:
        - delete created sriov vf interfaces
        - delete created nads
        - delete test pod
    """
    host, _, test_datanetwork, parent_datanetwork = prepare_test_interfaces
    parent_datanetwork = parent_datanetwork.replace('-', '_')
    test_nads = [
        create_network_attachment_definitions([host], 1, test_datanetwork)[0],
        create_network_attachment_definitions([host], 1, parent_datanetwork)[0],
    ]
    ip_version = IPV6_VERSION if ProjVar.get_var('IPV6_OAM') else IPV4_VERSION

    LOG.tc_step('Create a sriov netdevice pod with both netdevice and vfio interfaces configured')
    test_pod = create_sriov_pods([host], test_nads, POD_TYPE_NETDEVICE, ip_version=ip_version)[0][
        'name'
    ]

    LOG.tc_step("verify pod's interfaces are the ones provisioned")
    expected_interfaces = [
        POD_INTERFACE.format(test_datanetwork.upper()),
        POD_INTERFACE.format(parent_datanetwork.upper()),
    ]
    sriov_helper.SriovVerifiers().verify_pod_interfaces(
        test_pod,
        interface_filter='DEVICE_INTEL_COM_PCI_SRIOV_',
        expected_interfaces=expected_interfaces,
    )


@mark.p3
def test_verify_vfs_cannot_be_created_over_data_interface(prepare_data_interface):
    """
    This test verifies sriov VFs cannot be created over a data class parent interface

    Args:
        - prepare_data_interface(function fixture):

    Steps:
        - Try to create child VF interface over data class interface
        - Verify expected failure to match operation output

    Teardown:
        - Delete created data class interface
    """
    host, data_interface = prepare_data_interface
    sriov_if = TEST_SRIOV_INTERFACE
    expected_output = InterfaceErr.INVALID_PARENT_IF_CLASS.format(INTERFACE_CLASS_PCI_SRIOV)

    LOG.tc_step(
        'Try to create {} VF interface over {} data interface'.format(sriov_if, data_interface)
    )
    rc, out = host_helper.add_host_interface(
        host,
        sriov_if,
        '',
        mtu=1500,
        if_class=INTERFACE_CLASS_PCI_SRIOV,
        sriov_vf_count=1,
        parent_sriov_vf=data_interface,
        sriov_vf_driver=VF_DRIVER_VFIO,
        fail_ok=True,
    )

    LOG.tc_step('Verify expected failure to match operation output')
    msg = 'Output did not match expected failure message: {}'.format(out)
    assert rc == 1 and expected_output in out, msg


@mark.p3
def test_verify_class_modification_when_vf_interface_configured(request, get_base_interface_info):
    """
    This test verifies parent interface class cannot be modified when a VF child interface
    is configured over it

    Setup:
        - get_base_interface_info(function_fixture):

    Steps:
        - Lock target host
        - Create child VF interface
        - Try to modify parent interface class and expect to fail
        - Verify cmd failed and expected output was prompted

    Teardown:
        - Delete created interface and unlock host
    """
    sriov_vf_driver, host, parent_if, _ = get_base_interface_info

    LOG.tc_step('Lock {}'.format(host))
    host_helper.lock_host(host)

    def delete_interface():
        LOG.fixture_step('Delete created interface {}'.format(TEST_SRIOV_INTERFACE))
        rc, out = host_helper.delete_host_interface(host, TEST_SRIOV_INTERFACE, fail_ok=True)
        if rc:
            LOG.fixture_step('Unlock {}'.format(host))
            host_helper.unlock_host(host)
            raise exceptions.CLIRejected(
                'Failed to delete {} interface: {}'.format(TEST_SRIOV_INTERFACE, out)
            )

    request.addfinalizer(delete_interface)

    LOG.tc_step(
        'Create {} VF interface in {} over {}'.format(TEST_SRIOV_INTERFACE, host, parent_if)
    )
    add_sriov_interfaces(host, TEST_SRIOV_INTERFACE, parent_if, sriov_vf_driver)

    LOG.tc_step('Try to modify {} interface class and expect to fail'.format(parent_if))
    out = host_helper.modify_host_interface(host, parent_if, if_class='data', fail_ok=True)[1]

    LOG.tc_step('Verify cmd failed and expected output was prompted')
    expected_output = InterfaceErr.CLASS_MODIFY_WHEN_IF_CONFIG.format(INTERFACE_CLASS_PCI_SRIOV)
    msg = 'Command actual output did not match expected output: {}'.format(out)
    assert expected_output in out, msg

