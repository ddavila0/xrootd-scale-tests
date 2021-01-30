FROM opensciencegrid/xrootd-standalone

RUN yum -y --enablerepo=osg-upcoming-development update xrootd
RUN mkdir /data/
ADD store /data/store/
