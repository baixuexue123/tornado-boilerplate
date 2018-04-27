import os
import tempfile
import datetime

import tornado.web
from tornado.log import app_log
from utils.text import get_valid_filename


class UploadBase(tornado.web.RequestHandler):

    rel_dirname = 'files'

    def get_dir(self):
        root_dir = self.settings['media']['root']
        date = datetime.date.today()
        dir_ = os.path.join(root_dir, self.rel_dirname, str(date.year), str(date.month))
        os.makedirs(dir_, exist_ok=True)
        return dir_

    def generate_filename(self, filename):
        fn, ext = os.path.splitext(get_valid_filename(filename))
        filepath = tempfile.mktemp(suffix=ext, prefix=fn, dir=self.get_dir())
        return os.path.normpath(filepath)


class UploadFileHandler(UploadBase):

    @staticmethod
    def human_size(_bytes, traditional=((1024 ** 5, ' P'),
                                        (1024 ** 4, ' T'),
                                        (1024 ** 3, ' G'),
                                        (1024 ** 2, ' M'),
                                        (1024 ** 1, ' K'),
                                        (1024 ** 0, ' B'))):

        for factor, suffix in traditional:
            if _bytes >= factor:
                amount = round(_bytes/factor, 2)
                return str(amount) + suffix
        else:
            return str(_bytes)

    def post(self):
        for field_name, files in self.request.files.items():
            for info in files:
                filename, content_type = info['filename'], info['content_type']
                path = self.generate_filename(filename)
                size = self.human_size(len(info['body']))
                with open(path, 'wb') as f:
                    f.write(info['body'])

                app_log.info('POST "%s" "%s"', filename, content_type)

        self.redirect("/")
