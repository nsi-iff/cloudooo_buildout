Buildout for cloudooo
=====================

How to Install
--------------

sudo apt-get install gcc g++ make diff groff rpm2cpio patch uml-utilities bridge-utils git-core

python2.6 -S -c 'import urllib2; exec urllib2.urlopen("http://python-distribute.org/bootstrap.py").read()'

bin/buildout -vv


Dependencies
~~~~~~~~~~~~~~~~~~~
Cloudooo uses a system buildout so most of all dependencies are installed by it, 
but it assumes that it has git and python.
