FROM ubuntu:zesty

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


###########################
### ffmpeg ################
###########################

RUN mkdir ~/ffmpeg_sources && mkdir ~/ffmpeg_build && mkdir ~/bin

# path where ffmpeg-binaries are emmited to and read from
ENV PATH="~/bin:${PATH}"

# path where ffmpeg looks for vid.stab
# note: $HOME is not available for docker-commands, only for bash-commands. https://github.com/moby/moby/issues/28971
ENV LD_LIBRARY_PATH /root/ffmpeg_build/lib:$LD_LIBRARY_PATH

# NASM assembler
RUN cd ~/ffmpeg_sources \
  && wget http://www.nasm.us/pub/nasm/releasebuilds/2.13.01/nasm-2.13.01.tar.bz2 \
  && tar xjvf nasm-2.13.01.tar.bz2 \
  && cd nasm-2.13.01 \
  && ./autogen.sh \
  && ./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" \
  && make \
  && make install


# vid.stab
RUN cd ~/ffmpeg_sources \
  && git clone https://github.com/georgmartius/vid.stab.git \
  && cd vid.stab \
  && cmake \
  -DCMAKE_INSTALL_PREFIX:PATH=$HOME/ffmpeg_build . \
  && make \
  && make install


## ffmpeg
RUN cd ~/ffmpeg_sources \
    && wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 \
    && tar xjvf ffmpeg-snapshot.tar.bz2 \
    && cd ffmpeg \
    && PATH="$HOME/bin:$PATH"   PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
      --prefix="$HOME/ffmpeg_build" \
      --pkg-config-flags="--static" \
      --extra-cflags="-I$HOME/ffmpeg_build/include" \
      --extra-ldflags="-L$HOME/ffmpeg_build/lib" \
      --bindir="$HOME/bin" \
      --enable-gpl \
      --enable-libass \
      --enable-libfdk-aac \
      --enable-libfreetype \
      --enable-libmp3lame \
      --enable-libopus \
      --enable-libtheora \
      --enable-libvorbis \
      --enable-libvpx \
      --enable-libx264 \
#     --enable-libx265 \
      --enable-nonfree \
      --enable-libvidstab \
    && PATH="$HOME/bin:$PATH" make \
    && make install \
    && hash -r

# workaround: ffprobe-wrapper doesn't find ffprobe otherwise
RUN cp -r ~/bin/* /bin

###########################
### python ################
###########################


WORKDIR /bot
COPY requirements.txt /bot
RUN pip install -r requirements.txt

COPY praw.ini /bot
COPY bot.py /bot
COPY secret.py /bot
COPY scrapeVid.py /bot
COPY stabVid.py /bot

ENV PYTHONUNBUFFERED 0
CMD ["python", "bot.py"]
