from django.contrib import admin
from django.urls import path, include
from . import views
from .admin import admin_site
from rest_framework.routers import DefaultRouter
from .views import (UserViewSet, PostViewSet, CommentViewSet,
                   SurveyViewSet, GroupViewSet)

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('posts', PostViewSet)
router.register('comments', CommentViewSet)
router.register('surveys', SurveyViewSet)
router.register('groups', GroupViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin_site.urls)
]
