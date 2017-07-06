import tornado.escape


class FlashMessagesMixin(object):
    @property
    def messages(self):
        if not hasattr(self, '_messages'):
            messages = self.get_secure_cookie('flash_messages')
            self._messages = []
            if messages:
                self._messages = tornado.escape.json_decode(messages)
        return self._messages

    def flash(self, message, type='error'):
        self.messages.append((type, message))
        self.set_secure_cookie('flash_messages', tornado.escape.json_encode(self.messages))

    def get_flashed_messages(self):
        messages = self.messages
        self._messages = []
        self.clear_cookie('flash_messages')
        return messages
