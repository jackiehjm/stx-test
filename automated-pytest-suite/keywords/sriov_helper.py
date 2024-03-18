#
# Copyright (c) 2020 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast
import ipaddress
import json
import re

import yaml

from consts.auth import Tenant
from consts.proj_vars import ProjVar
from consts.stx import MELLANOX_DEVICE, SRIOV, PodStatus
from keywords import host_helper, kube_helper, system_helper
from keywords.general import file_utilities
from utils import exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG

PCI_CLASSES = ['pci-sriov', 'pci-passthrough']
SRIOVDP_ANNOTATION_PREFIX = 'intel.com/pci_sriov_net_'
IPV4_VERSION = 4
IPV6_VERSION = 6
POD_TYPE_DPDK = 'dpdk'
POD_TYPE_NETDEVICE = 'netdevice'
POD_TYPE = [POD_TYPE_DPDK, POD_TYPE_NETDEVICE]


def get_sriov_config(
    administrative=None,
    operational=None,
    availability=None,
    con_ssh=None,
    use_telnet=False,
    con_telnet=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Get the configuration of all SR-IOV enabled interfaces in the system
    Args:
        administrative
        operational
        availability
        con_ssh (SSHClient):
        use_telnet
        con_telnet
        auth_info

    Returns (list): A list of SR-IOV config dictionaries:
                    [{host: (str), interfaces: (list)}..]

    """

    # Get all of the nodes capable of running SR-IOV workloads
    workers = system_helper.get_computes(
        administrative=administrative,
        operational=operational,
        availability=availability,
        con_ssh=con_ssh,
        use_telnet=use_telnet,
        con_telnet=con_telnet,
        auth_info=auth_info,
    )

    if system_helper.is_aio_system(
        controller_ssh=con_ssh, use_telnet=use_telnet, con_telnet=con_telnet, auth_info=auth_info
    ):
        workers = list(workers)
        workers += system_helper.get_controllers(
            administrative=administrative,
            operational=operational,
            availability=availability,
            con_telnet=con_telnet,
            con_ssh=con_ssh,
            auth_info=auth_info,
        )

    sriov_config = []
    for worker in workers:
        # Get all of the compatible PCI interfaces
        pci_interfaces = host_helper.get_host_interfaces(worker, field='name', net_type=PCI_CLASSES)
        if not pci_interfaces:
            continue

        host_config = {'host': worker, 'interfaces': []}

        # Collect PCI configuration information
        for interface in pci_interfaces:
            datanetworks = host_helper.get_host_datanetworks(worker, interface)

            sriov_info = host_helper.get_host_interface_values(
                worker,
                interface,
                ['ifname', 'ifclass', 'iftype', 'ports', 'uses', 'sriov_numvfs', 'sriov_vf_driver'],
            )

            if len(sriov_info) != 7:
                raise exceptions.CommonError(
                    'Unable to get SR-IOV info for interface {}'.format(interface)
                )

            ifname = sriov_info[0]
            ifclass = sriov_info[1]
            iftype = sriov_info[2]
            ports = sriov_info[3]
            uses = sriov_info[4]
            num_vfs = sriov_info[5]
            vf_driver = sriov_info[6]

            if iftype == 'vf':
                parent_interface = ast.literal_eval(uses)
                parent = parent_interface[0]
                parent_port = ast.literal_eval(
                    host_helper.get_host_interface_values(worker, parent, 'ports')[0]
                )[0]
                mlx_port = host_helper.get_host_ports(
                    worker,
                    'uuid',
                    if_name=parent_port,
                    strict=False,
                    regex=True,
                    **{'device type': MELLANOX_DEVICE},
                )
            else:
                port = ast.literal_eval(ports)[0]
                mlx_port = host_helper.get_host_ports(
                    worker,
                    'uuid',
                    if_name=port,
                    strict=False,
                    regex=True,
                    **{'device type': MELLANOX_DEVICE},
                )

            is_mellanox = True if mlx_port else False

            host_config['interfaces'].append(
                {
                    'name': ifname,
                    'class': ifclass,
                    'type': iftype,
                    'ports': ports,
                    'uses': uses,
                    'num_vfs': num_vfs,
                    'vf_driver': vf_driver,
                    'is_mellanox': is_mellanox,
                    'datanetworks': datanetworks,
                }
            )

        sriov_config.append(host_config)

    LOG.debug("System SR-IOV config: %r", sriov_config)
    return sriov_config


def get_sriov_node_capacity():
    """
    Get the SR-IOV device plugin capacity (number of vfs available)
    on each datanetwork in the system.

    Returns (dict): A dictionary of nodes with their SR-IOV device plugin
                    discovered virtual functions.
                    {node_name: {datanetwork_name: num_vfs}, ...}

    """

    system_pod_names = kube_helper.get_pods(field=('NAME', 'STATUS'), namespace='kube-system')
    for system_pod in system_pod_names:
        system_pod_name = system_pod[0]
        pod_status = system_pod[1]
        if SRIOV.SRIOV_DEVICE_PLUGIN_POD_NAME in system_pod_name:
            sriov_device_plugin_pod_name = system_pod_name
            break
    else:
        raise exceptions.CommonError(
            "Unable to find pod {}".format(SRIOV.SRIOV_DEVICE_PLUGIN_POD_NAME)
        )

    LOG.info(
        "sriov device plugin pod name is {} and its status is {}".format(
            sriov_device_plugin_pod_name, pod_status
        )
    )
    if pod_status != PodStatus.RUNNING:
        LOG.info(
            "Wait till the status of {} gets {}".format(
                sriov_device_plugin_pod_name, PodStatus.RUNNING
            )
        )
        kube_helper.wait_for_pods_status(
            pod_names=sriov_device_plugin_pod_name,
            namespace='kube-system',
            status=PodStatus.RUNNING,
        )

    cmd = 'get node -o=json'
    code, output = kube_helper.exec_kube_cmd('get node -o=json')

    data = json.loads(output)
    if 'items' not in data:
        raise exceptions.CommonError('Unexpected output from {}: {}'.format(cmd, data))

    datanetwork_capacity = {}
    for p in data['items']:
        if 'status' not in p:
            raise exceptions.CommonError(
                'Unexpected output from {}: no status: {}'.format(cmd, data)
            )
        status = p['status']

        if 'capacity' not in status:
            raise exceptions.CommonError(
                'Unexpected output from {}: no capacity: {}'.format(cmd, data)
            )
        capacity = p['status']['capacity']

        if 'metadata' not in p:
            raise exceptions.CommonError(
                'Unexpected output from {}: no metadata: {}'.format(cmd, data)
            )
        metadata = p['metadata']
        if 'name' not in metadata:
            raise exceptions.CommonError(
                'Unexpected output from {}: no name in metadata: {}'.format(cmd, data)
            )
        name = metadata['name']

        datanetwork_capacity[name] = {}
        for key, val in capacity.items():
            if key.startswith(SRIOVDP_ANNOTATION_PREFIX):
                datanetwork = key[len(SRIOVDP_ANNOTATION_PREFIX) :]
                datanetwork_capacity[name][datanetwork] = int(val)

    return datanetwork_capacity


def normalize_metadata_name(name):
    """
    A metadata name must consist of lower case alphanumeric characters,
    '-' or '.', and must start and end with an alphanumeric character
    Args:
        name: The metadata name

    Returns (str): The normalized metadata name
    """
    return name.lower().replace("_", "-")


def normalize_datanetwork_name(name):
    """
    Datanetwork names which are embedded in the sriovdp network annotation(s)
    must consist of lower case alphanumeric characters, and must use
    underscores rather than hyphens
    Args:
        name: The datanetwork name

    Returns (str): The normalized datanetwork name
    """
    return name.lower().replace("-", "_")


def get_host_local_ipam_config(host_idx, num_hosts, cidr, ip_version=IPV4_VERSION):
    """
    Create an IPAM config for the host-local CNI plugin
    Args:
        host_idx (int): The host index (id in a list)
        num_hosts (int): The number of hosts (pods) in the test
        cidr (str): Classless inter-domain routing (ip/prefix)
        ip_version (int): The IP version of the pod's default network

    Returns ipam_config (dict): A host-local compatible ipam config dictionary
    """
    # For an ipam of host-local, we need separate ipam configuration
    # definitions for each host, so that a pod cannot get a duplicate
    # IP address.  This is why we need the 'host index'
    offset = host_idx * num_hosts
    range_start = '{}'.format(str(ipaddress.ip_interface(cidr).ip + offset + 2))
    range_end = '{}'.format(str(ipaddress.ip_interface(cidr).ip + offset + num_hosts + 2))

    ipam_config = create_host_local_ipam_config(cidr, range_start, range_end)

    return ipam_config


def create_network_attachment_definition_yaml(
    filename,
    name,
    datanetwork,
    cnitype="sriov",
    vlan=None,
    ipam=None,
    mac=None,
    spoofchk=None,
    trust=None,
    datastore_type="\"kubernetes\"",
    kubernetes={"\"kubeconfig\"": "\"/etc/cni/net.d/calico-kubeconfig\""},
):
    """
    Create a network attachment definition .yaml file on the active controller
    Args:
        filename (str): The absolute path to the file to create
        name (str): The name of the network attachment definition
        datanetwork (str): The datanetwork of the network attachment definition
        cnitype (str): The CNI type of the network attachment definition
        vlan (int): The VLAN id of the network attachment definition
        ipam (dict): The IPAM config for the network attachment definition
        mac (str): The MAC address of the network attachment definition
        spoofchk (str): The spoofchk value for the network attachment definition
        trust (str): The trust value for the network attachment definition
        datastore_type (str): Data store type
        kubernetes (str): kubernetes config

    Returns (exit code (int), command output (str))
    """
    cni_config = {"\"cniVersion\"": "\"0.3.0\"", "\"type\"": "\"{}\"".format(cnitype)}
    if datastore_type:
        cni_config["\"datastore_type\""] = datastore_type
    if kubernetes:
        cni_config["\"kubernetes\""] = kubernetes
    if vlan:
        cni_config["\"vlan\""] = vlan
    if ipam:
        cni_config["\"ipam\""] = ipam
    if mac:
        cni_config["\"mac\""] = "\"{}\"".format(mac)
    if spoofchk:
        cni_config["\"spoofchk\""] = "\"{}\"".format(spoofchk)
    if trust:
        cni_config["\"trust\""] = "\"{}\"".format(trust)

    cni_config_json = json.dumps(cni_config)

    datanetwork = normalize_datanetwork_name(datanetwork)
    config = {
        'apiVersion': 'k8s.cni.cncf.io/v1',
        'kind': 'NetworkAttachmentDefinition',
        'metadata': {
            'name': normalize_metadata_name(name),
            'annotations': {
                'k8s.v1.cni.cncf.io/resourceName': 'intel.com/pci_sriov_net_{}'.format(datanetwork)
            },
        },
        'spec': {'config': cni_config_json},
    }
    content = yaml.dump(config, default_flow_style=False)

    return file_utilities.create_file(filename, content)


def create_network_attachment_definition(
    nadname,
    datanetwork,
    cni_type="sriov",
    vlan=None,
    ipam=None,
    mac=None,
    spoofchk=None,
    trust=None,
    file_path=None,
    datastore_type="\"kubernetes\"",
    kubernetes={"\"kubeconfig\"": "\"/etc/cni/net.d/calico-kubeconfig\""},
):
    """
    Create a network attachment definition .yaml file on the active controller
    Args:
        nadname (str): The name of the network attachment definition
        datanetwork (str): The datanetwork of the network attachment definition
        cni_type (str): The CNI type of the network attachment definition
        vlan (int): The VLAN id of the network attachment definition
        ipam (dict): The IPAM config for the network attachment definition
        mac (str): The MAC address of the network attachment definition
        spoofchk (str): The spoofchk value for the network attachment definition
        trust (str): The trust value for the network attachment definition
        file_path (str): The path to the yaml file
        datastore_type (str): Data store type
        kubernetes (str): kubernetes config

    Returns filename (str)
    """
    if file_path is None:
        file_path = '/tmp/netdef_{}.yaml'.format(nadname)
    create_network_attachment_definition_yaml(
        file_path,
        nadname,
        datanetwork,
        cni_type,
        vlan,
        ipam,
        mac,
        spoofchk,
        trust,
        datastore_type=datastore_type,
        kubernetes=kubernetes,
    )
    return file_path


def get_pod_pci_device_info(podname):
    """
    Get the PCI device info for SR-IOV interfaces in a pod
    Args:
        podname (str): The name of the pod to check

    Returns devices (list): A list of SR-IOV interface PCI information
    """

    def ordered_by_pci(elem):
        """
        Specify that the pci address should define the order of the device
        info list (lower PCI address first)
        """
        return int(elem['pci_address'][-1])

    cmd = "printenv"
    cmd += " | grep PCIDEVICE"
    cmd += " | awk -FPCIDEVICE_INTEL_COM_PCI_SRIOV_NET_ '{print $2}'"
    code, output = kube_helper.exec_cmd_in_container(cmd, pod=podname, namespace='default')

    devices = []
    for line in output.splitlines():
        datanetwork, pci_addrs = line.split('=')
        datanetwork = datanetwork.lower()

        pci_addrs = pci_addrs.split(',')
        for addr in pci_addrs:
            drvpath = '/sys/bus/pci/devices/{}/driver/module/drivers/'.format(addr)

            # Get the driver symlink
            cmd = 'ls {}'.format(drvpath)
            code, links = kube_helper.exec_cmd_in_container(cmd, pod=podname, namespace='default')

            link = None
            links = links.split()
            for link_iterator in links:
                if "pci" in link_iterator:
                    link = link_iterator
                    break

            assert link is not None, "unable to find drivers at {}".format(drvpath)
            # Read the driver symlink to get the actual driver name
            cmd = 'readlink {}{}'.format(drvpath, link)
            code, output = kube_helper.exec_cmd_in_container(cmd, pod=podname, namespace='default')

            driver = output.rsplit('/')[-1]

            # Get the kernel interface name (netdevice)
            cmd = 'dir /sys/bus/pci/devices/{}/net/'.format(addr)
            code, output = kube_helper.exec_cmd_in_container(
                cmd, pod=podname, namespace='default', fail_ok=True
            )
            if code > 0:
                ifname = None
            else:
                ifname = output

            devices.append(
                {
                    'datanetwork': datanetwork,
                    'pci_address': addr,
                    'driver': driver,
                    'ifname': ifname,
                }
            )

    devices.sort(key=ordered_by_pci)
    return devices


def get_pod_interfaces(pod_name, namespace="default", filter_name=None):
    """
    Get the pod interfaces' info by running ip link show
    Args:
        pod_name (str): The name of the pod to check.
        namespace (str): The name space that pod is created.
        filter_name (str): The filter to grep output based on that.

    Return interfaces (dict): A Dictionary of interfaces with corresponding fields.
    """

    interfaces_dict = dict()
    cmd = "ip link show"
    regex = (
        r'\d+:\s+(?P<interface_name>\S+):\s+<(?P<mode>\S+)>'
        r'\s+mtu\s+(?P<mtu>\d+)[\s\S]+state\s+(?P<state>\w+)'
    )
    LOG.info("Running {} in pod {}".format(cmd, pod_name))
    code, output = kube_helper.exec_cmd_in_container(cmd, pod=pod_name, namespace=namespace)

    for line in output.splitlines():
        match = re.match(regex, line)
        if match:
            interface_name = match.group("interface_name")
            interface_modes = match.group("mode")

            if filter_name not in interface_name:
                continue

            interfaces_dict[interface_name] = dict()
            interfaces_dict[interface_name]["mtu"] = match.group("mtu")
            interfaces_dict[interface_name]["state"] = match.group("state")
            for mode_name in interface_modes.split(","):
                interfaces_dict[interface_name][mode_name] = True

    return interfaces_dict


def create_daemoset_pod_yaml(
    daemonset_name,
    container_name,
    net_defs,
    pod_type="netdevice",
    host=None,
    file_path=None,
    label_name="daemonset_sriov",
    restart_on_reboot=True,
    ip_version=IPV4_VERSION,
    namespace='default',
    image='centos/tools',
    default_ipv6_pool=True,
):
    """
    Create a DaemonSet pod .yaml file on the active controller based on a netdevice
    (kernel interface) application
    Args:
        daemonset_name (str): The name of DaemonSet
        container_name (str): The name of the pod
        net_defs (list): The list of network attachment definitions dictionary
        pod_type (str): The type of pod to create (netdevice / DPDK)
        host (str): The host to place the pod on
        file_path (str): The absolute path to the file to create
        label_name (str): The label to assign
        restart_on_reboot (bool): The flag to add label restart-on-reboot
        ip_version (int): The IP version of the default pod network
        namespace (str): The namespace to create daemonset
        image (str): The image to create pod based on that
        default_ipv6_pool (bool): Use default-ipv6-pool or not

    Returns (exit code (int), command output (str))
    """

    def _get_netdevice_pod_spec(container_name, image):
        netdevice_pod_spec = {
            'restartPolicy': 'Always',
            'securityContext': {
                'runAsUser': 1000,
                'runAsGroup': 3000,
                'fsGroup': 2000,
            },
            'containers': [
                {
                    'name': container_name,
                    'image': image,
                    'imagePullPolicy': 'IfNotPresent',
                    'command': ['/bin/bash', '-c', '--'],
                    'args': ['while true; do sleep 300000; done;'],
                    'resources': {'requests': {}, 'limits': {}},
                }
            ],
        }

        return netdevice_pod_spec

    def _get_dpdk_pod_spec(container_name, image):
        dpdk_pod_spec = {
            'restartPolicy': 'Always',
            'containers': [
                {
                    'name': container_name,
                    'image': image,
                    'imagePullPolicy': 'IfNotPresent',
                    'command': ["/bin/bash", "-ec", "sleep infinity"],
                    'stdin': True,
                    'tty': True,
                    'volumeMounts': [{'mountPath': '/mnt/huge-1048576kB', 'name': 'hugepage'}],
                    'securityContext': {
                        'capabilities': {'add': ["IPC_LOCK", "NET_ADMIN", "NET_RAW"]}
                    },
                    'resources': {
                        'requests': {'memory': '3Gi', 'cpu': 2},
                        'limits': {'hugepages-1Gi': '2Gi', 'memory': '3Gi', 'cpu': 2},
                    },
                }
            ],
            'volumes': [{'name': 'hugepage', 'emptyDir': {'medium': 'HugePages'}}],
        }

        return dpdk_pod_spec

    assert pod_type in POD_TYPE, "pod_type should be one of {}".format(POD_TYPE)
    container_name = normalize_metadata_name(container_name)
    daemonset_name = normalize_metadata_name(daemonset_name)

    if file_path is None:
        file_path = '/tmp/daemon_set-{}.yaml'.format(daemonset_name)

    networks = ""
    data_networks = dict()

    for net_def in net_defs:
        nad_name = net_def['name']
        vfs = net_def['vfs']
        data_network = net_def['datanetwork']

        if networks != "":
            networks += ","
        networks += ",".join([nad_name] * vfs)

        data_networks[data_network] = (
            vfs if data_network not in data_networks.keys() else data_networks[data_network] + vfs
        )

    config = {
        'apiVersion': 'apps/v1',
        'kind': 'DaemonSet',
        'metadata': {
            'name': daemonset_name,
            'namespace': namespace,
            'labels': {"app": '{}'.format(label_name)},
        },
        'spec': {
            'selector': {"matchLabels": {"app": '{}'.format(label_name)}},
            'template': {
                'metadata': {
                    'labels': {'app': '{}'.format(label_name)},
                    'annotations': {'k8s.v1.cni.cncf.io/networks': '{}'.format(networks)},
                }
            },
        },
    }

    if pod_type == POD_TYPE_NETDEVICE:
        config['spec']['template']['spec'] = _get_netdevice_pod_spec(container_name, image)
    else:
        config['spec']['template']['spec'] = _get_dpdk_pod_spec(container_name, image)

    for datanetwork in data_networks.keys():
        vfs = data_networks[datanetwork]
        config['spec']['template']['spec']['containers'][0]['resources']['requests'].update(
            {'intel.com/pci_sriov_net_{}'.format(datanetwork): vfs}
        )
        config['spec']['template']['spec']['containers'][0]['resources']['limits'].update(
            {'intel.com/pci_sriov_net_{}'.format(datanetwork): vfs}
        )

    if host is not None:
        config['spec']['template']['spec'].update(
            {'nodeSelector': {'kubernetes.io/hostname': host}}
        )

    if ip_version == IPV4_VERSION:
        config['spec']['template']['metadata']['annotations'].update(
            {'cni.projectcalico.org/ipv4pools': '\"[\\"default-ipv4-ippool\\"]\"'}
        )

    elif ip_version == IPV6_VERSION and default_ipv6_pool:
        config['spec']['template']['metadata']['annotations'].update(
            {'cni.projectcalico.org/ipv6pools': '\"[\\"default-ipv6-ippool\\"]\"'}
        )

    if restart_on_reboot:
        config['spec']['template']['metadata']['labels'].update({"restart-on-reboot": "true"})

    content = yaml.dump(config, default_flow_style=False)
    file_utilities.create_file(file_path, content)

    return daemonset_name


def create_host_local_ipam_config(
    subnet, range_start=None, range_end=None, routes=None, gateway=None
):
    """
    Create IPAM config
    Args:
        subnet (str): Subnet addres of IP
        range_start (str): The start IP from a range
        range_end (str): The end IP from a range
        routes (list): List of dicts for routes information
        gateway (str): Gateway address

    Returns ipam_config (dict): A host-local compatible ipam config dictionary
    """
    ipam_config = {"\"type\"": "\"host-local\"", "\"subnet\"": "\"{}\"".format(str(subnet))}
    if range_start:
        ipam_config["\"rangeStart\""] = "\"{}\"".format(range_start)
    if range_end:
        ipam_config["\"rangeEnd\""] = "\"{}\"".format(range_end)
    if routes:
        ipam_config["\"routes\""] = routes
    if gateway:
        ipam_config["\"gateway\""] = gateway

    return ipam_config


def get_node_sriov_allocated_resources(host, data_networks=None):
    """
    Gets allocated resources for sriov

    Args:
        host (str): The name of host to get allocated sriov resources
        data_networks (list): The list of data networks which needs
        to be consider for allocated resources

    Return (dict): Dictionary of datanetworks with corresponding request and limit sriov resources
    """

    cmd = 'describe nodes {}'.format(host)
    _, output = kube_helper.exec_kube_cmd(cmd)
    allocated_sriov_vfs = {}
    for line in output.splitlines():
        match = re.match(
            r'\s+intel.com/pci_sriov_net_(?P<datanetwork>\w+)'
            r'\s+(?P<requests>\d+)\s+(?P<limits>\d+)',
            line,
        )
        if match:
            datanetwork = match.group("datanetwork")
            requests = int(match.group("requests"))
            limits = int(match.group("limits"))
            temp_dict = {datanetwork: {"requests": requests, "limits": limits}}
            if data_networks:
                if datanetwork in data_networks:
                    allocated_sriov_vfs.update(temp_dict)
            else:
                allocated_sriov_vfs.update(temp_dict)

    return allocated_sriov_vfs


def create_sriov_deployment_yaml(
    deployment_name, nads_name, image, network, vfs, replicas=None, image_pull_policy="IfNotPresent"
):
    """
    Create SRIOV POD Deployment Yaml file
    Args:
        deployment_name (str): name of deployment
        nads_name (str): name of nads seperate by ,
        image (str): image to create pods based on that
        network (str): name of network to create interfaces from that
        vfs (int): number of vfs
        replicas (int): number of replicas
        image_pull_policy (str): Image policy
    return (dict): dictionary of deployment
    """
    pod_deployment_dict = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "DEPLOYMENT_NAME", "labels": {"app": "sriov"}},
        "spec": {
            "selector": {"matchLabels": {"sriovdp": "enabled"}},
            "template": {
                "metadata": {
                    "annotations": {"k8s.v1.cni.cncf.io/networks": "NADNAME"},
                    "labels": {"sriovdp": "enabled", "restart-on-reboot": "true"},
                },
                "spec": {
                    "containers": [
                        {
                            "name": "sriov-container-1",
                            "command": [
                                "/bin/bash",
                                "-c",
                                "--",
                                "while true; do sleep 300000; done;",
                            ],
                            "image": "IMAGE",
                            "imagePullPolicy": "IfNotPresent",
                            "resources": {"requests": {}, "limits": {}},
                        }
                    ]
                },
            },
        },
    }
    pod_deployment_dict["metadata"]["name"] = deployment_name
    pod_deployment_dict["spec"]["template"]["metadata"]["annotations"][
        "k8s.v1.cni.cncf.io/networks"
    ] = nads_name
    pod_deployment_dict["spec"]["template"]["spec"]["containers"][0]["image"] = image
    pod_deployment_dict["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"][
        "intel.com/pci_sriov_net_{}".format(network)
    ] = str(vfs)
    pod_deployment_dict["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"][
        "intel.com/pci_sriov_net_{}".format(network)
    ] = str(vfs)
    pod_deployment_dict["spec"]["template"]["spec"]["containers"][0][
        "imagePullPolicy"
    ] = image_pull_policy
    if replicas:
        pod_deployment_dict["spec"]["replicas"] = replicas

    return pod_deployment_dict


class SriovVerifiers:
    def verify_pod_interfaces(
        self, pod_names, expected_interfaces, interface_filter=None, con_ssh=None
    ):
        """
        Verify specific interfaces are configured on given pods

        Args:
            - pod_names(list|str): pod names to verify on
            - interface_filter(str): a str to grep from 'printenv' cmd inside pod
            - expected_interfaces(list|str): interfaces expected to be configured on pods
        """
        if not con_ssh:
            con_name = 'RegionOne' if ProjVar.get_var('IS_DC') else None
            con_ssh = ControllerClient.get_active_controller(name=con_name)
        if isinstance(pod_names, str):
            pod_names = [pod_names]
        if isinstance(expected_interfaces, str):
            expected_interfaces = [expected_interfaces]
        for pod in pod_names:
            cmd = "printenv"
            if interface_filter:
                cmd += " | grep --color=never {}".format(interface_filter)
            configured_interfaces = kube_helper.exec_cmd_in_container(cmd, pod)[1]
            LOG.info('{} sriov interfaces: \n {}'.format(pod, configured_interfaces))
            failed_interfaces = []
            msg = 'Some interface/s  are not configured on {}: {}'
            for interface in expected_interfaces:
                if interface not in configured_interfaces:
                    failed_interfaces.append(interface)
            assert not failed_interfaces, msg.format(pod, failed_interfaces)

    def verify_sriov_pods_status(self, pods_name, expected_values):
        """
        Verify the status of pods to be the same as expected values
        Args:
            pods_name (srt|list): name of pods
            expected_values (dict): Expected status of each pod
            Example: {"pod_name1": "Running", "pod_name2": "Terminating"}

        Return None
        """
        exception_list = []
        actual_values = kube_helper.get_pods(field=["NAME", "STATUS"], pod_names=pods_name)
        for actual_value in actual_values:
            pod_name, status = actual_value
            if status != expected_values[pod_name]:
                LOG.warning(
                    "POD {} expected to be in {} while actual value is {}".format(
                        pod_name, expected_values[pod_name], status
                    )
                )
                exception_list.append(pod_name)

        assert not exception_list, LOG.error(
            "Not all pods {} has expected status".format(pods_name)
        )

    def verify_number_of_sriov_interface(self, podname, expected_vfs, pod_type):
        """
        Verify the number of sriov interfaces on pod
        Args:
            podname: nameof pod
            expected_vfs: expected number of vfs in pod podname
        Return: None
        """
        devices = get_pod_pci_device_info(podname)
        net_devices = []
        dpdk_devices = []
        for device in devices:
            if pod_type == POD_TYPE_DPDK:
                for driver in ['vfio', 'mlx']:
                    if driver in device['driver']:
                        dpdk_devices.append(device)

            else:
                if device['ifname'] is not None:
                    net_devices.append(device)

        assert len(devices) == expected_vfs

        if pod_type == POD_TYPE_DPDK:
            assert (
                len(dpdk_devices) == expected_vfs
            ), "Number of dpdk devices: {} is not the same as expected: {}".format(
                dpdk_devices, expected_vfs
            )
        else:
            assert (
                len(net_devices) == expected_vfs
            ), "Number of netdevices: {} is not the same as expected: {}".format(
                net_devices, expected_vfs
            )

    def verify_allocated_vfs(self, host, expected_values):
        """
        Verify the number of allocated sriov vfs to be the same as expected ones on host

        Args:
            host (str): name of host where the pods are created
            expected_values (dict): Dictionary of datanetworks with corresponding
            expected request and limit values,
            Example: {name_of_data_network: {"requests": #vfs, "limits": #vfs}}

        Return (None)
        """
        data_networks = list(expected_values.keys())
        allocated_sriov_vfs = get_node_sriov_allocated_resources(host, data_networks)
        assert (
            allocated_sriov_vfs == expected_values
        ), "Allocated sriov resource is not the same as expected values"

