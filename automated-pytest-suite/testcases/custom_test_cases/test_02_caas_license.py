from pytest import fixture, mark, skip
from utils import cli
from utils.tis_log import LOG
from keywords import host_helper, system_helper
import re

@mark.caas
def test_cass_license(request):
    host=system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        alarms = system_helper.get_alarms_table()
        LOG.info(alarms)
        assert "license" not in str(alarms).lower()