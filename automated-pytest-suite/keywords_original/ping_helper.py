from utils.tis_log import LOG

from utils.clients.ssh import SSHClient
from datetime import datetime
import time
import re


class PingTraffic(object):
    def __init__(self):
        """ Initializer for ping traffic class """
        pass

    def run_ping_in_background(self, device, command, logfile=None, duration=10):
        """ Runs command and returns process id
        Args:
            device_ssh : device object to be used to run the command
            command (str): command to be executed
        Returns:
            int: process id
        """

        if logfile is None:
            command = "nohup {} >/dev/null 2>&1 & echo $!".format(command)
        else:
            command = "nohup {} >/dev/null 2>&1 > {logfile} & echo $!".format(command)

        pid = device.execute(command)
        LOG.info("waiting for {} seconds for ping to complete".format(duration+5))
        time.sleep(duration+5)
        for pid_result in pid.split('\n'):
            if pid_result != '':
                if ']' not in pid_result:
                    return int(pid_result)
                else:
                    return int(pid_result.split('] ')[-1])
        return None

    def get_background_traffic_result(self, con_ssh, username, password, logfile, **kwargs):
        pid = kwargs.get('pid', None)
        start_time = kwargs.get('start_time')
        duration = kwargs.get('duration', 0)
        time_elapsed = int((datetime.now() - start_time).total_seconds())
        if time_elapsed < duration + 8:
            LOG.info("Wait for remaining {} seconds (duration + 8 - time_elapsed) for background traffic to finish"
                   .format(duration + 8 - time_elapsed))
            time.sleep(duration + 8 - time_elapsed)

        output = con_ssh.exec_cmd("cat {}".format(logfile), fail_ok=False, get_exit_code=False)[1]
        LOG.info("Output is: {}".format(output))
        time.sleep(2)
        con_ssh.exec_cmd("kill -9 {}".format(pid))
        con_ssh.exec_cmd('rm {}'.format(logfile))

        return self.parse_traffic_output(output, dest_addr=con_ssh.host), output


    def _get_match_groups(self, output, regex):
        """ Gets match groups
        Args:
            output (str): output
            regex (obj): regex compiled object
        Returns:
            list: returns matching groups
        """

        match = regex.search(output)
        if not match:
            raise Exception('Pattern : {} not found in output:{}'.format(regex.pattern, output))
        LOG.info("Matched groups {}".format(match.groups()))
        return match.groups()

    def parse_traffic_output(self, output, **kwargs):
        dest_addr = kwargs.get("dest_addr", "")
        ping_output = output

        # default return params
        sent = received = duplicates = loss = errors = mtu = duration = 0
        minping, avgping, maxping, jitter = ['NaN'] * 4

        matcher = re.compile(r'PING ([a-zA-Z0-9.\-]+) \(')
        try:
            matcher = re.compile(
                r'(\d+) packets transmitted, (\d+).*received, (\d+)% packet loss'
            )
            sent, received, loss = self._get_match_groups(ping_output, matcher)
            LOG.info("Loss is {}".format(loss))
        except Exception:
            pattern = r"(\d+)\s+packets\s+transmitted,\s+(\d+)\s+packets\s+received,"
            error_flag = False
            duplicates_flag = False
            if 'duplicates' in ping_output:
                pattern = r"{}\s+\+(\d+)\s+duplicates".format(pattern)
                duplicates_flag = True
            if 'errors' in ping_output:
                pattern = r"{}\s+\+(\d+)\s+errors".format(pattern)
                error_flag = True
            pattern = r"{}\s+(\d+)%\s+packet\s+loss".format(pattern)
            matcher = re.compile(pattern)
            if error_flag and not duplicates_flag:
                sent, received, errors, loss = self._get_match_groups(
                    ping_output, matcher)
            elif duplicates_flag and not error_flag:
                sent, received, duplicates, loss = self._get_match_groups(
                    ping_output, matcher)
            elif error_flag and duplicates_flag:
                sent, received, errors, duplicates, loss = self._get_match_groups(
                    ping_output, matcher)
        host = dest_addr
        LOG.info("Loss before return is {}".format(loss))
        return {
            'host': host,
            'sent': int(sent),
            'received': int(received),
            'minping': float(minping),
            'avgping': float(avgping),
            'maxping': float(maxping),
            'jitter': float(jitter),
            'packet_loss': int(loss),
            'duplicates': int(duplicates),
            'errors': int(errors),
            'mtu': int(mtu),
            'duration': round(int(duration) / 1000)
        }


if __name__ == "__main__":
    pass


