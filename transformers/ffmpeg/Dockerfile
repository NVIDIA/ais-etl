FROM python:3.11-alpine

RUN apk update && apk add --no-cache wget tar xz

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

RUN mkdir /code
WORKDIR /code
COPY server.py server.py

RUN wget -nv http://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xf ffmpeg-release-amd64-static.tar.xz \
    && FFMPEG_DIR=$(ls | grep ffmpeg-*-static) \
    && cp ${FFMPEG_DIR}/ffmpeg /usr/local/bin/ \
    && cp ${FFMPEG_DIR}/ffprobe /usr/local/bin/ \
    && rm -rf ffmpeg-*-static ffmpeg-release-amd64-static.tar.xz

RUN ffmpeg -version

ENV PYTHONUNBUFFERED 1

EXPOSE 80
