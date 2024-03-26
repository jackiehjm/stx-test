FROM harbor.kista.wrs.local/ps_emea/wrcptestsuite:base
RUN git clone http://bitbucket.wrs.com/scm/eps/emea-ps-cloud-team.git
RUN mkdir -p /wrcp-testsuite
RUN mv /emea-ps-cloud-team/platform-sanity-testcases/ /usr/wrcptestsuite
RUN mkdir -p RUN mkdir -p /usr/wrcptestsuite/bin
COPY files/entrypoint.sh /usr/wrcptestsuite/bin
RUN rm -rf /emea-ps-cloud-team
RUN chmod -R +x /usr/wrcptestsuite/bin
