import csv
import json
import traceback
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.exportimport.instruments import IInstrumentAutoImportInterface
from bika.lims.exportimport.instruments import IInstrumentExportInterface
from bika.lims.exportimport.instruments import IInstrumentImportInterface
from bika.lims.exportimport.instruments.instrument import format_keyword
from bika.lims.exportimport.instruments.resultsimport import AnalysisResultsImporter
from bika.lims.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser
from bika.lims.utils import t
from cStringIO import StringIO
from plone.i18n.normalizer.interfaces import IIDNormalizer
from senaite.core.supermodel.interfaces import ISuperModel
from zope.component import getAdapter
from zope.component import getUtility
from zope.interface import implements


class MaldiBiotyperParser(InstrumentCSVResultsFileParser):
    """ Parser
    """

    def __init__(self, infile, encoding=None):
        InstrumentCSVResultsFileParser.__init__(self, infile)
        self._end_header = False
        self._delimiter = ','

    def _parseline(self, line):
        return self.parse_resultsline(line)

    def parse_resultsline(self, line):
        """ Parses result lines
        """
        splitted = [token.strip() for token in line.split(self._delimiter)]
        if len(filter(lambda x: len(x), splitted)) == 0:
            return 0

        ar_id = splitted[0]
        # sampleType = splitted[1]
        # best_match = splitted[2]
        kw = splitted[3]
        # info = splitted[4]
        best_match_result = splitted[5]
        # secbest = splitted[6]
        # secbest_match_result = splitted[7]

        # No result field
        kw = format_keyword(kw)
        record = {
            'DefaultResult': kw,
            'Remarks': '',
        }

        # Interim values can get added to record here
        result = best_match_result
        result = self.get_result(kw, result, 0)
        record[kw] = result

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


class maldibiotyperimport(object):
    implements(IInstrumentImportInterface, IInstrumentAutoImportInterface)
    title = "Maldibiotyper2"

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

        # Load the most suitable parser according to file extension/options/etc...
        parser = MaldiBiotyperParser(infile)

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


class maldibiotyperexport(object):
    implements(IInstrumentExportInterface)
    title = "MaldiBiotyperParser2"

    def __init__(self, context):
        self.context = context
        self.request = None

    def Export(self, context, request):
        norm = getUtility(IIDNormalizer).normalize
        filename = '{}-{}.in.'.format(
            context.getId(), norm(self.title))

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
        ARs_exported = []
        for item in layout:
            p_uid = item.get('parent_uid')
            if not p_uid:
                p_uid = item.get('container_uid')
            if not p_uid:
                continue
            if p_uid in ARs_exported:
                continue
            ARs_exported.append(p_uid)
            cup = 'A{}'.format(parent_to_slot[p_uid])
            ar_id = getAdapter(item['container_uid'], ISuperModel).Title()
            analysis = getAdapter(item['analysis_uid'], ISuperModel).title
            rows.append([cup, ar_id, analysis])

        rows.sort(lambda a, b: cmp(a[1], b[1]))
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
