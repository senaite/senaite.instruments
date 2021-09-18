import csv
import json
import traceback
from os.path import abspath

from bika.lims import api
from bika.lims import bikaMessageFactory as _
from senaite.core.exportimport.instruments import IInstrumentAutoImportInterface
from senaite.core.exportimport.instruments import IInstrumentExportInterface
from senaite.core.exportimport.instruments import IInstrumentImportInterface
from senaite.core.exportimport.instruments.instrument import format_keyword
from senaite.core.exportimport.instruments.resultsimport import AnalysisResultsImporter
from bika.lims.utils import t
from cStringIO import StringIO
from DateTime import DateTime
from plone.i18n.normalizer.interfaces import IIDNormalizer
from senaite.instruments.instrument import InstrumentXLSResultsFileParser
from zope.component import getUtility
from zope.interface import implements


class chemstationexport(object):
    implements(IInstrumentExportInterface)
    title = "Agilent ChemStation Exporter"

    def __init__(self, context):
        self.context = context
        self.request = None

    def Export(self, context, request):
        tray = 1
        now = DateTime().strftime('%Y%m%d-%H%M')
        uc = api.get_tool('uid_catalog')
        instrument = context.getInstrument()
        norm = getUtility(IIDNormalizer).normalize
        filename = '{}-{}.csv'.format(
            context.getId(), norm(instrument.getDataInterface()))
        listname = '{}_{}_{}'.format(
            context.getId(), norm(instrument.Title()), now)
        options = {
            'dilute_factor': 1,
            'method': 'F SO2 & T SO2'
        }
        for k, v in instrument.getDataInterfaceOptions():
            options[k] = v

        # for looking up "cup" number (= slot) of ARs
        parent_to_slot = {}
        layout = context.getLayout()
        for x in range(len(layout)):
            a_uid = layout[x]['analysis_uid']
            p_uid = uc(UID=a_uid)[0].getObject().aq_parent.UID()
            layout[x]['parent_uid'] = p_uid
            if p_uid not in parent_to_slot.keys():
                parent_to_slot[p_uid] = int(layout[x]['position'])

        # write rows, one per PARENT
        header = [listname, options['method']]
        rows = []
        rows.append(header)
        tmprows = []
        ARs_exported = []
        for x in range(len(layout)):
            # create batch header row
            c_uid = layout[x]['container_uid']
            p_uid = layout[x]['parent_uid']
            if p_uid in ARs_exported:
                continue
            cup = parent_to_slot[p_uid]
            tmprows.append([tray,
                            cup,
                            p_uid,
                            c_uid,
                            options['dilute_factor'],
                            ""])
            ARs_exported.append(p_uid)
        tmprows.sort(lambda a, b: cmp(a[1], b[1]))
        rows += tmprows

        ramdisk = StringIO()
        writer = csv.writer(ramdisk, delimiter=';')
        assert(writer)
        writer.writerows(rows)
        result = ramdisk.getvalue()
        ramdisk.close()

        # stream file to browser
        setheader = request.RESPONSE.setHeader
        setheader('Content-Length', len(result))
        setheader('Content-Type', 'text/comma-separated-values')
        setheader('Content-Disposition', 'inline; filename=%s' % filename)
        request.RESPONSE.write(result)


class ChemStationParser(InstrumentXLSResultsFileParser):
    """ Parser
    """
    def __init__(self, infile, encoding=None):
        InstrumentXLSResultsFileParser.__init__(
            self, infile, worksheet=2, encoding=encoding)
        self._end_header = False
        self._ar_id = None

    def _parseline(self, line):
        if self._end_header:
            return self.parse_resultsline(line)
        return self.parse_headerline(line)

    def parse_headerline(self, line):
        """ Parses header lines
        """
        if self._end_header:
            # Header already processed
            return 0

        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            self._end_header = True

        if splitted[0].startswith('Sample Name:'):
            self._ar_id = splitted[0].split(':')[1].strip()

        return 0

    def parse_resultsline(self, line):
        """ Parses result lines
        """
        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            return 0

        # Header
        if splitted[0] == 'Comp #':
            self._header = splitted
            return 0

        # No default
        record = {
            'DefaultResult': None,
            'Remarks': ''
        }
        # 4 Interim fields
        value_column = 'Amount'
        result = splitted[4]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'ReturnTime'
        result = splitted[2]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'Area'
        result = splitted[3]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'QVal'
        result = splitted[6]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        # assign record to kw dict
        kw = splitted[1]
        kw = format_keyword(kw)
        self._addRawResult(self._ar_id, {kw: record})

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


class chemstationimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Agilent ChemStation"
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
            parser = ChemStationParser(infile, encoding=fileformat)
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
