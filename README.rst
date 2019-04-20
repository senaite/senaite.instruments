*Instrument results import and export add-on for SENAITE*
=========================================================

.. image:: https://img.shields.io/github/issues-pr/senaite/senaite.instruments.svg?style=flat-square
   :target: https://github.com/senaite/senaite.instruments/pulls

.. image:: https://img.shields.io/github/issues/senaite/senaite.instruments.svg?style=flat-square
   :target: https://github.com/senaite/senaite.instruments/issues

.. image:: https://img.shields.io/badge/README-GitHub-blue.svg?style=flat-square
   :target: https://github.com/senaite/senaite.instruments#readme


Introduction
============

SENAITE INSTRUMENTS adds **instrument results import and export** capabilities to `SENAITE LIMS <https://www.senaite.com>`_.


Installation
============

Please follow the installations instructions for `Plone 4`_ and
`senaite.lims`_.

To install SENAITE INSTRUMENTS, you have to add `senaite.instruments` into the `eggs`
list inside the `[buildout]` section of your `buildout.cfg`::

   [buildout]
   parts =
       instance
   extends =
       http://dist.plone.org/release/4.3.18/versions.cfg
   find-links =
       http://dist.plone.org/release/4.3.18
       http://dist.plone.org/thirdparty
   eggs =
       Plone
       Pillow
       senaite.lims
       senaite.instruments
   zcml =
   eggs-directory = ${buildout:directory}/eggs

   [instance]
   recipe = plone.recipe.zope2instance
   user = admin:admin
   http-address = 0.0.0.0:8080
   eggs =
       ${buildout:eggs}
   zcml =
       ${buildout:zcml}

   [versions]
   setuptools =
   zc.buildout =


**Note**

The above example works for the buildout created by the unified
installer. If you however have a custom buildout you might need to add
the egg to the `eggs` list in the `[instance]` section rather than
adding it in the `[buildout]` section.

Also see this section of the Plone documentation for further details:
https://docs.plone.org/4/en/manage/installing/installing_addons.html

**Important**

For the changes to take effect you need to re-run buildout from your
console::

   bin/buildout


Installation Requirements
-------------------------

The following versions are required for SENAITE INSTRUMENTS:

-  Plone 4.3.18
-  senaite.lims >= 1.3.0


Activate the Add-on
-------------------

Please browse to the *Add-ons* Controlpanel and activate the **SENAITE INSTRUMENTS** Add-on:

<img src="static/activate_addon.png" alt="Activate SENAITE INSTRUMENTS Add-on" />

Contribute
==========

We want contributing to SENAITE.INSTRUMENTS to be fun, enjoyable, and educational
for anyone, and everyone. This project adheres to the `Contributor Covenant
<https://github.com/senaite/senaite.instruments/blob/master/CODE_OF_CONDUCT.md>`_.

By participating, you are expected to uphold this code. Please report
unacceptable behavior.

Contributions go far beyond pull requests and commits. Although we love giving
you the opportunity to put your stamp on SENAITE.INSTRUMENTS, we also are thrilled
to receive a variety of other contributions.

Please, read `Contributing to senaite.instruments document
<https://github.com/senaite/senaite.instruments/blob/master/CONTRIBUTING.md>`_.


Feedback and support
====================

* `Community site <https://community.senaite.org/>`_
* `Gitter channel <https://gitter.im/senaite/Lobby>`_
* `Users list <https://sourceforge.net/projects/senaite/lists/senaite-users>`_


License
=======

**SENAITE.INSTRUMENTS** Copyright (C) 2019 Senaite Foundation

This program is free software; you can redistribute it and/or modify it under
the terms of the `GNU General Public License version 2
<https://github.com/senaite/senaite.instruments/blob/master/LICENSE>`_ as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
