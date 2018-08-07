import os
import uuid
import pysftp

import pyimgur


class NoNSFWException(Exception):
    pass


class imgUpload(object):

    def __init__(self, user_agent, debug, dryrun):
        import secret

        self.dryrun = dryrun
        self.debug = debug
        
        self.imgur = pyimgur.Imgur(secret.imgur_client_id)

        #cnopts = pysftp.CnOpts()
        #cnopts.hostkeys = None  # disable host key checking.
        #self.ixny = {
        #    'host':secret.ixni_host,
        #    'user':secret.ixni_user,
        #    'pass':secret.ixni_pass,
        #    'cnopts':cnopts}

    def __call__(self, file_name, over_18):
        return self.upload_file(file_name, over_18)
    
    def upload_file_imgur(self, file_name, over_18):
        return self.imgur.upload_image(file_name, title="Colorized File")

    def upload_file(self, locale_file_name, over_18):
        # need unique filename for openload
        oldext = os.path.splitext(locale_file_name)[1]
        newName = str(uuid.uuid4()) + oldext
        os.rename(locale_file_name, newName)

        if self.dryrun:
            return "null"

        try:
            return self.upload_file_imgur(newName, over_18)
        except Exception as e:
            print "imgur-error: ", e.__class__, e.__doc__, e.message


        raise RuntimeError("could not upload file")

