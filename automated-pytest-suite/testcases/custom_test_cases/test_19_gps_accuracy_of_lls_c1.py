import re
from pytest import fixture, mark, skip
from utils.tis_log import LOG
from keywords import host_helper, system_helper

@mark.caas
def test_gps_accuracy_of_lls_c1(request):
    host = system_helper.get_active_controller_name()
    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Checking if the GNSS is valid and locked ")
        code, output = con_ssh.exec_sudo_cmd("cat /sys/kernel/debug/ice/0000:51:00.0/cgu")
        matcher1 = re.compile("GNSS-1PPS (6) |      valid |       0 |       0 |")
        assert bool(matcher1.search(output)), "GNSS is not valid"
        matcher2 = re.compile("EEC DPLL:[\n\s\t]+Current reference:[\n\s\t]+GNSS-1PPS[\n\s\t]+Status:[\n\s\t]+locked_ho_ack")
        assert bool(matcher2.search(output)), "GNSS is not locked"
        matcher3 = re.compile("PPS DPLL:[\n\s\t]+Current reference:[\n\s\t]+GNSS-1PPS[\n\s\t]+Status:[\n\s\t]+locked_ho_ack")
        assert bool(matcher2.search(output)), "GNSS is not locked"

