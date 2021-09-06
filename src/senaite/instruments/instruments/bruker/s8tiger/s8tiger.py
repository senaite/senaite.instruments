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
from os.path import basename
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
from senaite.instruments.instrument import xls_to_csv
from senaite.instruments.instrument import xlsx_to_csv
from zope.interface import implements
from zope.publisher.browser import FileUpload

field_interim_map = {
    "Formula": "formula",
    "Concentration": "concentration",
    "Z": "z",
    "Status": "status",
    "Line 1": "line_1",
    "Net int.": "net_int",
    "LLD": "lld",
    "Stat. error": "stat_error",
    "Analyzed layer": "analyzed_layer",
    "Bound %": "bound_pct"
}


class SampleNotFound(Exception):
    pass


class MultipleAnalysesFound(Exception):
    pass


class AnalysisNotFound(Exception):
    pass


class S8TigerParser(InstrumentResultsFileParser):
    ar = None

    def __init__(self, infile, worksheet=None, encoding=None,
                 final_result_unit=None, delimiter=None):
        self.delimiter = delimiter if delimiter else ','
        self.unit = final_result_unit if final_result_unit else "pct"
        self.ar = None
        self.analyses = None
        self.worksheet = worksheet if worksheet else 0
        self.infile = infile
        self.csv_data = None
        self.csv_data = None
        self.sample_id = None
        mimetype = guess_type(self.infile.filename)
        InstrumentResultsFileParser.__init__(self, infile, mimetype)

    def parse(self):
        order = []
        if '.xlsx' in self.infile.filename.lower():
            order = (xlsx_to_csv, xls_to_csv)
        elif '.xls' in self.infile.filename.lower():
            order = (xls_to_csv, xlsx_to_csv)
        elif '.csv' in self.infile.filename.lower():
            self.csv_data = self.infile
        if order:
            for importer in order:
                try:
                    self.csv_data = importer(
                        infile=self.infile,
                        worksheet=self.worksheet,
                        delimiter=self.delimiter)
                    break
                except Exception as e:  # noqa
                    pass
            else:
                self.warn("Can't parse input file as XLS, XLSX, or CSV.")
                return -1
        stub = FileStub(file=self.csv_data, name=str(self.infile.filename))
        self.csv_data = FileUpload(stub)

        try:
            sample_id, ext = splitext(basename(self.infile.filename))
            # maybe the filename is a sample ID, just the way it is
            ar = self.get_ar(sample_id)
            if not ar:
                # maybe we need to chop of it's -9digit suffix
                sample_id = '-'.join(sample_id.split('-')[:-1])
                ar = self.get_ar(sample_id)
                if not ar:
                    # or we are out of luck
                    msg = "Can't find sample for " + self.infile.filename
                    self.warn(msg)
                    return -1
            self.ar = ar
            self.sample_id = sample_id
            self.analyses = self.get_analyses(ar)
        except Exception as e:
            self.err(repr(e))
            return False
        lines = self.csv_data.readlines()
        reader = csv.DictReader(lines)
        for row in reader:
            self.parse_row(reader.line_num, row)

    def parse_row(self, row_nr, row):
        # convert row to use interim field names
        parsed = {field_interim_map[k]: v for k, v in row.items()}
        default_result = 'reading'
        parsed.update({'DefaultResult': default_result})

        formula = parsed.get('formula')
        try:
            analysis = self.get_analysis(formula)
            keyword = analysis.getKeyword
        except Exception as e:
            self.warn(msg="Error getting analysis for '${f}': ${e}",
                      mapping={'f': formula, 'e': repr(e)},
                      numline=row_nr, line=str(row))
            return

        # Concentration can be PPM or PCT as it likes, I'll save both.
        concentration = parsed['concentration']
        try:
            val = float(subn(r'[^.\d]', '', str(concentration))[0])
        except (TypeError, ValueError, IndexError):
            self.warn(msg="Can't extract numerical value from `concentration`",
                      numline=row_nr, line=str(row))
            parsed['pct'] = ''
            parsed['ppm'] = ''
            parsed['reading'] = ''
        else:
            if 'ppm' in concentration.lower():
                parsed['pct'] = val * 0.0001
                parsed['ppm'] = val
            elif '%' in concentration:
                parsed['pct'] = val
                parsed['ppm'] = 1 / 0.0001 * val
            else:
                self.warn("Can't decide if concentration units are PPM or %",
                          numline=row_nr, line=str(row))
                return 0
            reading = parsed['ppm'] if self.unit == 'ppm' else parsed['pct']
            parsed['reading'] = reading

        self._addRawResult(self.sample_id, {keyword: parsed})
        return 0

    @staticmethod
    def get_ar(sample_id):
        query = dict(portal_type="AnalysisRequest", getId=sample_id)
        brains = api.search(query, CATALOG_ANALYSIS_REQUEST_LISTING)
        try:
            return api.get_object(brains[0])
        except IndexError:
            pass

    @staticmethod
    def get_analyses(ar):
        analyses = ar.getAnalyses()
        return dict((a.getKeyword, a) for a in analyses)

    def get_analysis(self, f):
        analyses = [v for k, v in self.analyses.items() if k.startswith(f)]
        if len(analyses) < 1:
            msg = "No analysis found matching Keyword '${kw}'",
            raise AnalysisNotFound(msg, kw=f)
        if len(analyses) > 1:
            msg = "Multiple analyses found matching Keyword '${kw}'",
            raise MultipleAnalysesFound(msg, kw=f)
        return analyses[0]


class importer(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Bruker S8 Tiger"

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
            errors.append(_("No file selected"))

        artoapply = request.form['artoapply']
        override = request.form['results_override']
        instrument = request.form.get('instrument', None)

        final_result_unit = request.form['final_result_unit']
        parser = S8TigerParser(infile, final_result_unit=final_result_unit)
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
