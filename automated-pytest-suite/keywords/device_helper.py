"""
This module provides helper functions for device-image, device-label commands
"""
import time

from consts.auth import Tenant
from consts.stx import HostAvailState
from consts.timeout import DeviceImageTimeout
from keywords import host_helper, system_helper
from utils import cli, exceptions, table_parser
from utils.tis_log import LOG


def get_device_labels_output(con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Get output of device-label-list

    Args:
        con_ssh (SSHClient):
        auth_info:

    Returns (str): string output of the command

    """
    return cli.system('device-label-list --nowrap', ssh_client=con_ssh, auth_info=auth_info)[1]


def get_device_labels(
    fields=('hostname', 'PCI device name', 'label key', 'label value'),
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
    rtn_dict=False,
    evaluate=False,
    zip_values=False,
    strict=True,
    regex=False,
    **kwargs,
):
    """
    Get values of device labels

    Args:
        fields (str | tuple): fields of value to get
        con_ssh (SSHClient):
        auth_info (dict):
        rtn_dict (bool): whether to return dict of field/value pairs
        evaluate (bool): whether to convert value to python data type
        zip_values (bool): whether to zip values
        strict (bool): True to use re.match, False to use re.search
        regex (bool): whether to use regex to find value(s)
        **kwargs: header/value pair(s) as search criteria

    Returns (list | dict):
        when rtn_dict is False, list of values
        when rtn_dict is True, dict of field/values pairs

    """
    table_ = table_parser.table(
        cli.system('device-label-list --nowrap', ssh_client=con_ssh, auth_info=auth_info)[1]
    )
    return table_parser.get_multi_values(
        table_,
        fields,
        rtn_dict=rtn_dict,
        evaluate=evaluate,
        zip_values=zip_values,
        strict=strict,
        regex=regex,
        **kwargs,
    )


def get_host_device_labels(
    host,
    device,
    fields=('label key', 'label value'),
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
    rtn_dict=False,
    evaluate=False,
    zip_values=False,
    strict=True,
    regex=False,
    **kwargs,
):
    """
    Get values of host device labels

    Args:
        host (str): hostname
        device (str): device name or address
        fields (str | tuple): fields of value to get
        con_ssh (SSHClient):
        auth_info (dict):
        rtn_dict (bool): whether to return dict of field/value pairs
        evaluate (bool): whether to convert value to python data type
        zip_values (bool): whether to zip values
        strict (bool): True to use re.match, False to use re.search
        regex (bool): whether to use regex to find value(s)
        **kwargs: header/value pair(s) as search criteria

    Returns (list | dict):
        when rtn_dict is False, list of values
        when rtn_dict is True, dict of field/values pairs

    """
    table_ = table_parser.table(
        cli.system(
            'host-device-label-list --nowrap',
            [host, device],
            ssh_client=con_ssh,
            auth_info=auth_info,
        )[1]
    )
    return table_parser.get_multi_values(
        table_,
        fields,
        rtn_dict=rtn_dict,
        evaluate=evaluate,
        zip_values=zip_values,
        strict=strict,
        regex=regex,
        **kwargs,
    )


def assign_host_device_labels(
    host,
    device,
    labels,
    overwrite=False,
    check_first=True,
    fail_ok=False,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Assign host device labels

    Args:
        host (str): hostname
        device (str): device name or address
        labels (tuple or list of tuple): [(<label key>, <label value>), ...]
        overwrite (bool): whether or not to overwrite
        check_first (bool): whether to check first before assigning labels
        fail_ok (bool): whether or not raise exception if command fails
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (-1, "<host> <device> already has labels: <labels>. Do nothing.")
        (0, <assigned labels>(list of tuple))
        (1, <std_err>)

    """
    labels = [labels] if isinstance(labels, tuple) else labels
    to_assign = labels
    if check_first:
        existing_labels = get_host_device_labels(
            host, device, con_ssh=con_ssh, auth_info=auth_info, zip_values=True
        )
        to_assign = [label for label in labels if label not in existing_labels]
        if not to_assign:
            msg = '{} {} already has labels: {}. Do nothing.'.format(host, device, labels)
            LOG.info(msg)
            return -1, msg
    LOG.info('{} {} labels to be assigned: {}'.format(host, device, to_assign))
    args = [
        host,
        device,
        ' '.join(['{}={}'.format(name, value) for name, value in to_assign]),
        ' --overwrite' if overwrite else '',
    ]
    code, output = cli.system(
        'host-device-label-assign', args, ssh_client=con_ssh, fail_ok=fail_ok, auth_info=auth_info
    )
    if code > 0:
        return 1, output

    post_labels = get_host_device_labels(
        host, device, con_ssh=con_ssh, auth_info=auth_info, zip_values=True
    )
    not_assigned = [label for label in labels if label not in post_labels]
    if not_assigned:
        raise exceptions.SysinvError(
            'Unexpected {} {} labels {}'.format(host, device, not_assigned)
        )
    LOG.info('{} {} labels assigned: {}'.format(host, device, to_assign))
    return 0, to_assign


def remove_host_device_labels(
    host,
    device,
    labels,
    check_first=True,
    fail_ok=False,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Remove host device labels

    Args:
        host (str): hostname
        device (str): device name or address
        labels (str or list of str): [<label key>, ...]
        check_first (bool): whether to check first before removing labels
        fail_ok (bool): whether or not raise exception if command fails
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (-1, "<host> <device> does not have labels: <labels>. Do nothing.")
        (0, <removed labels>(list of str))
        (1, <std_err>)

    """
    labels = [labels] if isinstance(labels, str) else labels
    to_remove = labels
    if check_first:
        existing_labels = get_host_device_labels(
            host, device, fields='label key', con_ssh=con_ssh, auth_info=auth_info
        )
        to_remove = [label for label in labels if label in existing_labels]
        if not to_remove:
            msg = '{} {} does not have labels: {}. Do nothing.'.format(host, device, labels)
            LOG.info(msg)
            return -1, msg
    LOG.info('{} {} labels to be removed: {}'.format(host, device, to_remove))
    args = [host, device, ' '.join(to_remove)]
    code, output = cli.system(
        'host-device-label-remove', args, ssh_client=con_ssh, fail_ok=fail_ok, auth_info=auth_info
    )
    if code > 0:
        return 1, output

    post_labels = get_host_device_labels(
        host, device, fields='label key', con_ssh=con_ssh, auth_info=auth_info
    )
    not_removed = [label for label in labels if label in post_labels]
    if not_removed:
        raise exceptions.SysinvError('Unexpected {} {} labels {}'.format(host, device, not_removed))
    LOG.info('{} {} labels removed: {}'.format(host, device, to_remove))
    return 0, to_remove


def get_device_images(
    fields='uuid',
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
    rtn_dict=False,
    evaluate=False,
    strict=True,
    regex=False,
    **kwargs,
):
    """
    Get values of device images

    Args:
        fields (str | tuple): fields of value to get
        con_ssh (SSHClient):
        auth_info (dict):
        rtn_dict (bool): whether to return dict of field/value pairs
        evaluate (bool): whether to convert value to python data type
        strict (bool): True to use re.match, False to use re.search
        regex (bool): whether to use regex to find value(s)
        **kwargs: header/value pair(s) as search criteria

    Returns (list | dict):
        when rtn_dict is False, list of values
        when rtn_dict is True, dict of field/values pairs

    """
    table_ = table_parser.table(
        cli.system('device-image-list --nowrap', ssh_client=con_ssh, auth_info=auth_info)[1]
    )
    return table_parser.get_multi_values(
        table_, fields, rtn_dict=rtn_dict, evaluate=evaluate, strict=strict, regex=regex, **kwargs
    )


def get_device_images_state(
    fields='status',
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
    rtn_dict=False,
    evaluate=False,
    strict=True,
    regex=False,
    **kwargs,
):
    """
    Get values of device images state

    Args:
        fields (str | tuple): fields of value to get
        con_ssh (SSHClient):
        auth_info (dict):
        rtn_dict (bool): whether to return dict of field/value pairs
        evaluate (bool): whether to convert value to python data type
        strict (bool): True to use re.match, False to use re.search
        regex (bool): whether to use regex to find value(s)
        **kwargs: header/value pair(s) as search criteria

    Returns (list | dict):
        when rtn_dict is False, list of values
        when rtn_dict is True, dict of field/values pairs

    """
    table_ = table_parser.table(
        cli.system('device-image-state-list --nowrap', ssh_client=con_ssh, auth_info=auth_info)[1]
    )
    return table_parser.get_multi_values(
        table_, fields, rtn_dict=rtn_dict, evaluate=evaluate, strict=strict, regex=regex, **kwargs
    )


def wait_for_device_image_status(
    host,
    pci_device_address,
    device_image_uuid,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
    status='completed',
    timeout=DeviceImageTimeout.COMPLETE,
):
    """
    Wait for a period of time to find expected status of specific image on a host for a device

    Args:
        host (str): host name
        pci_device_address (str): pci of device address
        device_image_uuid (str): uuid of device image
        con_ssh (SSHClient): active controller ssh session
        auth_info (dict): auth info
        status (str): expected status of image
        timeout (int): Timeout to check the status of image

    Return: None
    """
    status_found = False
    end_time = time.time() + timeout
    while time.time() < end_time:
        (
            actual_hostname_list,
            actual_pci_device_address_list,
            actual_device_image_uuid_list,
            actual_status_list,
        ) = get_device_images_state(
            fields=('hostname', 'PCI device address', 'Device image uuid', 'status'),
            con_ssh=con_ssh,
            auth_info=auth_info,
        )
        for (
            actual_hostname,
            actual_pci_device_address,
            actual_device_image_uuid,
            actual_status,
        ) in zip(
            actual_hostname_list,
            actual_pci_device_address_list,
            actual_device_image_uuid_list,
            actual_status_list,
        ):
            if (
                actual_hostname == host
                and actual_pci_device_address == pci_device_address
                and actual_device_image_uuid == device_image_uuid
                and actual_status == status
            ):
                status_found = True
                break
        if status_found:
            break

    assert status_found, (
        "Expected status {} for device {} on host {} with image uuid {} "
        "during {} did not find".format(
            status, pci_device_address, host, device_image_uuid, timeout
        )
    )


def upload_device_image(
    bitstream_file,
    bitstream_type,
    pci_vendor,
    pci_device,
    bitstream_id='',
    key_signature='',
    revoke_key_id='',
    name='',
    description='',
    image_version='',
    uuid='',
    bmc='',
    retimer_included='',
    fail_ok=False,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Upload a device image

    Args:
        bitstream_file (str): path to Bitstream file
        bitstream_type (str): type of the device image bitstream
        pci_vendor (str): PCI vendor (hexadecimal) of the device image
        pci_device (str): PCI device (hexadecimal) of the device image
        bitstream_id (str): bitstream ID (hexadecimal) of the functional device image
        key_signature (str): key signature (hexadecimal) of the root-key device image
        revoke_key_id (str): key ID of the key revocation device image
        name (str): name of the device image
        description (str): description of the device image
        image_version (str): version of the device image
        uuid (str): UUID of the device image
        bmc (bool): BMC image
        retimer_included (bool): Retimer firmware included in BMC FW binary
        fail_ok (bool): whether or not raise exception if command fails
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (0, <uuid of uploaded image>(str))
        (1, <std_err>)

    """
    image_info = {
        'bitstream_type': bitstream_type,
        'pci_vendor': pci_vendor,
        'pci_device': pci_device,
        'bitstream_id': bitstream_id or 'None',
        'key_signature': key_signature or 'None',
        'revoke_key_id': revoke_key_id or 'None',
        'name': name or 'None',
        'description': description or 'None',
        'image_version': image_version or 'None',
    }
    pre_uuids = get_device_images(con_ssh=con_ssh, auth_info=auth_info, **image_info)
    cmd_args = [bitstream_file, bitstream_type, pci_vendor, pci_device]
    optional_arg_map = {
        '--bitstream-id': bitstream_id,
        '--key-signature': key_signature,
        '--revoke-key-id': revoke_key_id,
        '--name': name,
        '--description': description,
        '--image-version': image_version,
        '--uuid': uuid,
        '--bmc': bmc,
        '--retimer-included': retimer_included,
    }
    for key, value in optional_arg_map.items():
        if isinstance(value, bool):
            value = str(value).lower()
        if value:
            cmd_args.append('{} {}'.format(key, value))
    LOG.info('upload device image: {}'.format(cmd_args))
    code, output = cli.system(
        'device-image-upload', cmd_args, ssh_client=con_ssh, fail_ok=fail_ok, auth_info=auth_info
    )
    if code > 0:
        return 1, output

    post_uuids = get_device_images(con_ssh=con_ssh, auth_info=auth_info, **image_info)
    if len(post_uuids) - len(pre_uuids) != 1:
        raise exceptions.SysinvError('Unexpected device image')
    uploaded_uuid = (set(post_uuids) - set(pre_uuids)).pop()
    if uuid and uploaded_uuid != uuid:
        raise exceptions.SysinvError('image uuid is not as expected')
    LOG.info('device image uploaded with uuid: {}'.format(uploaded_uuid))
    return 0, uploaded_uuid


def delete_device_image(
    device_image_uuid,
    check_first=True,
    fail_ok=False,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Delete a device image

    Args:
        device_image_uuid (str): UUID of device image entry
        check_first (bool): whether to check first before deleting image
        fail_ok (bool): whether or not raise exception if command fails
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (-1, "device image <device_image_uuid> does not exist. Do nothing.")
        (0, <device_image_uuid>(str))
        (1, <std_err>)

    """
    if check_first:
        uuids = get_device_images(con_ssh=con_ssh, auth_info=auth_info)
        if device_image_uuid not in uuids:
            msg = 'device image {} does not exist. Do nothing.'.format(device_image_uuid)
            LOG.info(msg)
            return -1, msg
    LOG.info('device image to be deleted: {}'.format(device_image_uuid))
    code, output = cli.system(
        'device-image-delete',
        device_image_uuid,
        ssh_client=con_ssh,
        fail_ok=fail_ok,
        auth_info=auth_info,
    )
    if code > 0:
        return 1, output

    post_uuids = get_device_images(con_ssh=con_ssh, auth_info=auth_info)
    if device_image_uuid in post_uuids:
        raise exceptions.SysinvError('Unexpected device image {}'.format(device_image_uuid))
    LOG.info('device image deleted: {}'.format(device_image_uuid))
    return 0, device_image_uuid


def apply_device_image_labels(
    device_image_uuid,
    labels,
    check_first=True,
    fail_ok=False,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Apply labels to a device image

    Args:
        device_image_uuid (str): UUID of device image entry
        labels (tuple or list of tuple): [(<label key>, <label value>), ...]
        check_first (bool): whether to check first before applying labels
        fail_ok (bool): whether or not raise exception if command fails
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (-1, "image <device_image_uuid> already has labels: <labels>. Do nothing.")
        (0, <applied labels>(list of tuple))
        (1, <std_err>)

    """
    labels = [labels] if isinstance(labels, tuple) else labels
    to_apply = labels
    if check_first:
        image_values = get_device_images(
            fields=('applied', 'applied_labels'),
            con_ssh=con_ssh,
            auth_info=auth_info,
            evaluate=True,
            uuid=device_image_uuid,
        )
        existing_labels = [label.popitem() for label in image_values[1][0] or []]
        to_apply = [label for label in labels if label not in existing_labels]
        if not to_apply:
            msg = 'image {} already has labels: {}. Do nothing.'.format(device_image_uuid, labels)
            LOG.info(msg)
            return -1, msg
    LOG.info('image {} labels to be applied: {}'.format(device_image_uuid, to_apply))
    args = [device_image_uuid, ' '.join(['{}={}'.format(name, value) for name, value in to_apply])]
    code, output = cli.system(
        'device-image-apply', args, ssh_client=con_ssh, fail_ok=fail_ok, auth_info=auth_info
    )
    if code > 0:
        return 1, output

    image_values = get_device_images(
        fields=('applied', 'applied_labels'),
        con_ssh=con_ssh,
        auth_info=auth_info,
        evaluate=True,
        uuid=device_image_uuid,
    )
    post_applied_flag = image_values[0][0]
    if not post_applied_flag:
        raise exceptions.SysinvError('Unexpected image {} applied value'.format(device_image_uuid))
    post_labels = [label.popitem() for label in image_values[1][0] or []]
    not_applied = [label for label in labels if label not in post_labels]
    if not_applied:
        raise exceptions.SysinvError(
            'Unexpected image {} labels {}'.format(device_image_uuid, not_applied)
        )
    LOG.info('image {} labels assigned: {}'.format(device_image_uuid, to_apply))
    return 0, to_apply


def remove_device_image_labels(
    device_image_uuid,
    labels,
    check_first=True,
    fail_ok=False,
    con_ssh=None,
    auth_info=Tenant.get('admin_platform'),
):
    """
    Remove labels from a device image

    Args:
        device_image_uuid (str): UUID of device image entry
        labels (tuple or list of tuple): [(<label key>, <label value>), ...]
        check_first (bool): whether to check first before removing labels
        fail_ok (bool): whether or not raise exception if command fails
        con_ssh (SSHClient):
        auth_info (dict):

    Returns (tuple):
        (-1, "image <device_image_uuid> does not have labels: <labels>. Do nothing.")
        (0, <removed labels>(list of tuple))
        (1, <std_err>)

    """
    labels = [labels] if isinstance(labels, tuple) else labels
    to_remove = labels
    if check_first:
        image_values = get_device_images(
            fields=('applied', 'applied_labels'),
            con_ssh=con_ssh,
            auth_info=auth_info,
            evaluate=True,
            uuid=device_image_uuid,
        )
        existing_labels = [label.popitem() for label in image_values[1][0] or []]
        to_remove = [label for label in labels if label in existing_labels]
        if not to_remove:
            msg = 'image {} does not have labels: {}. Do nothing.'.format(device_image_uuid, labels)
            LOG.info(msg)
            return -1, msg
    LOG.info('image {} labels to be removed: {}'.format(device_image_uuid, to_remove))
    args = [device_image_uuid, ' '.join(['{}={}'.format(name, value) for name, value in to_remove])]
    code, output = cli.system(
        'device-image-remove', args, ssh_client=con_ssh, fail_ok=fail_ok, auth_info=auth_info
    )
    if code > 0:
        return 1, output

    image_values = get_device_images(
        fields=('applied', 'applied_labels'),
        con_ssh=con_ssh,
        auth_info=auth_info,
        evaluate=True,
        uuid=device_image_uuid,
    )
    applied_flag = True if image_values[1][0] else False
    post_applied_flag = image_values[0][0]
    if post_applied_flag is not applied_flag:
        raise exceptions.SysinvError('Unexpected image {} applied value'.format(device_image_uuid))
    post_labels = [label.popitem() for label in image_values[1][0] or []]
    not_removed = [label for label in labels if label in post_labels]
    if not_removed:
        raise exceptions.SysinvError(
            'Unexpected image {} labels {}'.format(device_image_uuid, not_removed)
        )
    LOG.info('image {} labels removed: {}'.format(device_image_uuid, to_remove))
    return 0, to_remove


def get_hosts_by_device(device_class_id, con_ssh=None, auth_info=Tenant.get('admin_platform')):
    """
    Get all nodes where the device is present.

    Args:
        - device_class_id(str):
        - con_ssh(SSHClient):
        - auth_info:

    Returns(list):
        list of hosts were the board is present

    """

    hosts = []
    host_list = system_helper.get_hosts(
        availability=[HostAvailState.AVAILABLE, HostAvailState.ONLINE],
        con_ssh=con_ssh,
        auth_info=auth_info,
    )

    if not host_list:
        LOG.warning("No host is available or online")
        return []

    for host in host_list:
        devices = host_helper.get_host_devices(
            host, field='device_id', con_ssh=con_ssh, auth_info=auth_info
        )
        for device in devices:
            if device == device_class_id:
                hosts.append(host)
                break

    LOG.info("Device {} is present on hosts: {}".format(device_class_id, hosts))
    return hosts


def update_device_image(host_name):
    """
    update the device image on host

    Args:
        host_name (str): Host name

    Returns (tuple):
        (0, successful operation)
        (1, <std_err>)
    """

    LOG.info("Updating th device image on host {}".format(host_name))
    return cli.system("host-device-image-update {}".format(host_name))

