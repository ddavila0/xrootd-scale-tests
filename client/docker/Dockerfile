FROM centos:7

RUN yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm -y
RUN yum install https://repo.opensciencegrid.org/osg/3.5/osg-3.5-el7-release-latest.rpm -y

RUN yum install xrootd xrootd-server xrootd-client xrootd-client-devel xrootd-python python3-xrootd -y
RUN yum install vim less -y

RUN yum install python3 -y

RUN pip3 install pika python-dotenv

ADD docker/vimrc /root/.vimrc
ADD utils /utils
