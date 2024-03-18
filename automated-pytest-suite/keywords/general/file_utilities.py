from keywords import host_helper
from utils import exceptions
from utils.clients.ssh import ControllerClient
from utils.tis_log import LOG


def create_file(file_path, content=None, con_ssh=None, apply_newline=False, fail_ok=False):
    """
    Create a file on the active controller based on provided content
    Args:
        file_path: The absolute path to the file to create
        content: The contents of the file
        con_ssh: The connection to the active controller host
        apply_newline (bool): To applying new line char (\n)
        fail_ok: Whether to exception on error

    Returns (exit code (int), command output (str))
    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    if apply_newline:
        cmd = 'echo -e "{}" > {}'.format(content, file_path)
    else:
        cmd = 'echo "{}" > {}'.format(content, file_path)
    code, out = con_ssh.exec_cmd(cmd, fail_ok=fail_ok)

    if code != 0 and not fail_ok:
        raise exceptions.SSHExecCommandFailed('CMD: {} Output: {}'.format(cmd, out))
    return code, out


def get_file_content(file, host, con_ssh=None, fail_ok=False):
    """
    Get given file's content via cat cmd on given host

    Args:
        - file(str): target file's absolute path to get content from
        - hosts(str): host where target file is located
        - con_ssh(SSHConnection):
        - fail_ok(bool): wether to return or raise in case of failure

    Returns:
        - (0, file_content) if succedeed
        - (1, output) in case of failure and fail_ok
    """

    LOG.info("Getting {} content on {}".format(file, host))
    cmd = "cat {}".format(file)
    with host_helper.ssh_to_host(host) as host_ssh:
        rc, out = host_ssh.exec_sudo_cmd(cmd, fail_ok=fail_ok)
    return rc, out


def get_files_in_tar_verbosely(file_path, con_ssh=None):
    """
    Get the files inside a tar file

    Args:
        file_path (str): path to the file
        con_ssh (SSHConnection): ssh connection to lab

    Returns (str): output of tar -tvf <file-name>
    """
    if con_ssh is None:
        con_ssh = ControllerClient.get_active_controller()

    _, output = con_ssh.exec_cmd("tar -tvf {}".format(file_path))

    return output


def touch_file(file_path, con_ssh=None, fail_ok=False):
    """
    Create an empty file

    Args:
        file_path (str): The absolute path of the file
        con_ssh: The connection to the active controller host
        fail_ok: Whether to exception on error

    Returns (exit code (int), command output (str))
    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    cmd = "touch {}".format(file_path)
    code, out = con_ssh.exec_sudo_cmd(cmd, fail_ok=fail_ok)

    if code != 0 and not fail_ok:
        raise exceptions.SSHExecCommandFailed('CMD: {} Output: {}'.format(cmd, out))
    return code, out


def change_file_mode(file_path, octal_permissions="666", con_ssh=None, fail_ok=False):
    """
    Change file mode

    Args:
        file_path (str): The absolute path of the file
        octal_permissions (str): Octal permission value (e.g. 666 = u=rw,g=rw,o=rw)
        con_ssh: The connection to the active controller host
        fail_ok: Whether to exception on error

    Returns (exit code (int), command output (str))
    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    cmd = "chmod {} {}".format(octal_permissions, file_path)
    code, out = con_ssh.exec_sudo_cmd(cmd, fail_ok=fail_ok)

    if code != 0 and not fail_ok:
        raise exceptions.SSHExecCommandFailed('CMD: {} Output: {}'.format(cmd, out))
    return code, out


def create_repo_file(
        repo_dir="/etc/yum.repos.d/",
        file_name=None,
        repo=None,
        repo_name=None,
        baseurl=None,
        enabled=0,
        gpgcheck=1,
        gpgkey=None,
        con_ssh=None,
        fail_ok=False
):
    """
    Create a repo file on the active controller based on provided content

    Args:
        repo_dir (str): The repository's directory
        file_name (str): The name of the repository file
        repo (str): The repository global name
        repo_name (str): Human readable repository name
        baseurl (str): URL to repodata dir (e.g. http://path/to/repo)
        enabled (bool): Enable(1)/disable(0) repo (Default = 0)
        gpgcheck (bool): Enable(1)/disable(0) repo GPG signature
                         check (Default = 1)
        gpgkey (str): URL to specify the source of the GPG key to be
                      imported (e.g. http://path/to/key)
        con_ssh: The connection to the active controller host
        fail_ok: Whether to exception on error

    Returns (exit code (int), command output (str))
    """
    if not con_ssh:
        con_ssh = ControllerClient.get_active_controller()

    file_absolute_path = "{}/{}".format(repo_dir, file_name)

    touch_file(file_absolute_path, con_ssh=con_ssh)
    change_file_mode(file_absolute_path, con_ssh=con_ssh)

    repo_file_content = "\n".join(['[{}]',
                                   'name={}',
                                   'baseurl={}',
                                   'enabled={}',
                                   'gpgcheck={}',
                                   'gpgkey={}']).format(repo, repo_name, baseurl, enabled, gpgcheck, gpgkey)

    cmd = 'echo -e "{}" > {}'.format(repo_file_content, file_absolute_path)
    code, out = con_ssh.exec_sudo_cmd(cmd, fail_ok=fail_ok)

    if code != 0 and not fail_ok:
        raise exceptions.SSHExecCommandFailed('CMD: {} Output: {}'.format(cmd, out))
    return code, out

