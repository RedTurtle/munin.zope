from unittest import TestSuite
from zope.testing import doctest
from AccessControl.SecurityManagement import newSecurityManager
from App.config import getConfiguration
from Testing.ZopeTestCase import installPackage, utils, layer
from Testing.ZopeTestCase import FunctionalTestCase, FunctionalDocFileSuite
from Products.Five import zcml, fiveconfigure
from Products.Five.testbrowser import Browser

optionflags = (doctest.REPORT_ONLY_FIRST_FAILURE |
               doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)


class TestLayer(layer.ZopeLiteLayer):
    """ layer for integration tests """

    @classmethod
    def setUp(cls):
        cfg = getConfiguration()
        cfg.product_config = {'munin.zope': {'secret': 'muninsecret'}}
        # load zcml & install package
        fiveconfigure.debug_mode = True
        import munin.zope
        zcml.load_site()
        zcml.load_config('configure.zcml', munin.zope)
        fiveconfigure.debug_mode = False
        # installPackage('munin.zope', quiet=True)

    @classmethod
    def tearDown(cls):
        pass


class TestCase(FunctionalTestCase):
    """ base class for functional tests;  please note that this test case
        creates another user on the application root, which is why it needs
        a special version of `setRoles` """

    layer = TestLayer

    def afterSetUp(self):
        uf = self.app.acl_users
        uf._doAddUser('manager', 's3kr3t', ['Member'], [])
        user = uf.getUserById('manager').__of__(uf)
        newSecurityManager(None, user)

    def setRoles(self, roles):
        uf = self.app.acl_users
        uf.userFolderEditUser('manager', None, utils.makelist(roles), [])

    def getBrowser(self, loggedIn=True):
        """ instantiate and return a testbrowser for convenience """
        browser = Browser()
        if loggedIn:
            browser.addHeader('Authorization',
                'Basic %s:%s' % ('manager', 's3kr3t'))
        return browser


def test_suite():
    return TestSuite([
        FunctionalDocFileSuite(
           'browser.txt', package='munin.zope',
           test_class=TestCase, optionflags=optionflags),
    ])
