import re
import subprocess

def start_process1(output_file):
    command1 = "kubectl exec -it dpdk-testpmd -- /opt/bin/testpmd -l testpmd_affinity -n4 -w testpmd_PCI --socket-mem 1024 -- --forward-mode=mac --eth-peer=0,\"9e:fd:e6:dd:44:44\" --auto-start --no-lsc-interrupt --stats-period 1"
    with open(output_file, "w") as file:
        process1 = subprocess.Popen(command1, shell=True, stdout=file, stderr=subprocess.STDOUT)
    return process1

def start_process2(output_file):
    command2 = "expect Test10_expect.expect"
    with open(output_file, "w") as file:
        process2 = subprocess.Popen(command2, shell=True, stdout=file, stderr=subprocess.STDOUT)
    return process2

def get_values_from_output(output_file, keyword):
    values = []
    with open(output_file, "r") as file:
        for line in file:
            match = re.search(f'{keyword}:\s+(\d+)', line)
            if match:
                value = int(match.group(1))
                values.append(value)
    return values

def main():
    process1 = start_process1("output_process1.txt")

    process2 = start_process2("output_process2.txt")

    process2.wait()

    process1.terminate()

    keyword1 = "Rx-bps"
    keyword2 = "Tx-bps"

    values_process1_word1 = get_values_from_output("output_process1.txt", keyword1)
    values_process1_word2 = get_values_from_output("output_process1.txt", keyword2)


    # Calculate averages for each set of values
    average_word1_process1 = sum(values_process1_word1) / len(values_process1_word1)
    average_word2_process1 = sum(values_process1_word2) / len(values_process1_word2)

    print(f"{average_word1_process1}")
    print(f"{average_word2_process1}")

if __name__ == "__main__":
    main()
