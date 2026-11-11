"""
Tests unitaires pour l'app units.

Couvre :
- Unit : création, unicité du code, types valides
- Ordering par code
- __str__

Utilise les types réels de la section MIRE-Informatique (COM, OTHER).
"""

from django.test import TestCase
from django.db import IntegrityError

from apps.units.models import Unit


class UnitModelTest(TestCase):

    def test_create_unit_cns(self):
        """Création d'une unité CNS (type COM)."""
        u = Unit.objects.create(
            code='MIRE-CNS',
            name='CNS (Communication, Navigation, Surveillance)',
            unit_type=Unit.UnitType.COM,
            location='Section MIRE-Informatique',
            country='Sénégal',
        )
        self.assertEqual(u.code, 'MIRE-CNS')
        self.assertEqual(u.unit_type, 'COM')
        self.assertTrue(u.is_active)

    def test_create_unit_rsi_mto(self):
        """Création d'une unité RSI/MTO (type OTHER)."""
        u = Unit.objects.create(
            code='MIRE-RSI-MTO',
            name='RSI/MTO (Réseaux et Systèmes d\'Information / Météorologie)',
            unit_type=Unit.UnitType.OTHER,
            location='Section MIRE-Informatique',
            country='Sénégal',
        )
        self.assertEqual(u.unit_type, 'OTHER')

    def test_create_unit_qip(self):
        """Création de l'unité QIP (Qualification et Intégration du Personnel)."""
        u = Unit.objects.create(
            code='MIRE-QIP',
            name='QIP (Qualification et Intégration du Personnel)',
            unit_type=Unit.UnitType.OTHER,
            location='Section MIRE-Informatique',
            country='Sénégal',
        )
        self.assertEqual(u.code, 'MIRE-QIP')
        self.assertTrue(u.is_active)

    def test_create_unit_elb(self):
        """Création de l'unité ELB (Énergie et Balisage)."""
        u = Unit.objects.create(
            code='MIRE-ELB',
            name='ELB (Énergie et Balisage)',
            unit_type=Unit.UnitType.OTHER,
            location='Section MIRE-Informatique',
        )
        self.assertEqual(u.code, 'MIRE-ELB')

    def test_unit_str(self):
        u = Unit.objects.create(
            code='MIRE-CNS',
            name='CNS Communication',
            unit_type=Unit.UnitType.COM,
        )
        s = str(u)
        self.assertIn('MIRE-CNS', s)
        self.assertIn('CNS', s)

    def test_unit_code_unique(self):
        Unit.objects.create(code='MIRE-CNS', name='CNS', unit_type=Unit.UnitType.COM)
        with self.assertRaises(IntegrityError):
            Unit.objects.create(code='MIRE-CNS', name='Doublon', unit_type=Unit.UnitType.COM)

    def test_unit_is_active_by_default(self):
        u = Unit.objects.create(
            code='MIRE-ELB', name='ELB', unit_type=Unit.UnitType.OTHER,
        )
        self.assertTrue(u.is_active)

    def test_unit_can_be_deactivated(self):
        u = Unit.objects.create(
            code='MIRE-QIP', name='QIP', unit_type=Unit.UnitType.OTHER,
            is_active=False,
        )
        self.assertFalse(u.is_active)

    def test_unit_ordering_by_code(self):
        Unit.objects.create(code='MIRE-RSI-MTO', name='RSI', unit_type=Unit.UnitType.OTHER)
        Unit.objects.create(code='MIRE-CNS',     name='CNS', unit_type=Unit.UnitType.COM)
        codes = list(Unit.objects.values_list('code', flat=True))
        self.assertEqual(codes, sorted(codes))

    def test_all_four_mire_units(self):
        """Les 4 unités MIRE-Informatique peuvent coexister."""
        Unit.objects.create(code='MIRE-CNS',     name='CNS',     unit_type=Unit.UnitType.COM)
        Unit.objects.create(code='MIRE-RSI-MTO', name='RSI/MTO', unit_type=Unit.UnitType.OTHER)
        Unit.objects.create(code='MIRE-QIP',     name='QIP',     unit_type=Unit.UnitType.OTHER)
        Unit.objects.create(code='MIRE-ELB',     name='ELB',     unit_type=Unit.UnitType.OTHER)
        self.assertEqual(Unit.objects.count(), 4)
