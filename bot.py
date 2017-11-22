import os
import praw
from praw.exceptions import APIException
import traceback
import shutil
import re
import hashlib
import redis
import prawcore
import time



# ####################### #
# ## local imports ###### #
# ####################### #

import secret
from scrapeVid import search_and_download_video
from stabVid import stab_file
import vidUpload


# ####################### #
# ## functions ########## #
# ####################### #

def post_reply(reply_md, mention):
    print "post_reply... "
    if dryrun:
        print "reply would be:" + reply_md
        return

    try:
        mention.reply(reply_md)
    except APIException as e:
        if e.error_type == 'RATELIMIT':
            print "I was posting too fast. Error-Message: " + e.message
            wait_time_m = int(re.search(r'\d+', e.message).group()) + 1
            if wait_time_m > 10:
                wait_time_m = 10
            print "going to sleep for " + str(wait_time_m) + " minutes."
            time.sleep(wait_time_m * 60)
            mention.reply(reply_md)

        else:
            raise e



def generate_reply(uploaded_url, proc_time, upload_time, over_18, cache_hit):
    nsfw_note = "# --- NSFW --- \n\n " if over_18 else ""

    result_note = "\nI have stabilized the video for you: " \
                  + uploaded_url.replace("https://openload.co","https\://openload.co") \
                  + "\n"

    if cache_hit:
        time_note = ""
    else:
        time_note = "\nIt took " + "%.f" % proc_time + " seconds to process "\
                        "and " +  "%.f" % upload_time + " seconds to upload.\n"

    foot_note = "^^[&nbsp;how&nbsp;to&nbsp;use]"\
                "(https://www.reddit.com/r/stabbot/comments/72irce/how_to_use_stabbot/)"\
                "&nbsp;|&nbsp;[programmer](https://www.reddit.com/message/compose/?to=wotanii)"\
                "&nbsp;|&nbsp;[source&nbsp;code](https://gitlab.com/wotanii/stabbot)"\
                "&nbsp;|&nbsp;/r/ImageStabilization/"\
                "&nbsp;|&nbsp;for&nbsp;cropped&nbsp;results,&nbsp;use&nbsp;\/u/stabbot_crop"\

    return nsfw_note\
        + result_note\
        + time_note\
        + "___\n"\
        + foot_note


def clear_env():
    if os.path.exists(woring_path):
        shutil.rmtree(woring_path)
    os.makedirs(woring_path)
    os.chdir(woring_path)


def get_next_job():
    for mention in reddit.inbox.mentions(limit=50):
        if not mention.new and not include_old_mentions:
            continue
        if not dryrun:
            mention.mark_read()
        else:
            print("dryrun: " + str(dryrun))

        return mention

def check_cache(input_path):
    input_md5 = hashlib.md5(open(input_path, 'rb').read()).hexdigest()
    return r.get("md5-" + input_md5)


def set_cache(uploaded_url, input_path):
    input_md5 = hashlib.md5(open(input_path, 'rb').read()).hexdigest()
    r.set("md5-" + input_md5, uploaded_url)


def send_message(redditor, text):
    print("sending PM to " + redditor.name)
    if dryrun:
        print("message would be: " + text)
        return

    redditor.message('Video is stabilized', text)
    pass

def assume_over_18(mention):
    if mention.submission.over_18:
        return True

    if mention.subreddit.subscribers < 500:
        return True

    return False


def main():
    print "starting..."
    while True:
        try:
            clear_env()
            mention = get_next_job()
            if mention is None:
                time.sleep(sleep_time_s)
                continue
            print "submission: " + mention.submission.id + " - " + mention.submission.shortlink
            over_18 = assume_over_18(mention)
            start_time = time.time()

            input_path = search_and_download_video(mention.submission, user_agent)
            cached_result = check_cache(input_path)
            if(cached_result is None):
                stab_file(input_path, "stabilized.mp4")
                proc_time = time.time() - start_time
                uploaded_url = vidUploader('stabilized.mp4', over_18)
                set_cache(uploaded_url, input_path)
                upload_time = time.time() - start_time - proc_time
            else:
                uploaded_url = cached_result
                proc_time = 0
                upload_time = 0

            reply_md = generate_reply(uploaded_url, proc_time, upload_time, over_18, cached_result is not None)

            if True:
                post_reply(reply_md, mention)
            else:
                # "temporary" workaround
                send_message(mention.author, reply_md)

        except prawcore.exceptions.Forbidden:
            print("Error: prawcore.exceptions.Forbidden")
            send_message(mention.author, "I could not reply to [your comment]("+str(mention.context)+"), because I have been banned in this community. \n___\n" + reply_md)


        except Exception as e:
            print "Exception:"
            print e.__class__, e.__doc__, e.message
            print e
            traceback.print_exc()


def s2b(s,default):
    if not s: return default
    if s == "True": return True
    if s == "False": return False
    raise ValueError("string must be empty, True or False.")

# ####################### #
# ## global constants ### #
# ####################### #

user_agent = "ubuntu:de.wotanii.stabbot:v0.1 (by /u/wotanii)"

reddit = praw.Reddit('my_bot',
                     client_id=secret.reddit_client_id,
                     client_secret=secret.reddit_client_secret,
                     password=secret.reddit_password,
                     user_agent=user_agent)

print("reddit user: " + reddit.user.me().name)

sleep_time_s = 10

posts_replied_to_path = os.path.abspath("data/posts_replied_to.txt")

r = redis.Redis(
    host='redis',
    port=6379,
    password='')


dryrun = s2b(os.getenv('DRYRUN'), True)
debug = s2b(os.getenv('DEBUG'), False)
include_old_mentions = s2b(os.getenv('INCLUDE_OLD_MENTIONS'), False)


vidUploader = vidUpload.vidUpload(user_agent, debug, dryrun)

print("config:"
      "\n\tdryrun: " + str(dryrun)
      + "\n\tdebug: " + str(debug)
      + "\n\told_mentions: " + str(include_old_mentions))

woring_path = os.path.abspath("data/working")


# ####################### #
# ## excecution ######### #
# ####################### #

main()
