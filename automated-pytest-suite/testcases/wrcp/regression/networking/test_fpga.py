import json
import re
import time
from collections import OrderedDict

import pytest
from pytest import mark

from consts.proj_vars import ProjVar
from consts.stx import HostOperState
from consts.timeout import DeviceImageTimeout
from keywords import common, device_helper, host_helper, kube_helper, sriov_helper, system_helper
from keywords.devices import fec_device_keywords
from testcases.wrcp.regression.networking.test_sriovdp import (
    DPDK_HUGEPAGE_REQD,
    DPDK_POD_CPUS_REQD,
    INTERFACE_CLASS_PCI_SRIOV,
    POD_TYPE_DPDK,
    Host,
    PodCpu,
    TestPmd,
    check_system_compatibility,
    create_dpdk_pod,
)
from testfixtures.recover_hosts import HostsToRecover
from utils import cli, exceptions, table_parser
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG

BMC_IMAGE_WITH_RETIMER_6_1 = "VistaCreekBravoBMCFW_Release_WW16.1.bin"
BMC_IMAGE_WITH_RETIMER_5_5 = "VistaCreekBravoBMCFW_Release_WW05.5.bin"
REVERT_IMAGE = "VistaCreekBravoBMCFW_Release_WW05.5.bin"
UNSIGNED_IMAGE = "5gldpc_1x2x25g_20ww2.3_swap_ddr4_2xrefresh-unsigned.bin"
ROOT_PUBLIC_PROGRAM_SSL_IMAGE = "root_public_program_ssl.bin"
SSL_CSK_IMAGE = "ssl_csk1_cancel.bin"


@pytest.fixture(scope='module', autouse=True)
def check_lab_fpga_info():
    """
    Check whether the lab has fpga constants.
    Skip test if there is no fpga constants (meaning no fpga is installed for this lab).

    Returns: None

    """
    lab = ProjVar.get_var('lab')
    if 'fpga' not in lab:
        pytest.skip('Lab lacks fpga related info: {}'.format(lab))
    return lab['fpga']


@pytest.fixture(scope='module', autouse=True)
def assign_intelfpga_label(check_lab_fpga_info):
    """
    Assign intelfpga label on fpga hosts

    Args:
        check_lab_fpga_info: module fixture

    Returns: None

    """
    FPGA_LABEL = 'intelfpga'
    hosts = list(check_lab_fpga_info)
    LOG.fixture_step('Assign {} label on hosts: {}'.format(FPGA_LABEL, hosts))
    hosts_to_assign = []
    for host in hosts:
        labels = host_helper.get_host_labels_info(host)
        if labels.get(FPGA_LABEL, '') != 'enabled':
            hosts_to_assign.append(host)
    for host in hosts_to_assign:
        host_helper.assign_host_labels(
            host, [FPGA_LABEL], check_first=False, lock=False, unlock=False, overwrite=True
        )
    yield
    LOG.fixture_step('Remove {} label on hosts: {}'.format(FPGA_LABEL, hosts_to_assign))
    for host in hosts_to_assign:
        host_helper.remove_host_labels(host, [FPGA_LABEL], lock=False, unlock=False)


@pytest.fixture(scope='function')
def get_device_fpga(request):
    """
    Find and select a fpga device on a host.

    Returns:
        con_ssh (SSHClient): Active controller ssh session
        host_under_test (str): Host which has been selected for testing
        device_name_under_test (str): The device which has been selected for testing
        pci_vendor (str): pci vendor of the selected device
    """
    con_ssh = ControllerClient.get_active_controller()

    LOG.fixture_step("Get the FPGA devices on this lab")
    host_rsu_device_fpga_dict = FpgaLib.get_rsu_device_fpga(con_ssh)
    if not host_rsu_device_fpga_dict:
        pytest.mark.skip("Lab does not have any host with FPGA card with device_id=0b30")

    host_under_test = list(host_rsu_device_fpga_dict.keys())[0]
    device_name_under_test = list(host_rsu_device_fpga_dict[host_under_test].keys())[0]
    pci_vendor = host_rsu_device_fpga_dict[host_under_test][device_name_under_test]
    LOG.info(
        "host {} device {} with pci {} has been selected for this testcase".format(
            host_under_test, device_name_under_test, pci_vendor
        )
    )

    device_name = "pci_" + device_name_under_test.replace(":", "_").replace(".", "_")
    initial_device_labels = device_helper.get_host_device_labels(
        host=host_under_test, device=device_name, fields='label key'
    )

    initial_device_images_list = device_helper.get_device_images(con_ssh=con_ssh)

    def teardown():
        """
        Teardown the TC

        - Revert the image back to its initial image if needed
        - Delete labels on devices
        - Delete uploaded images
        - Delete copied images at /tmp/
        """
        global resources_to_delete
        global controller_to_lock_unlock
        global revert_is_needed
        file_names = []

        if revert_is_needed:
            LOG.banner(
                "Revert image on device {} host {}".format(device_name_under_test, host_under_test)
            )
            reveret_iamge_path = "/tmp/{}".format(REVERT_IMAGE)
            LOG.fixture_step(
                "Revert back the image for device {} on host {} using {}".format(
                    device_name_under_test, host_under_test, REVERT_IMAGE
                )
            )

            LOG.fixture_step("Copy the revert image {} to /tmp/".format(REVERT_IMAGE), depth=1)
            common.scp_from_localhost_to_active_controller(
                source_path="utils/test_files/N3000_images/{}".format(REVERT_IMAGE),
                dest_path=reveret_iamge_path,
            )
            resources_to_delete.append({'file': reveret_iamge_path})

            FpgaLib.apply_image_on_device(
                con_ssh,
                host_under_test,
                device_name_under_test,
                pci_vendor,
                labels=('revert_label', 'revert'),
                image_path=reveret_iamge_path,
                bmc=True,
                retimer_included=True,
                log_type="fixture_step",
                depth=1,
            )

        new_device_labels = device_helper.get_host_device_labels(
            host=host_under_test, device=device_name, fields='label key'
        )
        diff_device_labels_list = list(set(new_device_labels) - set(initial_device_labels))

        if diff_device_labels_list:
            LOG.fixture_step(
                "Remove labels {} on host {} for device {}".format(
                    diff_device_labels_list, host_under_test, device_name
                )
            )

            device_helper.remove_host_device_labels(
                host=host_under_test,
                device=device_name,
                labels=diff_device_labels_list,
                fail_ok=True,
            )

        new_device_images_list = device_helper.get_device_images(con_ssh=con_ssh)
        diff_device_images_list = list(
            set(new_device_images_list) - set(initial_device_images_list)
        )

        if diff_device_images_list:
            LOG.fixture_step("Remove images {}".format(diff_device_images_list))
            for device_image_uuid in diff_device_images_list:
                device_helper.delete_device_image(
                    device_image_uuid=device_image_uuid, con_ssh=con_ssh, fail_ok=True
                )

        LOG.info('Cleanup resources if any.')
        while resources_to_delete:
            to_delete = resources_to_delete.pop()
            file = to_delete.get('file', None)
            if file is not None:
                file_names.append(file)

        if file_names:
            LOG.fixture_step("Delete files {}".format(file_names))
        for file_name in list(set(file_names)):
            LOG.fixture_step("Delete file {}".format(file_names), depth=1)
            con_ssh.exec_sudo_cmd('rm -f {}'.format(file_name), fail_ok=True)

        if controller_to_lock_unlock:
            LOG.fixture_step("Lock/unlock host {}".format(controller_to_lock_unlock[0]))
            host_helper.lock_unlock_hosts(controller_to_lock_unlock[0])

    request.addfinalizer(teardown)

    return con_ssh, host_under_test, device_name_under_test, pci_vendor


@pytest.fixture(scope='function')
def get_devices_same_host(request):
    """
    Find and select multiple fpga devices on a host.

    Returns:
        con_ssh (SSHClient): Active controller ssh session
        host_under_test (str): Host which has been selected for testing
        devices_name_under_test_dict (dict): The devices which have been selected for
        testing with corresponding pci_vendor
    """
    host_under_test = None
    devices_name_under_test_dict = OrderedDict()
    initial_device_labels_dict = dict()
    con_ssh = ControllerClient.get_active_controller()

    LOG.fixture_step("Get the FPGA devices on this lab")
    host_rsu_device_fpga_dict = FpgaLib.get_rsu_device_fpga(con_ssh)

    if not host_rsu_device_fpga_dict:
        pytest.mark.skip("Lab does not have any host with FPGA card with device_id=0b30")

    for host, fpga_devices_dict in host_rsu_device_fpga_dict.items():
        if len(fpga_devices_dict) > 1:
            LOG.info("Host {} has more than one fpga devices {}".format(host, fpga_devices_dict))

            host_under_test = host
            devices_name_under_test_dict = fpga_devices_dict
            break

    if host_under_test is None:
        pytest.mark.skip(
            "Lab does not have any host with more than one FPGA card with device_id=0b30"
        )

    for device_name_under_test in devices_name_under_test_dict.keys():
        device_name = "pci_" + device_name_under_test.replace(":", "_").replace(".", "_")
        initial_device_labels_dict[device_name] = device_helper.get_host_device_labels(
            host=host_under_test, device=device_name, fields='label key'
        )

    initial_device_images_list = device_helper.get_device_images(con_ssh=con_ssh)

    def teardown():
        global resources_to_delete
        global controller_to_lock_unlock
        global revert_is_needed
        file_names = []

        if revert_is_needed:
            LOG.banner(
                "Revert image on devices {} host {}".format(
                    list(devices_name_under_test_dict.keys()), host_under_test
                )
            )

            reveret_iamge_path = "/tmp/{}".format(REVERT_IMAGE)
            LOG.fixture_step(
                "Revert back the image for device {} on host {} using {}".format(
                    list(devices_name_under_test_dict.keys()), host_under_test, REVERT_IMAGE
                )
            )

            LOG.fixture_step("Copy the revert image {} to /tmp/".format(REVERT_IMAGE), depth=1)
            common.scp_from_localhost_to_active_controller(
                source_path="utils/test_files/N3000_images/{}".format(REVERT_IMAGE),
                dest_path=reveret_iamge_path,
            )
            resources_to_delete.append({'file': reveret_iamge_path})

            device_name_1_under_test = list(devices_name_under_test_dict.keys())[0]
            pci_vendor = devices_name_under_test_dict[device_name_1_under_test]

            LOG.tc_step(
                "Upload and apply image {} on device {} on host {}".format(
                    reveret_iamge_path, device_name_1_under_test, host_under_test
                )
            )
            _, device_image_uuid_revert = FpgaLib.apply_image_on_device(
                con_ssh,
                host_under_test,
                device_name_1_under_test,
                pci_vendor,
                labels=('revert_label', 'revert'),
                image_path=reveret_iamge_path,
                bmc=True,
                retimer_included=True,
                update_device_image=False,
            )

            device_name_2_under_test = list(devices_name_under_test_dict.keys())[1]
            pci_vendor = devices_name_under_test_dict[device_name_2_under_test]

            (_, _) = FpgaLib.apply_image_on_device(
                con_ssh,
                host_under_test,
                device_name_2_under_test,
                pci_vendor,
                labels=('revert_label', 'revert'),
                image_path=reveret_iamge_path,
                bmc='',
                retimer_included='',
                update_device_image=False,
                upload_image=False,
            )

            LOG.fixture_step(
                "Update images for devices {} on host {}".format(
                    devices_name_under_test_dict.keys(), host_under_test
                ),
            )
            device_helper.update_device_image(host_name=host_under_test)

            LOG.tc_step(
                "Wait for image {} status on host {} to be Completed".format(
                    device_image_uuid_revert, device_name_1_under_test
                )
            )
            device_helper.wait_for_device_image_status(
                host=host_under_test,
                pci_device_address=device_name_1_under_test,
                device_image_uuid=device_image_uuid_revert,
                timeout=2 * DeviceImageTimeout.COMPLETE,
            )

            LOG.tc_step(
                "Wait for image {} status on host {} to be Completed".format(
                    device_image_uuid_revert, device_name_2_under_test
                )
            )
            device_helper.wait_for_device_image_status(
                host=host_under_test,
                pci_device_address=device_name_2_under_test,
                device_image_uuid=device_image_uuid_revert,
                timeout=2 * DeviceImageTimeout.COMPLETE,
            )
            LOG.tc_step("Lock/unlock host {}".format(host_under_test))
            host_helper.lock_unlock_hosts(host_under_test)

        for device_name_under_test in devices_name_under_test_dict.keys():
            device_name = "pci_" + device_name_under_test.replace(":", "_").replace(".", "_")
            new_device_labels = device_helper.get_host_device_labels(
                host=host_under_test, device=device_name, fields='label key'
            )

            diff_device_labels_list = list(
                set(new_device_labels) - set(initial_device_labels_dict[device_name])
            )

            if diff_device_labels_list:
                LOG.fixture_step(
                    "Remove labels {} on host {} for device {}".format(
                        diff_device_labels_list, host_under_test, device_name
                    )
                )

                device_helper.remove_host_device_labels(
                    host=host_under_test,
                    device=device_name,
                    labels=diff_device_labels_list,
                    fail_ok=True,
                )

        new_device_images_list = device_helper.get_device_images(con_ssh=con_ssh)
        diff_device_images_list = list(
            set(new_device_images_list) - set(initial_device_images_list)
        )

        if diff_device_images_list:
            LOG.fixture_step("Remove images {}".format(diff_device_images_list))
            for device_image_uuid in diff_device_images_list:
                device_helper.delete_device_image(
                    device_image_uuid=device_image_uuid, con_ssh=con_ssh, fail_ok=True
                )

        LOG.info('Cleanup resources if any.')
        while resources_to_delete:
            to_delete = resources_to_delete.pop()
            file = to_delete.get('file', None)
            if file is not None:
                file_names.append(file)

        if file_names:
            LOG.fixture_step("Delete files {}".format(file_names))
        for file_name in list(set(file_names)):
            LOG.fixture_step("Delete file {}".format(file_names), depth=1)
            con_ssh.exec_sudo_cmd('rm -f {}'.format(file_name), fail_ok=True)

        if controller_to_lock_unlock:
            LOG.fixture_step("Lock/unlock host {}".format(controller_to_lock_unlock[0]))
            host_helper.lock_unlock_hosts(controller_to_lock_unlock[0])

    request.addfinalizer(teardown)

    return con_ssh, host_under_test, devices_name_under_test_dict


class FpgaLib(object):
    @staticmethod
    def get_allocatable_fpga():
        """
        Get k8s node Allocatable fpga.intel.com resource.

        Returns (list):
            ['fpga.intel.com/af-9aeffe5f84570612c000c9660d824272:  1',
             'fpga.intel.com/af-9aeffe5f84570612c000c9660d824272:  1']

        """
        code, out = kube_helper.exec_kube_cmd('describe node', grep='-E "^Allocatable" -A10')
        return re.findall(r'^\s*(fpga.intel.com.*)\s*$', out, re.M)

    @staticmethod
    def get_detected_card(host):
        """
        Get fpga accelerators on host.

        Args:
            host (str): host name

        Returns (list): [<detected fpga accelerator info>]

        """
        with host_helper.ssh_to_host(host) as host_ssh:
            code, out = host_ssh.exec_sudo_cmd('lspci -kv | grep --color=never accelerators -A 16')
        return re.findall(r'Processing accelerators: Intel Corporation Device', out, re.S)

    @staticmethod
    def get_host_sensor_list(host):
        """
        Get sensors on host.

        Args:
            host (str): host name

        Returns (list): [<sensor name>, <sensor name>]

        """
        code, out = cli.system('host-sensor-list', positional_args=host)
        return table_parser.get_values(table_parser.table(out), 'name')

    @staticmethod
    def unlock_host_with_retries(host, retries_timeout=300, interval=60, **kwargs):
        """
        unlock host with retry for unlock failure.
        E.g. After fpga device is modified, the runtime manifest has not been fully applied.

        Args:
            host (str): host to unlock
            retries_timeout (int): seconds of timeout
            interval (int): seconds of interval between retries
            **kwargs: kwargs for host_helper.unlock_host

        Returns (tuple):
            code and output from host_helper.unlock_host

        Raises:
            CLIRejected: If unlock host still fails after reaching retries_timeout

        """
        fail_ok = kwargs.get('fail_ok', False)
        kwargs.update(fail_ok=True)
        end_time = time.time() + retries_timeout
        while time.time() < end_time:
            code, out = host_helper.unlock_host(host, **kwargs)
            if code <= 0:
                return code, out
            time.sleep(interval)
        if fail_ok:
            return code, out
        raise exceptions.CLIRejected('CLI failed to unlock {}. Output: {}'.format(host, out))

    @staticmethod
    def get_rsu_device_fpga(con_ssh=None, device_id='0b30'):
        """
        Get devices with device_id on each controller.

        Args:
            con_ssh (SSHClient): active controller SSHClient object
            device_id (str): device id

        Returns (dict): dictionary of hosts and corresponding devices
        {
            "controller-0" : {"pci_1": "vendor_id_1", "pci_2": "vendor_id_2"},
            "controller-1": "pci_1": "vendor_id_1"
        }
        """
        host_device_dict = OrderedDict()
        if con_ssh is None:
            con_ssh = ControllerClient.get_active_controller()

        LOG.info("Get hosts list")
        hosts_list = system_helper.get_hosts(con_ssh=con_ssh)

        for host in hosts_list:
            pci_address_list, vendor_id_list, device_id_list = host_helper.get_host_devices(
                host=host, field=["address", "vendor id", "device id"], con_ssh=con_ssh
            )

            for index, output_device_id in enumerate(device_id_list):
                if output_device_id == device_id:
                    if host not in host_device_dict:
                        host_device_dict[host] = OrderedDict()
                    host_device_dict[host].update({pci_address_list[index]: vendor_id_list[index]})

        return host_device_dict

    @staticmethod
    def apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path,
        bmc,
        retimer_included,
        bitstream_type="functional",
        pci_device="0b30",
        bitstream_id=None,
        log_type="tc_step",
        depth=0,
        timeout=DeviceImageTimeout.COMPLETE,
        update_device_image=True,
        upload_image=True,
    ):
        """
        Apply image on a device of a host.

        - Assign label to device
        - Get md5sum of image to use as bitstream_id
        - Upload image on host ande device
        - Apply image on device with specific labels
        - Update the image on device
        - Wait until the status of image be completed
        - lock/unlock the host

        Args:
            con_ssh (SSHClient): active controller SSHClient object
            host_under_test (str): Name of host
            device_name_under_test (str): Device name
            pci_vendor (int): pci of vendor
            labels (tuple): label and its value to assign to device
            image_path (str): path to the image
            bmc (bool): whether to update bmc or not
            retimer_included (bool): whether to update retimer or not
            bitstream_type (str): bitstream type of image
            pci_device (str): pci of device
            bitstream_id (int): bitstream id
            log_type (tc_step, fixture_step): different type of log from class
                                                                TisLogger in tis_log.py
            depth (int): depth to be used for log indentation
            update_device_image (bool): Whether to update the device image or not
            upload_image (bool): Whether to upload the image or not
            timeout (int): Timeout to check the status of image

        Returns (tuple):
            list of hosts which need to lock//unlock, uuid of uploaded image
        """
        hosts_to_lock_unlock = list()
        device_image_uuid = None
        log_function = eval("LOG.{}".format(log_type))

        log_function(
            "Add {} to device {} on host {}".format(
                labels, device_name_under_test, host_under_test
            ),
            depth=depth,
        )
        device_helper.assign_host_device_labels(
            host=host_under_test,
            device=device_name_under_test,
            labels=labels,
            overwrite=True,
            con_ssh=con_ssh,
        )

        if bitstream_id is None:
            LOG.info("Getting md5sum of {}".format(image_path))
            bitstream_id = con_ssh.exec_cmd("md5sum {}".format(image_path))[1].split(" ")[0]

        log_function(
            "Upload image {} on host {} device {} with bmc={} and retimer={}, bitstream_id={}"
            .format(
                image_path,
                host_under_test,
                device_name_under_test,
                bmc,
                retimer_included,
                bitstream_id,
            ),
            depth=depth,
        )

        if upload_image:
            _, device_image_uuid = device_helper.upload_device_image(
                bitstream_file=image_path,
                bitstream_type=bitstream_type,
                pci_vendor=pci_vendor,
                pci_device=pci_device,
                bitstream_id=bitstream_id,
                bmc=bmc,
                retimer_included=retimer_included,
            )

        if device_image_uuid:
            log_function(
                "Apply image {} with uuid {} on devices with label {}".format(
                    image_path, device_image_uuid, labels
                ),
                depth=depth,
            )
            device_helper.apply_device_image_labels(device_image_uuid, labels)

        if update_device_image:
            hosts_to_lock_unlock.append(host_under_test)

            log_function(
                "Update image for devices with {} on host {}".format(labels, host_under_test),
                depth=depth,
            )
            device_helper.update_device_image(host_name=host_under_test)

            log_function(
                "Wait for image {} status to be Completed".format(device_image_uuid), depth=depth
            )
            device_helper.wait_for_device_image_status(
                host=host_under_test,
                pci_device_address=device_name_under_test,
                device_image_uuid=device_image_uuid,
                timeout=timeout,
            )
            log_function("Lock/unlock host {}".format(host_under_test), depth=depth)
            host_helper.lock_unlock_hosts(host_under_test)

            log_function(
                "Wait for image {} status to be Completed".format(device_image_uuid), depth=depth
            )
            device_helper.wait_for_device_image_status(
                host=host_under_test,
                pci_device_address=device_name_under_test,
                device_image_uuid=device_image_uuid,
                timeout=timeout,
            )
            log_function("Lock/unlock host {}".format(host_under_test), depth=depth)
            host_helper.lock_unlock_hosts(host_under_test)

            hosts_to_lock_unlock.remove(host_under_test)

        return hosts_to_lock_unlock, device_image_uuid


class TestFpgaAvailability(object):
    conf = {}

    @pytest.fixture(scope='class', autouse=True)
    def create_testing_data(self, check_lab_fpga_info):
        """
        Get lab fpga info
        Create testing data dict

        Args:
            check_lab_fpga_info: module fixture

        Returns: None

        """
        LOG.fixture_step('Create testing data')
        self.conf['fpga'] = check_lab_fpga_info
        self.conf['hosts'] = []
        for host in list(self.conf['fpga']):
            operational_state = system_helper.get_host_values(host, 'operational')[0]
            if operational_state == HostOperState.ENABLED:
                self.conf['hosts'].append(host)
        LOG.info('Testing data:')
        for key, value in self.conf.items():
            LOG.info('{}: {}'.format(key, value))

    @mark.p1
    @mark.lab_fpga
    def test_fpga_pod_and_resources(self):
        """
        Test fpga pod and related resource are available after configuration or installation.

        Test Steps:
            - verify intel-fpga-plugin pods are running on hosts
            - verify fpga cards are detected on hosts
            - verify fpga allocatable resource on hosts

        """
        self.verify_fpga_pod_and_resources()

    @mark.p2
    @mark.lab_fpga
    def test_fpga_pod_and_resources_after_lock_unlock(self):
        """
        Test fpga pod and related resource are available after host lock/unlock.

        Test Steps:
            - do host lock/unlock
            - verify intel-fpga-plugin pods are running on hosts
            - verify fpga cards are detected on hosts
            - verify fpga allocatable resource on hosts

        """
        host = self.conf['hosts'][0]
        LOG.tc_step('lock/unlock {}'.format(host))
        host_helper.lock_unlock_hosts(host)
        self.verify_fpga_pod_and_resources()

    @mark.p1
    @mark.lab_fpga
    def test_fpga_pod_and_resources_after_reboot(self):
        """
        Test fpga pod and related resource are available after host reboot.

        Test Steps:
            - do host reboot
            - verify intel-fpga-plugin pods are running on hosts
            - verify fpga cards are detected on hosts
            - verify fpga allocatable resource on hosts

        """
        host = self.conf['hosts'][0]
        LOG.tc_step('reboot {}'.format(host))
        host_helper.reboot_hosts(host)
        self.verify_fpga_pod_and_resources()

    def verify_fpga_pod_and_resources(self):
        """
        Verify fpga pod and related resource are available.
            - verify intel-fpga-plugin pods are running on hosts
            - verify fpga cards are detected on hosts
            - verify fpga allocatable resource on hosts
            - # TODO: wait for requirement clarification on fpga sensor

        Returns: None

        """
        self.verify_fpga_pod_running()
        self.verify_fpga_card_detected()
        self.verify_fpga_resource_allocatable()
        # self.verify_fpga_sensors()

    def verify_fpga_pod_running(self):
        """
        Verify intel-fpga-plugin pods are running on hosts.

        Returns: None

        """
        LOG.fixture_step('Verify fpga pods are running on hosts')
        ret, pods = kube_helper.wait_for_pods_status(
            namespace='kube-system', regex=True, **{'NAME': 'intel-fpga-plugin'}
        )
        assert len(pods) == len(self.conf['hosts']), 'expect {} intel-fpga pods, actual: {}'.format(
            len(self.conf['hosts']), len(pods)
        )

    def verify_fpga_card_detected(self):
        """
        Verify fpga cards are detected on hosts.

        Returns: None

        """
        LOG.fixture_step('Verify fpga cards are detected on hosts')
        for host in self.conf['hosts']:
            cards = FpgaLib.get_detected_card(host)
            assert len(cards) > 0, '{} has {} fpga card detected'.format(host, len(cards))

    def verify_fpga_resource_allocatable(self):
        """
        Verify fpga allocatable resource on hosts.

        Returns: None

        """
        LOG.fixture_step('Verify fpga allocatable resource')
        end_time = time.time() + 60
        while time.time() < end_time:
            resources = FpgaLib.get_allocatable_fpga()
            allocatable_resources = 0
            for resource in resources:
                allocatable_resources += int(resource.split(":")[1].strip())
            LOG.info("Resources found: {}".format(resources))
            cards = self.get_fpga_count(self.conf['hosts'])
            if allocatable_resources == cards:
                break
            time.sleep(5)
        assert allocatable_resources == cards, 'expect {} allocatable fpga, actual: {}'.format(
            cards, allocatable_resources
        )

    def verify_fpga_sensors(self):
        """
        Verify fpga sensors
        # TODO: wait for requirement clarification on fpga sensor

        Returns: None

        """
        LOG.fixture_step('Verify fpga sensors on hosts')
        for host in self.conf['hosts']:
            sensors = FpgaLib.get_host_sensor_list(host)
            for sensor in ['BB +12.0V', 'BB +3.3V Vbat', 'BB BMC Temp']:
                assert sensor in sensors, 'sensor {} does not exist'.format(sensor)

    def get_fpga_count(self, hosts):
        """
        Get the fpga cards count from the lab.py file.

        Args:
            - hosts(list): List of hosts to check fpga cards on.

        Returns(int):

        """
        lab = ProjVar.get_var("lab")
        fpga = lab.get('fpga')
        cards = 0
        if fpga:
            for host in hosts:
                host_info = fpga.get(host)
                if host_info:
                    interface = host_info.get('interface')
                    cards += int(len(interface.keys()) / 2)

        LOG.info("{} FPGA cards found".format(cards))
        return cards


class TestFpgaFec(object):
    conf = {}
    FEC_DEVICE_ID = '0d8f'

    @pytest.fixture(scope='class', autouse=True)
    def create_testing_data(self, check_lab_fpga_info):
        """
        Get lab fpga info
        Create testing data dict

        Args:
            check_lab_fpga_info: module fixture

        Returns: None

        """
        LOG.fixture_step('Create testing data')
        self.conf['fpga'] = check_lab_fpga_info
        fec_hosts = [
            host for host, values in self.conf['fpga'].items() if values['type'] == 'N3000v'
        ]
        if not fec_hosts:
            pytest.skip('No N3000v to test fec device')
        self.conf['host'] = fec_hosts[0]
        self.conf['intf'] = list(self.conf['fpga'][self.conf['host']])[0]
        LOG.info('Testing data:')
        for key, value in self.conf.items():
            LOG.info('{}: {}'.format(key, value))

    @mark.p1
    @mark.lab_fpga
    def test_fpga_fec_detect_and_config(self, request):
        """
        Test fpga fec device can be detected, configured.

        Test Steps:
            - verify fec device is detected
            - verify device cannot config more than maximum vfs
            - verify device can config maximum vfs
            - verify intel_fpga_fec in kubectl describe node
            - verify device driver is bound to igb_uio
            - verify fec entry is in /etc/pcidp/config.json

        """
        LOG.tc_step('Verify fec device is detected')
        addresses = host_helper.get_host_devices(
            self.conf['host'],
            field='address',
            list_all=True,
            strict=True,
            **{'device id': self.FEC_DEVICE_ID},
        )
        assert addresses, 'no fec device is detected'

        # The product only supports ONE N3000 card on a given host at this time.
        # The one with the smallest address must be selected.
        address = min(addresses)

        sriov_totalvfs = int(
            host_helper.get_host_device_values(self.conf['host'], address, 'sriov_totalvfs')[0]
        )

        HostsToRecover.add(self.conf['host'])
        host_helper.lock_host(self.conf['host'], swact=True)
        host_helper.assign_host_labels(self.conf['host'], ['sriovdp'], lock=False, unlock=False)

        LOG.tc_step('Modifying device vfs more than maximum {} should fail'.format(sriov_totalvfs))
        code, output = host_helper.modify_host_device(
            self.conf['host'],
            address,
            new_state=True,
            new_driver='igb_uio',
            new_vf_driver='igb_uio',
            sriov_numvfs=str(sriov_totalvfs + 1),
            check_first=False,
            lock_unlock=False,
            fail_ok=True,
        )
        assert (
            code > 0 and 'The device supports a maximum of {} VFs'.format(sriov_totalvfs) in output
        ), 'config more than maximum vfs did not fail as expected'

        LOG.tc_step('Modify {} device {}'.format(self.conf['host'], address))
        host_helper.modify_host_device(
            self.conf['host'],
            address,
            new_state=True,
            new_driver='igb_uio',
            new_vf_driver='igb_uio',
            sriov_numvfs=str(sriov_totalvfs),
            check_first=False,
            lock_unlock=False,
        )

        FpgaLib.unlock_host_with_retries(self.conf['host'])

        # Add Cleanup Step to reset the device configuration.
        def teardown():
            fec_device_keywords.reset_device_configuration([self.conf['host']])

        request.addfinalizer(teardown)

        LOG.tc_step('Verify intel_fpga_fec is in kubectl describe node')
        code, output = kube_helper.exec_kube_cmd(
            'describe node {}'.format(self.conf['host']), grep='intel_fpga'
        )
        assert re.search(
            r'intel\.com/intel_fpga_fec:\s*{}'.format(sriov_totalvfs), output
        ), 'intel_fpga_fec is not in kubectl describe node'

        with host_helper.ssh_to_host(self.conf['host']) as ssh:
            with ssh.login_as_root() as root_ssh:
                LOG.tc_step('Verify device driver is bound to igb_uio')
                code, output = root_ssh.exec_cmd(
                    '/usr/share/starlingx/scripts/dpdk-devbind.py --status'
                )
                assert (
                    "{} 'Device {}' drv=igb_uio unused=".format(address, self.FEC_DEVICE_ID)
                    in output
                ), 'device bound info is incorrect'

                LOG.tc_step('Verify fec entry is in /etc/pcidp/config.json')
                entry = {
                    'resourceName': 'intel_fpga_fec',
                    'deviceType': 'accelerator',
                    'selectors': {'vendors': ['8086'], 'drivers': ['igb_uio'], 'devices': ['0d90']},
                }
                code, output = root_ssh.exec_cmd('cat /etc/pcidp/config.json')
                output_dict = json.loads(output)
                if output_dict and "resourceList" in output_dict:
                    for resource_item_dict in output_dict["resourceList"]:
                        if (
                            "resourceName" in resource_item_dict
                            and resource_item_dict["resourceName"] == "intel_fpga_fec"
                        ):
                            assert entry == resource_item_dict, 'fec entry is not found'
                            break
                    else:
                        raise exceptions.CommonError(
                            "Unable to find intel_fpga_fec in output of cat /etc/pcidp/config.json"
                        )
                else:
                    raise exceptions.CommonError(
                        "Output from cat /etc/pcidp/config.json is not valid"
                    )


class TestFpgaConnectivity(object):
    conf = {}

    @pytest.fixture(scope='class', autouse=True)
    @mark.hw_validation
    def create_testing_data(self, check_lab_fpga_info):
        """
        Get lab fpga info
        Create testing data dict

        Args:
            check_lab_fpga_info: module fixture

        Returns: None

        """
        LOG.fixture_step('Create testing data')
        self.conf['fpga'] = check_lab_fpga_info
        host_intfs = [
            [host, [intf, p['connect_to']]]
            for host, v in self.conf['fpga'].items()
            for intf, p in v['interface'].items()
            if p.get('connect_to')
        ]
        if not host_intfs:
            pytest.skip('Need 2 connected interfaces to test connectivity')
        self.conf['host'], self.conf['intfs'] = host_intfs[0]
        self.conf['netns'] = [
            {
                'netns': 'ns11',
                'interface': self.conf['intfs'][0],
                'ip': '10.10.10.11',
                'netmask': '24',
            },
            {
                'netns': 'ns22',
                'interface': self.conf['intfs'][1],
                'ip': '10.10.10.22',
                'netmask': '24',
            },
        ]
        self.conf['config'] = []
        self.conf['unconfig'] = []
        for values in self.conf['netns']:
            ns = values['netns']
            intf = values['interface']
            self.conf['config'].append('ip netns add {}'.format(ns))
            self.conf['config'].append('ip link set {} netns {}'.format(intf, ns))
            self.conf['config'].append('ip netns exec {} ip link set dev {} up'.format(ns, intf))
            self.conf['config'].append(
                'ip netns exec {} ip addr add {}/{} dev {}'.format(
                    ns, values['ip'], values['netmask'], intf
                )
            )
            self.conf['unconfig'].append('ip netns delete {}'.format(ns))
        LOG.info('Testing data:')
        for key, value in self.conf.items():
            LOG.info('{}: {}'.format(key, value))
    @mark.hw_validation
    def _test_fpga_connectivity_traffic(self):
        """
        Test fpga connectivity on ethernets.

        Test Steps:
            - configure 2 netns and ip addresses on host
            - verify ping test from one ip to another successfully
            - verify iperf test from one ip to another successfully

        """
        try:
            LOG.tc_step('Configure netns and ip address')
            with host_helper.ssh_to_host(self.conf['host']) as host_ssh:
                for cmd in self.conf['config']:
                    host_ssh.exec_sudo_cmd(cmd, expect_timeout=10, fail_ok=False)
            FpgaLib.verify_ping_test_successful(
                dest=self.conf['netns'][1]['ip'],
                netns=self.conf['netns'][0]['netns'],
                host=self.conf['host'],
            )
            FpgaLib.verify_iperf_test_successful(
                server_ip=self.conf['netns'][0]['ip'],
                client_ip=self.conf['netns'][1]['ip'],
                server_netns=self.conf['netns'][0]['netns'],
                client_netns=self.conf['netns'][1]['netns'],
                server_host=self.conf['host'],
                client_host=self.conf['host'],
            )
        finally:
            LOG.tc_step('Unconfig ip related configuration')
            with host_helper.ssh_to_host(self.conf['host']) as host_ssh:
                for cmd in self.conf['unconfig']:
                    host_ssh.exec_sudo_cmd(cmd, expect_timeout=10, fail_ok=True)


class TestFpgaSriovDpdk:
    KUBE_CPU_MGR_POLICY_LABEL = 'kube-cpu-mgr-policy'
    KUBE_TOPOLOGY_MGR_POLICY_LABEL = 'kube-topology-mgr-policy'
    FEC_DEVICE_ID = '0d8f'

    @pytest.fixture(scope='function')
    def prepare_tests(self, request):
        """
        Discover the SR-IOV interface configuration of the system and
        ensure that the appropriate labels are applied. Enable FEC if FPGA card is detected.

        Returns (list): A list of SR-IOV config dictionaries:
                        [{host: (str), interfaces: (list)}..]
        """
        host_initial_labels = dict()
        new_hosts_labels = dict()
        kube_labels = {
            self.KUBE_CPU_MGR_POLICY_LABEL: 'static',
            self.KUBE_TOPOLOGY_MGR_POLICY_LABEL: 'restricted',
        }

        sriov_configs = sriov_helper.get_sriov_config()
        datanetwork_capacity = sriov_helper.get_sriov_node_capacity()

        if not sriov_configs:
            pytest.skip('no capable SR-IOV interfaces')

        LOG.fixture_step("Getting Initial Labels on hosts")
        # Get Initial labels on each host, to be used later to recover the labels
        for config in sriov_configs:
            host = config['host']
            LOG.fixture_step("Getting Initial Labels on host: {}".format(host), depth=1)
            host_initial_labels[host] = host_helper.get_host_labels_info(host)
            new_hosts_labels[host] = kube_labels

        LOG.fixture_step("Add host's labels: {}".format(new_hosts_labels))
        Host.assign_host_labels(new_hosts_labels, overwrite=True)

        LOG.fixture_step("Check whether hosts have an N3000 Card with FEC enabled.")
        hosts = [sriov_config['host'] for sriov_config in sriov_configs]
        for host in hosts:

            addresses = host_helper.get_host_devices(
                host,
                field='address',
                list_all=True,
                strict=True,
                **{'device id': self.FEC_DEVICE_ID},
            )

            if addresses:

                HostsToRecover.add(host)
                host_helper.lock_host(host, swact=True)

                # The product only supports ONE N3000 card on a given host at this time.
                # The one with the smallest address must be selected.
                address = min(addresses)

                LOG.fixture_step(
                    "Configure N3000 FEC driver to igb_ui on host: {}".format(host), depth=1
                )

                sriov_totalvfs = int(
                    host_helper.get_host_device_values(host, address, 'sriov_totalvfs')[0]
                )

                LOG.info(
                    "Total Number of SR-IOV configurable for device {} on host {} is {}".format(
                        address, host, sriov_totalvfs
                    )
                )

                host_helper.modify_host_device(
                    host,
                    address,
                    new_driver='igb_uio',
                    new_vf_driver='igb_uio',
                    sriov_numvfs=str(sriov_totalvfs),
                )

                FpgaLib.unlock_host_with_retries(host)
                HostsToRecover.remove(host)

        def teardown():
            fec_device_keywords.reset_device_configuration(hosts)

        request.addfinalizer(teardown)

        return sriov_configs, datanetwork_capacity

    @mark.p1
    @mark.lab_fpga
    @mark.lab_sriov
    def test_fpga_sriovdp_dpdk_connectivity(self, prepare_tests, prepare_resources):
        """
        Test connectivity between SR-IOV interfaces in a pod with DPDK and FEC enabled

        Args:
            prepare_resources: function fixture from test_sriov module
            prepare_tests: function fixture

        Setups:
            - Set Labels KUBE_CPU_MGR_POLICY_LABEL and KUBE_TOPOLOGY_MGR_POLICY_LABEL
                  to compute nodes
            - Find a datanetwork to use for SR-IOV VFs
            - Enable FPG FEC if it is not enabled

        Test Steps:
            - Create network attachment definitions for the SR-IOV VFs
            - Create sending and receiving pods with SR-IOV DPDK devices
            - Verify the number of VFs (PCI devices) in the pod
            - Run traffic between the sending pod and all receiving pods
            - Collect and verify the traffic statistics
        """
        num_vfs = num_hosts = 1
        sriov_config, datanetwork_capacity = prepare_tests
        pods_per_host = 2
        pods = []

        datanetwork, hosts = check_system_compatibility(
            num_hosts,
            pods_per_host,
            num_vfs,
            INTERFACE_CLASS_PCI_SRIOV,
            POD_TYPE_DPDK,
            sriov_config,
            datanetwork_capacity,
        )

        if not datanetwork:
            pytest.skip(
                'no data network exists with capacity for {} SR-IOV vfio VFs'.format(num_vfs)
            )

        if not hosts:
            pytest.skip(
                'no host exists with capacity for {} SR-IOV vfio VFs and {} 1G hugpages'.format(
                    num_vfs, DPDK_HUGEPAGE_REQD
                )
            )

        hosts = [hosts[0], hosts[0]]

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

            if len(rx_stats) != num_vfs:
                pytest.skip('Failed to get testpmd receive stats for all ports')
            if len(tx_stats) != num_vfs:
                pytest.skip('Failed to get testpmd transmit stats for all ports')
            for stat in rx_stats.keys():
                assert rx_stats[stat] > 10000
            for stat in tx_stats.keys():
                assert tx_stats[stat] > 10000


@mark.p1
@mark.lab_fpga
def test_apply_bmc_image_with_retimer_then_without_retimer(get_device_fpga):
    """
    Verify apply BMC image 6.1 with re-timer first and then
    BMC image 5.5 with re-timer, only latest image is kept in device-image-state-list (TC_26309).

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image bmc and re-timer version 6.1 to /tmp/ on the lab
        - Copy image bmc and re-timer version 5.5 to /tmp/ on the lab
        - Apply image 6.1 on device with bmc and re-timer
        - Apply image 5.5 on device with bmc and with re-timer
        - Verify only 5.5 is presented using system device-image-state-list

    TearDown:
        - Revert the image to its initial one if needed
        - Remove added labels to device
        - Remove added images
    """
    global resources_to_delete
    global controller_to_lock_unlock
    global revert_is_needed
    labels = ("label1", "abc")
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    bmc_with_retimer_6_1 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_6_1)
    bmc_with_retimer_5_5 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_5_5)

    (
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
    ) = get_device_fpga

    LOG.tc_step("Copy image BMC 6.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_6_1))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_6_1),
        dest_path=bmc_with_retimer_6_1,
    )
    resources_to_delete.append({'file': bmc_with_retimer_6_1})

    controller_to_lock_unlock, device_image_uuid_6_1 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_6_1,
        bmc=True,
        retimer_included=True,
    )

    revert_is_needed = True

    LOG.tc_step("Copy Image BMC 5.5 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_5_5))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_5_5),
        dest_path=bmc_with_retimer_5_5,
    )
    resources_to_delete.append({'file': bmc_with_retimer_5_5})

    controller_to_lock_unlock, device_image_uuid_5_5 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_5_5,
        bmc=True,
        retimer_included=True,
    )

    LOG.tc_step(
        "Verify image state list to see only images 5.5 {} in the list".format(
            device_image_uuid_5_5
        )
    )

    device_images_state_list = device_helper.get_device_images_state(
        con_ssh=con_ssh, fields=["Device image uuid"]
    )[0]

    assert (
        device_image_uuid_6_1 not in device_images_state_list
    ), "Expecting to do not see image 6.1 {} ({}) in the list".format(
        device_image_uuid_6_1, BMC_IMAGE_WITH_RETIMER_6_1
    )

    assert (
        device_image_uuid_5_5 in device_images_state_list
    ), "Expecting to see only image 5.5 {} in the list".format(device_image_uuid_5_5)

    device_helper.wait_for_device_image_status(
        host=host_under_test,
        pci_device_address=device_name_under_test,
        device_image_uuid=device_image_uuid_5_5,
        timeout=20,
    )


@mark.p2
@mark.lab_fpga
def test_apply_bmc_image_without_retimer_then_without_retimer(get_device_fpga):
    """
    Verify apply BMC image without re-timer first and then
    BMC image without re-timer, only latest image is kept in device-image-state-list (TC_26310).

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image bmc and re-timer version 6.1 to /tmp/ on the lab
        - Copy image bmc and re-timer version 5.5 to /tmp/ on the lab
        - Apply image 5.5 on device with bmc and without re-timer
        - Apply image 6.1 on device with bmc and without re-timer
        - Verify only 6.1 is presented using system device-image-state-list

    TearDown:
        - Revert the image to its initial one if needed
        - Remove added labels to device
        - Remove added images
    """
    global resources_to_delete
    global controller_to_lock_unlock
    global revert_is_needed
    labels = ("label1", "abc")
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    bmc_with_retimer_6_1 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_6_1)
    bmc_with_retimer_5_5 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_5_5)

    (con_ssh, host_under_test, device_name_under_test, pci_vendor) = get_device_fpga

    LOG.tc_step("Copy Image BMC 5.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_5_5))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_5_5),
        dest_path=bmc_with_retimer_5_5,
    )
    resources_to_delete.append({'file': bmc_with_retimer_5_5})

    controller_to_lock_unlock, device_image_uuid_5_5 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_5_5,
        bmc=True,
        retimer_included=False,
    )

    revert_is_needed = True

    LOG.tc_step("Copy image BMC 6.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_6_1))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_6_1),
        dest_path=bmc_with_retimer_6_1,
    )
    resources_to_delete.append({'file': bmc_with_retimer_6_1})

    controller_to_lock_unlock, device_image_uuid_6_1 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_6_1,
        bmc=True,
        retimer_included=False,
    )

    LOG.tc_step(
        "Verify image state list to see only images {} in the list".format(device_image_uuid_6_1)
    )

    device_images_state_list = device_helper.get_device_images_state(
        con_ssh=con_ssh, fields=["Device image uuid"]
    )[0]

    assert (
        device_image_uuid_5_5 not in device_images_state_list
    ), "Expecting to do not see image {} ({}) in the list".format(
        device_image_uuid_5_5, BMC_IMAGE_WITH_RETIMER_5_5
    )

    assert (
        device_image_uuid_6_1 in device_images_state_list
    ), "Expecting to see only image 6.1 {} in the list".format(device_image_uuid_6_1)

    device_helper.wait_for_device_image_status(
        host=host_under_test,
        pci_device_address=device_name_under_test,
        device_image_uuid=device_image_uuid_6_1,
        timeout=20,
    )


@mark.p2
@mark.lab_fpga
def test_apply_bmc_image_without_retimer_then_with_retimer(get_device_fpga):
    """
    Verify apply BMC image without re-timer first and then
    BMC image with re-timer, only latest image is kept in device-image-state-list (TC_26311).

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image version 6.1 to /tmp/ on the lab
        - Copy image version 5.5 to /tmp/ on the lab
        - Apply image 5.5 on device without bmc and without re-timer
        - Apply image 6.1 on device with bmc and with re-timer
        - Verify only 6.1 is presented using system device-image-state-list

    TearDown:
        - Revert the image to its initial one if needed
        - Remove added labels to device
        - Remove added images
    """
    global resources_to_delete
    global controller_to_lock_unlock
    global revert_is_needed
    labels = ("label1", "abc")
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    bmc_with_retimer_6_1 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_6_1)
    bmc_with_retimer_5_5 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_5_5)

    (con_ssh, host_under_test, device_name_under_test, pci_vendor) = get_device_fpga

    LOG.tc_step("Copy Image 5.5 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_5_5))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_5_5),
        dest_path=bmc_with_retimer_5_5,
    )
    resources_to_delete.append({'file': bmc_with_retimer_5_5})

    controller_to_lock_unlock, device_image_uuid_5_5 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_5_5,
        bmc=True,
        retimer_included=False,
    )

    revert_is_needed = True

    LOG.tc_step("Copy image 6.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_6_1))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_6_1),
        dest_path=bmc_with_retimer_6_1,
    )
    resources_to_delete.append({'file': bmc_with_retimer_6_1})

    controller_to_lock_unlock, device_image_uuid_6_1 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_6_1,
        bmc=True,
        retimer_included=True,
    )

    LOG.tc_step(
        "Verify image state list to see only images {} in the list".format(device_image_uuid_6_1)
    )

    device_images_state_list = device_helper.get_device_images_state(
        con_ssh=con_ssh, fields=["Device image uuid"]
    )[0]

    assert (
        device_image_uuid_5_5 not in device_images_state_list
    ), "Expecting to do not see image {} ({}) in the list".format(
        device_image_uuid_5_5, BMC_IMAGE_WITH_RETIMER_5_5
    )

    assert (
        device_image_uuid_6_1 in device_images_state_list
    ), "Expecting to see only image 6.1 {} in the list".format(device_image_uuid_6_1)

    device_helper.wait_for_device_image_status(
        host=host_under_test,
        pci_device_address=device_name_under_test,
        device_image_uuid=device_image_uuid_6_1,
        timeout=20,
    )


@mark.p2
@mark.lab_fpga
def test_verify_image_upload_optional_arguments_retimer_included_and_bmc(get_device_fpga):
    """
    Verify values of device-image-upload optional arguments
    retimer-included is True in Image 6.1 (TC_26317).

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image bmc and re-timer version 6.1 to /tmp/ on the lab
        - Upload image with bmc=true and retimer_included=True to the lab
        - Verify image retimer_included is True
        - Verify image BMC is True
        - Verify bitstream_type is 'functional'
        - Verify pci_device is '0b30'
        - Verify pci_vendor is '8086

    TearDown:
        - Revert the image to its initial one if needed
        - Remove added labels to device
        - Remove added images
    """
    global resources_to_delete
    global revert_is_needed
    global controller_to_lock_unlock
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    bmc_with_retimer_6_1 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_6_1)

    con_ssh, host_under_test, device_name_under_test, pci_vendor = get_device_fpga

    LOG.tc_step("Copy image 6.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_6_1))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_6_1),
        dest_path=bmc_with_retimer_6_1,
    )
    resources_to_delete.append({'file': bmc_with_retimer_6_1})

    bitstream_id = con_ssh.exec_cmd("md5sum {}".format(bmc_with_retimer_6_1))[1].split(" ")[0]

    _, device_image_uuid = device_helper.upload_device_image(
        bitstream_file=bmc_with_retimer_6_1,
        bitstream_type="functional",
        pci_vendor="8086",
        pci_device="0b30",
        bitstream_id=bitstream_id,
        bmc=True,
        retimer_included=True,
    )

    (
        uuid_list,
        bitstream_type_list,
        pci_vendor_list,
        pci_device_list,
        bmc_list,
        retimer_included_list,
    ) = device_helper.get_device_images(
        fields=['uuid', 'bitstream_type', 'pci_vendor', 'pci_device', 'bmc', 'retimer_included'],
        con_ssh=con_ssh,
    )

    LOG.tc_step("Verify parameters for image {}".format(device_image_uuid))
    image_uuid_found = False
    for uuid, bitstream_type, pci_vendor, pci_device, bmc, retimer_included in zip(
        uuid_list,
        bitstream_type_list,
        pci_vendor_list,
        pci_device_list,
        bmc_list,
        retimer_included_list,
    ):
        if uuid == device_image_uuid:
            image_uuid_found = True
            break

    assert image_uuid_found, "uploaded image with uuid {} did not find in device-image-list".format(
        device_image_uuid
    )

    LOG.tc_step("Verify image {} retimer_included is True".format(device_image_uuid), depth=1)
    assert (
        retimer_included == "True"
    ), "Expecting retimer_included to be False while it is {}".format(retimer_included)

    LOG.tc_step("Verify image {} bmc is True".format(device_image_uuid), depth=1)
    assert bmc == "True", "Expecting bmc to be True while it is {}".format(retimer_included)

    LOG.tc_step("Verify image {} bitstream_type is 'functional'".format(device_image_uuid), depth=1)
    assert (
        bitstream_type == "functional"
    ), "Expecting bitstream_type to be functional while it is {}".format(bitstream_type)

    LOG.tc_step("Verify image {} pci_device is '0b30'".format(device_image_uuid), depth=1)
    assert pci_device == "0b30", "Expecting pci_device to be 0b30 while it is {}".format(pci_device)

    LOG.tc_step("Verify image {} pci_vendor is '8086".format(device_image_uuid), depth=1)
    assert pci_vendor == "8086", "Expecting pci_vendor to be 8086 while it is {}".format(pci_vendor)


@mark.p1
@mark.lab_fpga
def test_verify_firmware_rollback_bmc_retimer(get_device_fpga):
    """
    Verify retimer_a_version and retimer_b_version after applying BMC image with re-timer and bmc
     (TC_26318, TC_26319).

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image bmc and re-timer version 6.1 to /tmp/ on the lab
        - Apply image 6.1 on device with bmc and re-timer
        - Verify retimer_a_version and retimer_b_version to be 101c.105c and 0000.0000, respectively
        - Copy image bmc and re-timer version 5.5 to /tmp/ on the lab
        - Apply image 5.5 on device with bmc and re-timer
        - Verify retimer_a_version and retimer_b_version to be 101c.1064 and 0000.0000, respectively

    TearDown:
        - Revert the image to its initial one if needed
        - Remove added labels to device
        - Remove added images
    """
    global resources_to_delete
    global controller_to_lock_unlock
    global revert_is_needed
    labels = ("label1", "abc")
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    bmc_with_retimer_6_1 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_6_1)
    bmc_with_retimer_5_5 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_5_5)

    (
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
    ) = get_device_fpga

    LOG.tc_step(
        "Copy image BMC with TIMER verion 6.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_6_1)
    )
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_6_1),
        dest_path=bmc_with_retimer_6_1,
    )
    resources_to_delete.append({'file': bmc_with_retimer_6_1})

    controller_to_lock_unlock, device_image_uuid_6_1 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_6_1,
        bmc=True,
        retimer_included=True,
    )

    revert_is_needed = True

    (
        bmc_build_version,
        bmc_fw_version,
        retimer_a_version,
        retimer_b_version,
    ) = host_helper.get_host_device_values(
        host_under_test,
        device_name_under_test,
        fields=["bmc_build_version", "bmc_fw_version", "retimer_a_version", "retimer_b_version"],
        con_ssh=con_ssh,
    )
    LOG.tc_step("Verify bmc_build_version after update image")
    assert (
        bmc_build_version == "D.2.0.7"
    ), "Expecting to have D.2.0.7 as bmc_build_version after update"

    LOG.tc_step("Verify bmc_fw_version after update image")
    assert (
        bmc_fw_version == "D.2.238.24"
    ), "Expecting to have D.2.238.24 as bmc_fw_version after update"

    LOG.tc_step("Verify retimer_a_version after update image ")
    assert (
        retimer_a_version == "101c.105c"
    ), "Expecting to have 101c.105c for retimer_a_version on device {} on host {}".format(
        device_name_under_test, host_under_test
    )

    LOG.tc_step("Verify retimer_b_version after update image to stay unchanged (0000.0000)")
    assert (
        retimer_b_version == "0000.0000"
    ), "Expecting to have 0000.0000 for retimer_b_version on device {} on host {} ".format(
        device_name_under_test, host_under_test
    )

    LOG.tc_step("Copy rollback image BMC TIMER {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_5_5))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_5_5),
        dest_path=bmc_with_retimer_5_5,
    )
    resources_to_delete.append({'file': bmc_with_retimer_5_5})

    controller_to_lock_unlock, device_image_uuid_5_5 = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_5_5,
        bmc=True,
        retimer_included=True,
    )

    retimer_a_version, retimer_b_version = host_helper.get_host_device_values(
        host_under_test,
        device_name_under_test,
        fields=["retimer_a_version", "retimer_b_version"],
        con_ssh=con_ssh,
    )

    LOG.tc_step("Verify retimer_a_version after rollback image to stay unchanged (101c.1064)")
    assert (
        retimer_a_version == "101c.1064"
    ), "Selected device {} on host {} does not have expected retimer_a_version".format(
        device_name_under_test, host_under_test
    )

    LOG.tc_step("Verify retimer_b_version after rollback image to stay unchanged (0000.0000)")
    assert (
        retimer_b_version == "0000.0000"
    ), "Selected device {} on host {} does not have expected retimer_b_version".format(
        device_name_under_test, host_under_test
    )

    revert_is_needed = False


@mark.p2
@mark.lab_fpga
def test_error_handling_device_image_upload_non_functional_with_retimer(get_device_fpga):
    """
    Test verify image upload with non-functional image with retimer-included
    True is not allowed (TC_26305)

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image root_public_program_ssl to /tmp/ on the lab
        - Copy image ssl_csk1_cancel.bin to /tmp/ on the lab
        - Apply image root_public_program_ssl with retimer=True
        - Apply image ssl_csk1_cancel.bin with retimer=True
        - Verify the retimer_included option in the uploaded image is False

    TearDown:
        - Remove added labels to device
        - Remove added images

    """
    global resources_to_delete
    global controller_to_lock_unlock
    global revert_is_needed
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    con_ssh, _, _, _ = get_device_fpga
    root_public_program_ssl = "/tmp/{}".format(ROOT_PUBLIC_PROGRAM_SSL_IMAGE)
    ssl_csk = "/tmp/{}".format(SSL_CSK_IMAGE)

    LOG.tc_step("Copy image {} to /tmp/".format(ROOT_PUBLIC_PROGRAM_SSL_IMAGE))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(ROOT_PUBLIC_PROGRAM_SSL_IMAGE),
        dest_path=root_public_program_ssl,
    )
    resources_to_delete.append({'file': root_public_program_ssl})

    _, output = device_helper.upload_device_image(
        bitstream_file=root_public_program_ssl,
        bitstream_type="root-key",
        pci_vendor="8086",
        pci_device="0b30",
        key_signature=1,
        retimer_included=True,
        fail_ok=True,
        con_ssh=con_ssh,
    )

    assert "retimer_included option is only applicable to functional BMC image" in output, (
        "Expecting to do not be able to upload the image and seeing error: retimer_included "
        "option is only applicable to functional BMC image"
    )

    LOG.tc_step("Copy image {} to /tmp/".format(SSL_CSK_IMAGE))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(SSL_CSK_IMAGE),
        dest_path=root_public_program_ssl,
    )
    resources_to_delete.append({'file': ssl_csk})

    _, output = device_helper.upload_device_image(
        bitstream_file=root_public_program_ssl,
        bitstream_type="key-revocation",
        pci_vendor="8086",
        pci_device="0b30",
        revoke_key_id=1,
        retimer_included=True,
        fail_ok=True,
        con_ssh=con_ssh,
    )

    assert "retimer_included option is only applicable to functional BMC image" in output, (
        "Expecting to do not be able to upload the image and seeing error retimer_included "
        "option is only applicable to functional BMC image"
    )


@mark.p1
@mark.lab_fpga
def test_verify_firmware_with_retimer(get_device_fpga):
    """
    Verify firmware update for BMC and retimer image with retimer-include=False (TC_26306)

    Args:
        get_device_fpga (function fixture): get a host and a fpga device with its specifications.

    Setups:
        - Find an FPGA device on a host
        - Get initial device labels
        - Get initial uploaded images

    Test Steps:
        - Copy image bmc and re-timer version 6.1 to /tmp/ on the lab
        - Apply image 6.1 on device with without re-timer
        - Verify device image gets updated
        - Verify retimer_a_version and retimer_b_version

    TearDown:
        - Revert the image to its initial one if needed
        - Remove added labels to device
        - Remove added images
    """

    global resources_to_delete
    global controller_to_lock_unlock
    global revert_is_needed
    labels = ("label1", "abc")
    resources_to_delete = list()
    controller_to_lock_unlock = list()
    revert_is_needed = False
    bmc_with_retimer_6_1 = "/tmp/{}".format(BMC_IMAGE_WITH_RETIMER_6_1)

    con_ssh, host_under_test, device_name_under_test, pci_vendor = get_device_fpga

    LOG.tc_step("Copy image 6.1 {} to /tmp/".format(BMC_IMAGE_WITH_RETIMER_6_1))
    common.scp_from_localhost_to_active_controller(
        source_path="utils/test_files/N3000_images/{}".format(BMC_IMAGE_WITH_RETIMER_6_1),
        dest_path=bmc_with_retimer_6_1,
    )
    resources_to_delete.append({'file': bmc_with_retimer_6_1})

    controller_to_lock_unlock, _ = FpgaLib.apply_image_on_device(
        con_ssh,
        host_under_test,
        device_name_under_test,
        pci_vendor,
        labels,
        image_path=bmc_with_retimer_6_1,
        bmc='',
        retimer_included=False,
    )

    revert_is_needed = True

    (
        bmc_build_version,
        bmc_fw_version,
        retimer_a_version,
        retimer_b_version,
    ) = host_helper.get_host_device_values(
        host_under_test,
        device_name_under_test,
        fields=["bmc_build_version", "bmc_fw_version", "retimer_a_version", "retimer_b_version"],
        con_ssh=con_ssh,
    )

    LOG.tc_step("Verify bmc_build_version after update image")
    assert (
        bmc_build_version == "D.2.0.7"
    ), "Expecting to have D.2.0.7 as bmc_build_version after update"

    LOG.tc_step("Verify bmc_fw_version after update image")
    assert (
        bmc_fw_version == "D.2.238.24"
    ), "Expecting to have D.2.238.24 as bmc_fw_version after update"

    LOG.tc_step("Verify retimer_a_version after update image ")
    assert (
        retimer_a_version == "101c.1064"
    ), "Expecting to have 101c.1064 for retimer_a_version on device {} on host {}".format(
        device_name_under_test, host_under_test
    )

    LOG.tc_step("Verify retimer_b_version after update image to stay unchanged (0000.0000)")
    assert (
        retimer_b_version == "0000.0000"
    ), "Expecting to have 0000.0000 for retimer_b_version on device {} on host {} ".format(
        device_name_under_test, host_under_test
    )

