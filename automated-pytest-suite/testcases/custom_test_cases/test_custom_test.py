from pytest import mark, fixture


@mark.platform_sanity
@mark.dc_subcloud
class TestCustomTest:
    def test_custom_test(self):
        """
        Verify Ping test between pods
        Args:
            deploy_test_pods(fixture): returns server_ips, client_pods, deployment_name, service_name
        Setup:
            - Label the nodes and add node selector to the deployment files
                if not simplex system
            - Copy the deployment files from localhost to active controller
            - Deploy server pod
            - Deploy client pods
        Steps:
            - Ping the server pod ip from the client pod
        Teardown:
            - Delete the service
            - Delete the server pod deployment
            - Delete the client pods
            - Remove the labels on the nodes if not simplex

        """
        print("This is a custom function")
