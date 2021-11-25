from plone.app.testing import FunctionalTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.testing import zope

import transaction


class BaseLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        super(BaseLayer, self).setUpZope(app, configurationContext)

        import bika.lims
        import senaite.core
        import senaite.app.listing
        import senaite.app.spotlight
        import senaite.app.supermodel
        import senaite.impress
        import senaite.lims
        import senaite.instruments
        import Products.TextIndexNG3

        self.loadZCML(package=bika.lims)
        self.loadZCML(package=senaite.core)
        self.loadZCML(package=senaite.app.listing)
        self.loadZCML(package=senaite.app.spotlight)
        self.loadZCML(package=senaite.app.supermodel)
        self.loadZCML(package=senaite.impress)
        self.loadZCML(package=senaite.lims)
        self.loadZCML(package=senaite.instruments)
        self.loadZCML(package=Products.TextIndexNG3)

        zope.installProduct(app, "bika.lims")
        zope.installProduct(app, "senaite.core")
        zope.installProduct(app, "senaite.app.listing")
        zope.installProduct(app, "senaite.app.spotlight")
        zope.installProduct(app, "senaite.app.supermodel")
        zope.installProduct(app, "senaite.impress")
        zope.installProduct(app, "senaite.lims")
        zope.installProduct(app, "senaite.instruments")
        zope.installProduct(app, "Products.TextIndexNG3")

    def setUpPloneSite(self, portal):
        super(BaseLayer, self).setUpPloneSite(portal)
        applyProfile(portal, "senaite.core:default")
        transaction.commit()


BASE_LAYER_FIXTURE = BaseLayer()
BASE_TESTING = FunctionalTesting(
    bases=(BASE_LAYER_FIXTURE,), name="SENAITE.INSTRUMENTS:BaseTesting")
