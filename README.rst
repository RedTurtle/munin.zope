munin.zope
===============

History
-------

This package was originally started as `redturtle.munin`_ by RedTurtle Technology.
From 1.1a1 we have move development to `munin.zope`_ leaving some free place 
for other munin plugins.
  
  
Introduction
------------

This package provides munin plugins for monitoring various aspects of a Zope
instance.

It uses `gocept.munin`_ for plugin registration. Please refer to its
documentation if you want to write new plugins.

Bits of the code is based on plugins found at `munin exchange`_ (many thanks
to Gaute Amundsen and Arthur Lutz).


Plugins
-------

Currently there are 4 plugins available:

* "zopethreads" - reports free Zope threads
* "zopecache" - reports database cache parameters
* "zodbactivity" - reports ZODB activity
* "zopememory" - reports Zope memory usage (only works on Linux)


How to use it
-------------

* First include the package in your buildout `instance` slot::

    [instance]
    ...
    eggs =
        ...
        munin.zope
    zcml =
        ...
        munin.zope

* If you use z3c.autoinclude and plone (default from Plone 3.3.x),
  you need only eggs stuff::

    [instance]
    ...
    eggs =
        ...
        munin.zope

* To create the pluging helper script you'll also need to include the
  following, additional section and extend your `parts` definition::

    [buildout]
    parts =
        ...
        munin

    [munin]
    recipe = zc.recipe.egg
    eggs = munin.zope
    arguments = http_address='${instance:http-address}', user='${instance:user}'

  The `arguments` option is used to pass configuration values to the generated
  helper script, which is then used as the actual munin plugin (see below).
  Any settings for `ip-address`, `http-address`, `port-base` and `user` given
  in the `instance` section should be repeated here, separated by commas.

    .. |---| unicode:: U+2014  .. em dash

  Please be aware, that the variable names use underscores instead of dashes
  here |---| the following list shows all supported settings and their
  respective default values:

  * ip_address='<ip-address>'    ['localhost']
  * http_address=<http-address>  [8080]
  * port_base=<port-base>        [0]
  * user=<user-credentials>      [n.a.]

  Either literal values or references to the `instance` part can be used here,
  i.e. "http_address='${instance:http-address}', user='${instance:user}'".
  Please note that the resulting line will be verbosely copied into the
  generated `bin/munin` script, so the extra quoting is required.

* When monitoring more than one Zope instance, i.e. in a ZEO setup, separate
  helper scripts need to be generated.  In order to do so the `scripts`
  option of `zc.recipe.egg` can be used like so::

    [buildout]
    parts =
        ...
        munin1
        munin2

    [munin1]
    recipe = zc.recipe.egg
    eggs = munin.zope
    scripts = munin=munin1
    arguments = http_address='${instance1:http-address}', user='${instance1:user}'

    [munin2]
    recipe = zc.recipe.egg
    eggs = munin.zope
    scripts = munin=munin2
    arguments = http_address='${instance2:http-address}', user='${instance2:user}'

  The necessary symlinks can then be created with each of the scripts in turn
  (see below).  Please note, that in this case you should explicitly provide
  at least a differing `prefix` argument.

* Now you should be able to call the plugins as follow::

    http://localhost:8080/@@munin.zope.plugins/zopethreads

  Where `zopethreads` is you plugin name.

* Next you need to make symlinks from the helper script inside your
  buildout's `bin/` to the munin plugin directory.  The helper script itself
  can assist you with this::

    $ bin/munin install /opt/munin/etc/plugins [<prefix>] [<suffix>]

  This will install the necessary symlinks in the given directory using
  either the provided prefix and suffix or else the hostname and current
  directory to assemble their names (see below).

  Alternatively, you may also install the desired symlinks yourself::

    $ cd /opt/munin/etc/plugins
    $ ln -s ~/zope/bin/munin company_zodbactivity_site1

  Here `/opt/munin/etc/plugins` is your munin directory, `~/zope/` is the
  root directory of your buildout, `zodb_activity` the name of the plugin
  you want to enable, `company` a placeholder for an arbitrary prefix and
  `site1` the name which will be shown in munin.

* Finally configure the plugin in munin (this step can be skipped if you have
  correctly set up the `arguments` option as described in step 2 above)::

    $ cd /opt/munin/etc/plugin-conf.d/
    $ vi munin.zope.conf
    ... [company_*_site1]
    ... env.AUTH myuser:myuser
    ... env.URL http://localhost:8080/@@munin.zope.plugins/%s

  Here `myuser:myuser` are your Zope user credentials and `localhost:8080`
  your site url.  Please check `munin`_ for more information about plugin
  configuration.

Multiple zodb storage
---------------------

If you have multiple zodb storage, you can manage it adding ``filestorage`` parameter
to the scripts using ``initFilestorages`` helper function, like so::

    [munin]
    recipe = zc.recipe.egg
    eggs = munin.zope
    initialization =
        from munin.zope.plugins import initFilestorages
        initFilestorages(['catalog', 'other'])

Or whith c.r.filestorage::

    [filestorage]
    recipe = collective.recipe.filestorage
    parts =
        catalog
        other

    [munin]
    recipe = zc.recipe.egg
    eggs = munin.zope
    initialization =
        from munin.zope.plugins import initFilestorages
        initFilestorages("""${filestorage:parts}""".split())
    arguments = http_address='${instance:http-address}', user='${instance:user}'

Security
--------
For security reasons the views requires the `View management screens` permission...

... or you can use a shared secret on the request, you must configure the shared key on
zope.conf adding a stanza like::

    <product-config munin.zope>
        secret yoursecrethere
    </product-config>

On your buildout `instance` slot::

    zope-conf-additional +=
        <product-config munin.zope>
            secret yoursecrethere
        </product-config>

So you can make a request without authentication, using the secret, like::

    http://localhost:8080/@@munin.zope.plugins/zopethreads?secret=yoursecrethere

You can also pass in the secret in the munin helper script::

    [munin3]
    recipe = zc.recipe.egg
    eggs = munin.zope
    scripts = munin=munin3
    arguments = http_address='${instance2:http-address}', secret='mylittlesecret'

Please note that, for `zopethreads`, you need to use the `secret` approach.

References
----------

* `munin.zope`_ at pypi
* `gocept.munin`_ at pypi
* `redturtle.munin`_ at pypi
* `munin`_ project
* `munin exchange`_

  .. _munin.zope: http://pypi.python.org/pypi/munin.zope/
  .. _gocept.munin: http://pypi.python.org/pypi/gocept.munin/
  .. _munin exchange: http://muninexchange.projects.linpro.no/
  .. _munin: http://munin.projects.linpro.no/
  .. _redturtle.munin: http://pypi.python.org/pypi/redturtle.munin/

Contact
-------

.. image:: http://www.redturtle.it/redturtle_banner.png

* | Andrew Mleczko <``andrew.mleczko at redturtle.net``>
  | **RedTurtle Technology**, http://www.redturtle.net/

* | Andreas Zeidler <``az at zitc.de``>
  | **ZITC**, http://zitc.de/

* | Mauro Amico <``mauro at biodec.com``>
  | **Biodec**, http://www.biodec.com/

* | Leonardo Rochael Almeida <``leorochael@gmail.com``>
  | **Simples Consultoria**, http://www.simplesconsultoria.com.br/
