# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.INSTRUMENTS.
#
# SENAITE.CORE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2018-2019 by it's authors.
# Some rights reserved, see README and LICENSE.

# instruments that record a single AS in the result file
SINGLE_AS_INSTRUMENTS = [
    'agilent.masshunter.quantitative',
    'agilent.masshunter.qualitative',
]
# instruments that record a multiple ASs in the result file
MULTI_AS_INSTRUMENTS = [
    'agilent.chemstation.chemstation',
]
# list of all instruments in this add on
ALL_INSTRUMENTS = SINGLE_AS_INSTRUMENTS + MULTI_AS_INSTRUMENTS
