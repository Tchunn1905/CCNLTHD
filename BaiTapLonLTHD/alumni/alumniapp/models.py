from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from ckeditor.fields import RichTextField


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        LECTURER = 'LECTURER', 'Lecturer'
        ALUMNI = 'ALUMNI', 'Alumni'

    role = models.CharField(max_length=10, choices=Role.choices)
    avatar = models.ImageField(upload_to='avatars/%Y/%m', null=True)
    cover_image = models.ImageField(upload_to='covers/%Y/%m', null=True)
    student_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\d{8}$',
            message='Mã số sinh viên phải là 8 chữ số'
        )]
    )
    is_verified = models.BooleanField(default=False)
    password_change_deadline = models.DateTimeField(null=True, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.role == self.Role.LECTURER and not self.password_change_deadline:
            self.password_change_deadline = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

        # Kiểm tra mã sinh viên khi đăng ký
        if self.role == self.Role.ALUMNI and self.student_id:
            self.is_verified = False  # Chờ quản trị viên xác nhận

        super().save(*args, **kwargs)

class Post(models.Model):
    class PostType(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular Post'
        SURVEY = 'SURVEY', 'Survey'
        EVENT = 'EVENT', 'Event'

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = RichTextField()
    post_type = models.CharField(max_length=10, choices=PostType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comments_locked = models.BooleanField(default=False)
    image = models.ImageField(upload_to='posts/%Y/%m', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = RichTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent_comment = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['created_at']


class Reaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = 'LIKE', 'Like'
        HEART = 'HEART', 'Heart'
        HAHA = 'HAHA', 'Haha'

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=ReactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']


class Survey(models.Model):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name='survey')
    title = models.CharField(max_length=200)
    description = RichTextField()
    end_date = models.DateTimeField()
    is_anonymous = models.BooleanField(default=False)

    @property
    def is_active(self):
        return timezone.now() <= self.end_date


class SurveyQuestion(models.Model):
    class QuestionType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        SINGLE_CHOICE = 'SINGLE', 'Single Choice'
        MULTIPLE_CHOICE = 'MULTIPLE', 'Multiple Choice'

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_text = RichTextField()
    question_type = models.CharField(max_length=10, choices=QuestionType.choices)
    required = models.BooleanField(default=True)
    order = models.IntegerField(default=0)


class SurveyOption(models.Model):
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=200)
    order = models.IntegerField(default=0)


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer_text = models.TextField(null=True, blank=True)
    selected_options = models.ManyToManyField(SurveyOption, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)


class Group(models.Model):
    name = models.CharField(max_length=100)
    description = RichTextField()
    members = models.ManyToManyField(User, related_name='groups_custom')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        POST = 'POST', 'Post Notification'
        COMMENT = 'COMMENT', 'Comment Notification'
        EVENT = 'EVENT', 'Event Notification'
        SYSTEM = 'SYSTEM', 'System Notification'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = RichTextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_at']