FROM python:3
MAINTAINER container
RUN mkdir /app
RUN pip install --no-cache-dir pycrypto
RUN pip install --no-cache-dir python-etcd
RUN pip install --no-cache-dir sleekxmpp
ADD container.py /app
ADD etcdf.py /app
ADD crypt.py /app
ADD hello_world /app
Add id_rsa /app
WORKDIR /app
EXPOSE 8080
CMD ["/app/hello_world"]
#CMD ["python", "./container.py"]
