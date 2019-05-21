# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS
#
# Copyright 2018 by it's authors.

from .base import SimpleTestCase

# instruments that record a single AS in the result file
SINGLE_AS_INSTRUMENTS = [
]
# instruments that record a multiple ASs in the result file
MULTI_AS_INSTRUMENTS = [
    # 'agilent.chemstation.chemstation',
]
# instruments that record multiple ASs in the result file
NO_AS_INSTRUMENTS = [
    'agilent.chemstation.chemstation',
]
# instruments that record interim fields in the result file
INTERIM_INSTRUMENTS = {
    'agilent.masshunter.aorc': {
        'as_title':  'Test Interims',
        'as_keyword':  'TestInterims',
        'interims': [
            {
                'keyword': 'Ion1SigNseRat',
                'title': 'Ion 1 Signal Noise Ratio',
                'value': 105,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
            {
                'keyword': 'Ion2SigNseRat',
                'title': 'Ion 2 Signal Noise Ratio',
                'value': 1177.9,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
        ],
        'result': '',
    },
    'agilent.masshunter.qualitative': {
        'as_title':  'Test Interims',
        'as_keyword':  'TestInterims',
        'interims': [
            {
                'keyword': 'mz',
                'title': 'mz',
                'value': 583.3,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
            {
                'keyword': 'mzProd',
                'title': 'mzProd',
                'value': 583.3,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
        ],
        'result': '',
    },
    'agilent.masshunter.quantitative': {
        'as_title':  'Test Interims',
        'as_keyword':  'TestInterims',
        'interims': [
            {
                'keyword': 'CalcConc',
                'title': 'CalcConc',
                'value': 0.1034,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
            {
                'keyword': 'FinalConc',
                'title': 'FinalConc',
                'value': 0.1034,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
        ],
        'result': '',
    },
    'agilent.chemstation.chemstation': {
        'as_title':  'Calcium',
        'as_keyword':  'Ca',
        'interims': [
            {
                'keyword': 'Area',
                'title': 'Area',
                'value': 1690,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
            {
                'keyword': 'QVal',
                'title': 'QVal',
                'value': 32,
                'type': 'int',
                'hidden': False,
                'unit': ''
            }
        ],
        'result': '',
    }
}

# list of all instruments in this add on
ALL_INSTRUMENTS = \
    SINGLE_AS_INSTRUMENTS + \
    MULTI_AS_INSTRUMENTS + \
    NO_AS_INSTRUMENTS + \
    INTERIM_INSTRUMENTS.keys()


class TestSetup(SimpleTestCase):
    """ Test Setup
    """


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSetup))
    return suite
