# -*- coding: utf-8 -*-
from __future__ import division

from openfisca_france.model.base import *  # noqa analysis:ignore

class rennes_metropole_transport(Variable):
    column = FloatCol
    entity_class = Familles
    label = u"Rennes"


    def function(self, simulation, period):
        return period, self.zeros() + 50
