FROM eos-dev
ENV get="apt-get -y --force-yes --allow-unauthenticated"
ENV DEBIAN_FRONTEND="noninteractive"

RUN $get update
RUN $get upgrade
RUN $get install sudo openssh-server
RUN mkdir /var/run/sshd
RUN adduser --system --shell=/bin/sh --home=/home/vagrant --ingroup sudo --disabled-password vagrant
RUN echo 'root:endlessm' | chpasswd
RUN echo 'vagrant:endlessm' | chpasswd
RUN echo 'vagrant ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/vagrant

RUN mkdir -p /home/vagrant/.ssh && chmod 700 /home/vagrant/.ssh
ADD id_rsa.pub /home/vagrant/.ssh/authorized_keys
RUN chmod 400 /home/vagrant/.ssh/authorized_keys && chown -R vagrant.root /home/vagrant/ && chmod 600 /home/vagrant/.ssh/*

EXPOSE 22

CMD /usr/sbin/sshd -D
