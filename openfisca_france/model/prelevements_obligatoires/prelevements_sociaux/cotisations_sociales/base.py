# -*- coding: utf-8 -*-

from openfisca_france.model.revenus.activite.salarie import type_sal_enum

from openfisca_core.formula_helpers import switch

def apply_bareme_for_relevant_type_sal(
        bareme_by_type_sal_name,
        bareme_name,
        type_sal,
        base,
        plafond_securite_sociale,
        round_base_decimals = 2,
        ):
    for parameter in [bareme_by_type_sal_name, bareme_name, type_sal, base, plafond_securite_sociale]:
        assert parameter is not None

    def iter_cotisations():
        for type_sal_name, type_sal_index in type_sal_enum:
            if type_sal_name not in bareme_by_type_sal_name:  # to deal with public_titulaire_militaire
                continue
            bareme = bareme_by_type_sal_name[type_sal_name].get(bareme_name)  # TODO; should have better warnings
            if bareme is not None:
                yield bareme.calc(
                    base * (type_sal == type_sal_index),
                    factor = plafond_securite_sociale,
                    round_base_decimals = round_base_decimals,
                    )
    return - sum(iter_cotisations())


def apply_bareme(simulation, period, cotisation_type = None, bareme_name = None, variable_name = None):
    # period = period.this_month
    def compute_for(_period):
        return compute_cotisation(
            simulation,
            _period,
            cotisation_type = cotisation_type,
            bareme_name = bareme_name,
            )

    return switch(
            simulation.calculate('cotisation_sociale_mode_recouvrement', period),
            {   # anticipé
                0: compute_cotisation_anticipee(
                    simulation,
                    period,
                    compute_for,
                    variable_name,
                    ),
                # en fin d'année
                1: compute_cotisation_annuelle(
                    period,
                    compute_for)
                },
            )


def compute_cotisation_anticipee(simulation, period, compute_for, variable_name=None):
    if period.start.month < 12:
        return compute_for(period.this_month)

    if period.start.month == 12:
        assert variable_name is not None
        _period = period.start\
                        .offset('first-of', 'month')\
                        .offset(-11, 'month')\
                        .period('month', 11)
        # December variable_name depends on variable_name in the past 11 months.
        # We need to explicitly allow this recursion.
        cumul = simulation.calculate_add(variable_name, _period, max_nb_cycles = 1)
        return compute_for(period.this_year) - cumul


def compute_cotisation_annuelle(period, compute_for):
    if period.start.month < 12:
        return 0
    if period.start.month == 12:
        return compute_for(period.this_year)


def compute_cotisation(simulation, period, cotisation_type = None, bareme_name = None):

    assert cotisation_type is not None
    law = simulation.legislation_at(period.start)
    if cotisation_type == "employeur":
        bareme_by_type_sal_name = law.cotsoc.cotisations_employeur
    elif cotisation_type == "salarie":
        bareme_by_type_sal_name = law.cotsoc.cotisations_salarie
    assert bareme_name is not None

    assiette_cotisations_sociales = simulation.calculate_add('assiette_cotisations_sociales', period)
    plafond_securite_sociale = simulation.calculate_add('plafond_securite_sociale', period)
    type_sal = simulation.calculate('type_sal', period)

    cotisation = apply_bareme_for_relevant_type_sal(
        bareme_by_type_sal_name = bareme_by_type_sal_name,
        bareme_name = bareme_name,
        base = assiette_cotisations_sociales,
        plafond_securite_sociale = plafond_securite_sociale,
        type_sal = type_sal,
        )
    return cotisation


