
# stabbot

a reddit bot, that stabilizes videos

**Ranking**: https://goodbot-badbot.herokuapp.com/all_filter

**Introduction**: https://www.reddit.com/r/botwatch/comments/6p1ilf/introducing_stabbot_a_bot_that_stabilizes_videos/

# User information

## how does it work?

### summoning

Mention /u/stabbot in a top-level comment to a submission.

The submission must be either:
  * a direct link to a video file
  * a html5 video
  * a link to youtube, gfycat, imgur or reddit

The video must be less than 60s

### Stabilization

**first pass**:
First it looks for edges and corners in a frame (= "image in a video").
Then it tries to find the same corners in the next frame. Then it tries
to rotate and translate the 2nd frame, so the so corresponding corners overlap with the
first frame. This transformation is saved in a separate file.
The process is repeated for all consecutive frames.

The result of the first pass is a file containing frame-to-frame transformations.

**second pass**:
Just applying the transformations would result in the video moving out of view eventually,
so the stabilized camera needs to follow the original camera. If it follows
too fast, the result will be too shaky. If it follows to slow the result will
be out of view for too long.

So the bot averages the transformation of the last 20 frames and the next 20 frames.
And this averaged transformation is then applied to frame, resulting in nice
and smooth camera movements.

### why it sometimes fails

**the black edges keep jumping around**: The could be solved by cropping the result,
but cropping too much would remove too much of the video in some cases, so
I decided against it. A positive side effect: by seeing how much the
result jumps around, you get a better feeling of how shaky the original really
was.A prime example of
this can be found [here](https://www.reddit.com/r/nonononoyes/comments/6vb4vb/motorcycle_takes_a_rocky_ride/dlyydcl/).

**It's way shakier then before**: The points where the frame is stabilized on, are
choosen almost randomly. So sometimes it chooses points, that are not
part of the background, but part of the foreground. And then it switches between
stabilizing on the foreground and stabilizing on the background, resulting in
a shakier result than the original video. The happens especially if moving objekts
are a big part of the video, and if they are very well structured. A prime example of
this can be found [here](https://www.reddit.com/r/Simulated/comments/6va1j9/voxelized_explosion/dlz5zmi/).


If you are interested in ImageStabilization visit [/r/ImageStabilization](https://www.reddit.com/r/ImageStabilization/)

**it didn' reply to my summon**: There was an internal error. (e.g. video
couldn't be found, the comment was no top-level comment,
result couldn't be uploaded).


# Dev-information

## relevant links

[guide to reddit bots](http://pythonforengineers.com/build-a-reddit-bot-part-1/)

[documention of vid.stab](https://github.com/georgmartius/vid.stab)

## deployment

    git pull git@gitlab.com:wotanii/stabbot.git
    cd stabbot
    nano secret.py
    docker-compose up --build -d
    docker-compose logs -f -t

secret.py must contain:

* imgur_id
* reddit_client_id
* reddit_client_secret
* reddit_password


## update

    cd stabbot
    git pull
    docker-compose down
    docker-compose up --build -d
    docker-compose logs -f -t

Then summon it somewhere to make sure nothing broke.
E.g. on [/r/testingground4bots](https://www.reddit.com/r/testingground4bots/)
