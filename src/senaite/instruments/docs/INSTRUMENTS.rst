SENAITE INSTRUMENTS
===================

Import and export instrument adapters for SENAITE

Running this test from the buildout directory::

    bin/test test_doctests -t INSTRUMENTS


Test Setup
----------
Needed imports::

    >>> import os
    >>> import cStringIO
    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> from DateTime import DateTime

    >>> from senaite.core.supermodel.interfaces import ISuperModel
    >>> from senaite.instruments import instruments
    >>> from senaite.instruments.tests import test_setup
    >>> from zope.component import getAdapter
    >>> from zope.publisher.browser import FileUpload, TestRequest

Functional helpers::

    >>> def timestamp(format="%Y-%m-%d"):
    ...     return DateTime().strftime(format)

    >>> class TestFile(object):
    ...     def __init__(self, file, filename='dummy.txt'):
    ...         self.file = file
    ...         self.headers = {}
    ...         self.filename = filename

Variables::

    >>> date_now = timestamp()
    >>> portal = self.portal
    >>> request = self.request
    >>> bika_setup = portal.bika_setup
    >>> bika_instruments = bika_setup.bika_instruments
    >>> bika_sampletypes = bika_setup.bika_sampletypes
    >>> bika_samplepoints = bika_setup.bika_samplepoints
    >>> bika_analysiscategories = bika_setup.bika_analysiscategories
    >>> bika_analysisservices = bika_setup.bika_analysisservices
    >>> bika_calculations = bika_setup.bika_calculations
    >>> bika_methods = portal.methods

We need certain permissions to create and access objects used in this test,
so here we will assume the role of Lab Manager::

    >>> from plone.app.testing import TEST_USER_ID
    >>> from plone.app.testing import setRoles
    >>> setRoles(portal, TEST_USER_ID, ['Manager',])


Import test
-----------

Instruments files path
----------------------
Where testing files live::

    >>> files_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'tests/files/instruments'))
    >>> instruments_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'instruments'))
    >>> files = os.listdir(files_path)
    >>> interfaces = []
    >>> importer_filename = [] #List of tuples [(importer,filename),(importer, filename)]
    >>> for fl in files:
    ...     if fl.startswith('.'):
    ...         # Ignore tmp files
    ...         continue
    ...     inst_interface = os.path.splitext(fl)[0] 
    ...     inst_path = '.'.join([inst_interface.replace('.', '/'), 'py'])
    ...     if os.path.isfile(os.path.join(instruments_path, inst_path)):
    ...         interfaces.append(inst_interface)
    ...         importer_filename.append((inst_interface, fl))
    ...     else:
    ...         inst_path = '.'.join([fl.replace('.', '/'), 'py'])
    ...         if os.path.isfile(os.path.join(instruments_path, inst_path)):
    ...             interfaces.append(fl)
    ...             importer_filename.append((fl, fl))
    ...         else:
    ...             self.fail('File {} found does match any import interface'.format(fl))

Availability of instrument interface
------------------------------------
Check that the instrument interface is available::

    >>> exims = []
    >>> for exim_id in test_setup.ALL_INSTRUMENTS:
    ...     exims.append(exim_id)
    >>> [f for f in interfaces if f not in exims] 
    []

Required steps: Create and receive Analysis Request for import test
...................................................................

An `AnalysisRequest` can only be created inside a `Client`, and it also requires a `Contact` and
a `SampleType`::

    >>> clients = self.portal.clients
    >>> client = api.create(clients, "Client", Name="NARALABS", ClientID="NLABS")
    >>> client
    <Client at /plone/clients/client-1>
    >>> contact = api.create(client, "Contact", Firstname="Juan", Surname="Gallostra")
    >>> contact
    <Contact at /plone/clients/client-1/contact-1>
    >>> sampletype = api.create(bika_sampletypes, "SampleType", Prefix="H2O", MinimumVolume="100 ml")
    >>> sampletype
    <SampleType at /plone/bika_setup/bika_sampletypes/sampletype-1>

Create an `AnalysisCategory` (which categorizes different `AnalysisServices`), and add to it an `AnalysisService`.
This service matches the service specified in the file from which the import will be performed::

    >>> analysiscategory = api.create(bika_analysiscategories, "AnalysisCategory", title="Water")
    >>> analysiscategory
    <AnalysisCategory at /plone/bika_setup/bika_analysiscategories/analysiscategory-1>
    >>> analysisservice1 = api.create(bika_analysisservices,
    ...                              "AnalysisService",
    ...                              title="HIV06ml",
    ...                              ShortTitle="hiv06",
    ...                              Category=analysiscategory,
    ...                              Keyword="HIV06ml")
    >>> analysisservice1
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-1>

    >>> analysisservice2 = api.create(bika_analysisservices,
    ...                       'AnalysisService',
    ...                       title='Magnesium',
    ...                       ShortTitle='Mg',
    ...                       Category=analysiscategory,
    ...                       Keyword="Mg")
    >>> analysisservice2
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-2>
    >>> analysisservice3 = api.create(bika_analysisservices,
    ...                     'AnalysisService',
    ...                     title='Calcium',
    ...                     ShortTitle='Ca',
    ...                     Category=analysiscategory,
    ...                     Keyword="Ca")
    >>> analysisservice3
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-3>

    >>> total_calc = api.create(bika_calculations, 'Calculation', title='TotalMagCal')
    >>> total_calc.setFormula('[Mg] + [Ca]')

    >>> a_method = api.create(bika_methods, 'Method', title='A Method')
    >>> a_method.setCalculation(total_calc)

    >>> analysisservice4 = api.create(bika_analysisservices, 'AnalysisService', title='THCaCO3', Keyword="THCaCO3")
    >>> analysisservice4.setUseDefaultCalculation(False)
    >>> analysisservice4.setCalculation(total_calc)
    >>> analysisservice4.setMethod(a_method)
    >>> analysisservice4
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-4>

    >>> interim_calc = api.create(bika_calculations, 'Calculation', title='Test-Total-Pest')
    >>> pest1 = {'keyword': 'pest1', 'title': 'Pesticide 1', 'value': 0, 'type': 'int', 'hidden': False, 'unit': ''}
    >>> pest2 = {'keyword': 'pest2', 'title': 'Pesticide 2', 'value': 0, 'type': 'int', 'hidden': False, 'unit': ''}
    >>> pest3 = {'keyword': 'pest3', 'title': 'Pesticide 3', 'value': 0, 'type': 'int', 'hidden': False, 'unit': ''}
    >>> interims = [pest1, pest2, pest3]
    >>> interim_calc.setInterimFields(interims)
    >>> self.assertEqual(interim_calc.getInterimFields(), interims)
    >>> interim_calc.setFormula('((([pest1] > 0.0) or ([pest2] > .05) or ([pest3] > 10.0) ) and "PASS" or "FAIL" )')
    >>> analysisservice5 = api.create(bika_analysisservices, 'AnalysisService', title='Total Terpenes', Keyword="TotalTerpenes")
    >>> analysisservice5.setUseDefaultCalculation(False)
    >>> analysisservice5.setCalculation(interim_calc)
    >>> analysisservice5.setInterimFields(interims)
    >>> analysisservice5
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-5>

    >>> service_uids = [
    ...     analysisservice1.UID(),
    ...     analysisservice2.UID(),
    ...     analysisservice3.UID(),
    ...     analysisservice4.UID(),
    ...     analysisservice5.UID()
    ... ]

Extend `AnalysisService` with test config data::

    >>> for inter in interfaces:
    ...     if inter not in test_setup.INTERIM_INSTRUMENTS.keys():
    ...         continue
    ...     as_data = test_setup.INTERIM_INSTRUMENTS[inter]
    ...     interims = as_data['interims']
    ...     interim_calc = api.create(bika_calculations, 'Calculation', title='{}-Calc'.format(as_data['as_title']))
    ...     interim_calc.setInterimFields(interims)
    ...     self.assertEqual(interim_calc.getInterimFields(), interims)
    ...     if as_data.get('formula'):
    ...         interim_calc.setFormula(as_data['formula'])
    ...     new_as = api.create(bika_analysisservices, 'AnalysisService', title=as_data['as_title'], Keyword=as_data['as_keyword'])
    ...     new_as.setUseDefaultCalculation(False)
    ...     new_as.setCalculation(interim_calc)
    ...     new_as.setInterimFields(interims)
    ...     service_uids.append(new_as.UID())
    ...     self.assertEqual(new_as.Title(), as_data['as_title'])

Create an `AnalysisRequest` with this `AnalysisService` and receive it::

    >>> values = {
    ...           'Client': client.UID(),
    ...           'Contact': contact.UID(),
    ...           'SamplingDate': date_now,
    ...           'DateSampled': date_now,
    ...           'SampleType': sampletype.UID()
    ...          }
    >>> ar = create_analysisrequest(client, request, values, service_uids)
    >>> ar
    <AnalysisRequest at /plone/clients/client-1/H2O-0001>
    >>> ar.getReceivedBy()
    ''
    >>> wf = api.get_tool('portal_workflow')
    >>> wf.doActionFor(ar, 'receive')
    >>> ar.getReceivedBy()
    'test_user_1_'


Assigning the Import Interface to an Instrument
-----------------------------------------------
Create an `Instrument` and assign to it the tested Import Interface::

    >>> for inter in interfaces:
    ...     title = inter.split('.')[0].title()
    ...     instrument = api.create(bika_instruments, "Instrument", title=title)
    ...     importer_class = 'senaite.instruments.instruments.{}.{}import'.format(inter, inter.split('.')[-1])
    ...     instrument.setImportDataInterface([importer_class])
    ...     if instrument.getImportDataInterface() != [importer_class]:
    ...         self.fail('Instrument Import Data Interface did not get set')
    
    >>> for inter in importer_filename:
    ...     as_data = test_setup.INTERIM_INSTRUMENTS.get(inter[0])
    ...     importer_class = '{}import'.format(inter[0].split('.')[-1])
    ...     exec('from senaite.instruments.instruments.{} import {}'.format(inter[0], importer_class))
    ...     filename = os.path.join(files_path, inter[1])
    ...     data = open(filename, 'r').read()
    ...     import_file = FileUpload(TestFile(cStringIO.StringIO(data), inter[1]))
    ...     request = TestRequest(form=dict(
    ...                                submitted=True,
    ...                                artoapply='received_tobeverified',
    ...                                results_override='override',
    ...                                instrument_results_file=import_file,
    ...                                sample='requestid',
    ...                                instrument=''))
    ...     context = self.portal
    ...     exec('importer = {}(context)'.format(importer_class))
    ...     results = importer.Import(context, request)
    ...     test_results = eval(results)
    ...     #TODO: Test for interim fields on other files aswell
    ...     analyses = ar.getAnalyses(full_objects=True)
    ...     if inter[0] in test_setup.MULTI_AS_INSTRUMENTS and \
    ...         'Import finished successfully: 1 Samples and 2 results updated' not in test_results['log']:
    ...         self.fail("Results Update failed for {}".format(inter[0]))
    ...     if inter[0] in test_setup.SINGLE_AS_INSTRUMENTS and \
    ...        'Import finished successfully: 1 Samples and 1 results updated' not in test_results['log']:
    ...         self.fail("Results Update failed for {}".format(inter[0]))
    ...
    ...     for an in analyses:
    ...         analysis = getAdapter(an.UID(), ISuperModel)
    ...         if analysis.Keyword == 'THCaCO3':
    ...             if not analysis.Method:
    ...                 self.fail("No Method on Analysis for {}".format(inter[0]))
    ...             elif analysis.Method.Title() != 'A Method':
    ...                 self.fail("Incorrect Method on Analysis for {}".format(inter[0]))
    ...         if inter[0] in test_setup.SINGLE_AS_INSTRUMENTS + test_setup.MULTI_AS_INSTRUMENTS and \
    ...            an.getKeyword() == 'Ca':
    ...             if an.getResult() != '3.0':
    ...                 msg = "Result {} = {}, not 3.0".format(
    ...                     an.getKeyword(), an.getResult())
    ...                 self.fail(msg)
    ...         if inter[0] in test_setup.MULTI_AS_INSTRUMENTS and \
    ...            an.getKeyword() == 'Mg':
    ...              if an.getResult() != '2.0':
    ...                 msg = "Result {} = {}, not 2.0".format(
    ...                     an.getKeyword(), an.getResult())
    ...                 self.fail(msg)
    ...         if inter[0] in test_setup.MULTI_AS_INSTRUMENTS and \
    ...            an.getKeyword() == 'THCaCO3':
    ...             if an.getResult() != '5.0':
    ...                 msg = "Result {} = {}, not 5.0".format(
    ...                     an.getKeyword(), an.getResult())
    ...                 self.fail(msg)
    ...         if inter[0] in test_setup.INTERIM_INSTRUMENTS and \
    ...            an.getKeyword() == as_data['as_keyword']:
    ...             if an.getResult() != as_data['result']:
    ...                 msg = "{}: Result {} = {}, not {}".format(
    ...                     inter[0], an.getKeyword(), an.getResult(), as_data['result'])
    ...                 self.fail(msg)
    ...             an_interims = an.getInterimFields()
    ...             test_interims = as_data.get('interims', [])
    ...             if test_interims and an_interims:
    ...                 for an_interim in an_interims:
    ...                     an_kw = an_interim.get('keyword')
    ...                     test_an = filter(lambda x: x['keyword'] == an_kw, test_interims)
    ...                     if len(test_an) == 0:
    ...                         continue
    ...                     test_an = test_an[0]
    ...                     if an_interim.get('value') != test_an.get('value', None):
    ...                         msg = "{}: Interim result {} = {}, not {}".format(
    ...                             inter[0],
    ...                             an_interim.get('keyword'),
    ...                             an_interim.get('value'),
    ...                             test_an.get('value'))
    ...                         self.fail(msg)
    ...
    ...     if 'port' in globals():
    ...         del Import

