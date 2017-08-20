from gfycat.client import GfycatClient
import os
import praw
from praw.exceptions import APIException
import traceback
import shutil
import time
import re
import hashlib


# ####################### #
# ## local imports ###### #
# ####################### #

import secret
from scrapeVid import search_and_download_video
from stabVid import stab_file


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


def upload_file(locale_file_name):
    print "uploading..."
    if dryrun:
        return "https://gfycat.com/FamiliarSimplisticAegeancat"

    for uplodad_it in range(0, 3):
        uploaded_file_info = gfyclient.upload_from_file(locale_file_name)
        local_md5 = hashlib.md5(open(locale_file_name, 'rb').read()).hexdigest()
        gfyclient.query_gfy(uploaded_file_info['gfyName'])
        for query_it in range(0,3):
            queried_file_info = gfyclient.query_gfy(uploaded_file_info['gfyName'])['gfyItem']
            if 'md5' not in queried_file_info:
                print("md5 is not yet ready. So pause and try again")
                time.sleep(5)
                continue

            if local_md5 != queried_file_info['md5']:
                print "hash mismatch. local_md5: " + local_md5 + "  remote_md5: " + queried_file_info['md5']
                print "uploading again..."
                break

            file_path =  queried_file_info['mp4Url']
            with open(gfylinks_path, "a") as f:
                f.write(file_path + "\n")

            return file_path
    raise RuntimeError("could not upload file")


def generate_reply(uploaded_url, conversion_time):
    return ""\
             "I have stabilized the video for you: " + uploaded_url + "\n\n" \
             "It took me " +  str(round(conversion_time))+ " seconds to process." \
             "\n\n ___ \n\n ^^If ^^you ^^want ^^to ^^know ^^how ^^to ^^summon ^^me: " \
             "[^^click ^^here](https://www.reddit.com/r/botwatch/comments/6p1ilf/introducing_stabbot_a_bot_that_stabilizes_videos/)^^. "


def clear_env():
    if os.path.exists(woring_path):
        shutil.rmtree(woring_path)
    os.makedirs(woring_path)
    os.chdir(woring_path)


def mark_submission(id,posts_replied_to):
    print "marking submission " + id + " ... "
    posts_replied_to.append(id)
    with open(posts_replied_to_path, "a") as f:
        f.write(id + "\n")


def get_replied_to_list():
    if os.path.isfile(posts_replied_to_path):
        with open(posts_replied_to_path, "r") as f:
            file_content = f.read()
            file_content = file_content.split("\n")
            return list(filter(None, file_content))

    return []


def get_next_job(posts_replied_to):
    #allMentions = list(reddit.inbox.mentions(limit=50))
    #sorted_mentions= sorted(allMentions, key=lambda m: (m.score, m.submission.score))
    for mention in reddit.inbox.mentions(limit=50):
        if not mention.new and not include_old_mentions:
            continue
        mention.mark_read()
        if not mention.is_root:
            print "comment is not root: ", mention
            continue
        if mention.submission.id in posts_replied_to:
            print "submission was alread replied to: " + mention.submission.id
            continue

        return mention


def main():
    print "starting..."
    posts_replied_to = get_replied_to_list()
    print "old replies found: " + str(len(posts_replied_to))
    while True:
        try:
            clear_env()
            mention = get_next_job(posts_replied_to)
            if mention is None:
                if debug:
                    print "No Mention found. Going back to sleep ..."
                time.sleep(sleep_time_s)
                continue
            mark_submission(mention.submission.id, posts_replied_to)
            if debug:
                print "submission: " + mention._submission.shortlink
            start_time = time.time()

            input_path = search_and_download_video(mention.submission)
            stab_file(input_path, "stabilized.mp4")
            uploaded_url = upload_file('stabilized.mp4')
            reply_md = generate_reply(uploaded_url, time.time() - start_time)

        except Exception as e:
            print "Exception:"
            print e.__class__, e.__doc__, e.message
            print e
            traceback.print_exc()

        else:
            try:
                if reply_md:
                    post_reply(reply_md, mention)
            except Exception as e:
                print "Exception during post_reply:"
                print e.__class__, e.__doc__, e.message
                print e
                traceback.print_exc()

        print 'sleeping for ' + str(sleep_time_s) + ' seconds ...'
        time.sleep(sleep_time_s)


# ####################### #
# ## global constants ### #
# ####################### #

reddit = praw.Reddit('my_bot',
    client_id = secret.reddit_client_id,
    client_secret = secret.reddit_client_secret,
    password = secret.reddit_password)
gfyclient = GfycatClient()

posts_replied_to_path = os.path.abspath("data/posts_replied_to.txt")
gfylinks_path = os.path.abspath("data/gfylinks.txt")

dryrun = False
debug = False
include_old_mentions = False
woring_path = os.path.abspath("data/working")

sleep_time_s = 10

# ####################### #
# ## excecution ######### #
# ####################### #

main()
