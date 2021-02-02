FROM opensciencegrid/xrootd-standalone:fresh

# Get Xrootd-5
RUN yum -y --enablerepo=osg-upcoming-development update xrootd
RUN mkdir /data/
ADD store /data/store/
