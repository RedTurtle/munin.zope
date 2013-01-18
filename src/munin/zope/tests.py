from unittest import TestSuite
import doctest
from App.config import getConfiguration
from Products.Five import fiveconfigure
from plone.testing import layered
from plone.testing import z2
from plone.app.testing.layers import PloneFixture

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)

class MuninZopeFixture(PloneFixture):
    """ munin.zope text fixture """

    # XXX: The PloneFixture with an empty set of products and an overriden
    # setUpDefaultContent is the closest to an empty Zope2 layer we got
    # but it forces requiring the plone.app.testing layer. If we copy the
    # relevant portions over, we can ditch plone.app.testing and use only
    # plone.testing a a test requirement
    products = ()

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
        fiveconfigure.debug_mode = False

    def setUpDefaultContent(self, app):
        uf = app.acl_users
        uf._doAddUser('member', 's3kr3t', ['Member'], [])
        uf._doAddUser('manager', 's3kr3t', ['Manager'], [])

MUNIN_ZOPE_FIXTURE = MuninZopeFixture()

MUNIN_ZOPE_INTEGRATION_TESTING = z2.IntegrationTesting(bases=(MUNIN_ZOPE_FIXTURE,), name='MuninZope:Integration')

MUNIN_ZOPE_ZSERVER = z2.FunctionalTesting(bases=(MUNIN_ZOPE_FIXTURE, z2.ZSERVER_FIXTURE), name='MuninZope:ZServer')

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
    ])

