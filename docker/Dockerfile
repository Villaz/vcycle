FROM ubuntu:latest

RUN apt-get -y update
RUN apt-get -y install wget git python
RUN apt-get -y install build-essential
RUN apt-get -y install g++
RUN apt-get -y install python-dev
RUN apt-get -y install openssl
RUN apt-get -y install libssl-dev
RUN apt-get -y install libyaml-dev libpython2.7-dev
WORKDIR /
RUN wget https://www.python.org/ftp/python/2.7.10/Python-2.7.10.tar.xz
RUN tar xf Python-2.7.10.tar.xz
WORKDIR /Python-2.7.10
RUN ./configure --prefix /usr/local/lib/python2.7.10 && make && make install
RUN wget https://bootstrap.pypa.io/ez_setup.py -O - | /usr/local/lib/python2.7.10/bin/python
RUN /usr/local/lib/python2.7.10/bin/easy_install pip
RUN /usr/local/lib/python2.7.10/bin/pip install virtualenv
RUN /usr/local/lib/python2.7.10/bin/virtualenv -p /usr/local/lib/python2.7.10/bin/python /venv

RUN git clone -b new https://github.com/Villaz/vcycle.git /usr/vcycle

ADD start.sh /
VOLUME /etc/vcycle/
VOLUME /var/log/vcycle
VOLUME /proxies
RUN chmod u+x /start.sh
CMD ["/bin/bash","/start.sh"]
