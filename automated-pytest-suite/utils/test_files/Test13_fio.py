import pexpect
import subprocess
import re
import time

command = "sudo docker run -it joshuarobinson/fio:3.26 fio --randrepeat=1 --ioengine=libaio --direct=1 --gtod_reduce=1 --name=test --filename=/mnt1/random_read_write.fio --bs=4k --iodepth=64 --size=4G --readwrite=randrw --rwmixread=80 --runtime 3 --time_based"

child = pexpect.spawn(f"sudo {command}")

password = "Li69nux*"
child.expect(".*[Pp]assword.*")
child.sendline(password)

child.wait()

process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(55)
stdout, stderr = process.communicate()

output = stdout.decode().strip()

exit_code = child.exitstatus

word1 = "read"
word2 = "write"
end_character = "k"

pattern = rf"\b{re.escape(word1)}\b(.*?{re.escape(end_character)})|\b{re.escape(word2)}\b(.*?{re.escape(end_character)})"
matches = re.findall(pattern, output, re.DOTALL)
if matches:
    extracted_texts = []
    for match in matches:
        for group in match:
            if group:
                extracted_text = group.strip()
                if word1 in extracted_text:
                    extracted_text = extracted_text[7:-1]
                else:
                    extracted_text = extracted_text[7:-1]
                extracted_texts.append(extracted_text)
    print(extracted_texts[0])
    print(extracted_texts[1])
else:
    print("No matches found.")
