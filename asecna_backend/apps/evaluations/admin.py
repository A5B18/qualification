"""Admin pour l'app evaluations."""

from django.contrib import admin
from .models import Question, Exam, ExamSession, Answer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    # `question_kind` ne filtre plus rien : toute question est un QCM. On
    # affiche en revanche le nombre d'options, qui dit si la question est
    # exploitable.
    list_display = ('text_short', 'question_type', 'options_count',
                    'difficulty', 'points', 'is_active')
    list_filter = ('question_type', 'difficulty', 'is_active')
    search_fields = ('text',)

    def text_short(self, obj):
        return obj.text[:80]
    text_short.short_description = 'Énoncé'

    def options_count(self, obj):
        return len(obj.clean_options)
    options_count.short_description = 'Options'


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'training', 'exam_status', 'passing_score', 'created_by')
    list_filter = ('exam_status',)
    filter_horizontal = ('questions',)


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ('agent', 'exam', 'session_status', 'score', 'is_passed', 'started_at')
    list_filter = ('session_status', 'is_passed')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('session', 'question', 'is_correct', 'answered_at')
    list_filter = ('is_correct',)
