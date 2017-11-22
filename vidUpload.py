

import sys
import os
import time
import hashlib
import uuid

from openload import OpenLoad
from gfycat.client import GfycatClient

from pystreamable import StreamableApi


class NoNSFWException(Exception):
    pass


class vidUpload(object):

    def __init__(self, user_agent, debug, dryrun):
        import secret

        self.gfycat_md5_retry_sleep_s = 15
        self.gfycat_error_retry_sleep_s = 300
        self.gfycat_max_retry = 20

        self.dryrun = dryrun
        self.debug = debug

        self.openload = OpenLoad(secret.openload_id, secret.openload_api_key)
        print("openload: " + str(self.openload.account_info()))

        self.gfyclient = GfycatClient()

        self.client_streamable = StreamableApi(secret.streamable_user, secret.streamable_pass)

    def __call__(self, file_name, over_18):
        return self.upload_file(file_name, over_18)

    def upload_file_gfycat(self, locale_file_name):
        print("upload_file...")
        if self.dryrun:
            return "https://gfycat.com/FamiliarSimplisticAegeancat"


        for uplodad_it in range(0, self.gfycat_max_retry):
            try:
                file_info = self.gfyclient.upload_from_file(locale_file_name)
            except Exception as e:
                print "Exception:" + str(e) + str(e.message)
                time.sleep(self.gfycat_error_retry_sleep_s)
                continue

            local_md5 = hashlib.md5(open(locale_file_name, 'rb').read()).hexdigest()
            for query_it in range(0, 3):
                if 'md5' not in file_info:
                    print("md5 is not yet ready. So pause and try again")
                    time.sleep(self.gfycat_md5_retry_sleep_s)
                    file_info = self.gfyclient.query_gfy(file_info['gfyName'])['gfyItem']
                    continue

                if local_md5 != file_info['md5']:
                    print "hash mismatch. local_md5: " + local_md5 + "  remote_md5: " + file_info['md5']
                    print "uploading again..."
                    time.sleep(self.gfycat_md5_retry_sleep_s)
                    break

                file_path = "https://gfycat.com/" + file_info['gfyName']

                return file_path
        raise RuntimeError("could not upload file")

    def upload_file_openload(self, locale_file_name):
        upload_resp = self.openload.upload_file(locale_file_name)
        return "https://openload.co/embed/" + upload_resp[u'id']

    def upload_file_streamable(self, locale_file_name, over_18):
        if over_18:
            raise NoNSFWException()

        result = self.client_streamable.upload_video(locale_file_name, 'stable video')
        return 'https://streamable.com/' + result['shortcode']

    def upload_file(self, locale_file_name, over_18):
        # need unique filename for openload
        oldext = os.path.splitext(locale_file_name)[1]
        newName = str(uuid.uuid4()) + oldext
        os.rename(locale_file_name, newName)


        try:
            return self.upload_file_streamable(newName, over_18)
        except Exception as e:
            print "streamable-error: ", e.__class__, e.__doc__, e.message

        try:
            return self.upload_file_gfycat(newName)
        except Exception as e:
            print "gfycat-error: ", e.__class__, e.__doc__, e.message

        try:
            return self.upload_file_openload(newName)
        except Exception as e:
            print "openload-error: ", e.__class__, e.__doc__, e.message

        raise RuntimeError("could not upload file")

