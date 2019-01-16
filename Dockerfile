FROM ubuntu:18.04

MAINTAINER Mykola Yakovliev "vegasq@gmail.com"

RUN apt-get update -y && \
    apt-get install -y python3-pip

RUN mkdir /app
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

EXPOSE 5000
VOLUME ["/app/posters"]

ENTRYPOINT [ "/bin/bash" ]

CMD [ "run.sh" ]
