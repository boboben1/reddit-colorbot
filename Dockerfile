FROM ubuntu:artful

ENV cache_breaker "2018-01-17"

###########################
### from ubuntu ###########
###########################

### general
# Not sure if all of these are needed...
#RUN apt-get update && apt-get install -y git tar curl nano wget dialog net-tools build-essential
RUN apt-get update && apt-get install -y git tar wget build-essential

### building ffmpeg itself

RUN apt-get update && apt-get -y install autoconf automake build-essential libass-dev libfreetype6-dev libsdl2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev pkg-config texinfo wget zlib1g-dev


### building ffmpeg-libs

RUN apt-get update && apt-get -y install yasm libx264-dev libx265-dev libfdk-aac-dev libmp3lame-dev libopus-dev libvpx-dev cmake mercurial cmake-curses-gui


### python

RUN apt-get update && apt-get install -y \
	python-pip \
	python-configparser \
	libffi-dev \
	libssl-dev \
    python-dev

WORKDIR /bot
COPY requirements.txt /bot
RUN pip install -r requirements.txt

COPY praw.ini /bot
COPY bot.py /bot
COPY secret.py /bot
COPY scrapeImg.py /bot
COPY colorize.py /bot
COPY imgUpload.py /bot
COPY helper.py /bot
COPY superres.py /bot

ENV PYTHONUNBUFFERED 0
CMD ["python", "bot.py"]
