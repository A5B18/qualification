"""URLs pour evaluations."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestionViewSet, ExamViewSet, ExamSessionViewSet

router = DefaultRouter()
router.register(r'questions', QuestionViewSet,    basename='question')
router.register(r'exams',     ExamViewSet,        basename='exam')
router.register(r'sessions',  ExamSessionViewSet, basename='session')
urlpatterns = [path('', include(router.urls))]
