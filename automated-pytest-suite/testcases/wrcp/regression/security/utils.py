import re
import socket
import time
from subprocess import PIPE, STDOUT, Popen, check_output
from urllib.parse import urlsplit

import yaml

from consts.auth import HostLinuxUser, Tenant
from consts.proj_vars import ProjVar
from framework.runner.system_info.os.os_manager import OSManager
from framework.runner.system_info.os.os_types import OSTypes
from framework.runner.system_info.wrcp import version_manager_wrcp
from framework.runner.system_info.wrcp.versions_wrcp import WRCPVersion
from keywords import common, dc_helper, keystone_helper, kube_helper, system_helper
from keywords.general import file_utilities
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG


def get_regions_list(return_all=True):
    """
    Returns the regions list if DC otherwise returns ["non_dc"]
    Args:
        return_all (bool):default True
    Return: list of regions
    """
    if ProjVar.get_var('IS_DC'):
        regions_list = list()
        regions_list.append('central_region')
        con_ssh = ControllerClient.get_active_controller()
        active_subclouds = dc_helper.get_subclouds(
            field='name', avail='online', mgmt='managed', con_ssh=con_ssh
        )
        if return_all:
            return regions_list + active_subclouds
        if active_subclouds:
            regions_list.append("subcloud")
        return regions_list
    return ["RegionOne"]


def create_file_on_controller(filenames, src_dir, dest_dir, con_ssh=None):
    """
    Create files on the controller
    Args:
        filenames (str|list): files to be created on controller
        con_ssh (obj): ssh conn of lab, default is None
    """
    if isinstance(filenames, str):
        filenames = [
            filenames,
        ]
    for filename in filenames:
        content = common.get_yaml_data("{}/{}".format(src_dir, filename), multiple_docs=True)
        data = yaml.dump_all(content, default_flow_style=False)
        LOG.info("Create the {} file on active controller".format(filename))
        file_utilities.create_file("{}/{}".format(dest_dir, filename), data, con_ssh=con_ssh)


def get_dnsname(region):
    """
    Returns dnsname of the region
    Args:
        region (str): region name
    Returns (str): dnsname of the region
    """
    if ProjVar.get_var('IS_DC'):
        name = ProjVar.get_var('lab')[region]['name']
    else:
        name = ProjVar.get_var('lab')['name']
    return "{}.{}".format(name.split('yow-', 1)[-1].replace('_', '-'), "cumulus.wrs.com")


def exec_cmd_on_controller(cmd, con_ssh=None):
    """
    Execute the command on the active controller,verify exit status and
    return the output
    Args:
        cmd (str): command to execute
        con_ssh (obj): ssh conn of lab, default is None
    Returns:
        returns code,ouput
    """
    LOG.info("Execute '{}' on active controller".format(cmd))
    code, output = con_ssh.exec_cmd(cmd=cmd, fail_ok=False)
    return code, strip_ansi_codes(output)


def strip_ansi_codes(s):
    """
    Method to filter out the ansi-escape-sequences
    For example:
        the string'\x1b[0m\x1b[01;32m/usr/local/share/applications/helm/vault-1.0-9.tgz\x1b[0m'
        is stripped of all the ansi characters and
        returns "/usr/local/share/applications/helm/vault-1.0-9.tgz"
    Returns:
        stripped output
    """
    return re.sub(r'\x1b\[([0-9,A-Z]{1,2}(;[0-9]{1,2})?(;[0-9]{3})?)?[m|K]?', '', s)


def create_cert_file_on_controller(
    secret_name, jsonpath="{.data.tls\\.crt}", namespace="default", output_file=None, con_ssh=None
):
    """
    Extract the secret and create the cert file on controller
    Args:
        secret_name(str): name of the secret
        jsonpath(str): jsonpath of secret
        namespace(str): namespace
        con_ssh (obj): ssh conn of lab, default is None
    """
    cert = kube_helper.get_resource_value_jsonpath(
        "secret", secret_name, jsonpath=jsonpath, namespace=namespace, con_ssh=con_ssh
    )
    if not output_file:
        output_file = "{}.pem".format(secret_name)
    cmd = "echo {} | base64 --decode > {}".format(cert, output_file)
    LOG.info("Create the cert file on controller with command '{}'".format(cmd))
    exec_cmd_on_controller(cmd=cmd, con_ssh=con_ssh)


def wait_for_expected_exit_code(func, expected_rc=0, timeout=300, **kwargs):
    """
    Method to verify the expected status of the executed command within the given time
    otherwise raises exception
    Args:
        cmd (str): command to execute on active controller
        expected_rc (any type): expected exit code
        timeout (int): default set to 300
        con_ssh (obj): ssh conn of lab
    Returns (str|excep): returns the expected value or raises exception
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        actual_rc, out = func(**kwargs)
        LOG.info(
            "expected exit code: {}, actual exit code: {}, output is '{}'".format(
                expected_rc, actual_rc, out
            )
        )
        if actual_rc == expected_rc:
            return actual_rc, strip_ansi_codes(out)
        time.sleep(5)
    raise AssertionError(
        "expected exit code: {}, actual exit code: {}".format(expected_rc, actual_rc)
    )


def check_dnsname_resolution(region):
    """
    Method to verify the dnsname resolution of the lab
    Args:
        region (str): region name
    Returns (bool): True|False
    """
    family = socket.AF_INET
    oam_fip = common.get_lab_fip(region=region)
    dnsname = get_dnsname(region)
    LOG.info("Checking the dns lookup of the system with 'nslookup {}'".format(dnsname))
    if common.get_ip_version(ip_addr=oam_fip) == 6:
        family = socket.AF_INET6
    try:
        socket.getaddrinfo(dnsname, None, family)
        return True
    except socket.error as msg:
        LOG.info("nslookup failed with error '{}'".format(msg))
        return False


def get_mgmt_ip_of_region(
    region="RegionOne", service_name="keystone", interface="internal", con_ssh=None, auth_info=None
):
    """
    Get the management ip of the region
    Args:
        region (str): Region name
        auth_info (dict|None): Tenant dict
        con_ssh (obj): ssh conn of the lab,default is None
        service_name (str): service name, default is keystone
        interface (str): default is internal
    Returns: returns mgnt_ip of the region
    """
    if region == "central_region":
        region = "RegionOne"
    keystone_url = keystone_helper.get_endpoints(
        field='URL',
        service_name=service_name,
        interface=interface,
        region=region,
        auth_info=auth_info,
        con_ssh=con_ssh,
    )[-1]
    url = urlsplit(keystone_url)
    return url.hostname


def ensure_endpoint_list(region, include_registry=False):
    """
    Method returns the platform endpoint list
        configuration api:  https://<dns_name>:6385/v1
        dcmanager : https://<dns_name>:8119/v1.0
        faultmanagement:  https://<dns_name>:18002
        stx ha services:  https://<dns_name>:7777
        nfv vim api:  https://<dns_name>:4545/api/
        patching api:  https://<dns_name>:15491
        keystone : https://<dns_name>:5000/v3
        horizon : https://<dns_name>:8443
    Args:
        region (str): region of the lab
    Return:
        returns the endpoint list
    """
    dns_name = get_dnsname(region)
    url_tags = ["6385/v1", "5000/v3", "8443", "18002", "4545/api", "7777"]
    if ProjVar.get_var('IS_DC'):
        if region in ["central_region", "RegionOne"]:
            url_tags.append("8119/v1.0")
        else:
            # Subcloud's Horizon api is not accessible on floating ip in DC
            url_tags.remove("8443")
    urls = ["https://{}:{}".format(dns_name, tag) for tag in url_tags]
    if include_registry:
        urls.append("https://registry.local:9001")
        if ProjVar.get_var('IS_DC'):
            urls.append("https://registry.central:9001")
    return urls


def generate_cert_data(
    cert_name,
    secret_name=None,
    dns_names=None,
    ip_addresses=None,
    issuer_name="cloudplatform-interca-issuer",
    issuer_kind="Issuer",
    namespace="default",
    duration="2160h",
    renew_before="360h",
    is_ca=False,
    common_name=None,
):
    """
    Returns the yaml data for the Certificate request
    Args:
        cert_name (str): Certificate name
        dns_name (list): dns names of the lab
        issuer_name (str): certificate issuer
        issuer_kind (str): issuer kind
        ip_addresses (list) : ip addresses of the lab
        is_ca (bool) : default is false
        common_name (str) : common name
    Returns:
        returns the yaml data
    """
    api_version = "cert-manager.io/v1alpha2"
    sw_version = version_manager_wrcp.VersionManagerWRCP.get_sw_version()
    if sw_version.is_after_or_equal_to(WRCPVersion.WRCP_22_02):
        api_version = "cert-manager.io/v1"

    if not secret_name:
        secret_name = cert_name
    spec = {
        "secretName": secret_name,
        "duration": duration,
        "renewBefore": renew_before,
        "issuerRef": {"name": issuer_name, "kind": issuer_kind},
    }
    if is_ca:
        spec["commonName"] = common_name
        spec["isCA"] = True
    else:
        spec["dnsNames"] = dns_names
        spec["ipAddresses"] = ip_addresses
    cert_request = {
        "apiVersion": api_version,
        "kind": "Certificate",
        "metadata": {"name": cert_name, "namespace": namespace},
        "spec": spec,
    }
    data = yaml.dump(cert_request, default_flow_style=False)
    return data


def generate_issuer_data(issuer_name, secret_name, namespace="default"):
    """
    Returns the yaml data for the issuer request
    Args:
        issuer_name (str): issuer name
        secret_name (str): secret name
        namespace (str): name of namespace
    Returns:
        returns the yaml data
    """
    api_version = "cert-manager.io/v1alpha2"
    sw_version = version_manager_wrcp.VersionManagerWRCP.get_sw_version()
    if sw_version.is_after_or_equal_to(WRCPVersion.WRCP_22_02):
        api_version = "cert-manager.io/v1"
    issuer_request = {
        "apiVersion": api_version,
        "kind": "Issuer",
        "metadata": {"name": issuer_name, "namespace": namespace},
        "spec": {"ca": {"secretName": secret_name}},
    }
    data = yaml.dump(issuer_request, default_flow_style=False)
    return data


def get_cluster_issuer_data(cluster_issuer_name):
    """
    Returns the yaml data for the cluster_issuer request
    Args:
        cluster_issuer_name (str): issuer name
    Returns:
        returns the yaml data
    """
    api_version = "cert-manager.io/v1alpha2"
    sw_version = version_manager_wrcp.VersionManagerWRCP.get_sw_version()
    if sw_version.is_after_or_equal_to(WRCPVersion.WRCP_22_02):
        api_version = "cert-manager.io/v1"
    issuer_request = {
        "apiVersion": api_version,
        "kind": "ClusterIssuer",
        "metadata": {
            "name": cluster_issuer_name,
        },
        "spec": {"selfSigned": {}},
    }
    data = yaml.dump(issuer_request, default_flow_style=False)
    return data


def deploy_cm_resource(
    yaml_data, resource_name, resource_type="certificate", con_ssh=None, namespace="default"
):
    """
    Helper method to create and deploy the cert-manager resource
    Args:
        yaml_data (obj): yaml data
        cert_name (str): certificate name
        con_ssh (obj): ssh conn of lab, default is None
        namespace (str): namespace, default is "default"
    """
    system_dir = HostLinuxUser.get_home()

    LOG.info("Create {}.yaml on active controller".format(resource_name))
    file_utilities.create_file(
        "{}/{}".format(system_dir, "{}.yaml".format(resource_name)), yaml_data, con_ssh=con_ssh
    )
    LOG.info("Deploy {}.yaml on active controller".format(resource_name))
    kube_helper.apply_resource(
        "{}/{}".format(system_dir, "{}.yaml".format(resource_name)), con_ssh=con_ssh
    )

    LOG.info("Verify that {} {} is issued".format(resource_type, resource_name))
    kube_helper.wait_for_resource_value(
        resource_type,
        resource_name,
        "{.status.conditions[0].status}",
        "True",
        con_ssh=con_ssh,
        namespace=namespace,
    )


def delete_the_certs(certs, namespace, con_ssh, region):
    """
    Helper method to delete the certs
    Args:
        certs (list or str): certificates to delete
        namespace (str):
        con_ssh (obj):
        region (str):
    """
    if isinstance(certs, str):
        certs = [certs]
    for resource_type in ["certificate", "secret"]:
        for resource_name in certs:
            LOG.info("{}:Delete the {} '{}' if exist".format(region, resource_type, resource_name))
            kube_helper.delete_resources(
                resource_names=resource_name,
                resource_types=resource_type,
                namespace=namespace,
                ignore_not_found="True",
                con_ssh=con_ssh,
            )


def generate_ingress_data(
    ingress_name, issuer_name, secret_name, host_name, service_name, namespace="default"
):
    """
    Returns the yaml data for the issuer request
    Args:
        issuer_name (str): issuer name
        secret_name (str): secret name
        host_name (str): lab dns name
        service_name (str): service name
        namespace (str): name of namespace
    Returns:
        returns the yaml data
    """
    ingress_request = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "annotations": {
                "cert-manager.io/issuer": issuer_name,
                "kubernetes.io/ingress.class": "nginx",
            },
            "name": ingress_name,
            "namespace": namespace,
        },
        "spec": {
            "rules": [
                {
                    "host": host_name,
                    "http": {
                        "paths": [
                            {
                                "backend": {
                                    "service": {"name": service_name, "port": {"number": 80}}
                                },
                                "path": "/",
                                "pathType": "Prefix",
                            }
                        ]
                    },
                }
            ],
            "tls": [{"hosts": [host_name], "secretName": secret_name}],
        },
    }

    data = yaml.dump(ingress_request, default_flow_style=False)
    return data


def remove_ssl_ca_if_exist(cert_subject, con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """Starting from 22.12 onwards, when ssl_ca cert is installed the system checks if
    the cert with same CN is already exist and notify user with message
    "Please uninstall the following CA certs that have the same subject first" , so this
    method removes the cert if exist already with same subject.
    Args:
        cert_subject (str): cert subject
        con_ssh (obj): con_ssh object
        auth_info (obj): auth_info
    """

    cert_uuids = system_helper.get_certificates(
        con_ssh=con_ssh, auth_info=auth_info, certtype='ssl_ca'
    )
    for uuid in cert_uuids:
        subject = system_helper.get_certificate_values(
            uuid, 'subject', con_ssh=con_ssh, auth_info=auth_info
        )
        if subject == cert_subject:
            system_helper.uninstall_certificate(
                uuid, mode='ssl_ca', con_ssh=con_ssh, auth_info=auth_info
            )


def exec_cmd_on_test_server(cmd, **kwargs):
    """
    Executes the given command and captures the output
    Args:
        cmd (str): cmd to execute
    """
    check_output("{} ; echo 0".format(cmd), shell=True, stderr=STDOUT, **kwargs)

