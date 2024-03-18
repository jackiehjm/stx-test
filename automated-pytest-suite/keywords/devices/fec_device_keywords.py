from keywords import host_helper, system_helper
from testcases.wrcp.regression.networking.test_fpga import FpgaLib
from testfixtures.recover_hosts import HostsToRecover
from utils.tis_log import LOG


def reset_device_configuration(hosts):
    """
    The function will reset the N3000 cards to default settings.
    Args:
        hosts (List[String]): The list of hosts on which we want to look for the fec devices.
    Returns:
        None
    """

    fec_device_id = '0d8f'

    LOG.info("Resetting N3000 FEC driver")
    for host in hosts:

        addresses = host_helper.get_host_devices(
            host,
            field='address',
            list_all=True,
            strict=True,
            **{'device id': fec_device_id},
        )

        if addresses:

            HostsToRecover.add(host)
            host_helper.lock_host(host, swact=True)

            # The product only supports ONE N3000 card on a given host at this time.
            # The one with the smallest address must be selected.
            address = min(addresses)

            LOG.fixture_step("Reset N3000 FEC driver to igb_ui on host: {}".format(host), depth=1)

            # Removing Host Devices needs to be done in two steps.
            # See https://jira.wrs.com/browse/CGTS-29639 for Details
            host_helper.modify_host_device(
                host,
                address,
                new_state=True,
                new_driver='igb_uio',
                new_vf_driver='none',
                sriov_numvfs=0,
            )

            LOG.fixture_step(f"Checking current state on host: {host} before the reset")
            system_helper.get_hosts_values(
                hosts=system_helper.get_controllers(),
                fields=[
                    'id',
                    'hostname',
                    'personality',
                    'administrative',
                    'operational',
                    'availability',
                    'task',
                    'subfunctions',
                ],
            )

            current_sriov_numvfs = int(
                host_helper.get_host_device_values(
                    host=host, device=address, fields='sriov_numvfs'
                )[0]
            )

            assert (
                current_sriov_numvfs == 0
            ), f"The current value of sriov_numvfs is {current_sriov_numvfs}, the expected is 0"

            LOG.fixture_step(f"Resuming modify's task on host: {host}")
            host_helper.modify_host_device(
                host,
                address,
                new_state=False,
                new_driver='none',
            )

            FpgaLib.unlock_host_with_retries(host)
            HostsToRecover.remove(host)
