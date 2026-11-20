"""
Le QCM devient le seul format de question.

Deux effets :

1. `question_kind` ne propose plus que MCQ (les choix 'TF' et 'OPEN' sont
   retires), et `correct_answer` rappelle qu'elle doit figurer parmi les
   options.

2. Les questions deja enregistrees dans un autre format sont reprises :

   - Vrai/Faux : c'est un QCM a deux options. On lui pose les options
     « Vrai » / « Faux » et on aligne `correct_answer` sur l'une des deux.
   - Reponse ouverte : il n'existe aucune proposition dont on puisse faire un
     QCM, et en fabriquer serait inventer le bareme. Ces questions sont donc
     retirees de la banque (`is_active=False`) et detachees des examens, pour
     qu'aucun candidat ne recoive un enonce sans choix et que le bareme des
     examens reste coherent. Leur enonce reste en base : un evaluateur peut
     les reecrire en QCM et les reactiver.
"""

from django.db import migrations, models


TRUE_WORDS = {'vrai', 'true', 'oui', 'v', '1'}


def to_mcq(apps, schema_editor):
    Question = apps.get_model('evaluations', 'Question')

    # ── Vrai/Faux → QCM a deux options ───────────────────────────────────────
    for question in Question.objects.filter(question_kind='TF'):
        answer = (question.correct_answer or '').strip().casefold()
        question.options = ['Vrai', 'Faux']
        question.correct_answer = 'Vrai' if answer in TRUE_WORDS else 'Faux'
        question.question_kind = 'MCQ'
        question.save(update_fields=['options', 'correct_answer', 'question_kind'])

    # ── Reponse ouverte → retiree de la banque et des examens ────────────────
    for question in Question.objects.filter(question_kind='OPEN'):
        question.exams.clear()
        question.question_kind = 'MCQ'
        question.is_active = False
        question.save(update_fields=['question_kind', 'is_active'])


def noop(apps, schema_editor):
    """
    Pas de retour en arriere : on ne sait pas distinguer un QCM d'origine
    d'un ancien Vrai/Faux converti. La migration inverse se contente de
    rouvrir les choix du champ (AlterField, reversible par nature).
    """


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0002_answer_corrected_at_answer_corrected_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='question_kind',
            field=models.CharField(
                choices=[('MCQ', 'QCM (choix multiple)')],
                default='MCQ',
                help_text='QCM — seul format accepté.',
                max_length=10,
                verbose_name='Format',
            ),
        ),
        migrations.AlterField(
            model_name='question',
            name='correct_answer',
            field=models.TextField(
                help_text="Doit être l'une des options proposées.",
                verbose_name='Bonne réponse',
            ),
        ),
        migrations.RunPython(to_mcq, noop),
    ]
