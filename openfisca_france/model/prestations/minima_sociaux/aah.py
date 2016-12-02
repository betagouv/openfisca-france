# -*- coding: utf-8 -*-
from __future__ import division

from numpy import (maximum as max_, logical_not as not_, absolute as abs_, minimum as min_)

from openfisca_france.model.base import *  # noqa analysis:ignore

# TODO : Aujourd'hui, cette BR correspond uniquement au demandeur, pas au conjoint.
class aah_base_ressources(Variable):
    column = FloatCol
    label = u"Base ressources de l'allocation adulte handicapé"
    entity = Famille

    def function(self, simulation, period):
        period = period.this_month
        law = simulation.legislation_at(period.start)

        salaire_this_month = simulation.compute('salaire_imposable', period)
        demandeur_en_activite = self.filter_role(salaire_this_month, role = CHEF) > 0

        def assiette_conjoint(revenus_conjoint):
            return 0.9 * (1 - 0.2) * revenus_conjoint

        def assiette_demandeur(revenus_demandeur):
            smic_brut_annuel = 12 * law.cotsoc.gen.smic_h_b * law.cotsoc.gen.nb_heure_travail_mensuel
            tranche1 = min_(0.3 * smic_brut_annuel, revenus_demandeur)
            tranche2 = revenus_demandeur - tranche1
            return (1 - 0.8) * tranche1 + (1 - 0.4) * tranche2

        def base_ressource_eval_trim():
            aah_base_ressources_eval_trimestrielle = simulation.compute('aah_base_ressources_eval_trimestrielle', period)
            base_ressource_demandeur = self.filter_role(aah_base_ressources_eval_trimestrielle, role = CHEF)
            base_ressource_conjoint = self.filter_role(aah_base_ressources_eval_trimestrielle, role = PART)

            return assiette_demandeur(base_ressource_demandeur) + assiette_conjoint(base_ressource_conjoint)

        def base_ressource_eval_annuelle():
            aah_base_ressources_eval_annuelle = simulation.compute('aah_base_ressources_eval_annuelle', period)
            base_ressource_demandeur = self.filter_role(aah_base_ressources_eval_annuelle, role = CHEF)
            base_ressource_conjoint = self.filter_role(aah_base_ressources_eval_annuelle, role = PART)

            return assiette_demandeur(base_ressource_demandeur) + assiette_conjoint(base_ressource_conjoint)

        aah_base_ressource = (
            demandeur_en_activite * base_ressource_eval_trim() +
            not_(demandeur_en_activite) * base_ressource_eval_annuelle()
        )

        return period, aah_base_ressource


class aah_base_ressources_eval_trimestrielle(Variable):
    column = FloatCol
    label = u"Base de ressources de l'ASS pour un individu, évaluation trimestrielle"
    entity = Individu

    '''
        N'entrent pas en compte dans les ressources :
        L'allocation compensatrice tierce personne, les allocations familiales,
        l'allocation de logement, la retraite du combattant, les rentes viagères
        constituées en faveur d'une personne handicapée ou dans la limite d'un
        montant fixé à l'article D.821-6 du code de la sécurité sociale (1 830 €/an),
        lorsqu'elles ont été constituées par une personne handicapée pour elle-même.
        Le RMI (article R 531-10 du code de la sécurité sociale).
        A partir du 1er juillet 2007, votre Caf, pour le calcul de votre Aah,
        continue à prendre en compte les ressources de votre foyer diminuées de 20%.
        Notez, dans certaines situations, la Caf évalue forfaitairement vos
        ressources à partir de votre revenu mensuel.
    '''

    def function(individu, period):
        period = period.this_month
        three_previous_months = period.start.period('month', 3).offset(-3)
        last_year = period.last_year

        ressources_a_inclure = [
            'allocation_securisation_professionnelle',
            'bourse_recherche',
            'chomage_net',
            'gains_exceptionnels',
            'indemnites_chomage_partiel',
            'indemnites_journalieres_imposables',
            'indemnites_stage',
            'pensions_alimentaires_percues',
            'pensions_alimentaires_versees_individu',
            'pensions_invalidite',
            'prestation_compensatoire',
            'retraite_nette',
            'revenus_stage_formation_pro',
            'rsa_base_ressources_patrimoine_individu',
            'salaire_net',
            ]

        ressources = sum(
            [individu(ressource, options = [ADD]) for ressource in ressources_a_inclure]
            )


        def revenus_tns():
            revenus_auto_entrepreneur = individu('tns_auto_entrepreneur_benefice', three_previous_months, options = [ADD])

            # Les revenus TNS hors AE sont estimés en se basant sur le revenu N-1
            tns_micro_entreprise_benefice = individu('tns_micro_entreprise_benefice', last_year) * 3 / 12
            tns_benefice_exploitant_agricole = individu('tns_benefice_exploitant_agricole', last_year) * 3 / 12
            tns_autres_revenus = individu('tns_autres_revenus', last_year) * 3 / 12

            return revenus_auto_entrepreneur + tns_micro_entreprise_benefice + tns_benefice_exploitant_agricole + tns_autres_revenus

        return period, (ressources + revenus_tns()) * 4


class aah_base_ressources_eval_annuelle(Variable):
    column = FloatCol
    label = u"Base de ressources de l'AAH pour un individu, évaluation annuelle"
    entity = Individu

    def function(self, simulation, period):
        period = period.this_month
        return period, simulation.calculate('revenu_activite', period.n_2) + simulation.calculate('revenu_assimile_pension', period.n_2)


class aah_eligible(Variable):
    column = BoolCol
    label = u"Eligibilité à l'Allocation adulte handicapé"
    entity = Individu

    '''
        Allocation adulte handicapé

        Conditions liées au handicap
        La personne doit être atteinte d’un taux d’incapacité permanente :
        - d’au moins 80 %,
        - ou compris entre 50 et 79 %. Dans ce cas, elle doit remplir deux conditions
        supplémentaires : être dans l’impossibilité de se procurer un emploi compte
        tenu de son handicap et ne pas avoir travaillé depuis au moins 1 an
        Condition de résidence
        L'AAH peut être versée aux personnes résidant en France métropolitaine ou
         dans les départements d'outre-mer ou à Saint-Pierre et Miquelon de façon permanente.
         Les personnes de nationalité étrangère doivent être en possession d'un titre de séjour
         régulier ou être titulaire d'un récépissé de renouvellement de titre de séjour.
        Condition d'âge
        Age minimum : Le demandeur ne doit plus avoir l'âge de bénéficier de l'allocation d'éducation de l'enfant
        handicapé, c'est-à-dire qu'il doit être âgé :
        - de plus de vingt ans,
        - ou de plus de seize ans, s'il ne remplit plus les conditions pour ouvrir droit aux allocations familiales.
        Pour les montants http://www.handipole.org/spip.php?article666

        Âge max_
        Le versement de l'AAH prend fin à partir de l'âge minimum légal de départ à la retraite en cas d'incapacité
        de 50 % à 79 %. À cet âge, le bénéficiaire bascule dans le régime de retraite pour inaptitude.
        En cas d'incapacité d'au moins 80 %, une AAH différentielle (c'est-à-dire une allocation mensuelle réduite)
        peut être versée au-delà de l'âge minimum légal de départ à la retraite en complément d'une retraite inférieure
        au minimum vieillesse.
    '''

    def function(self, simulation, period):
        period = period.this_month
        law = simulation.legislation_at(period.start).prestations
        taux_incapacite = simulation.calculate('taux_incapacite', period)
        age = simulation.calculate('age', period)
        autonomie_financiere = simulation.calculate('autonomie_financiere', period)
        eligible_aah = (
            (taux_incapacite >= 0.5) *
            (age <= law.minima_sociaux.aah.age_legal_retraite) *
            ((age >= law.minima_sociaux.aah.age_minimal) + ((age >= 16) * (autonomie_financiere)))
            )

        return period, eligible_aah
    # TODO: dated_function : avant 2008, il fallait ne pas avoir travaillé pendant les 12 mois précédant la demande.


class aah_non_calculable(Variable):
    column = EnumCol(
        enum = Enum([
            u"",
            u"intervention_CDAPH_necessaire"
        ]),
        default = 0
    )
    entity = Individu
    label = u"AAH non calculable"

    def function(individu, period):
        period = period.this_month
        taux_incapacite = individu('taux_incapacite', period)
        aah_eligible = individu('aah_eligible', period)

        return period, aah_eligible  * (taux_incapacite < 0.8) * False


class aah_base(Variable):
    calculate_output = calculate_output_add
    column = FloatCol
    label = u"Montant de l'Allocation adulte handicapé (hors complément) pour un individu, mensualisée"
    entity = Individu

    def function(individu, period, legislation):
        period = period.this_month
        law = legislation(period).prestations

        aah_eligible = individu('aah_eligible', period)
        aah_non_calculable = individu('aah_non_calculable', period)
        aah_base_ressources = individu.famille('aah_base_ressources', period) / 12
        en_couple = individu.famille('en_couple', period)
        af_nbenf = individu.famille('af_nbenf', period)
        montant_max = law.minima_sociaux.aah.montant
        plaf_ress_aah = montant_max * (1 + en_couple + law.minima_sociaux.aah.tx_plaf_supp * af_nbenf)
        montant_aah = min_(plaf_ress_aah - aah_base_ressources, montant_max) # Le montant de l'AAH est plafonné au montant de base.
        montant_aah = max_(montant_aah, 0)

        # Pour le moment, on ne neutralise pas l'aah en cas de non calculabilité pour pouvoir tester
        return period, aah_eligible *  montant_aah # * not_(aah_non_calculable)


class aah(Variable):
    calculate_output = calculate_output_add
    column = FloatCol
    label = u"Allocation adulte handicapé (Individu) mensualisée"
    entity = Individu

    def function(self, simulation, period):
        period = period.this_month

        aah_base = simulation.calculate('aah_base', period)
        # caah
        # mva

        return period, aah_base


class caah(DatedVariable):
    calculate_output = calculate_output_add
    column = FloatCol
    label = u"Complément d'allocation adulte handicapé (mensualisé)"
    entity = Individu
    '''
        Complément d'allocation adulte handicapé : complément de ressources ou majoration vie autonome.

        Complément de ressources

        Pour bénéficier du complément de ressources, l’intéressé doit remplir les conditions
        suivantes :
        - percevoir l’allocation aux adultes handicapés à taux normal ou en
           complément d’une pension d’invalidité, d’une pension de vieillesse ou
           d’une rente accident du travail ;
        - avoir un taux d’incapacité égal ou supérieur à 80 % ;
        - avoir une capacité de travail, appréciée par la commission des droits et
           de l’autonomie (CDAPH) inférieure à 5 % du fait du handicap ;
        - ne pas avoir perçu de revenu à caractère professionnel depuis un an à la date
           du dépôt de la demande de complément ;
        - disposer d’un logement indépendant.
        A noter : une personne hébergée par un particulier à son domicile n’est pas
        considérée disposer d’un logement indépendant, sauf s’il s’agit de son conjoint,
        de son concubin ou de la personne avec laquelle elle est liée par un pacte civil
        de solidarité.

        Le complément de ressources est destiné aux personnes handicapées dans l’incapacité de
        travailler. Il est égal à la différence entre la garantie de ressources pour les personnes
        handicapées (GRPH) et l’AAH.

        Majoration pour la vie autonome

        La majoration pour la vie autonome est destinée à permettre aux personnes, en capacité de travailler et
        au chômage en raison de leur handicap, de pourvoir faire face à leur dépense de logement.

        Conditions d'attribution
        La majoration pour la vie autonome est versée automatiquement aux personnes qui remplissent les conditions
        suivantes :
        - percevoir l'AAH à taux normal ou en complément d'un avantage vieillesse ou d'invalidité ou d'une rente
        accident du travail,
        - avoir un taux d'incapacité au moins égal à 80 %,
        - disposer d'un logement indépendant,
        - bénéficier d'une aide au logement (aide personnelle au logement, ou allocation de logement sociale ou
        familiale), comme titulaire du droit, ou comme conjoint, concubin ou partenaire lié par
        un Pacs au titulaire du droit,
        - ne pas percevoir de revenu d'activité à caractère professionnel propre.

        Choix entre la majoration ou la garantie de ressources
        La majoration pour la vie autonome n'est pas cumulable avec la garantie de ressources pour les personnes
        handicapées.
        La personne qui remplit les conditions d'octroi de ces deux avantages doit choisir de bénéficier de l'un ou de
        l'autre.
    '''

    @dated_function(start = date(2005, 7, 1))
    def function_2005_07_01(self, simulation, period):
        period = period.this_month
        law = simulation.legislation_at(period.start).prestations

        garantie_ressources = law.minima_sociaux.caah.garantie_ressources
        aah_montant = law.minima_sociaux.aah.montant

        aah = simulation.calculate('aah', period)
        asi_eligibilite = simulation.calculate('asi_eligibilite', period)
        asi_holder = simulation.compute('asi', period)  # montant asi de la famille
        asi = self.cast_from_entity_to_roles(asi_holder)  # attribué à tous les membres de la famille
        benef_asi = (asi_eligibilite * (asi > 0))
        al_holder = simulation.compute('aide_logement_montant', period)  # montant allocs logement de la famille
        al = self.cast_from_entity_to_roles(al_holder)  # attribué à tout individu membre de la famille

        elig_cpl = ((aah > 0) | (benef_asi > 0))
        # TODO: & logement indépendant & inactif 12 derniers mois
        # & capa de travail < 5% & taux d'incapacité >= 80%
        compl_ress = elig_cpl * max_(garantie_ressources - aah_montant, 0)

        elig_mva = (al > 0) * ((aah > 0) | (benef_asi > 0))
        # TODO: & logement indépendant & pas de revenus professionnels
        # propres & capa de travail < 5% & taux d'incapacité >= 80%
        mva = 0.0 * elig_mva  # TODO: rentrer mva dans paramètres. mva (mensuelle) = 104,77 en 2015, était de 101,80 en 2006, et de 119,72 en 2007

        return period, max_(compl_ress, mva)

    @dated_function(start = date(2002, 1, 1), stop = date(2005, 6, 30))  # TODO FIXME start date
    def function_2005_06_30(self, simulation, period):
        period = period.this_month
        law = simulation.legislation_at(period.start).prestations

        cpltx = law.minima_sociaux.caah.cpltx
        aah_montant = law.minima_sociaux.aah.montant

        aah = simulation.calculate('aah', period)
        asi_eligibilite = simulation.calculate('asi_eligibilite', period)
        asi_holder = simulation.compute('asi', period)  # montant asi de la famille
        asi = self.cast_from_entity_to_roles(asi_holder)  # attribué à tous les membres de la famille
        benef_asi = (asi_eligibilite * (asi > 0))
        al_holder = simulation.compute('aide_logement_montant', period)  # montant allocs logement de la famille
        al = self.cast_from_entity_to_roles(al_holder)  # attribué à tout individu membre de la famille

        elig_ancien_caah = (al > 0) * ((aah > 0) | (benef_asi > 0))  # TODO: & invalidité >= 80%  & logement indépendant
        ancien_caah = cpltx * aah_montant * elig_ancien_caah
        # En fait le taux cpltx perdure jusqu'en 2008

        return period, ancien_caah

class mva(Variable):
    entity = Individu
    column = FloatCol
    label = u"Majoration pour la vie autonome"

class pch(Variable):
    entity = Individu
    column = FloatCol
    label = u"Prestation de compensation du handicap"
