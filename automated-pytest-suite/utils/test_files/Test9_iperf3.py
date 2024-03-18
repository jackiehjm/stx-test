import subprocess
import time

def run_kubectl_exec(pod_name, command):
    kubectl_command = f"kubectl exec -it {pod_name} -- {command}"
    process = subprocess.Popen(kubectl_command, stdout=subprocess.PIPE, shell=True)
    return process

pod_name1 = "iperf-server"
command1 = "iperf3 -s -f m -I 60 -p 4444"

pod_name2 = "iperf-client"
command2 = "iperf3 -c 100.56.217.112 -p 4444 -t 30"

# Start iperf server
process1 = run_kubectl_exec(pod_name1, command1)
time.sleep(5)

# Start iperf client
process2 = run_kubectl_exec(pod_name2, command2)
output2, _ = process2.communicate()
output2 = output2.decode('utf-8')

time.sleep(5)
process1.terminate()

output1, _ = process1.communicate()
output1 = output1.decode('utf-8')

print("Iperf Server Output")
print(output1)

print("Iperf Client Output")
print(output2)

lines = output1.split("\n")
result = lines[35]
words = result.split()
bandwidth = words[6]
print(bandwidth)
