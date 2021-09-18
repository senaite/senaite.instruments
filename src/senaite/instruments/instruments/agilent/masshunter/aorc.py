import json
import traceback
from os.path import abspath

from bika.lims import api
from bika.lims import bikaMessageFactory as _
from senaite.core.exportimport.instruments import IInstrumentAutoImportInterface
from senaite.core.exportimport.instruments import IInstrumentImportInterface
from senaite.core.exportimport.instruments.instrument import format_keyword
from senaite.core.exportimport.instruments.resultsimport import AnalysisResultsImporter
from bika.lims.utils import t
from DateTime import DateTime
from senaite.instruments.instrument import InstrumentXLSResultsFileParser
from zope.interface import implements


class AORCParser(InstrumentXLSResultsFileParser):
    """ Parser
    """
    def __init__(self, infile, encoding=None):
        InstrumentXLSResultsFileParser.__init__(
            self, infile, worksheet=0, encoding=encoding)
        self._end_header = False
        self._delimiter = '|'
        self._ar_id = None
        self._kw = None
        self._retentiontime = None
        self._retentiontimeref = None
        self._ions = []

    def _parseline(self, line):
        if self._end_header:
            return self.parse_resultsline(line)
        return self.parse_headerline(line)

    def parse_headerline(self, line):
        """ Parse everything in parse_resultsline
        """
        self._end_header = True

        return 0

    def parse_resultsline(self, line):
        """ Parses result lines
        """
        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            return 0

        # AR id
        if splitted[0] == 'Laboratory number':
            self._ar_id = splitted[2]
            return 0

        if splitted[0] == 'Molecule':
            self._kw = format_keyword(splitted[2])
            return 0

        if splitted[0] == 'Retention time in the molecule':
            if self._retentiontime:
                self._retentiontimeref = splitted[1]
            else:
                self._retentiontime = splitted[1]
            return 0

        if splitted[0].startswith('ion'):
            ion_number = splitted[0].split(' ')[1]
            mz_values = splitted[1].split('---')
            self._ions.append({
                'Ion{}mzmax'.format(ion_number): mz_values[0],
                'Ion{}mzmin'.format(ion_number): mz_values[1],
                'Ion{}Area'.format(ion_number): splitted[2],
                'Ion{}AreaRef'.format(ion_number): splitted[3],
                'Ion{}SigNseRat'.format(ion_number): splitted[4],
            })

        if splitted[0] == 'PARAMETERS TO BE CONSIDERED FOR THE CALCULATION':
            # No result field
            record = {
                'DefaultResult': None,
                'Remarks': '',
                'DateTime': str(DateTime())[:16]
            }

            # Interim values
            column_name = 'RetentionTime'
            record[column_name] = self.get_result(
                column_name, self._retentiontime, 0)

            column_name = 'RetentionTimeRef'
            record[column_name] = self.get_result(
                column_name, self._retentiontimeref, 0)

            for ion in self._ions:
                for interim_key in ion.keys():
                    record[interim_key] = self.get_result(
                        interim_key, ion[interim_key], 0)

            # Append record
            self._addRawResult(self._ar_id, {self._kw: record})

        return 0

    def get_result(self, column_name, result, line):
        result = str(result)
        if result.startswith('--') or result == '' or result == 'ND':
            return 0.0

        if api.is_floatable(result):
            result = api.to_float(result)
            return result > 0.0 and result or 0.0

        self.err("No valid number ${result} in column (${column_name})",
                 mapping={"result": result,
                          "column_name": column_name},
                 numline=self._numline, line=line)
        return


class aorcimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Quanti AORC"
    __file__ = abspath(__file__)  # noqa

    def __init__(self, context):
        self.context = context
        self.request = None

    def Import(self, context, request):
        """ Import Form
        """
        infile = request.form['instrument_results_file']
        fileformat = request.form.get(
            'instrument_results_file_format', 'xls')
        artoapply = request.form['artoapply']
        override = request.form['results_override']
        instrument = request.form.get('instrument', None)
        errors = []
        logs = []
        warns = []

        # Load the most suitable parser according to file extension/options/etc...
        parser = None
        if not hasattr(infile, 'filename'):
            errors.append(_("No file selected"))
        if fileformat in ('xls', 'xlsx'):
            parser = AORCParser(infile, encoding=fileformat)
        else:
            errors.append(t(_("Unrecognized file format ${fileformat}",
                              mapping={"fileformat": fileformat})))

        if parser:
            # Load the importer
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
            tbex = ''
            try:
                importer.process()
                errors = importer.errors
                logs = importer.logs
                warns = importer.warns
            except Exception as e:
                tbex = traceback.format_exc()
                errors.append(tbex)

        results = {'errors': errors, 'log': logs, 'warns': warns}

        return json.dumps(results)
