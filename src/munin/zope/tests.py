from unittest import TestSuite
import doctest
from App.config import getConfiguration
from Products.Five import fiveconfigure
from plone.testing import layered
from plone.testing import z2
from plone.app.testing.layers import PloneFixture
from threading import Lock, Event
from Products.Five.browser import BrowserView

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)

class MuninStartup(z2.Startup):
    """Our own start-up layer that creates a ZServer with 2 threads"""

    threads = 2

MUNIN_STARTUP = MuninStartup()

class MuninZopeFixture(PloneFixture):
    """ munin.zope text fixture """

    defaultBases = (MUNIN_STARTUP,)

    # XXX: The PloneFixture with an empty set of products and an overriden
    # setUpDefaultContent is the closest to an empty Zope2 layer we got
    # but it forces requiring the plone.app.testing layer. If we copy the
    # relevant portions over, we can ditch plone.app.testing and use only
    # plone.testing a a test requirement
    products = (
        ('Products.ZServerThreads', {'loadZCML': True},),
        ('munin.zope', {'loadZCML': True},),
    )

    def setUpZCML(self):
        super(MuninZopeFixture, self).setUpZCML()
        from zope.configuration import xmlconfig
        import munin.zope
        cfg = getConfiguration()
        cfg.product_config = {'munin.zope': {'secret': 'muninsecret'}}
        # load zcml & install package
        context = self['configurationContext']
        fiveconfigure.debug_mode = True
        xmlconfig.file('configure.zcml', munin.zope, context=context)
        # load our holder_view for the 'threads.txt' test
        xmlconfig.file('tests.zcml', munin.zope, context=context)
        fiveconfigure.debug_mode = False

    def setUpDefaultContent(self, app):
        uf = app.acl_users
        uf._doAddUser('member', 's3kr3t', ['Member'], [])
        uf._doAddUser('manager', 's3kr3t', ['Manager'], [])

MUNIN_ZOPE_FIXTURE = MuninZopeFixture()

class ZServer(z2.ZServer):

    defaultBases = (MUNIN_ZOPE_FIXTURE,)

    def setUpServer(self):
        super(ZServer, self).setUpServer()
        zope_conf = getConfiguration()
        # Put the ZServer we launched into the configured servers list
        zope_conf.servers = [self.zserver]
        # The STARTUP fixture has already been run, and Products.ZServerViews
        # didn't find a ZServer to initialize, so rerun its initialization now:
        import Products.ZServerViews
        Products.ZServerViews.initialize(None)

    def tearDownServer(self):
        getConfiguration().servers.remove(self.zserver)
        super(ZServer, self).tearDownServer()

ZSERVER_FIXTURE = ZServer()

MUNIN_ZOPE_INTEGRATION_TESTING = z2.IntegrationTesting(bases=(MUNIN_ZOPE_FIXTURE,), name='MuninZope:Integration')

MUNIN_ZOPE_ZSERVER = z2.FunctionalTesting(bases=(ZSERVER_FIXTURE,), name='MuninZope:ZServer')

class HolderView(BrowserView):

    _lock = Lock()
    green_light = Event()
    # view is non-blocked at first
    green_light.set()

    def __call__(self):
        with self._lock:
            self.green_light.wait()
            return 'OK'

    @classmethod
    def tearDown(cls, doctest):
        cls.green_light.set()

def muninSetUp(doctest):

    app = doctest.globs['layer']['app']
    def getBrowser(login='', password=''):
        """ instantiate and return a testbrowser for convenience """
        browser = z2.Browser(app)
        if login:
            browser.addHeader('Authorization',
                'Basic %s:%s' % (login, password))
        return browser

    doctest.globs.update(getBrowser=getBrowser)

def MuninZopeDocFileSuite(*args, **kw):
    doctest_layer = kw.pop('layer', MUNIN_ZOPE_INTEGRATION_TESTING)
    default_kw = dict(
        optionflags=optionflags,
        package='munin.zope',
    )
    default_kw.update(kw)
    kw.setdefault('optionflags', optionflags)
    return layered(doctest.DocFileSuite(*args, **kw), layer=doctest_layer)

def test_suite():
    return TestSuite([
        MuninZopeDocFileSuite('browser.txt', setUp=muninSetUp),
        MuninZopeDocFileSuite('threads.txt', layer=MUNIN_ZOPE_ZSERVER,
                              tearDown=HolderView.tearDown),
    ])

