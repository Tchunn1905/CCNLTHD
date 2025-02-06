from django.contrib import admin
from django import forms
from django.db.models import Count
from django.template.response import TemplateResponse
from django.utils.html import mark_safe
from .models import User, Post, Comment, Reaction, Survey, SurveyQuestion, SurveyOption, SurveyResponse, Group
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.urls import path
from django.db.models.functions import TruncMonth, TruncYear, TruncQuarter
from django.http import JsonResponse
import json


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'student_id', 'is_verified', 'date_joined')
    list_filter = ('role', 'is_verified', 'date_joined')
    search_fields = ('username', 'email', 'student_id')
    ordering = ('-date_joined',)

class PostForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget)
    class Meta:
        model =Post
        fields = '__all__'


class CommentInline(admin.StackedInline):
    model = Comment
    pk_name = 'post'


class ReactInline(admin.StackedInline):
    model = Reaction
    pk_name = 'post'


class PostAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('/static/css/main.css', )
        }

    form = PostForm
    list_display = ('author', 'post_type', 'created_at', 'comments_locked')
    list_filter = ('post_type', 'created_at', 'comments_locked')
    search_fields = ('content', 'author__username')
    ordering = ('-created_at',)
    inlines = (CommentInline, ReactInline)
    readonly_fields = ['avatar']

    def avatar(self, Post):
        if Post:
            return mark_safe(
                '<img src="/static/{url}" width="120" />' \
                    .format(url=Post.image.name)
            )

class CommentForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget)
    class Meta:
        model = Comment
        fields = '__all__'

class CommentAdmin(admin.ModelAdmin):
    form = CommentForm
    list_display = ('author', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username')
    ordering = ('-created_at',)


class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('user__username',)


class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'end_date', 'is_anonymous')
    list_filter = ('end_date', 'is_anonymous')
    search_fields = ('title', 'description')


class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ('survey', 'question_text', 'question_type', 'required')
    list_filter = ('question_type', 'required')
    search_fields = ('question_text',)


class SurveyOptionAdmin(admin.ModelAdmin):
    list_display = ('question', 'option_text', 'order')
    search_fields = ('option_text',)


class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('survey', 'user', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('user__username',)


class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    filter_horizontal = ('members',)

class PostAdminSite(admin.AdminSite):
    site_header = 'HE THONG MANG XA HOI CUU SINH VIEN'

    def get_urls(self):
        return [
            path('post-stats/', self.post_stats)
        ] + super().get_urls()

    def post_stats(self, request):
        # Helper function to format data
        def format_data(queryset, key):
            return [
                {'label': item[key].strftime('%Y-%m' if key == 'month' else '%Y-%m-%d' if key == 'quarter' else '%Y'),
                 'count': item['count']}
                for item in queryset]

        # Get posts statistics
        posts_by_month = format_data(
            Post.objects.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month'),
            'month'
        )

        posts_by_quarter = format_data(
            Post.objects.annotate(quarter=TruncQuarter('created_at'))
            .values('quarter')
            .annotate(count=Count('id'))
            .order_by('quarter'),
            'quarter'
        )

        posts_by_year = format_data(
            Post.objects.annotate(year=TruncYear('created_at'))
            .values('year')
            .annotate(count=Count('id'))
            .order_by('year'),
            'year'
        )

        # Get users statistics
        users_by_month = format_data(
            User.objects.annotate(month=TruncMonth('date_joined'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month'),
            'month'
        )

        users_by_quarter = format_data(
            User.objects.annotate(quarter=TruncQuarter('date_joined'))
            .values('quarter')
            .annotate(count=Count('id'))
            .order_by('quarter'),
            'quarter'
        )

        users_by_year = format_data(
            User.objects.annotate(year=TruncYear('date_joined'))
            .values('year')
            .annotate(count=Count('id'))
            .order_by('year'),
            'year'
        )

        context = {
            'posts_by_month': json.dumps(posts_by_month),
            'posts_by_quarter': json.dumps(posts_by_quarter),
            'posts_by_year': json.dumps(posts_by_year),
            'users_by_month': json.dumps(users_by_month),
            'users_by_quarter': json.dumps(users_by_quarter),
            'users_by_year': json.dumps(users_by_year),
        }

        return TemplateResponse(request, 'admin/post-stats.html', context)

admin_site = PostAdminSite('myalumniapp')


admin_site.register(User, UserAdmin)
admin_site.register(Post, PostAdmin)
admin_site.register(Comment, CommentAdmin)
admin_site.register(Reaction, ReactionAdmin)
admin_site.register(Survey, SurveyAdmin)
admin_site.register(SurveyQuestion, SurveyQuestionAdmin)
admin_site.register(SurveyOption, SurveyOptionAdmin)
admin_site.register(SurveyResponse, SurveyResponseAdmin)
admin_site.register(Group, GroupAdmin)

