# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS
#
# Copyright 2018 by it's authors.

from .base import SimpleTestCase

# instruments that record a single AS in the result file
SINGLE_AS_INSTRUMENTS = [
    'agilent.masshunter.quantitative',
    'agilent.masshunter.qualitative',
]
# instruments that record a multiple ASs in the result file
MULTI_AS_INSTRUMENTS = [
    'agilent.chemstation.chemstation',
]
# instruments that record multiple ASs in the result file
NO_AS_INSTRUMENTS = [
    'agilent.masshunter.aorc',
]
# list of all instruments in this add on
ALL_INSTRUMENTS = \
    SINGLE_AS_INSTRUMENTS + MULTI_AS_INSTRUMENTS + NO_AS_INSTRUMENTS

# instruments that record interim fields in the result file
INTERIM_INSTRUMENTS = {
    'agilent.masshunter.aorc': {
        'as_title':  'Total Interims',
        'as_keyword':  'TotalInterims',
        'interims': [
            {
                'keyword': 'Ion1SigNseRat',
                'title': 'Ion 1 Signal Noise Ratio',
                'value': 0,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
            {
                'keyword': 'Ion2SigNseRat',
                'title': 'Ion 2 Signal Noise Ratio',
                'value': 0,
                'type': 'int',
                'hidden': False,
                'unit': ''
            },
        ],
        'formula': '((([Ion1SigNseRat] > 100) or ([Ion2SigNseRat] > 1000) ) and "PASS" or "FAIL" )',
        'result': 'PASS',
    }
}


class TestSetup(SimpleTestCase):
    """ Test Setup
    """


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSetup))
    return suite
