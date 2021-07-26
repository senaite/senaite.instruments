# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS
#
# Copyright 2018 by it's authors.
import cStringIO
from datetime import datetime
from os.path import abspath
from os.path import dirname
from os.path import join

from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles
from senaite.core.tests.base import DataTestCase

import unittest2 as unittest
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFPlone.utils import _createObjectByType
from bika.lims import SETUP_CATALOG
from bika.lims import api
from bika.lims.idserver import renameAfterCreation
from bika.lims.utils import tmpID
from bika.lims.utils.analysisrequest import create_analysisrequest
from senaite.instruments.instruments.perkinelmer.nexion350x.nexion350x import \
    importer
from zope.event import notify
from zope.publisher.browser import FileUpload
from zope.publisher.browser import TestRequest

IFACE = ("senaite.instruments.instruments"
         ".perkinelmer.pe900h8300.pe900h8300.importer")

TITLE = "Perkin Elmer Nexion 350X"

path = join(abspath(dirname(__file__)), 'files', 'instruments', 'perkinelmer')
FN = join(path, 'nexion350x.xlsx')

interims = [
    dict(keyword="reading", title="Reading", hidden=False)
]


class TestFile(object):
    def __init__(self, file, filename=None):
        self.file = file
        self.headers = {}
        self.filename = filename


class TestNexion350X(DataTestCase):

    def setUp(self):
        super(TestNexion350X, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ['Member', 'LabManager'])
        login(self.portal, TEST_USER_NAME)
        # instrument
        self.instrument = add_instrument(self.portal)
        # client
        query = dict(portal_type="Client", title="Happy Hills")
        brains = api.search(query, 'portal_catalog')
        self.client = api.get_object(brains[0])
        # service
        self.service = add_analysisservice(self.client)


def add_analysisrequest(client, service, request):
    # contact
    contacts = client.getContacts()
    contact = contacts[0]
    # sampletype
    query = dict(portal_type="SampleType", title="Silver")
    brains = api.search(query, SETUP_CATALOG)
    sampletype = api.get_object(brains[0])

    values = {
        "Client": api.get_uid(client),
        "Contact": api.get_uid(contact),
        "DateSampled": datetime.now().date().isoformat(),
        "SampleType": api.get_uid(sampletype)}

    service_uids = [api.get_uid(service)]
    return create_analysisrequest(client, request, values, service_uids)


def add_instrument(context):
    folder = context.bika_setup.bika_instruments
    obj = _createObjectByType("Instrument", folder, tmpID())
    iface = IFACE
    obj.edit(title=TITLE, ImportDataInterface=iface)
    # instrument type
    query = dict(portal_type="InstrumentType", title="Mass Spectrometer")
    brains = api.search(query, SETUP_CATALOG)
    obj.setInstrumentType(api.get_object(brains[0]))
    # manufacturer
    query = dict(portal_type="Manufacturer", title="Boss")
    brains = api.search(query, SETUP_CATALOG)
    obj.setManufacturer(api.get_object(brains[0]))
    # supplier
    query = dict(portal_type="Supplier", title="Instruments Inc")
    brains = api.search(query, SETUP_CATALOG)
    obj.setSupplier(api.get_object(brains[0]))
    # done
    obj.unmarkCreationFlag()
    renameAfterCreation(obj)
    notify(ObjectInitializedEvent(obj))
    return obj


def add_analysisservice(context, calculation=None):
    # sampletype
    folder = context.bika_setup.bika_sampletypes
    obj = _createObjectByType("SampleType", folder, tmpID())
    retentionperiod = {'days': 0, 'hours': 0, 'minutes': 0}
    obj.edit(title="Silver",
             RetentionPeriod=retentionperiod,
             Prefix="Silver",
             MinimumVolume="1000 g")
    obj.unmarkCreationFlag()
    renameAfterCreation(obj)
    notify(ObjectInitializedEvent(obj))

    # category
    query = dict(portal_type="AnalysisCategory", title="Metals")
    brains = api.search(query, SETUP_CATALOG)
    category = api.get_object(brains[0])
    # service
    folder = context.bika_setup.bika_analysisservices
    obj = _createObjectByType("AnalysisService", folder, tmpID())
    obj.edit(
        title="Silver",
        Keyword="Ag107",
        PointOfCapture='lab',
        Category=category,
        InterimFields=interims if calculation else [],
        Calculation=calculation)
    # done
    obj.unmarkCreationFlag()
    renameAfterCreation(obj)
    notify(ObjectInitializedEvent(obj))
    return obj


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestNexion350X))
    return suite
