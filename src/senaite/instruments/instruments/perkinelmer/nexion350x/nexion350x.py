# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS.
#
# SENAITE.CORE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
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
# Copyright 2018-2019 by it's authors.
# Some rights reserved, see README and LICENSE.
import csv
import json
import traceback
from mimetypes import guess_type
from os.path import abspath
from os.path import splitext
from re import subn

from senaite.core.exportimport.instruments import IInstrumentAutoImportInterface
from senaite.core.exportimport.instruments import IInstrumentImportInterface
from senaite.core.exportimport.instruments.resultsimport import \
    AnalysisResultsImporter
from senaite.core.exportimport.instruments.resultsimport import \
    InstrumentResultsFileParser

from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.catalog import CATALOG_ANALYSIS_REQUEST_LISTING
from senaite.instruments.instrument import FileStub
from senaite.instruments.instrument import SheetNotFound
from senaite.instruments.instrument import xls_to_csv
from senaite.instruments.instrument import xlsx_to_csv
from zope.interface import implements
from zope.publisher.browser import FileUpload

non_analyte_row_headers = [
    'Sample Id',
    'R',
    'Acquisition Time',
    'QC Status',
    'Dataset File',
    'Method File',
]


class MultipleAnalysesFound(Exception):
    pass


class AnalysisNotFound(Exception):
    pass


class Nexion350xParser(InstrumentResultsFileParser):
    ar = None

    def __init__(self, infile, worksheet=0, encoding=None, delimiter=None):
        self.delimiter = delimiter if delimiter else ','
        self.encoding = encoding
        self.infile = infile
        self.worksheet = worksheet
        self.csv_data = None
        self.sample_id = None
        mimetype, encoding = guess_type(self.infile.filename)
        InstrumentResultsFileParser.__init__(self, infile, mimetype)

    def parse(self):
        order = []
        ext = splitext(self.infile.filename.lower())[-1]
        if ext == '.xlsx':
            order = (xlsx_to_csv, xls_to_csv)
        elif ext == '.xls':
            order = (xls_to_csv, xlsx_to_csv)
        elif ext == '.csv':
            self.csv_data = self.infile
        if order:
            for importer in order:
                try:
                    self.csv_data = importer(
                        infile=self.infile,
                        worksheet=self.worksheet,
                        delimiter=self.delimiter)
                    break
                except SheetNotFound:
                    self.err("Sheet not found in workbook: %s" % self.worksheet)
                    return -1
                except Exception as e:  # noqa
                    pass
            else:
                self.warn("Can't parse input file as XLS, XLSX, or CSV.")
                return -1
        stub = FileStub(file=self.csv_data, name=str(self.infile.filename))
        self.csv_data = FileUpload(stub)

        lines = self.csv_data.readlines()
        reader = csv.DictReader(lines)
        for row in reader:
            self.parse_row(reader.line_num, row)
        return 0

    def parse_row(self, row_nr, row):
        if row['Sample Id'].lower().strip() in (
                '', 'sample id', 'blk', 'rblk', 'calibration curves'):
            return 0

        # Get sample for this row
        sample_id = subn(r'[^\w\d\-_]*', '', row.get('Sample Id', ''))[0]
        ar = self.get_ar(sample_id)
        if not ar:
            msg = 'Sample not found for {}'.format(sample_id)
            self.warn(msg, numline=row_nr, line=str(row))
            return 0
        # Search for rows who's headers are analyte keys
        for key in row.keys():
            if key in non_analyte_row_headers:
                continue
            kw = subn(r'[^\w\d]*', '', key)[0]
            if not kw:
                continue
            try:
                brain = self.get_analysis(ar, kw, row_nr=row_nr, row=row)
                if not brain:
                    continue
                new_kw = brain.getKeyword
                parsed = dict(reading=float(row[key]), DefaultResult='reading')
                self._addRawResult(sample_id, {new_kw: parsed})
            except (TypeError, ValueError):
                self.warn('Value for keyword ${kw} is not numeric',
                          mapping=dict(kw=kw),
                          numline=row_nr, line=str(row))

        return 0

    @staticmethod
    def get_ar(sample_id):
        query = dict(portal_type='AnalysisRequest', getId=sample_id)
        brains = api.search(query, CATALOG_ANALYSIS_REQUEST_LISTING)
        try:
            return api.get_object(brains[0])
        except IndexError:
            pass

    @staticmethod
    def get_analyses(ar):
        analyses = ar.getAnalyses()
        return dict((a.getKeyword, a) for a in analyses)

    def get_analysis(self, ar, kw, row_nr="", row=""):
        kw = kw
        items = self.get_analyses(ar)
        brains = [v for k, v in items.items() if k.startswith(kw)]
        if len(brains) < 1:
            return None
        if len(brains) > 1:
            msg = "Multiple brains found matching Keyword '${kw}'",
            raise MultipleAnalysesFound(msg, kw=kw)
        return brains[0]


class importer(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = 'Perkin Elmer Nexion 350X'
    __file__ = abspath(__file__)  # noqa

    def __init__(self, context):
        self.context = context
        self.request = None

    @staticmethod
    def Import(context, request):
        errors = []
        logs = []
        warns = []

        infile = request.form['instrument_results_file']
        if not hasattr(infile, 'filename'):
            errors.append(_('No file selected'))

        artoapply = request.form['artoapply']
        override = request.form['results_override']
        instrument = request.form.get('instrument', None)
        worksheet = request.form['worksheet']

        parser = Nexion350xParser(infile, worksheet=worksheet)
        if parser:

            status = ['sample_received', 'attachment_due', 'to_be_verified']
            if artoapply == 'received':
                status = ['sample_received']
            elif artoapply == 'received_tobeverified':
                status = ['sample_received', 'attachment_due', 'to_be_verified']

            over = [False, False]
            if override == 'nooverride':
                over = [False, False]
            elif override == 'override':
                over = [True, False]
            elif override == 'overrideempty':
                over = [True, True]

            importer = AnalysisResultsImporter(
                parser=parser,
                context=context,
                allowed_ar_states=status,
                allowed_analysis_states=None,
                override=over,
                instrument_uid=instrument)

            try:
                importer.process()
                errors = importer.errors
                logs = importer.logs
                warns = importer.warns
            except Exception as e:
                errors.extend([repr(e), traceback.format_exc()])

        results = {'errors': errors, 'log': logs, 'warns': warns}

        return json.dumps(results)
