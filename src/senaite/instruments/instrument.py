import types
from bika.lims.exportimport.instruments.resultsimport import InstrumentResultsFileParser
from cStringIO import StringIO
from xlrd import open_workbook
from zope.publisher.browser import FileUpload


def xls_to_csv(infile, worksheet=0, delimiter=","):
    # TODO: Move to utility module
    """
    Convert xlsx to easier format first, since we want to use the
    convenience of the CSV library

    """
    def find_sheet(wb, worksheet):
        for sheet in wb.sheets():
            if sheet.name == worksheet:
                return sheet

    wb = open_workbook(file_contents=infile.read())
    sheet = wb.sheets()[worksheet]

    buffer = StringIO()

    # extract all rows
    for n, row in enumerate(sheet.get_rows()):
        line = []
        for cell in row:
            value = cell.value
            if type(value) in types.StringTypes:
                value = value.encode("utf8")
            if value is None:
                value = ""
            line.append(str(value))
        print >>buffer, delimiter.join(line)
    buffer.seek(0)
    return buffer


def xlsx_to_csv(infile, worksheet=0, delimiter=","):
    # TODO: Move to utility module
    """
    Convert xlsx to easier format first, since we want to use the
    convenience of the CSV library

    """
    wb = load_workbook(filename=infile)
    sheet = wb.worksheets[worksheet]
    buffer = StringIO()

    # extract all rows
    for n, row in enumerate(sheet.rows):
        line = []
        for cell in row:
            value = cell.value
            if type(value) in types.StringTypes:
                value = value.encode("utf8")
            if value is None:
                value = ""
            line.append(str(value))
        print >>buffer, delimiter.join(line)
    buffer.seek(0)
    return buffer


class FileStub:

    def __init__(self, file, name):
        self.file = file
        self.headers = {}
        self.filename = name


class InstrumentXLSResultsFileParser(InstrumentResultsFileParser):
    """ Parser
    """
    def __init__(self, infile, mimetype='xlsx'):
        InstrumentResultsFileParser.__init__(self, infile, mimetype.upper())
        # Convert xls to csv
        self._delimiter = "|"
        if mimetype == 'xlsx':
            csv_data = xlsx_to_csv(
                infile, worksheet=2, delimiter=self._delimiter)
        elif mimetype == 'xls':
            csv_data = xls_to_csv(
                infile, worksheet=2, delimiter=self._delimiter)

        # adpat csv_data into a FileUpload for parse method
        self._infile = infile
        stub = FileStub(file=csv_data, name=str(infile.filename))
        self._csvfile = FileUpload(stub)

        self._encoding = None
        self._mimetype = mimetype
        self._end_header = False

    def parse(self):
        infile = self._csvfile
        self.log("Parsing file ${file_name}",
                 mapping={"file_name": infile.filename})
        jump = 0
        # We test in import functions if the file was uploaded
        try:
            if self._encoding:
                f = codecs.open(infile.name, 'r', encoding=self._encoding)
            else:
                f = open(infile.name, 'rU')
        except AttributeError:
            f = infile
        for line in f.readlines():
            self._numline += 1
            if jump == -1:
                # Something went wrong. Finish
                self.err("File processing finished due to critical errors")
                return False
            if jump > 0:
                # Jump some lines
                jump -= 1
                continue

            if not line or not line.strip():
                continue

            line = line.strip()
            jump = 0
            if line:
                jump = self._parseline(line)

        self.log(
            "End of file reached successfully: ${total_objects} objects, "
            "${total_analyses} analyses, ${total_results} results",
            mapping={"total_objects": self.getObjectsTotalCount(),
                     "total_analyses": self.getAnalysesTotalCount(),
                     "total_results": self.getResultsTotalCount()}
        )
        return True
