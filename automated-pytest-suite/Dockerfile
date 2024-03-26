FROM python:3.6.8-jessie

#ENV http_proxy=http://147.11.252.42:9090
#ENV https_proxy=http://147.11.252.42:9090

# Install required Python packages
RUN pip3 install \
    pytest==3.6.1 \
    pexpect \
    pyyaml \
    requests

# Set default command to bash
CMD ["bash"]
