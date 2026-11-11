"""
Tests unitaires pour l'app arcep.

Couvre :
- ARCEPBook : unicité par agent (OneToOne)
- ARCEPEntry : création d'entrées d'activité
- ARCEPSignature : signature périodique du chef d'unité
"""

import datetime
from django.test import TestCase
from django.db import IntegrityError

from apps.accounts.models import User
from apps.arcep.models import ARCEPBook, ARCEPEntry, ARCEPSignature


def make_user(matricule, email, admin=False):
    kwargs = dict(
        matricule=matricule, email=email,
        password='Test123!', first_name='Test', last_name='User',
    )
    if admin:
        return User.objects.create_superuser(**kwargs)
    return User.objects.create_user(**kwargs)


class ARCEPBookTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0210', 'arcep@asecna.com')

    def test_create_arcep_book(self):
        book = ARCEPBook.objects.create(agent=self.agent)
        self.assertEqual(book.agent, self.agent)
        self.assertTrue(book.is_active)
        self.assertIsNotNone(book.opened_at)

    def test_one_book_per_agent(self):
        """Un agent ne peut avoir qu'un seul carnet ARCEP (OneToOne)."""
        ARCEPBook.objects.create(agent=self.agent)
        with self.assertRaises(IntegrityError):
            ARCEPBook.objects.create(agent=self.agent)

    def test_arcep_book_str(self):
        book = ARCEPBook.objects.create(agent=self.agent)
        s = str(book)
        self.assertIn('Carnet ARCEP', s)

    def test_book_can_be_deactivated(self):
        book = ARCEPBook.objects.create(agent=self.agent)
        book.is_active = False
        book.save()
        book.refresh_from_db()
        self.assertFalse(book.is_active)


class ARCEPEntryTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0211', 'arcep_e@asecna.com')
        self.book = ARCEPBook.objects.create(agent=self.agent)
        self.today = datetime.date.today()

    def test_create_entry(self):
        entry = ARCEPEntry.objects.create(
            book=self.book,
            entry_date=self.today,
            activity='Contrôle de la position TWR de 08h à 14h',
            duration_hours=6.0,
        )
        self.assertEqual(entry.book, self.book)
        self.assertEqual(float(entry.duration_hours), 6.0)

    def test_create_entry_with_notes(self):
        entry = ARCEPEntry.objects.create(
            book=self.book,
            entry_date=self.today,
            activity='Formation sur le radar primaire',
            duration_hours=3.5,
            notes='RAS — formation théorique complète.',
        )
        self.assertEqual(entry.notes, 'RAS — formation théorique complète.')

    def test_entry_str(self):
        entry = ARCEPEntry.objects.create(
            book=self.book,
            entry_date=self.today,
            activity='Test str',
            duration_hours=1.0,
        )
        s = str(entry)
        self.assertIn(str(self.today), s)

    def test_multiple_entries_per_book(self):
        ARCEPEntry.objects.create(book=self.book, entry_date=self.today,
                                   activity='Activité A', duration_hours=4.0)
        yesterday = self.today - datetime.timedelta(days=1)
        ARCEPEntry.objects.create(book=self.book, entry_date=yesterday,
                                   activity='Activité B', duration_hours=8.0)
        self.assertEqual(self.book.entries.count(), 2)


class ARCEPSignatureTest(TestCase):

    def setUp(self):
        self.agent = make_user('ASE-2024-0212', 'arcep_s@asecna.com')
        self.chief = make_user('ASE-2024-0213', 'chief_s@asecna.com', admin=True)
        self.book = ARCEPBook.objects.create(agent=self.agent)
        self.today = datetime.date.today()
        self.start = self.today.replace(day=1)
        self.end = self.today

    def test_create_signature(self):
        sig = ARCEPSignature.objects.create(
            book=self.book,
            unit_chief=self.chief,
            period_start=self.start,
            period_end=self.end,
            comment='Carnet vérifié et signé — RAS.',
        )
        self.assertEqual(sig.unit_chief, self.chief)
        self.assertEqual(sig.book, self.book)
        self.assertEqual(sig.comment, 'Carnet vérifié et signé — RAS.')

    def test_signature_str(self):
        sig = ARCEPSignature.objects.create(
            book=self.book,
            unit_chief=self.chief,
            period_start=self.start,
            period_end=self.end,
        )
        s = str(sig)
        self.assertIn(str(self.start), s)
        self.assertIn(str(self.end), s)

    def test_multiple_signatures_per_book(self):
        """Un carnet peut avoir plusieurs signatures (périodes différentes)."""
        ARCEPSignature.objects.create(
            book=self.book, unit_chief=self.chief,
            period_start=datetime.date(2024, 1, 1),
            period_end=datetime.date(2024, 1, 31),
        )
        ARCEPSignature.objects.create(
            book=self.book, unit_chief=self.chief,
            period_start=datetime.date(2024, 2, 1),
            period_end=datetime.date(2024, 2, 29),
        )
        self.assertEqual(self.book.signatures.count(), 2)
