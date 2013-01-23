import sys

from Products.Five.browser import BrowserView
import ZServer.PubCore
from App.config import getConfiguration
from AccessControl import getSecurityManager
from zExceptions import Unauthorized, NotFound
from logging import getLogger
from munin.zope.memory import vmstats
from time import time
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
from Products.ZServerViews.base import ViewError, TextView
if sys.version_info < (2, 5):
    import threadframe
    thread = threadframe.dict
else:
    thread = sys._current_frames

PERMISSION = "View management screens"
log = getLogger('munin.zope')
info = log.info


def getSecret():
    product_config = getattr(getConfiguration(), 'product_config', None)
    config = product_config and product_config.get('munin.zope')
    return config and config.get('secret')

secret = _MARKER = object()

def timer(fn):
    def decorator(*args, **kw):
        start = time()
        value = fn(*args, **kw)
        elapsed = time() - start
        if elapsed > 0.1:   # only log when execution took more than 100ms
            info('calling %s took %.3fs', fn.__name__, elapsed)
        return value
    decorator.__doc__ = fn.__doc__
    decorator.__name__ = fn.__name__
    return decorator


def checkSecret(environment):
    global secret
    if secret is _MARKER:
        secret = getSecret()
    query = environment.get('QUERY_STRING', '')
    check_secret = secret and (
        query == secret or
        environment.get('secret') == secret or
        parse_qs(query).get('secret') == [secret]
    )
    return check_secret

def perm(fn):
    def decorator(*args, **kw):
        if checkSecret(args[0].request):
            pass
        elif getSecurityManager().checkPermission(PERMISSION, args[0].context):
            pass
        else:
            msg = "Insufficient privilege to perform this action. It requires the permission: " + PERMISSION
            raise Unauthorized(msg, needed={'permission': PERMISSION})
        # zope2.ViewManagementScreens
        value = fn(*args, **kw)
        return value
    decorator.__doc__ = fn.__doc__
    decorator.__name__ = fn.__name__
    return decorator


@TextView
@timer
def zopethreads(environment):
    """ zope thread statistics """
    if not checkSecret(environment):
        # XXX: Move check into a decorator?
        raise ViewError('404 Not Found')
    result = []
    frames = thread()
    total_threads = len(frames)
    if ZServer.PubCore._handle is not None:
        handler_lists = ZServer.PubCore._handle.im_self._lists
    else:
        handler_lists = ((), (), ())
    # Check the ZRendevous __init__ for the definitions below
    busy_count, request_queue_count, free_count = [
        len(l) for l in handler_lists
    ]
    result.append(u'total_threads:%.1f' % total_threads)
    result.append(u'free_threads:%.1f' % free_count)
    # NOTE: We could do more with the values above, e.g:
    #result.append('worker_threads:%.1f' % (free_count + busy_count))
    #result.append('request_queue_length:%.1f' % request_queue_count)
    #
    # One cool property is that if request_queue_count > 0, then
    # free_count = 0, so we could usefully plot them in the same graph.
    #
    # Another property is that free_threads will never reach total_threads
    # because there's at least the ZServer thread. But it could be useful
    # to see if total_threads starts to increase. It means there's a
    # thread leak somewhere, e.g. in an add-on library. But perhaps this
    # would be better off in a different graph
    return u'\n'.join(result)

class Munin(BrowserView):

    def _getdbs(self):
        filestorage = self.request.get('filestorage')
        db = self.context.unrestrictedTraverse('/Control_Panel/Database')
        if filestorage == '*':
            db = self.context.unrestrictedTraverse('/Control_Panel/Database')
            for filestorage in db.getDatabaseNames():
                yield (db[filestorage], '_%s' % filestorage)
        elif filestorage:
            if not filestorage in db.getDatabaseNames():
                raise NotFound
            yield (db[filestorage], '')
        else:
            yield (db['main'], '')

    @perm
    @timer
    def zopecache(self):
        """ zodb cache statistics """
        results = []
        for (db, suffix) in self._getdbs():
            results.append(self._zopecache(db, suffix))
        return '\n'.join(results)

    def _zopecache(self, db, suffix):
        result = []
        result.append('total_objs%s:%.1f' % (suffix, db.database_size()))
        result.append('total_objs_memory%s:%.1f' % (suffix, db.cache_length()))
        result.append('target_number%s:%.1f' %
            (suffix, (len(db.cache_detail_length()) * db.cache_size())))
        return '\n'.join(result)

    @perm
    @timer
    def zodbactivity(self):
        """ zodb activity statistics """
        results = []
        for (db, suffix) in self._getdbs():
            results.append(self._zodbactivity(db, suffix))
        return '\n'.join(results)

    def _zodbactivity(self, db, suffix):
        result = []
        now = time()
        start = now - 300   # munin's polls every 5 minutes (*60 seconds)
        end = now
        params = dict(chart_start=start, chart_end=end)
        chart = db.getActivityChartData(200, params)
        result.append('total_load_count%s:%.1f' % (suffix, chart['total_load_count']))
        result.append('total_store_count%s:%.1f' % (suffix, chart['total_store_count']))
        result.append('total_connections%s:%.1f' % (suffix, chart['total_connections']))
        return '\n'.join(result)

    @perm
    @timer
    def zopememory(self):
        """ zope memory usage statistics """
        result = ['%s:%s' % item for item in vmstats()]
        return '\n'.join(result)
