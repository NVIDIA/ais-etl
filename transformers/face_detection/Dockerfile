# Prior to building this image make you own kaggle_creds.json file
# containing kaggle keys to download dataset
FROM python:3.8-slim

WORKDIR /

# install packages needed for open-cv to work
RUN apt-get update && apt-get -y install gcc ffmpeg libsm6 libxext6 unzip curl

# install python dependencies
COPY ./requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt

# Make .kaggle directory and copy creds
RUN mkdir ~/.kaggle
COPY kaggle_creds.json /root/.kaggle/kaggle.json

# Give read and write permissions to kaggle.json
RUN chmod 600 /root/.kaggle/kaggle.json

# Create a directory to store the model
RUN mkdir model

# Download the dataset
RUN kaggle datasets download -d sambitmukherjee/caffe-face-detector-opencv-pretrained-model && \
    unzip caffe-face-detector-opencv-pretrained-model.zip -d model/ && \
    rm caffe-face-detector-opencv-pretrained-model.zip && \
    rm /root/.kaggle/kaggle.json

COPY main.py main.py

ENV PYTHONUNBUFFERED 1

ENV LOG_LEVEL DEBUG

EXPOSE 8000
