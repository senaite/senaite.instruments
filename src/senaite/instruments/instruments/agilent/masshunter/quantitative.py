import json
import traceback
import xml.etree.cElementTree as ET
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.exportimport.instruments import IInstrumentAutoImportInterface
from bika.lims.exportimport.instruments import IInstrumentExportInterface
from bika.lims.exportimport.instruments import IInstrumentImportInterface
from bika.lims.exportimport.instruments.instrument import format_keyword
from bika.lims.exportimport.instruments.resultsimport import AnalysisResultsImporter
from bika.lims.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser
from bika.lims.utils import t
from plone.i18n.normalizer.interfaces import IIDNormalizer
from senaite.core.supermodel.interfaces import ISuperModel
from zope.component import getAdapter
from zope.component import getUtility
from zope.interface import implements


class QuantitativeParser(InstrumentCSVResultsFileParser):
    """ Parser
    """

    def __init__(self, infile, encoding=None):
        InstrumentCSVResultsFileParser.__init__(self, infile, 'CSV')
        self._end_header = False
        self._delimiter = ','
        self._kw = None

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
            self._kw = splitted[7].split(' ')[0]
            self._kw = format_keyword(self._kw)
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

        ar_id = splitted[2]
        # No result field
        record = {
            'DefaultResult': None,
            'Remarks': '',
            'DateTime': splitted[6]
        }

        # Interim values can get added to record here
        value_column = 'ReturnTime'
        result = splitted[8]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'Resp'
        result = splitted[9]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'CalcConc'
        result = splitted[10]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'FinalConc'
        result = splitted[11]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'Accuracy'
        result = splitted[12]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'Ratio'
        result = splitted[13]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        value_column = 'MI'
        result = splitted[14]
        result = self.get_result(value_column, result, 0)
        record[value_column] = result

        # Append record
        self._addRawResult(ar_id, {self._kw: record})

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


class QuantitativeImporter(AnalysisResultsImporter):
    """ Importer
    """


class quantitativeimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Agilent Masshunter Quantitative"

    def __init__(self, context):
        self.context = context
        self.request = None

    def Import(self, context, request):
        """ Import Form
        """
        infile = request.form['instrument_results_file']
        fileformat = request.form.get(
            'instrument_results_file_format', 'csv')
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
            parser = QuantitativeParser(infile)
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

            importer = QuantitativeImporter(
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


class quantitativeexport(object):
    implements(IInstrumentExportInterface)
    title = "Agilent Masshunter Quantitative Exporter"

    def __init__(self, context):
        self.context = context
        self.request = None

    def Export(self, context, request):
        tray = 1
        instrument = context.getInstrument()
        norm = getUtility(IIDNormalizer).normalize
        filename = '{}-{}.xml'.format(
            context.getId(), norm(instrument.getDataInterface()))
        options = {
            'dilute_factor': 1,
            'method': 'F SO2 & T SO2'
        }
        for k, v in instrument.getDataInterfaceOptions():
            options[k] = v

        root = ET.Element('SequenceTableDataSet')
        root.set('SchemaVersion', "1.0")
        root.set('SequenceComment', "")
        root.set('SequenceOperator', "")
        root.set('SequenceSeqPathFileName', "")
        root.set('SequencePreSeqAcqCommand', "")
        root.set('SequencePostSeqAcqCommand', "")
        root.set('SequencePreSeqDACommand', "")
        root.set('SequencePostSeqDACommand', "")
        root.set('SequenceReProcessing', "False")
        root.set('SequenceInjectBarCodeMismatch', "OnBarcodeMismatchInjectAnyway")
        root.set('SequenceOverwriteExistingData', "False")
        root.set('SequenceModifiedTimeStamp', "Wed Mar 06 16:11:49 2019")
        root.set('SequenceFileECMPath', "")

        # for looking up "cup" number (= slot) of ARs
        parent_to_slot = {}
        layout = context.getLayout()
        for item in layout:
            p_uid = item['parent_uid']
            if p_uid not in parent_to_slot.keys():
                parent_to_slot[p_uid] = int(item['position'])

        rows = []
        sequences = []
        for item in layout:
            # create batch header row
            p_uid = item['parent_uid']
            if p_uid in sequences:
                continue
            sequences.append(p_uid)
            cup = parent_to_slot[p_uid]
            rows.append({
                'tray': tray,
                'cup': cup,
                'analysis_uid': getAdapter(item['analysis_uid'], ISuperModel),
                'sample': getAdapter(item['container_uid'], ISuperModel)
            })
        rows.sort(lambda a, b: cmp(a['cup'], b['cup']))

        for row in rows:
            seq = ET.SubElement(root, 'Sequence')
            ET.SubElement(seq, 'SequenceID').text = str(row['tray'])
            ET.SubElement(seq, 'SampleID').text = row['sample'].getId()
            # ET.SubElement(seq, 'AcqMethodFileName').text = AAS_SCR_MRM 2015.m
            # ET.SubElement(seq, 'AcqMethodPathName').text = D:\MassHunter\GCMS\2\methods\methods
            # ET.SubElement(seq, 'DataFileName').text = 9HEPT0603-01
            # ET.SubElement(seq, 'DataPathName').text = D:\MassHunter\GCMS\1\data
            ET.SubElement(seq, 'DataFileName').text = row['sample'].Title()
            ET.SubElement(seq, 'SampleName').text = row['sample'].Title()
            ET.SubElement(seq, 'SampleType').text = row['sample'].SampleType.Title()
            ET.SubElement(seq, 'Vial').text = str(row['cup'])

        xml = ET.tostring(root, method='xml')
        # stream file to browser
        setheader = request.RESPONSE.setHeader
        setheader('Content-Length', len(xml))
        setheader('Content-Disposition',
                  'attachment; filename="%s"' % filename)
        setheader('Content-Type', 'text/xml')
        request.RESPONSE.write(xml)
