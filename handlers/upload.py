import os
import tempfile
import datetime

from tornado.log import app_log
from utils.text import get_valid_filename
from base import ExportBase


class UploadBase(ExportBase):

    rel_dirname = ''

    def get_current_user(self):
        try:
            user_id = self.session['userId']
        except KeyError:
            return
        user = self.get_user(id=user_id)
        return user

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


class PictureHandler(UploadBase):

    rel_dirname = 'pictures'

    def insert_db(self, path, job_id):
        rel_path = path.replace(self.settings['media']['root'], '')
        fid = self.db.insert(
            "INSERT INTO picture (`path`, `url`, `job_id`) VALUE (%s, %s, %s)",
            path, rel_path, job_id
        )
        return fid, os.path.join(self.settings['media']['url'], rel_path)

    def post(self):
        job_id = self.get_body_argument('job_id')
        res = []
        for field_name, files in self.request.files.items():
            for info in files:
                filename, content_type = info['filename'], info['content_type']
                path = self.generate_filename(filename)

                with open(path, 'wb') as f:
                    f.write(info['body'])

                fileid, url = self.insert_db(path, job_id)
                res.append({'id': fileid, 'url': url, 'name': filename})

                app_log.info('POST "%s" "%s"', filename, content_type)

        self.write(dict(code=0, message='', data=dict(list=res)))


class ContractFileHandler(UploadBase):

    rel_dirname = 'contracts'

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

    def insert_db(self, cid, filename, path, size, tmpl):
        rel_path = path.replace(self.settings['media']['root'], '')
        fileid = self.db.insert(
            "INSERT INTO contract_file "
            "(`contract_id`, `name`, `path`, `size`, `url`, `user_id`, `is_tmpl`) "
            "VALUE (%s, %s, %s, %s, %s, %s, %s)",
            cid, filename, path, size, rel_path, self.current_user.id, tmpl
        )
        return fileid, os.path.join(self.settings['media']['url'], rel_path)

    def post(self):
        contract_id = self.get_body_argument('contract_id', None)
        tmpl = self.get_body_argument('tmpl', 0)
        res = []
        for field_name, files in self.request.files.items():
            for info in files:
                filename, content_type = info['filename'], info['content_type']
                path = self.generate_filename(filename)
                size = self.human_size(len(info['body']))
                with open(path, 'wb') as f:
                    f.write(info['body'])

                fileid, url = self.insert_db(contract_id, filename, path, size, tmpl)
                res.append({'id': fileid, 'url': url, 'name': filename, 'size': size})

                app_log.info('POST "%s" "%s"', filename, content_type)

        self.write(dict(code=0, message='', data=dict(list=res)))
