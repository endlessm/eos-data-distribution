FROM eos-dev
ENV get="apt-get -y --force-yes --allow-unauthenticated"
ENV DEBIAN_FRONTEND="noninteractive"

RUN $get install systemd
RUN rm -f /lib/systemd/system/multi-user.target.wants/*;
RUN rm -f /etc/systemd/system/*.wants/*;
RUN rm -f /lib/systemd/system/local-fs.target.wants/*;
RUN rm -f /lib/systemd/system/sockets.target.wants/*udev*;
RUN rm -f /lib/systemd/system/sockets.target.wants/*initctl*;
RUN rm -f /lib/systemd/system/basic.target.wants/*;

VOLUME [ “/sys/fs/cgroup” ]
CMD /sbin/init
