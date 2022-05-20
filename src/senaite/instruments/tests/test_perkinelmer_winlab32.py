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

from bika.lims import api
from senaite.instruments.instruments.perkinelmer.winlab32.winlab32 import \
    importer
from senaite.instruments.tests import TestFile
from senaite.instruments.tests.base import BaseTestCase
from zope.publisher.browser import FileUpload
from zope.publisher.browser import TestRequest

TITLE = 'Perkin Elmer Winlab32'
IFACE = 'senaite.instruments.instruments' \
        '.perkinelmer.winlab32.winlab32.importer'

here = abspath(dirname(__file__))
path = join(here, 'files', 'instruments', 'perkinelmer', 'winlab32')
fn = join(path, 'winlab32.csv')

service_interims = [
    dict(keyword='reading', title='Reading', hidden=False)
]

calculation_interims = [
    dict(keyword='reading', title='Reading', hidden=False),
    dict(keyword='factor', title='Factor', hidden=False)
]


class TestWinlab32(BaseTestCase):

    def setUp(self):
        super(TestWinlab32, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ['Member', 'LabManager'])
        login(self.portal, TEST_USER_NAME)

        self.client = self.add_client(title='Happy Hills', ClientID='HH')

        self.contact = self.add_contact(
            self.client, Firstname='Rita', Surname='Mohale')

        self.instrument = self.add_instrument(
            title=TITLE,
            InstrumentType=self.add_instrumenttype(title='Mass Spectrometer'),
            Manufacturer=self.add_manufacturer(title='Pelmer Erkin'),
            Supplier=self.add_supplier(title='Instruments Inc'),
            ImportDataInterface=IFACE)

        self.calculation = self.add_calculation(
            title='Dilution', Formula='[reading] * [factor]',
            InterimFields=calculation_interims)

        self.services = [
            self.add_analysisservice(
                title='Ag 107',
                Keyword='Ag107',
                PointOfCapture='lab',
                Category=self.add_analysiscategory(title='Metals'),
                Calculation='Dilution',
                InterimFields=service_interims),
            self.add_analysisservice(
                title='al 27',
                Keyword='Al27',
                PointOfCapture='lab',
                Category=self.add_analysiscategory(title='Metals'),
                Calculation='Dilution',
                InterimFields=service_interims)
        ]
        self.sampletype = self.add_sampletype(
            title='Dust', RetentionPeriod=dict(days=1),
            MinimumVolume='1 kg', Prefix='DU')

    def test_import_csv_without_filename_suffix(self):
        ar = self.add_analysisrequest(
            self.client,
            dict(Client=self.client.UID(),
                 Contact=self.contact.UID(),
                 DateSampled=datetime.now().date().isoformat(),
                 SampleType=self.sampletype.UID()),
            [srv.UID() for srv in self.services])
        api.do_transition_for(ar, 'receive')
        data = open(fn, 'r').read()
        import_file = FileUpload(TestFile(cStringIO.StringIO(data), fn))
        request = TestRequest(form=dict(
            submitted=True,
            artoapply='received_tobeverified',
            results_override='override',
            instrument_results_file=import_file,
            instrument=api.get_uid(self.instrument)))
        results = importer.Import(self.portal, request)
        ag = ar.getAnalyses(full_objects=True, getKeyword='Ag107')[0]
        al = ar.getAnalyses(full_objects=True, getKeyword='Al27')[0]
        test_results = eval(results)  # noqa
        self.assertEqual(ag.getResult(), '0.111')
        self.assertEqual(al.getResult(), '0.222')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWinlab32))
    return suite
