import subprocess
import time
import signal

def execute_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def save_output_to_file(filename, stdout, stderr):
    with open(filename, 'w') as file:
        file.write("Standard Output:\n")
        file.write(stdout)
        file.write("\nStandard Error:\n")
        file.write(stderr)

# Command for the first session
command_session1 = "kubectl exec -it fl0 -- /bin/bash -c 'source /opt/setup.sh && cd /opt/FlexRAN/bin/nr5g/gnb/l1 && ./l1.sh -e'"

# Command for the second session
command_session2 = "kubectl exec -it fl0 -- /bin/bash -c 'source /opt/setup.sh && cd /opt/FlexRAN/bin/nr5g/gnb/testmac && ./l2.sh -testfile mwc-6389.cfg'"

# Execute the first command in the first session
session1_process = execute_command(command_session1)
time.sleep(30)  # Wait for 30 seconds before interrupting the first session

# Execute the second command in the second session
session2_process = execute_command(command_session2)
time.sleep(60)  # Wait for 60 seconds before interrupting the second session
session1_process.send_signal(signal.SIGINT)
session2_process.send_signal(signal.SIGINT)

# Get the output of the first session
stdout_session1, stderr_session1 = session1_process.communicate()
save_output_to_file("session1_14-2_output.txt", stdout_session1, stderr_session1)


# Get the output of the second session
stdout_session2, stderr_session2 = session2_process.communicate()
save_output_to_file("session2_14-2_output.txt", stdout_session2, stderr_session2)

subprocess.run(["kubectl", "cp", "fl0:./session1_14-2_output.txt", "./session1_14-2_output.txt"])
subprocess.run(["kubectl", "cp", "fl0:./session2_14-2_output.txt", "./session2_14-2_output.txt"])
subprocess.run(["kubectl", "cp", "fl0:/opt/FlexRAN/bin/nr5g/gnb/l1/l1_mlog_stats.txt", "./session2_14-2_output_python.txt"])
