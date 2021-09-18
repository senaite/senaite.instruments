# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS.
#
# SENAITE.INSTRUMENTS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2018-2021 by it's authors.
# Some rights reserved, see README and LICENSE.

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
from senaite.instruments.instruments.bruker.s8tiger.s8tiger import importer
from senaite.instruments.tests import TestFile
from senaite.instruments.tests.base import BaseTestCase
from zope.publisher.browser import FileUpload
from zope.publisher.browser import TestRequest

IFACE = 'senaite.instruments.instruments' \
        '.bruker.s8tiger.s8tiger.importer'
TITLE = 'Bruker S8 Tiger'

here = abspath(dirname(__file__))
path = join(here, 'files', 'instruments', 'bruker', 's8tiger')
fn1 = join(path, 'DU-0001-234987347.xlsx')
fn2 = join(path, 'DU-0001.csv')

service_interims = [
    dict(keyword='formula', title='Formula', hidden=True),
    dict(keyword='reading', title='Reading', hidden=True),
    dict(keyword='z', title='Z', hidden=True),
    dict(keyword='status', title='Status', hidden=True),
    dict(keyword='line_1', title='Line 1', hidden=True),
    dict(keyword='net_int', title='Net int.', hidden=True),
    dict(keyword='lld', title='LLD', hidden=True),
    dict(keyword='stat_error', title='Stat. error', hidden=True),
    dict(keyword='analyzed_layer', title='Analyzed layer', hidden=True),
    dict(keyword='bound_pct', title='Bound %', hidden=True),
    dict(keyword='reading_ppm', title='Reading PPM', hidden=True),
    dict(keyword='reading_pct', title='Reading PCT', hidden=False),
    dict(keyword='factor', title='Factor', hidden=False),
]

calculation_interims = [
    dict(keyword='reading', title='Reading', hidden=False),
    dict(keyword='factor', title='Factor', hidden=False)
]


class TestBrukerS8Tiger(BaseTestCase):

    def setUp(self):
        super(TestBrukerS8Tiger, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ['Member', 'LabManager'])
        login(self.portal, TEST_USER_NAME)

        self.client = self.add_client(title='Happy Hills', ClientID='HH')

        self.contact = self.add_contact(
            self.client, Firstname='Rita', Surname='Mohale')

        self.instrument = self.add_instrument(
            title=TITLE,
            InstrumentType=self.add_instrumenttype(title='Mass Spectrometer'),
            Manufacturer=self.add_manufacturer(title='Bruker'),
            Supplier=self.add_supplier(title='Instruments Inc'),
            ImportDataInterface=IFACE,
        )

        self.calculation = self.add_calculation(
            title='Dilution', Formula='[reading] * [factor]',
            InterimFields=calculation_interims)

        self.services = [
            self.add_analysisservice(title='Ag 107',
                                     Keyword='ag107',
                                     PointOfCapture='lab',
                                     Category='Metals',
                                     Calculation='Dilution',
                                     InterimFields=service_interims),
            self.add_analysisservice(title='al 27',
                                     Keyword='al27',
                                     PointOfCapture='lab',
                                     Category='Metals',
                                     Calculation='Dilution',
                                     InterimFields=service_interims)
        ]
        self.sampletype = self.add_sampletype(
            title='Dust', RetentionPeriod=dict(days=1),
            MinimumVolume='1 kg', Prefix='DU')

    def test_import_xlsx_with_suffix(self):
        # create AR
        ar = self.add_analysisrequest(
            self.client,
            dict(Client=self.client.UID(),
                 Contact=self.contact.UID(),
                 DateSampled=datetime.now().date().isoformat(),
                 SampleType=self.sampletype.UID()),
            [srv.UID() for srv in self.services])
        api.do_transition_for(ar, 'receive')
        data = open(fn1, 'rb').read()
        import_file = FileUpload(TestFile(cStringIO.StringIO(data), fn1))
        request = TestRequest(form=dict(
            instrument_results_file_format='xlsx',
            submitted=True,
            artoapply='received_tobeverified',
            results_override='override',
            instrument_results_file=import_file,
            default_unit='pct',
            instrument=''))
        results = importer.Import(self.portal, request)
        ag = ar.getAnalyses(full_objects=True, getKeyword='ag107')[0]
        al = ar.getAnalyses(full_objects=True, getKeyword='al27')[0]
        test_results = eval(results)  # noqa
        self.assertEqual(ag.getResult(), '111.8')
        self.assertEqual(al.getResult(), '222.8')

    def test_import_csv_no_suffix(self):
        # create AR
        ar = self.add_analysisrequest(
            self.client,
            dict(Client=self.client.UID(),
                 Contact=self.contact.UID(),
                 DateSampled=datetime.now().date().isoformat(),
                 SampleType=self.sampletype.UID()),
            [srv.UID() for srv in self.services])
        api.do_transition_for(ar, 'receive')
        data = open(fn2, 'rb').read()
        import_file = FileUpload(TestFile(cStringIO.StringIO(data), fn2))
        request = TestRequest(form=dict(
            instrument_results_file_format='xlsx',
            submitted=True,
            artoapply='received_tobeverified',
            results_override='override',
            instrument_results_file=import_file,
            default_unit='pct',
            instrument=''))
        results = importer.Import(self.portal, request)
        ag = ar.getAnalyses(full_objects=True, getKeyword='ag107')[0]
        al = ar.getAnalyses(full_objects=True, getKeyword='al27')[0]
        test_results = eval(results)  # noqa
        self.assertEqual(ag.getResult(), '111.8')
        self.assertEqual(al.getResult(), '222.8')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBrukerS8Tiger))
    return suite
