import random
import time
from tornado import gen
from tornado.ioloop import IOLoop


@gen.coroutine
def gen_url(url):
    wait_time = random.randint(4, 5)
    yield gen.sleep(wait_time)
    print('URL {} took {}s to get!'.format(url, wait_time))
    return url, wait_time


@gen.coroutine
def fetch_url():
    before = time.time()
    urls = [gen_url(url) for url in ['URL1', 'URL2', 'URL3']]
    result = yield urls
    after = time.time()
    print(result)
    print('total time: {} seconds'.format(after - before))


if __name__ == '__main__':
    print('output:')
    IOLoop.current().run_sync(fetch_url)
