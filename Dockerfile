FROM golang:1.8 as build
RUN mkdir /app
ADD hello_world /app

FROM alpine:latest
RUN mkdir /application
COPY --from=build /app /application
WORKDIR /application
#EXPOSE 8080
#CMD ["./hello_world"]
