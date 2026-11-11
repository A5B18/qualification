"""Admin pour l'app training."""

from django.contrib import admin
from .models import Specialty, Training, Course, Internship


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ('title', 'training_type', 'specialty', 'duration_days', 'passing_score', 'is_active')
    list_filter = ('training_type', 'is_active')
    search_fields = ('title',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'training', 'instructor', 'is_published', 'order')
    list_filter = ('is_published',)
    search_fields = ('title', 'training__title')


@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ('agent', 'internship_type', 'start_date', 'end_date', 'is_passed')
    list_filter = ('internship_type', 'is_passed')
