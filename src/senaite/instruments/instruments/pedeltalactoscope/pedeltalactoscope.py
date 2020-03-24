import os
import json
import traceback
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.exportimport.instruments import IInstrumentAutoImportInterface
from bika.lims.exportimport.instruments import IInstrumentImportInterface
from bika.lims.exportimport.instruments.instrument import format_keyword
from bika.lims.exportimport.instruments.resultsimport import AnalysisResultsImporter
from bika.lims.utils import t
from senaite.instruments.instrument import InstrumentXLSResultsFileParser
from zope.interface import implements


class PEDeltaLactorScopeParser(InstrumentXLSResultsFileParser):
    """ Parser
    """
    def __init__(self, infile, encoding=None):
        InstrumentXLSResultsFileParser.__init__(
            self, infile, worksheet=0, encoding=encoding)
        self._end_header = False
        self._keywords = []
        self._units = []
        self._ar_id = None
        self._users_roles = []
        self._remarks = []

    def _parseline(self, line):
        return self.parse_resultsline(line)

    def parse_resultsline(self, line):
        """ Parses result lines
        """
        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            return 0
        if len(filter(lambda x: len(x), splitted)) == 2:
            # AR and SampleType, not used
            self._ar_id = splitted[3]
            return 0

        if not self._keywords and self._ar_id:
            self._keywords = [format_keyword(i) for i in splitted[4:-3]]
            return 0
        if not self._units:
            self._units = splitted[4:-3]
            return 0

        if splitted[3].startswith('#'):
            return 0

        skip = ['StdDev', 'Version', 'Slope', 'Intercept',
                'Calibrated']
        if splitted[3] in skip:
            return 0

        records = {}
        if splitted[3] == "Mean":
            results = splitted[4:-3]
            records.update(dict(zip(self._keywords, results)))
            ar_id = splitted[-3]
            # assign record to kw dict
            for i in records:
                record = {'DefaultResult': i,
                          i: records[i],
                          'DateTime': splitted[-1],
                          }
                self._addRawResult(ar_id, {i: record})
            self._ar_id = None
            self._keywords = []
            return 0

        # TODO: Get users roles
        if splitted[2] in ['Lab Manager']:
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


class pedeltalactoscopeimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "PE Delta LactoScope"

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
        filename, file_extension = os.path.splitext(infile.filename)
        fileformat = file_extension.replace('.', '')
        if fileformat not in ('xls', 'xlsx'):
            errors.append(t(_("Unrecognized file format ${fileformat}",
                              mapping={"fileformat": fileformat})))
        if not errors:
            parser = PEDeltaLactorScopeParser(infile, encoding=fileformat)

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
            except Exception:
                tbex = traceback.format_exc()
                errors.append(tbex)

        results = {'errors': errors, 'log': logs, 'warns': warns}

        return json.dumps(results)
