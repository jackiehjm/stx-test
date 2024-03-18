#!/bin/bash
pullImages(){
sudo docker login harbor.kista.wrs.local
sudo docker pull harbor.kista.wrs.local/ps_emea/wrcptestsuite:22.21
sudo docker pull harbor.kista.wrs.local/ps_emea/mantri425/wind-test:latest
sudo docker pull harbor.kista.wrs.local/ps_emea/node-hello:1.0
sudo docker pull harbor.kista.wrs.local/ps_emea/resource-consumer:1.9
}

tagAndPushImages(){
sudo docker login registry.local:9001
sudo docker image tag harbor.kista.wrs.local/ps_emea/wrcptestsuite:22.21 registry.local:9001/ps_emea/wrcptestsuite:22.21
sudo docker image tag harbor.kista.wrs.local/ps_emea/mantri425/wind-test:latest registry.local:9001/mantri425/wind-test:latest
sudo docker image tag harbor.kista.wrs.local/ps_emea/node-hello:1.0 registry.local:9001/ps_emea/node-hello:1.0
sudo docker image tag harbor.kista.wrs.local/ps_emea/resource-consumer:1.9 registry.local:9001/ps_emea/resource-consumer:1.9
sudo docker push registry.local:9001/ps_emea/wrcptestsuite:22.21
sudo docker push registry.local:9001/ps_emea/node-hello:1.0
sudo docker push registry.local:9001/ps_emea/resource-consumer:1.9
}

createSecrets(){
sudo docker push registry.local:9001/mantri425/wind-test:latest
kubectl create secret docker-registry --docker-server=registry.local:9001 --docker-username=admin --docker-password=Wind2022@ registry-creds
kubectl create namespace test
kubectl create secret docker-registry --docker-server=registry.local:9001 --docker-username=admin --docker-password=Wind2022@ registry-creds -n test
}

createFile(){
cat  << EOF > wrcptestsuite.yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
  namespace: test
data:
 lab.json: |
   {
    "short_name": "CASS1",
    "name": "kista_CASS1.com",
    "floating ip": "128.224.211.35",
    "controller-0 ip": "128.224.211.36",
    "controller-1 ip": "128.224.211.37"
   }
 stx-test_template.conf: |
   [auth]
   oam_floating_ip =
   controller0_oam_ip =
   controller1_oam_ip =
   linux_username = sysadmin
   linux_user_password = Wind2022@
   # Platform keystone admin user and project info
   platform_admin_username = admin
   platform_admin_project_name = admin
   platform_admin_password = Wind2022@
   platform_admin_domain_name = Default

   [natbox]
   natbox_host = localhost
   natbox_user = tester
   natbox_password = tester
---
apiVersion: v1
kind: Pod
metadata:
  name: wrcptestsuite
  namespace: test
spec:
  nodeName: controller-1
  imagePullSecrets:
   - name: registry-creds
  containers:
   - name: wrcptestsuite
     image: registry.local:9001/ps_emea/wrcptestsuite:22.21
     volumeMounts:
       - name: test-config
         mountPath: /root/test-config/
     env:
       - name: SOURCE_OPENRC
         value: "True"
       - name: IS_SIMPLEX
         value: "False"
       - name: IS_DC
         value: "False"
     imagePullPolicy: Always
     command: ["bash", "/usr/wrcptestsuite/bin/entrypoint.sh"]
  volumes:
     - name: test-config
       configMap:
         name: test-config
EOF
}

echo "pulling the images"
pullImages
echo "Tagging and pushing the images"
tagAndPushImages
echo "Crewating required secrets"
createSecrets
echo "Creating the pod manifestfile"
createFile
