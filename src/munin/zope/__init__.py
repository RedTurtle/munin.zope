#

def initialize(context):
    import Products.ZServerViews
    Products.ZServerViews.update_configuration({
       'zserver-threads':
         '/@@munin.zope.plugins/zopethreads munin.zope.browser.zopethreads'
    })
