# -*- coding: utf-8 -*-

import datetime

from openfisca_core import periods
from openfisca_core.tools import assert_near

from openfisca_france.tests import base

from openfisca_france.reforms import inversion_revenus


def check_chomage_net_to_chomage_brut(count, chomage_brut_max, chomage_brut_min, year):
    scenario_args = dict(
        axes = [
            dict(
                count = count,
                name = 'chomage_brut',
                max = chomage_brut_max,
                min = chomage_brut_min,
                ),
            ],
        period = "{}-01".format(year),
        parent1 = dict(
            birth = datetime.date(year - 40, 1, 1),
            ),
        )
    simulation = base.tax_benefit_system.new_scenario().init_single_entity(
        **scenario_args
        ).new_simulation(debug = True)

    chomage_brut = simulation.get_holder('chomage_brut').array
    chomage_net = simulation.calculate('chomage_net')

    inversion_reform = inversion_revenus.build_reform(base.tax_benefit_system)
    inverse_simulation = inversion_reform.new_scenario().init_single_entity(
        **scenario_args
        ).new_simulation(debug = True)

    inverse_simulation.get_holder('chomage_brut').delete_arrays()
    inverse_simulation.get_or_new_holder('chomage_net').array = chomage_net
    new_chomage_brut = inverse_simulation.calculate('chomage_brut')

    assert_near(new_chomage_brut, chomage_brut, absolute_error_margin = 0.1)


def test_chomage_net_to_chomage_brut():
    count = 101
    chomage_brut_max = 5000
    chomage_brut_min = 2000
    for year in range(2006, 2015):
        yield check_chomage_net_to_chomage_brut, count, chomage_brut_max, chomage_brut_min, year


def check_rstnet_to_rstbrut(count, rstbrut_max, rstbrut_min, year):
    scenario_args = dict(
        axes = [
            dict(
                count = count,
                name = 'retraite_brute',
                max = rstbrut_max,
                min = rstbrut_min,
                ),
            ],
        period = "{}-01".format(year),
        parent1 = dict(
            birth = datetime.date(year - 40, 1, 1),
            ),
        )

    simulation = base.tax_benefit_system.new_scenario().init_single_entity(
        **scenario_args
        ).new_simulation(debug = True)

    retraite_brute = simulation.get_holder('retraite_brute').array
    retraite_nette = simulation.calculate('retraite_nette')

    inversion_reform = inversion_revenus.build_reform(base.tax_benefit_system)
    inverse_simulation = inversion_reform.new_scenario().init_single_entity(
        **scenario_args
        ).new_simulation(debug = True)

    inverse_simulation.get_holder('retraite_brute').delete_arrays()
    inverse_simulation.get_or_new_holder('retraite_nette').array = retraite_nette
    new_rstbrut = inverse_simulation.calculate('retraite_brute')

    assert_near(new_rstbrut, retraite_brute, absolute_error_margin = 0.1)


def test_rstnet_to_rstbrut():
    count = 101
    rstbrut_max = 5000
    rstbrut_min = 0
    for year in range(2006, 2015):
        yield check_rstnet_to_rstbrut, count, rstbrut_max, rstbrut_min, year


def check_salaire_net_to_salaire_de_base(count, salaire_de_base_max, salaire_de_base_min, type_sal, year):
    period = periods.period("{}-01".format(year))
    scenario_args = dict(
        axes = [
            dict(
                count = count,
                name = 'salaire_de_base',
                max = salaire_de_base_max,
                min = salaire_de_base_min,
                ),
            ],
        period = period,
        parent1 = dict(
            birth = datetime.date(year - 40, 1, 1),
            type_sal = type_sal,
            ),
        )

    simulation = base.tax_benefit_system.new_scenario().init_single_entity(
        **scenario_args
        ).new_simulation()

    salaire_de_base = simulation.get_holder('salaire_de_base').array
    smic_horaire = simulation.legislation_at(period.start).cotsoc.gen.smic_h_b
    smic_mensuel = smic_horaire * 35 * 52 / 12
    brut = simulation.get_holder('salaire_de_base').array
    simulation.get_or_new_holder('contrat_de_travail').array = brut < smic_mensuel  # temps plein ou temps partiel
    simulation.get_or_new_holder('heures_remunerees_volume').array = brut // smic_horaire  # temps plein / partiel

    salaire_net = simulation.calculate('salaire_net')

    inversion_reform = inversion_revenus.build_reform(base.tax_benefit_system)
    inverse_simulation = inversion_reform.new_scenario().init_single_entity(
        **scenario_args
        ).new_simulation()

    inverse_simulation.get_holder('salaire_de_base').delete_arrays()
    inverse_simulation.get_or_new_holder('salaire_net').array = salaire_net
    inverse_simulation.get_or_new_holder('contrat_de_travail').array = brut < smic_mensuel  # temps plein / partiel
    inverse_simulation.get_or_new_holder('heures_remunerees_volume').array = (
        (brut // smic_horaire) * (brut < smic_mensuel)
        )
    new_salaire_de_base = inverse_simulation.calculate('salaire_de_base')
    assert_near(new_salaire_de_base, salaire_de_base, absolute_error_margin = 0.1,
        message = 'Failing test for type_sal={}'.format(type_sal))


def test_salaire_net_to_salaire_de_base():
    count = 101
    salaire_de_base_max = 5000
    salaire_de_base_min = 0
    for year in range(2006, 2015):
        for type_sal in [0, 1]:  # type_sal_enum._vars:   TODO: work on other categories of employee
            yield check_salaire_net_to_salaire_de_base, count, salaire_de_base_max, salaire_de_base_min, type_sal, year


if __name__ == '__main__':
    import logging
    import sys

    logging.basicConfig(level = logging.ERROR, stream = sys.stdout)
    # TOD0 test_chomage_net_to_chomage_brut,
    for test in (test_chomage_net_to_chomage_brut, test_rstnet_to_rstbrut, test_salaire_net_to_salaire_de_base):
        for function_and_arguments in test():
            function_and_arguments[0](*function_and_arguments[1:])
