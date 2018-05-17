FROM golang
MAINTAINER container
RUN mkdir /app
ADD container.py /app
ADD hello_world /app
Add id_rsa /app
WORKDIR /app
EXPOSE 8080
CMD ["/app/hello_world", "python /app/container.py"]
