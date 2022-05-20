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
from senaite.instruments.instruments.perkinelmer.nexion350x.nexion350x import \
    importer
from senaite.instruments.tests import TestFile
from senaite.instruments.tests.base import BaseTestCase
from zope.publisher.browser import FileUpload
from zope.publisher.browser import TestRequest

TITLE = 'Nexion 350X'
IFACE = 'senaite.instruments.instruments' \
        '.perkinelmer.nexion350x.nexion350x.importer'

here = abspath(dirname(__file__))
path = join(here, 'files', 'instruments', 'perkinelmer', 'nexion350x')
fn = join(path, 'nexion350x.xlsx')

service_interims = [
    dict(keyword='reading', title='Reading', hidden=False)
]

calculation_interims = [
    dict(keyword='reading', title='Reading', hidden=True),
    dict(keyword='factor', title='Factor', hidden=False)
]


class TestNexion350X(BaseTestCase):

    def setUp(self):
        super(TestNexion350X, self).setUp()
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
            self.add_analysisservice(title='Ag 107',
                                     Keyword='Ag107',
                                     PointOfCapture='lab',
                                     Category='Metals',
                                     Calculation='Dilution',
                                     InterimFields=service_interims),
            self.add_analysisservice(title='al 27',
                                     Keyword='Al27',
                                     PointOfCapture='lab',
                                     Category='Metals',
                                     Calculation='Dilution',
                                     InterimFields=service_interims)
        ]
        self.sampletype = self.add_sampletype(
            title='Dust', RetentionPeriod=dict(days=1),
            MinimumVolume='1 kg', Prefix='DU')

    def test_import_xlsx(self):
        ar1 = self.add_analysisrequest(
            self.client,
            dict(Client=self.client.UID(),
                 Contact=self.contact.UID(),
                 DateSampled=datetime.now().date().isoformat(),
                 SampleType=self.sampletype.UID()),
            [srv.UID() for srv in self.services])
        ar2 = self.add_analysisrequest(
            self.client,
            dict(Client=self.client.UID(),
                 Contact=self.contact.UID(),
                 DateSampled=datetime.now().date().isoformat(),
                 SampleType=self.sampletype.UID()),
            [srv.UID() for srv in self.services])
        api.do_transition_for(ar1, 'receive')
        api.do_transition_for(ar2, 'receive')

        data = open(fn, 'rb').read()
        import_file = FileUpload(TestFile(cStringIO.StringIO(data), fn))
        request = TestRequest(form=dict(
            submitted=True,
            artoapply='received_tobeverified',
            results_override='override',
            instrument_results_file=import_file,
            worksheet='Concentrations',
            instrument=api.get_uid(self.instrument)))
        results = importer.Import(self.portal, request)
        test_results = eval(results)  # noqa
        ag1 = ar1.getAnalyses(full_objects=True, getKeyword='Ag107')[0]
        al1 = ar1.getAnalyses(full_objects=True, getKeyword='Al27')[0]
        ag2 = ar2.getAnalyses(full_objects=True, getKeyword='Ag107')[0]
        al2 = ar2.getAnalyses(full_objects=True, getKeyword='Al27')[0]
        self.assertEqual(ag1.getResult(), '0.111')
        self.assertEqual(al1.getResult(), '0.555')
        self.assertEqual(ag2.getResult(), '0.222')
        self.assertEqual(al2.getResult(), '0.666')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestNexion350X))
    return suite
