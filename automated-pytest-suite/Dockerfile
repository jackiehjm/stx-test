FROM python:3.6.8-jessie

#ENV http_proxy=http://147.11.252.42:9090
#ENV https_proxy=http://147.11.252.42:9090

# Install required Python packages
RUN pip3 install \
    pexpect \
    pytest-html==1.22.1 \
    pytest-rerunfailures==5.0 \
    pytest==3.6.1 \
    pyyaml \
    requests \
    tabulate \
    xmltodict

# Set default command to bash
CMD ["bash"]
