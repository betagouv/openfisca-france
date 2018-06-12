# -*- coding: utf-8 -*-
import openfisca_france
from openfisca_france.model.base import *
from openfisca_core import reforms

class date_demande_mes_aides(Variable):
    value_type = date
    entity = Individu
    label = u"Date de la simulation"
    definition_period = MONTH


class aah(Variable):
    calculate_output = calculate_output_add
    value_type = float
    label = u"Allocation adulte handicapé (Individu) mensualisée"
    entity = Individu
    definition_period = MONTH
    set_input = set_input_divide_by_period

    def formula(individu, period):
        known_periods = individu.get_holder('date_demande_mes_aides').get_known_periods()
        if known_periods:
            date_demande = sorted(known_periods, reverse = True)[0]
            return individu('aah_base', date_demande)

        return individu('aah_base', period)

class simulation_reform(reforms.Reform):

    def apply(self):
        self.add_variable(date_demande_mes_aides)
        self.update_variable(aah)
