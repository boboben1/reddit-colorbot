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

from imgUpload import imgUpload
from scrapeImg import search_and_download_image
from colorize import Colorizer
from helper import s2b


# ####################### #
# ## functions ########## #
# ####################### #

def post_reply(reply_md, mention):
    print "post_reply... "
    if dryrun:
        print "reply would be:" + reply_md
        return

    for i in range(0, 5):
        try:
            mention.reply(reply_md)
            return

        except prawcore.exceptions.RequestException:
            print "RequestException... trying again"

        except APIException as e:
            if e.error_type == 'RATELIMIT':
                print "I was posting too fast. Error-Message: " + e.message
                wait_time_m = int(re.search(r'\d+', e.message).group()) + 1
                if wait_time_m > 10:
                    wait_time_m = 10
                print "going to sleep for " + str(wait_time_m) + " minutes."
                time.sleep(wait_time_m * 60)
            else:
                raise e
    print "post_reply... failed"


def generate_reply(uploaded_url, proc_time, upload_time, over_18, cache_hit):
    nsfw_note = "# --- NSFW --- \n\n " if over_18 else ""

    result_note = "\nI have colorized the image for you: " \
                    + uploaded_url + "\n"

    if cache_hit:
        time_note = ""
    else:
        time_note = "\nIt took " + "%.f" % proc_time + " seconds to process " \
                    + "and " + "%.f" % upload_time + " seconds to upload.\n"

    foot_note = "^^(This project is currently in development.)" #\
                #"Colorbot costs money to operate." \ 
                #"Please consider donating to support this project."


    return nsfw_note \
           + result_note \
           + time_note \
           + "___\n" \
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


def get_message_submission(over_18):
    subr = reddit.subreddit('coloringbot')

    submission_name = message_submission_name
    if over_18:
        submission_name = submission_name + " - NSFW"
    candidates = subr.search(submission_name, sort="new", time_filter="week")

    for c in candidates:
        if c.over_18 != over_18:
            pass
        if c.author.name == me:
            return c

    s = subr.submit(submission_name, send_replies=False, selftext="""
    This thread is used by coloringbot&co to reply to summons 
    """)
    s.mod.distinguish()
    if over_18:
        s.mod.nsfw()

    return s


def send_message(mention, text):
    text = "pinging /u/" + mention.author.name + "\n\n" + text
    if dryrun:
        print("message would be: " + text)
        return

    s = get_message_submission(assume_over_18(mention))
    print("replying...")
    s.reply(text)


def assume_over_18(mention):
    if mention.submission.over_18:
        return True

    if mention.subreddit_name_prefixed == 'r/coloringbot':
        return False

    if mention.subreddit.subscribers < 500:
        return True

    return False


def main():
    print "starting..."
    while True:
        reply_md = ""
        try:
            clear_env()
            mention = get_next_job()
            if mention is None:
                time.sleep(sleep_time_s)
                continue
            print "submission: " + mention.submission.id + " - " + mention.submission.shortlink
            over_18 = assume_over_18(mention)
            start_time = time.time()

            input_path = search_and_download_image(mention.submission, user_agent)
            cached_result = check_cache(input_path)
            if cached_result is None:
                colorizer(input_path, "colorized.png")
                proc_time = time.time() - start_time
                uploaded_url = imgUploader('colorized.png', over_18)
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
                send_message(mention, reply_md)

        except prawcore.exceptions.Forbidden:
            print("Error: prawcore.exceptions.Forbidden")
            send_message(mention, "I could not reply to [your comment](" + str(
                mention.context) + "), because I have been banned in this community. \n___\n" + reply_md)

        except Exception as e:
            print "Exception:"
            print e.__class__, e.__doc__, e.message
            print e
            traceback.print_exc()

            send_message(mention, "Something broke inside. [your request](" + str(mention.context)
                         + ").")


# ####################### #
# ## global constants ### #
# ####################### #

user_agent = "ubuntu:com.bluudlust.colorbot:v0.1 (by /u/BluudLust)"
sleep_time_s = 10
dryrun = s2b(os.getenv('DRYRUN'), True)
debug = s2b(os.getenv('DEBUG'), False)
include_old_mentions = s2b(os.getenv('INCLUDE_OLD_MENTIONS'), False)
woring_path = os.path.abspath("data/working")

imgUploader = imgUpload(user_agent, debug, dryrun)

reddit = praw.Reddit('my_bot',
                     client_id=secret.reddit_client_id,
                     client_secret=secret.reddit_client_secret,
                     password=secret.reddit_password,
                     user_agent=user_agent)
print("reddit user: " + reddit.user.me().name)

me = reddit.user.me().name
message_submission_name = "replies_from_" + me

r = redis.Redis(
    host='redis',
    port=6379,
    password='')

colorizer = Colorizer()

print("config:"
      "\n\tdryrun: " + str(dryrun)
      + "\n\tdebug: " + str(debug)
      + "\n\told_mentions: " + str(include_old_mentions))

# ####################### #
# ## excecution ######### #
# ####################### #

main()
