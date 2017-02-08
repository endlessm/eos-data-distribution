FROM eos-dev-ssh
ENV get="apt-get -y --force-yes --allow-unauthenticated"
ENV DEBIAN_FRONTEND="noninteractive"
ENV LANG=C

RUN $get update
RUN $get install nfd python-eos-data-distribution

RUN setcap all=e /usr/bin/nfd
COPY nfd.conf /etc/ndn/nfd.conf

CMD /usr/sbin/sshd -D & /usr/bin/nfd

