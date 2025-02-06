from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import PermissionDenied

from .models import (
    User, Post, Comment, Reaction, Survey,
    SurveyResponse, Group, Notification
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, PostSerializer,
    CommentSerializer, ReactionSerializer, SurveySerializer,
    SurveyResponseSerializer, GroupSerializer, NotificationSerializer,
    GroupMembershipSerializer, NotificationBulkCreateSerializer
)


class IsAdminOrLecturerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in [User.Role.ADMIN, User.Role.LECTURER]


class AuthViewSet(viewsets.ViewSet):
    permission_classes = []

    @action(detail=False, methods=['post'])
    def alumni_register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(role=User.Role.ALUMNI)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        user = request.user
        if user.role == User.Role.LECTURER:
            if user.password_change_deadline and timezone.now() > user.password_change_deadline:
                return Response(
                    {"error": "Password change deadline has passed. Contact admin."},
                    status=status.HTTP_403_FORBIDDEN
                )
            user.password_change_deadline = None
            user.save()
        return Response({"message": "Password changed successfully"})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def create_lecturer(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(
                role=User.Role.LECTURER,
                password='ou@123'
            )
            # Gửi email thông báo
            send_mail(
                'Tài khoản giảng viên mới',
                f'Tài khoản của bạn đã được tạo.\nTên đăng nhập: {user.username}\nMật khẩu: ou@123\n'
                f'Vui lòng đổi mật khẩu trong vòng 24 giờ.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify_alumni(self, request, pk=None):
        user = self.get_object()
        if user.role != User.Role.ALUMNI:
            return Response(
                {"error": "User is not an alumni"},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_verified = True
        user.save()
        return Response({"message": "Alumni verified successfully"})


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if not (request.user == post.author or request.user.role == User.Role.ADMIN):
            raise PermissionDenied("You don't have permission to delete this post")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        post = self.get_object()
        reaction_type = request.data.get('reaction_type')
        reaction, created = Reaction.objects.get_or_create(
            post=post,
            user=request.user,
            defaults={'reaction_type': reaction_type}
        )
        if not created:
            if reaction.reaction_type == reaction_type:
                reaction.delete()
                return Response({"message": "Reaction removed"})
            reaction.reaction_type = reaction_type
            reaction.save()
        return Response({"message": "Reaction updated"})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post = get_object_or_404(Post, id=self.request.data.get('post'))
        if post.comments_locked:
            raise PermissionDenied("Comments are locked for this post")
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        post = comment.post
        if not (request.user == comment.author or
                request.user == post.author or
                request.user.role == User.Role.ADMIN):
            raise PermissionDenied("You don't have permission to delete this comment")
        return super().destroy(request, *args, **kwargs)


class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    permission_classes = [IsAdminOrLecturerOrReadOnly]

    @action(detail=True, methods=['post'])
    def submit_response(self, request, pk=None):
        survey = self.get_object()
        if not survey.is_active:
            return Response(
                {"error": "Survey has ended"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = SurveyResponseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, survey=survey)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True)
    def statistics(self, request, pk=None):
        survey = self.get_object()
        responses = SurveyResponse.objects.filter(survey=survey)
        return Response({
            'total_responses': responses.count(),
            'responses_by_question': self.get_question_statistics(survey)
        })


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Only admins can create groups")
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def manage_members(self, request, pk=None):
        group = self.get_object()
        serializer = GroupMembershipSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['action'] == 'add':
                group.members.add(*serializer.validated_data['user_ids'])
            else:
                group.members.remove(*serializer.validated_data['user_ids'])
            return Response({"message": "Members updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def send_bulk(self, request):
        serializer = NotificationBulkCreateSerializer(data=request.data)
        if serializer.is_valid():
            notifications = serializer.create(serializer.validated_data)
            return Response(
                NotificationSerializer(notifications, many=True).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"message": "Marked as read"})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_statistics(request):
    timeframe = request.query_params.get('timeframe', 'month')
    now = timezone.now()

    if timeframe == 'month':
        start_date = now - timezone.timedelta(days=30)
    elif timeframe == 'quarter':
        start_date = now - timezone.timedelta(days=90)
    else:  # year
        start_date = now - timezone.timedelta(days=365)

    stats = {
        'users': {
            'total': User.objects.count(),
            'alumni': User.objects.filter(role=User.Role.ALUMNI).count(),
            'verified_alumni': User.objects.filter(role=User.Role.ALUMNI, is_verified=True).count(),
            'lecturers': User.objects.filter(role=User.Role.LECTURER).count(),
        },
        'posts': {
            'total': Post.objects.filter(created_at__gte=start_date).count(),
            'by_type': Post.objects.filter(created_at__gte=start_date).values('post_type').annotate(count=Count('id')),
        },
        'surveys': {
            'total': Survey.objects.filter(post__created_at__gte=start_date).count(),
            'active': Survey.objects.filter(end_date__gt=now).count(),
            'completed': Survey.objects.filter(end_date__lte=now).count(),
        },
        'interactions': {
            'comments': Comment.objects.filter(created_at__gte=start_date).count(),
            'reactions': Reaction.objects.filter(post__created_at__gte=start_date).count(),
        }
    }

    return Response(stats)