from gfycat.client import GfycatClient
import os
import praw
from praw.exceptions import APIException
import traceback
import shutil
import time
import re
import hashlib
import redis
import prawcore
from openload import OpenLoad
import uuid


# ####################### #
# ## local imports ###### #
# ####################### #

import secret
from scrapeVid import search_and_download_video
from stabVid import stab_file
import stabVid


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


def upload_file_gfycat(locale_file_name):
    print("upload_file...")
    if dryrun:
        return "https://gfycat.com/FamiliarSimplisticAegeancat"

    for uplodad_it in range(0, gfycat_max_retry):
        try:
            file_info = gfyclient.upload_from_file(locale_file_name)
        except Exception as e:
            print "Exception:" + str(e) + str(e.message)
            time.sleep(gfycat_error_retry_sleep_s)
            continue

        local_md5 = hashlib.md5(open(locale_file_name, 'rb').read()).hexdigest()
        for query_it in range(0, 3):
            if 'md5' not in file_info:
                print("md5 is not yet ready. So pause and try again")
                time.sleep(gfycat_md5_retry_sleep_s)
                file_info = gfyclient.query_gfy(file_info['gfyName'])['gfyItem']
                continue

            if local_md5 != file_info['md5']:
                print "hash mismatch. local_md5: " + local_md5 + "  remote_md5: " + file_info['md5']
                print "uploading again..."
                time.sleep(gfycat_md5_retry_sleep_s)
                break

            file_path = "https://gfycat.com/" + file_info['gfyName']
            with open(gfylinks_path, "a") as f:
                f.write(file_path + "\n")

            return file_path
    raise RuntimeError("could not upload file")


def upload_file_openload(locale_file_name):
    upload_resp = openload.upload_file(locale_file_name)
    return upload_resp.get('url')

def upload_file(locale_file_name):
    # need unique filename for openload
    oldext = os.path.splitext(locale_file_name)[1]
    newName = str(uuid.uuid4()) + oldext
    os.rename(locale_file_name, newName)
    try:
        return upload_file_openload(newName)
    except Exception as e:
        print "openload-error: ", e.__class__, e.__doc__, e.message
        return upload_file_gfycat(newName)


def generate_reply(uploaded_url, proc_time, upload_time, over_18, cache_hit):
    nsfw_note = "# --- NSFW --- \n\n " if over_18 else ""

    result_note = "I have stabilized the video for you: " + uploaded_url + " \n"

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
            print("bbb _ dryrun: " + str(dryrun))

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
            start_time = time.time()

            input_path = search_and_download_video(mention.submission, user_agent)
            cached_result = check_cache(input_path)
            if(cached_result is None):
                stab_file(input_path, "stabilized.mp4")
                proc_time = time.time() - start_time
                uploaded_url = upload_file('stabilized.mp4')
                set_cache(uploaded_url, input_path)
                upload_time = time.time() - start_time - proc_time
            else:
                uploaded_url = cached_result
                proc_time = 0
                upload_time = 0

            reply_md = generate_reply(uploaded_url, proc_time, upload_time, mention.submission.over_18, cached_result is not None)

            post_reply(reply_md, mention)
        except prawcore.exceptions.Forbidden:
            print("Error: prawcore.exceptions.Forbidden")
            send_message(mention.author, "I could not reply to [your comment]("+str(mention.permalink())+"), because I have been banned in this community. \n___\n" + reply_md)


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

gfyclient = GfycatClient()

posts_replied_to_path = os.path.abspath("data/posts_replied_to.txt")
gfylinks_path = os.path.abspath("data/gfylinks.txt")

r = redis.Redis(
    host='redis',
    port=6379,
    password='')

openload = OpenLoad(secret.openload_id, secret.openload_api_key)
print("openload: " + str(openload.account_info()))

dryrun = s2b(os.getenv('DRYRUN'), True)
debug = s2b(os.getenv('DEBUG'), False)
include_old_mentions = s2b(os.getenv('INCLUDE_OLD_MENTIONS'), False)

print("config:"
      "\n\tdryrun: " + str(dryrun)
      + "\n\tdebug: " + str(debug)
      + "\n\told_mentions: " + str(include_old_mentions))

woring_path = os.path.abspath("data/working")

sleep_time_s = 10
gfycat_md5_retry_sleep_s = 15
gfycat_error_retry_sleep_s = 300
gfycat_max_retry = 20

# ####################### #
# ## excecution ######### #
# ####################### #

main()
