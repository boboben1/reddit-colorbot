
# stabot - the video-stabilising rebot

reddit bot, der Bild stabilisiert

# dev


### Entwicklungsablauf:

- [x] install docker
- [x] create container, that compiles ffmpeg has python and stuff stalled
- [ ] create py-module, that checks and stabilizes vid
- [ ] create python script, that does all the rest, except posting to ddit
- [ ] create account for bot
- [ ] get karma for bot
- [ ] test live-version locally
- [ ] upload live-version to vserver

### Programmablauf

1. Scan subs --> todo list of posts+vids
1. choose vid to download and download it
  1. prefer vids, that are new, trending, short and/or from well known subs (e.g. subs with more phone-videos) or vids with phone-aspect-ratio
1. apply ffmpeg ''ffmpeg -i e9k3i5fbp2az.gif -vf deshake=edge='blank' out.gif''
  1. shakiness als zahl:
    1. ffmpeg -i input.mp4 -vf vidstabdetect=shakiness=10:accuracy=15 -f null -
    1. if < 'X' then break
  1. apply vectors to vid
  1. convert to mp4
1. upload to giffy
1. make comment

#### shakiness ermitteln

Wenn mehr als 10% der Frames um mehr els 10% der Bildiagonalen verschoben werden, dann muss das Video stabilisiert werden. 



#### related links
  * https://github.com/georgmartius/vid.stab#usage-instructions
  * https://askubuntu.com/questions/405244/deshaking-videos-using-script/405557#405557
  * https://www.reddit.com/r/botwatch/
  * https://praw.readthedocs.io/en/latest/
  * https://github.com/kkroening/ffmpeg-python
  * https://mhaller.github.io/pyffmpeg/
  * http://ffmpy.readthedocs.io/en/latest/


## dockerfile ausführen


### bauen und testen

docker build -t c . ;and docker run -it -v (pwd)/test-data:/test c bash


## ffmpeg usage

Gut funktioniert:

ffmpeg -i input.mp4 -vf vidstabdetect -f null -

dann:

ffmpeg -i input.mp4 -vf vidstabtransform=smoothing=20:crop=black:zoom="-15":optzoom=0 out_stabilized.mp4

###### Erklärung für crop=black:zoom="-15":

Zoom -15, damit man immer das ganze Bild sieht (--> für den User gehen keine Informationen verloren).

Black, damit man leichter versteht, was stabilisierung gemacht hat. Bei mirror, wird man meiner Meinung nach eher verwirrt, weil man erstmal verstehen muss, was da am Rand passiert. Bei Black ist offensichtlich, was da passiert.

Außerdem: Zoom + Schwarzer zusammen bewirkt, dass man immer sehr gut sehen kann, wie stark die Kamera gerade gewackelt hat. Meiner Meinung nach schwächt das noch weiter die Wackler ab, die am Ende noch im Video geblieben sind.


https://github.com/georgmartius/vid.stab#usage-instructions

### first pass

Use default values:

ffmpeg -i input.mp4 -vf vidstabdetect -f null -

-f null - makes sure that no output is produced as this is just the first pass. This in-turn results in faster speed.

Analyzing strongly shaky video and putting the results in file mytransforms.trf:

ffmpeg -i input.mp4 -vf vidstabdetect=shakiness=10:accuracy=15:result="mytransforms.trf" -f null -

Visualizing the result of internal transformations in the resulting video:

ffmpeg -i input.mp4 -vf vidstabdetect=show=1 dummy_output.mp4

Analyzing a video with medium shakiness:

ffmpeg -i input.mp4 -vf vidstabdetect=shakiness=5:show=1 dummy_output.mp4


### 2nd pass

Using default values:

ffmpeg -i input.mp4 -vf vidstabtransform,unsharp=5:5:0.8:3:3:0.4 out_stabilized.mp4

Note the use of the ffmpeg's unsharp filter which is always recommended.

Zooming-in a bit more and load transform data from a given file:

ffmpeg -i input.mp4 -vf vidstabtransform=zoom=5:input="mytransforms.trf" out_stabilized2.mp4

Smoothening the video even more:

ffmpeg -i input.mp4 -vf vidstabtransform=smoothing=30:input="mytransforms.trf" out_stabilized.mp4
