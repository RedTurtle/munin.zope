import sys

from Products.Five.browser import BrowserView
from ZServer.PubCore.ZRendezvous import ZRendevous
from App.config import getConfiguration
from AccessControl import getSecurityManager
from zExceptions import Unauthorized
from logging import getLogger
from munin.zope.memory import vmstats
from time import time
if sys.version_info < (2, 5):
    import threadframe
    thread = threadframe.dict
else:
    thread = sys._current_frames

PERMISSION = "View managment screens"
log = getLogger('munin.zope').info


def getSecret():
    product_config = getattr(getConfiguration(), 'product_config', None)
    config = product_config and product_config.get('munin.zope')
    return config and config.get('secret')

secret = getSecret()


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


def perm(fn):
    def decorator(*args, **kw):
        if secret and args[0].request.get('QUERY_STRING') == secret:
            pass
        elif getSecurityManager().checkPermission(PERMISSION, args[0].context):
            pass
        else:
            msg = "Insufficient priviledge to perform this action. It requires the permission: " + PERMISSION
            raise Unauthorized(msg, needed={'permission': PERMISSION})
        # zope2.ViewManagementScreens
        value = fn(*args, **kw)
        return value
    decorator.__doc__ = fn.__doc__
    decorator.__name__ = fn.__name__
    return decorator


class Munin(BrowserView):

    @perm
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

    @perm
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

    @perm
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

    @perm
    @timer
    def zopememory(self):
        """ zope memory usage statistics """
        result = ['%s:%s' % item for item in vmstats()]
        return '\n'.join(result)
