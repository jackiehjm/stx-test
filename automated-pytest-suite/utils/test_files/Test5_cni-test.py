import subprocess

result = subprocess.run(['kubectl', 'get', 'pods', '-o', 'custom-columns=NAME:.metadata.name,IP:.status.podIP', '--no-headers'], stdout=subprocess.PIPE, text=True, check=True)

lines = result.stdout.strip().split('\n')

for line1 in lines:
    name1, ip1 = line1.split()

    if name1.startswith("cni"):
        # Loop through each line of the output again
        for line2 in lines:
            name2, ip2 = line2.split()

            if name2.startswith("cni") and name1 != name2:
                # Ping the second pod from the first pod 3 times
                print(f"Pinging {name2} from {name1}...")
                subprocess.run(['kubectl', 'exec', name1, '--', 'ping', '-c', '3', ip2])
                print()
