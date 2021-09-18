import json
import traceback
import xml.etree.cElementTree as ET
from os.path import abspath

from bika.lims import api
from bika.lims import bikaMessageFactory as _
from senaite.core.exportimport.instruments import IInstrumentAutoImportInterface
from senaite.core.exportimport.instruments import IInstrumentExportInterface
from senaite.core.exportimport.instruments import IInstrumentImportInterface
from senaite.core.exportimport.instruments.instrument import format_keyword
from senaite.core.exportimport.instruments.resultsimport import AnalysisResultsImporter
from senaite.core.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser
from bika.lims.utils import t
from DateTime import DateTime
from plone.i18n.normalizer.interfaces import IIDNormalizer
from senaite.app.supermodel.interfaces import ISuperModel
from zope.component import getAdapter
from zope.component import getUtility
from zope.interface import implements


class QualitativeParser(InstrumentCSVResultsFileParser):
    """ Parser
    """

    def __init__(self, infile, encoding=None):
        InstrumentCSVResultsFileParser.__init__(self, infile)
        self._end_header = False
        self._delimiter = ','

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
        if len(filter(lambda x: len(x), splitted)) == 0:
            self._end_header = True

        return 0

    def parse_resultsline(self, line):
        """ Parses result lines
        """
        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            return 0

        # Header
        if splitted[0].startswith('Score'):
            self._header = splitted
            return 0

        ar_id = splitted[104]
        kw = format_keyword(splitted[18])
        analysis_date = str(DateTime())[:16]

        # Result field
        record = {
            'DefaultResult': None,
            'Remarks': '',
            'DateTime': analysis_date
        }

        # Interim values can get added to record here
        interims = [
            ('Label', 22),
            ('Area', 48),
            ('File', 54),
            ('End', 55),
            ('mz', 67),
            ('mzProd', 68),
            ('ReturnTime', 69),
            ('Start', 71),
            ('Width', 72),
            ('AcqMethod', 110),
        ]
        for column_name, column_number in interims:
            result = splitted[column_number]
            record[column_name] = self.get_result(column_name, result, 0)

        # Append record
        self._addRawResult(ar_id, {kw: record})

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


class QualitativeImporter(AnalysisResultsImporter):
    """ Importer
    """


class qualitativeimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Agilent Masshunter Qualitative"

    def __init__(self, context):
        self.context = context
        self.request = None

    def Import(self, context, request):
        """ Import Form
        """
        infile = request.form['instrument_results_file']
        artoapply = request.form['artoapply']
        override = request.form['results_override']
        instrument = request.form.get('instrument', None)
        errors = []
        logs = []
        warns = []

        if not hasattr(infile, 'filename'):
            errors.append(_("No file selected"))
            results = {'errors': errors, 'log': logs, 'warns': warns}
            return json.dumps(results)

        file_formats = ['csv', ]
        if infile.filename.split('.')[-1].lower() not in file_formats:
            errors.append(t(_("Input file format must be ${file_formats}",
                              mapping={"file_formats": file_formats[0]})))
            results = {'errors': errors, 'log': logs, 'warns': warns}
            return json.dumps(results)

        parser = QualitativeParser(infile)

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

        importer = QualitativeImporter(
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


class qualitativeexport(object):
    implements(IInstrumentExportInterface)
    title = "Agilent Masshunter Qualitative Exporter"
    __file__ = abspath(__file__)  # noqa

    def __init__(self, context):
        self.context = context
        self.request = None

    def Export(self, context, request):
        tray = 1
        norm = getUtility(IIDNormalizer).normalize
        filename = '{}-{}.xml'.format(
            context.getId(), norm(self.title))
        now = str(DateTime())[:16]

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
        root.set('SequenceModifiedTimeStamp', now)
        root.set('SequenceFileECMPath', "")

        # for looking up "cup" number (= slot) of ARs
        parent_to_slot = {}
        layout = context.getLayout()
        for item in layout:
            p_uid = item.get('parent_uid')
            if not p_uid:
                p_uid = item.get('container_uid')
            if p_uid not in parent_to_slot.keys():
                parent_to_slot[p_uid] = int(item['position'])

        rows = []
        sequences = []
        for item in layout:
            # create batch header row
            p_uid = item.get('parent_uid')
            if not p_uid:
                p_uid = item.get('container_uid')
            if not p_uid:
                continue
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

        cnt = 0
        for row in rows:
            seq = ET.SubElement(root, 'Sequence')
            ET.SubElement(seq, 'SequenceID').text = str(row['tray'])
            ET.SubElement(seq, 'SampleID').text = str(cnt)
            ET.SubElement(seq, 'AcqMethodFileName').text = 'Dunno'
            ET.SubElement(seq, 'AcqMethodPathName').text = 'Dunno'
            ET.SubElement(seq, 'DataFileName').text = row['sample'].Title()
            ET.SubElement(seq, 'DataPathName').text = 'Dunno'
            ET.SubElement(seq, 'SampleName').text = row['sample'].Title()
            ET.SubElement(seq, 'SampleType').text = row['sample'].SampleType.Title()
            ET.SubElement(seq, 'Vial').text = str(row['cup'])
            cnt += 1

        xml = ET.tostring(root, method='xml')
        # stream file to browser
        setheader = request.RESPONSE.setHeader
        setheader('Content-Length', len(xml))
        setheader('Content-Disposition',
                  'attachment; filename="%s"' % filename)
        setheader('Content-Type', 'text/xml')
        request.RESPONSE.write(xml)
