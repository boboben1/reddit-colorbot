import os
import uuid
import pysftp

from openload import OpenLoad
from gfycat.client import GfycatClient

from pystreamable import StreamableApi


class NoNSFWException(Exception):
    pass


class vidUpload(object):

    def __init__(self, user_agent, debug, dryrun):
        import secret

        self.dryrun = dryrun
        self.debug = debug
        self.openload = OpenLoad(secret.openload_id, secret.openload_api_key)
        print("openload: " + str(self.openload.account_info()))

        self.gfyclient = GfycatClient()
        self.client_streamable = StreamableApi(secret.streamable_user, secret.streamable_pass)

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # disable host key checking.
        self.ixny = {
            'host':secret.ixni_host,
            'user':secret.ixni_user,
            'pass':secret.ixni_pass,
            'cnopts':cnopts}

    def __call__(self, file_name, over_18):
        return self.upload_file(file_name, over_18)

    def upload_file_gfycat(self, locale_file_name):
        raise NotImplementedError("gfycat")

    def upload_file_openload(self, locale_file_name):
        upload_resp = self.openload.upload_file(locale_file_name)
        return "https://openload.co/embed/" + upload_resp[u'id']

    def upload_file_streamable(self, locale_file_name, over_18):
        if over_18:
            raise NoNSFWException()

        result = self.client_streamable.upload_video(locale_file_name, 'stable video')
        return 'https://streamable.com/' + result['shortcode']

    def upload_file_insxnity(self, locale_file_name):

        srv = pysftp.Connection(
            host=self.ixny['host'],
            username=self.ixny['user'],
            password=self.ixny['pass'],
            cnopts=self.ixny['cnopts']
        )

        with srv.cd('/var/www/html/stabhost'): #chdir to public
            srv.put(locale_file_name) #upload file to nodejs/

        srv.close()
        return "http://stabbot.insxnity.net/stabhost/" + os.path.basename(locale_file_name)
        
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
            return self.upload_file_insxnity(newName)
        except Exception as e:
            print "insxnity-error: ", e.__class__, e.__doc__, e.message

        try:
            return self.upload_file_openload(newName)
        except Exception as e:
            print "openload-error: ", e.__class__, e.__doc__, e.message

        raise RuntimeError("could not upload file")

