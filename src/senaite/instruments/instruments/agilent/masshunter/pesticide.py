import json
import traceback
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.exportimport.instruments import IInstrumentAutoImportInterface
from bika.lims.exportimport.instruments import IInstrumentImportInterface
from bika.lims.exportimport.instruments.resultsimport import AnalysisResultsImporter
from bika.lims.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser
from bika.lims.utils import t
from zope.interface import implements


class PesticideParser(InstrumentCSVResultsFileParser):
    """ Parser
    """

    def __init__(self, infile, encoding=None):
        InstrumentCSVResultsFileParser.__init__(self, infile, 'CSV')
        self._end_header = False
        self._delimiter = ','
        self._spec = {
            'Propargite': {
                'col_num': 8, 'col_name': 'RT'},
            'TriphenylphosphateTPPISISTD': {
                'col_num': 11, 'col_name': 'RT'},
        }
        self._rawresults = {}

    def _parseline(self, line):
        if self._end_header:
            return self.parse_resultsline(line)
        return self.parse_headerline(line)

    def parse_headerline(self, line):
        """ Parses header lines

            Keywords example:
            Keyword1, Keyword2, Keyword3, ..., end
        """
        if self._end_header:
            # Header already processed
            return 0

        splitted = [token.strip() for token in line.split(self._delimiter)]
        if splitted[0].startswith('Sample'):
            self._end_header = True

        return 0

    def parse_resultsline(self, line):
        """ Parses result lines
        """
        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            return 0

        # Header
        if splitted[2] == 'Name':
            self._header = splitted
            return 0

        # self._rawresults = {ar_id: [{}]}
        # value_column = 'Q-value'
        # result = splitted[6]
        # result = self.get_result(value_column, result, 0)
        # record['QValue'] = result

        # # assign record to kw dict
        # kw = splitted[1]
        # kw = format_keyword(kw)
        # ar_id = self._rawresults.keys()[0]
        # self._rawresults[ar_id][0][kw] = record

        ar_id = splitted[2]
        # analysed_datetime = splitted[6]
        self._rawresults[ar_id] = []
        for kw in self._spec:
            col_name = self._spec[kw]['col_name']
            col_num = self._spec[kw]['col_num']
            record = {
                'DefaultResult': col_name,
                'Remarks': ''
            }
            result = splitted[col_num]
            record[col_name] = self.get_result(col_name, result, 0)

            # Interim values can get added to record here

            # Append record
            self._rawresults[ar_id].append({kw: record})

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


class PesticideImporter(AnalysisResultsImporter):
    """ Importer
    """


class pesticideimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Agilent Masshunter Pesticide"

    def __init__(self, context):
        self.context = context
        self.request = None

    def Import(self, context, request):
        """ Import Form
        """
        infile = request.form['instrument_results_file']
        fileformat = request.form['instrument_results_file_format']
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
        if fileformat in ('csv'):
            parser = PesticideParser(infile)
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

            importer = PesticideImporter(
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
