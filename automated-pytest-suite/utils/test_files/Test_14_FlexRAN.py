import subprocess
import re

def execute_kubectl_command(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print("Error executing command:")
            print(result.stderr)
            return None
    except Exception as e:
        print("An error occurred:", str(e))
        return None

if __name__ == "__main__":

    # First command: Get some output
    PCI = f"kubectl exec -it fl0 -- env | grep PCI"
    output = execute_kubectl_command(PCI)
    if output:
        # Extract the last 12 characters from the output
        extracted_chars = output[-12:]
        print("PCI is " + extracted_chars)
        if f"kubectl exec -it fl0 -- grep -i '0000:70:00.0' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml":
            replace_PCI = f"kubectl exec -it fl0 -- sed -i 's/0000:70:00.0/" + extracted_chars +"/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_PCI)
            print("PCI replaced in the file.")
        else:
            print("PCI not replaced in the file.")
    if f"kubectl exec -it fl0 -- grep -i 'BbuPoolSleepEnable>1' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml":
        replace_BbuPoolSleepEnable = f"kubectl exec -it fl0 -- sed -i 's/BbuPoolSleepEnable>1/BbuPoolSleepEnable>0/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
        execute_kubectl_command(replace_BbuPoolSleepEnable)
        print("BbuPoolSleepEnable replaced in the file.")
    else:
        print("BbuPoolSleepEnable not replaced in the file.")
    taskset = f"kubectl exec -it fl0 -- taskset -pc 1"
    affinity = execute_kubectl_command(taskset)
    print(affinity)
    separator = ": "
    affinity_list = affinity.split(separator, 1)[-1]
    print(affinity_list)
    CPUs = []
    ranges_and_numbers = affinity_list.split(',')
    for entry in ranges_and_numbers:
        if "-" in entry:
            start, end = map(int, entry.split('-'))
            CPUs.extend(range(start, end + 1))
        else:
            CPUs.append(int(entry))
    print(CPUs)
    systemCPU = CPUs[0]
    timerCPU = CPUs[1]
    radioDPDKCPU = CPUs[2]
    print("Selected CPUs are: " + str(systemCPU) + ", " + str(timerCPU) + " and " + str(radioDPDKCPU))
    pod_name = "fl0"

    pattern = r"<systemThread>(\d+),\s*\d+,\s*\d+</systemThread>"

    kubectl_command = f"kubectl exec -i {pod_name} -- cat /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"

# Run the kubectl command and capture its output
    try:
        output = subprocess.check_output(kubectl_command, shell=True, text=True)
    except subprocess.CalledProcessError:
        print("Error executing kubectl command.")
        exit(1)

# Search for the pattern in the output
    match = re.search(pattern, output)
    if match:
        print(match)
        first_number = int(match.group(1))
        print(first_number)
        if first_number not in CPUs:
        # Replace the first number with the replacement number
            replace_system = f"kubectl exec -it fl0 -- sed -i 's/<systemThread>{first_number}/<systemThread>{systemCPU}/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_system)
            replace_system = f"kubectl exec -it fl0 -- sed -i 's/<wlsNrtThread>{first_number}/<wlsNrtThread>{systemCPU}/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_system)
            replace_system = f"kubectl exec -it fl0 -- sed -i 's/<FpgaDriverCpuInfo>{first_number}/<FpgaDriverCpuInfo>{systemCPU}/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_system)
            replace_system = f"kubectl exec -it fl0 -- sed -i 's/<FrontHaulCpuInfo>{first_number}/<FrontHaulCpuInfo>{systemCPU}/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_system)
    pattern = r"<systemThread>(\d+),\s*\d+,\s*\d+</systemThread>"

    kubectl_command = f"kubectl exec -i {pod_name} -- cat /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"

# Run the kubectl command and capture its output
    try:
        output = subprocess.check_output(kubectl_command, shell=True, text=True)
    except subprocess.CalledProcessError:
        print("Error executing kubectl command.")
        exit(1)
    pattern = r"<timerThread>(\d+),\s*\d+,\s*\d+</timerThread>"
# Search for the pattern in the output
    match = re.search(pattern, output)
    if match:
        print(match)
        first_number = int(match.group(1))
        print(first_number)
        if first_number not in CPUs:
        # Replace the first number with the replacement number
            replace_system = f"kubectl exec -it fl0 -- sed -i 's/<timerThread>{first_number}/<timerThread>{timerCPU}/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_system)
    pattern = r"<radioDpdkMaster>(\d+),\s*\d+,\s*\d+</radioDpdkMaster>"
# Search for the pattern in the output
    match = re.search(pattern, output)
    if match:
        print(match)
        first_number = int(match.group(1))
        print(first_number)
        if first_number not in CPUs:
        # Replace the first number with the replacement number
            replace_system = f"kubectl exec -it fl0 -- sed -i 's/<radioDpdkMaster>{first_number}/<radioDpdkMaster>{radioDPDKCPU}/' /opt/FlexRAN/bin/nr5g/gnb/l1/phycfg_timer.xml"
            execute_kubectl_command(replace_system)


    # Calculate the start and end index of the middle 12 numbers
    middle_start = len(CPUs) // 2 - 6
    middle_end = len(CPUs) // 2 + 6

    # Extract the middle 12 numbers
    middle_numbers = CPUs[middle_start:middle_end]

    # Create the command string
    command_template = " 1 << {} "
    command_list = [command_template.format(idx) for idx in middle_numbers]
    command = " | ".join(command_list)

    # Print the final command
    final_command = "printf \"%x\\n\" $((" + command + "))"
    print(final_command)
    mask = subprocess.run(final_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Mask is " + mask.stdout)
    # Check the return code
    if mask.returncode == 0:
         print("Command executed successfully")
         mask_final = mask.stdout.split('\n')[0]
         replace_mask = f"kubectl exec -it fl0 -- sed -i 's/setcore 0x0005550000055500/setcore 0x{mask_final}/' /opt/FlexRAN/bin/nr5g/gnb/testmac/mwc-18220.cfg"
         execute_kubectl_command(replace_mask)
         replace_mask = f"kubectl exec -it fl0 -- sed -i 's/setcore 0x0005550000055500/setcore 0x{mask_final}/' /opt/FlexRAN/bin/nr5g/gnb/testmac/mwc-6389.cfg"
         execute_kubectl_command(replace_mask)
    else:
         print("Command failed with error:")
         print(mask.stderr)
