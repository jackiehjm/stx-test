import subprocess
import signal
import time
import pexpect

def check_output(output):
    return 'Memory' in output

# Start the first process with sudo
sudo_password = 'Li69nux*'
command1 = 'docker container run -it alexeiled/stress-ng --vm 4 --vm-bytes 8000M --vm-keep -m 1 --metrics-brief --timeout 1h'

child1 = pexpect.spawn(f'sudo -S {command1}')
child1.expect('Password:')
child1.sendline(sudo_password)

# Start the second process
command2 = 'fm alarm-list'

timeout = 300

# Get the start time
start_time = time.time()

while True:
    # Check for alarm generation 
    output2 = subprocess.check_output(command2, shell=True).decode()

    if check_output(output2):
        print(output2)
        # Send interrupt signal to the first process
        child1.sendintr()
        child1.close()
        break

    elapsed_time = time.time() - start_time
    if elapsed_time >= timeout:
        # Send interrupt signal to the first process
        child1.sendintr()
        child1.close()
        print("Timeout reached. First process stopped.")
        break

    time.sleep(1)
