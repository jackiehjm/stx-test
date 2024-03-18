from pytest import mark
from utils.tis_log import LOG
from keywords import host_helper,container_helper,system_helper,common
from consts.stx import HostAvailState, Container
from consts.filepaths import TestServerPath, StxPath
from utils import cli
from consts.auth import HostLinuxUser

@mark.caas
def test_push_docker_image_to_local_registry(request):
    home_dir = HostLinuxUser.get_home()
    common.scp_from_localhost_to_active_controller("/usr/wrcptestsuite/automated-pytest-suite/utils/test_files/busybox.tar.gz", dest_path=home_dir)
    test_image = "{}/busybox.tar.gz".format(home_dir)
    reg_addr = Container.LOCAL_DOCKER_REG
    host = system_helper.get_active_controller_name()

    with host_helper.ssh_to_host(hostname=host) as con_ssh:
        LOG.tc_step("Load {} image on controller "
                    "{}".format(test_image, host))
        image_id = container_helper.load_docker_image(name=test_image, imagename="busybox",
                                                      con_ssh=con_ssh)[1]

        def remove_local_images():
            cli.system("registry-image-delete busybox:latest", ssh_client=con_ssh)
            cli.system("registry-garbage-collect", ssh_client=con_ssh)
            _, ret = cli.system("registry-image-tags busybox", ssh_client=con_ssh)
            assert ret == "","Busybox registry image tag did not clear"

        request.addfinalizer(lambda: remove_local_images())
        LOG.tc_step("Tag image with local registry")
        target_name = '{}/busybox:latest'.format(reg_addr)
        container_helper.tag_docker_image(source_image=image_id,
                                          target_name=target_name,
                                          con_ssh=con_ssh)

        LOG.tc_step("Login to local docker registry and push busybox image from "
                    "controller {}".format(host))
        container_helper.login_to_docker(registry=reg_addr, con_ssh=con_ssh)
        container_helper.push_docker_image(target_name, con_ssh=con_ssh)
        LOG.tc_step("Remove cached busybox and pull from local "
                    "registry on {}".format(host))
        container_helper.remove_docker_images(images=("busybox", target_name),
                                              con_ssh=con_ssh)
        container_helper.pull_docker_image(name=target_name, con_ssh=con_ssh)

        _,ret= cli.system("registry-image-list | grep 'Image\|busybox\|+'", ssh_client=con_ssh)

        assert "busybox" in ret,"busybox is not present in registry-image-list"
        container_helper.remove_docker_images(images=(target_name, ),
                                              con_ssh=con_ssh)

