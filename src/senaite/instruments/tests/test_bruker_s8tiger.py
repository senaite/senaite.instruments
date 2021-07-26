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

import unittest2 as unittest
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles

from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFPlone.utils import _createObjectByType
from bika.lims import SETUP_CATALOG
from bika.lims import api
from bika.lims.idserver import renameAfterCreation
from bika.lims.utils import tmpID
from bika.lims.utils.analysisrequest import create_analysisrequest
from senaite.core.tests.base import DataTestCase
from senaite.instruments.instruments.bruker.s8tiger.s8tiger import importer
from zope.event import notify
from zope.publisher.browser import FileUpload
from zope.publisher.browser import TestRequest

IFACE = "senaite.instruments.instruments.bruker.s8tiger.s8tiger" \
                 ".importer"

TITLE = "Bruker S8 Tiger"

path = join(abspath(dirname(__file__)), 'files', 'instruments', 'brukers8tiger')
FN1 = join(path, 'DU-0001-234987347.xlsx')
FN2 = join(path, 'DU-0001.csv')

interims = [
    dict(keyword="formula", title="Formula", hidden=True),
    dict(keyword="concentration", title="Concentration", hidden=True),
    dict(keyword="z", title="Z", hidden=True),
    dict(keyword="status", title="Status", hidden=True),
    dict(keyword="line_1", title="Line 1", hidden=True),
    dict(keyword="net_int", title="Net int.", hidden=True),
    dict(keyword="lld", title="LLD", hidden=True),
    dict(keyword="stat_error", title="Stat. error", hidden=True),
    dict(keyword="analyzed_layer", title="Analyzed layer", hidden=True),
    dict(keyword="bound_pct", title="Bound %", hidden=True),
    dict(keyword="reading_ppm", title="Reading PPM", hidden=True),
    dict(keyword="reading_pct", title="Reading PCT", hidden=False),
    dict(keyword="factor", title="Factor", hidden=False),
]


class TestFile(object):
    def __init__(self, file, filename=None):
        self.file = file
        self.headers = {}
        self.filename = filename


class TestBrukerS8Tiger(DataTestCase):

    def setUp(self):
        super(TestBrukerS8Tiger, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ['Member', 'LabManager'])
        login(self.portal, TEST_USER_NAME)
        # instrument
        self.instrument = add_instrument(self.portal)
        # calculation
        self.calculation = add_calculation(self.portal)
        # client
        query = dict(portal_type="Client", title="Happy Hills")
        brains = api.search(query, 'portal_catalog')
        self.client = api.get_object(brains[0])
        # service
        self.service = add_analysisservice(self.client, self.calculation)

    def test_import_xlsx_with_suffix(self):
        # create AR
        ar = add_analysisrequest(self.client, self.service, self.request)
        api.do_transition_for(ar, "receive")
        data = open(FN1, 'rb').read()
        import_file = FileUpload(TestFile(cStringIO.StringIO(data), FN1))
        request = TestRequest(form=dict(
            instrument_results_file_format="xlsx",
            submitted=True,
            artoapply='received_tobeverified',
            results_override='override',
            instrument_results_file=import_file,
            final_result_unit='pct',
            instrument=''))
        context = self.portal
        results = importer.Import(context, request)
        analysis = ar.getAnalyses(full_objects=True)[0]
        test_results = eval(results)  # noqa
        self.assertEqual(analysis.getResult(), '67.9')

    def test_import_csv_no_suffix(self):
        # create AR
        ar = add_analysisrequest(self.client, self.service, self.request)
        api.do_transition_for(ar, "receive")
        data = open(FN2, 'rb').read()
        import_file = FileUpload(TestFile(cStringIO.StringIO(data), FN2))
        request = TestRequest(form=dict(
            instrument_results_file_format="xlsx",
            submitted=True,
            artoapply='received_tobeverified',
            results_override='override',
            instrument_results_file=import_file,
            final_result_unit='pct',
            instrument=''))
        context = self.portal
        results = importer.Import(context, request)
        analysis = ar.getAnalyses(full_objects=True)[0]
        test_results = eval(results)  # noqa
        self.assertEqual(analysis.getResult(), '67.8')


def add_analysisrequest(client, service, request):
    # contact
    contacts = client.getContacts()
    contact = contacts[0]
    # sampletype
    query = dict(portal_type="SampleType", title="Dust")
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


def add_calculation(context):
    # calculation
    folder = context.bika_setup.bika_calculations
    obj = _createObjectByType("Calculation", folder, tmpID())
    obj.edit(title="Bruker S8 Tiger",
             Formula="[reading_pct] * [factor]",
             InterimFields=interims)
    # done
    obj.unmarkCreationFlag()
    renameAfterCreation(obj)
    notify(ObjectInitializedEvent(obj))
    return obj


def add_analysisservice(context, calculation):
    # category
    query = dict(portal_type="AnalysisCategory", title="Metals")
    brains = api.search(query, SETUP_CATALOG)
    category = api.get_object(brains[0])
    # service
    folder = context.bika_setup.bika_analysisservices
    obj = _createObjectByType("AnalysisService", folder, tmpID())
    obj.edit(
        title="Fe2O3",
        Keyword="Fe2O3_Method_Etc",
        PointOfCapture='lab',
        Category=category,
        Calculation=calculation)
    # done
    obj.unmarkCreationFlag()
    renameAfterCreation(obj)
    notify(ObjectInitializedEvent(obj))
    return obj


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBrukerS8Tiger))
    return suite
