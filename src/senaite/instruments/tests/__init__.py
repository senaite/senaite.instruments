# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS
#
# Copyright 2018 by it's authors.
class TestFile(object):
    def __init__(self, file, filename=None):
        self.file = file
        self.headers = {}
        self.filename = filename
