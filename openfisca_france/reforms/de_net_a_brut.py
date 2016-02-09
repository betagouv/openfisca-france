# -*- coding: utf-8 -*-

from __future__ import division

from openfisca_core import columns, reforms
from scipy.optimize import fsolve

from .. import entities

def calculate_net_from(salaire_de_base, simulation, period):
    temp_simulation = simulation.clone()
    temp_simulation.get_or_new_holder('salaire_de_base').set_array(period, salaire_de_base)
    mon_net = temp_simulation.calculate('salaire_net')[0]
    return mon_net

def build_reform(tax_benefit_system):

    Reform = reforms.make_reform(
        key = 'de_net_a_brut',
        name = u'Inversion du calcul brut -> net',
        reference = tax_benefit_system,
        )

    class salaire_net_voulu(Reform.Variable):
        column = columns.FloatCol
        entity_class = entities.Individus

    class salaire_de_base_calcule(Reform.Variable):
        column = columns.FloatCol
        entity_class = entities.Individus
        label = u"Salaire brut ou traitement indiciaire brut"
        # reference = tax_benefit_system.column_by_name["salaire_de_base"]
        url = u"http://www.trader-finance.fr/lexique-finance/definition-lettre-S/Salaire-brut.html"

        def function(self, simulation, period):
            """Calcule le salaire brut à partir du salaire net.
            """

            salaire_net_voulu = simulation.get_array('salaire_net_voulu', period)

            # Calcule le salaire brut à partir du salaire net par inversion numérique.
            simulation = self.holder.entity.simulation

            def func(net):
                def innerfunc(salaire_de_base):
                    return calculate_net_from(salaire_de_base, simulation, period) - net
                return innerfunc

            def solve(net_voulu):
                return fsolve(
                    func(net_voulu),
                    net_voulu*1.5, # on entend souvent cette méthode...
                    xtol = 1/10 # précision
                )

            return period, solve(net_voulu = salaire_net_voulu)


    return Reform()
