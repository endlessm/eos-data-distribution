FROM    debian:stable
MAINTAINER xaiki@endlessm.com

ENV get="apt-get -y --force-yes --allow-unauthenticated"
ENV DEBIAN_FRONTEND="noninteractive"

RUN $get update
RUN $get install apt-transport-https

COPY endless.list /etc/apt/sources.list.d/
COPY 10insecure /etc/apt/apt.conf.d/
COPY 10force-yes /etc/apt/apt.conf.d/
COPY 10no-recommends /etc/apt/apt.conf.d/

RUN $get update -m
RUN $get install build-essential
RUN $get dist-upgrade 

