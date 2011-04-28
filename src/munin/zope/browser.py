from Products.Five.browser import BrowserView
from ZServer.PubCore.ZRendezvous import ZRendevous
from logging import getLogger
from munin.zope.memory import vmstats
from time import time
import sys
if sys.version_info < (2, 5):
    import threadframe
    thread = threadframe.dict
else:
    thread = sys._current_frames

log = getLogger('munin.zope').info

def timer(fn):
    def decorator(*args, **kw):
        start = time()
        value = fn(*args, **kw)
        elapsed = time() - start
        if elapsed > 0.1:   # only log when execution took more than 100ms
            log('calling %s took %.3fs', fn.__name__, elapsed)
        return value
    decorator.__doc__ = fn.__doc__
    decorator.__name__ = fn.__name__
    return decorator


class Munin(BrowserView):

    @timer
    def zopecache(self):
        """ zodb cache statistics """
        result = []
        db = self.context.unrestrictedTraverse('/Control_Panel/Database/main')
        result.append('total_objs:%.1f' % db.database_size())
        result.append('total_objs_memory:%.1f' % db.cache_length())
        result.append('target_number:%.1f' %
            (len(db.cache_detail_length()) * db.cache_size()))
        return '\n'.join(result)

    @timer
    def zodbactivity(self):
        """ zodb activity statistics """
        result = []
        now = time()
        start = now - 300   # munin's polls every 5 minutes (*60 seconds)
        end = now
        db = self.context.unrestrictedTraverse('/Control_Panel/Database/main')
        params = dict(chart_start=start, chart_end=end)
        chart = db.getActivityChartData(200, params)
        result.append('total_load_count:%.1f' % chart['total_load_count'])
        result.append('total_store_count:%.1f' % chart['total_store_count'])
        result.append('total_connections:%.1f' % chart['total_connections'])
        return '\n'.join(result)

    @timer
    def zopethreads(self):
        """ zope thread statistics """
        result = []
        frames = thread()
        total_threads = len(frames.values())
        free_threads = 0
        for frame in frames.values():
            _self = frame.f_locals.get('self')
            if hasattr(_self, '__module__') and \
                    _self.__module__ == ZRendevous.__module__:
                free_threads += 1
        result.append('total_threads:%.1f' % total_threads)
        result.append('free_threads:%.1f' % free_threads)
        return '\n'.join(result)

    @timer
    def zopememory(self):
        """ zope memory usage statistics """
        result = ['%s:%s' % item for item in vmstats()]
        return '\n'.join(result)
