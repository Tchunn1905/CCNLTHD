# serializers.py

from rest_framework import serializers
from .models import User, Post, Comment, Reaction, Survey, SurveyQuestion, SurveyOption, SurveyResponse, Group, Notification


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'password',
                  'avatar', 'student_id')
        read_only_fields = ('is_verified', 'role')


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name',
                  'student_id', 'graduation_year', 'avatar')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.role = User.Role.ALUMNI
        user.set_password(password)
        user.save()
        return user


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'post', 'author', 'content', 'created_at', 'updated_at',
                  'parent_comment')
        read_only_fields = ('author', 'created_at', 'updated_at')


class ReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Reaction
        fields = ('id', 'post', 'user', 'reaction_type', 'created_at')
        read_only_fields = ('user', 'created_at')


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    reaction_counts = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ('id', 'author', 'content', 'post_type', 'created_at',
                  'updated_at', 'comments_locked', 'image', 'comments',
                  'reactions', 'reaction_counts')
        read_only_fields = ('author', 'created_at', 'updated_at')

    def get_reaction_counts(self, obj):
        counts = {}
        for reaction_type in Reaction.ReactionType.choices:
            counts[reaction_type[0]] = obj.reactions.filter(reaction_type=reaction_type[0]).count()
        return counts


class SurveyOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyOption
        fields = ('id', 'question', 'option_text', 'order')


class SurveyQuestionSerializer(serializers.ModelSerializer):
    options = SurveyOptionSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyQuestion
        fields = ('id', 'survey', 'question_text', 'question_type', 'required',
                  'order', 'options')


class SurveyResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyResponse
        fields = ('id', 'survey', 'question', 'user', 'answer_text',
                  'selected_options', 'submitted_at')
        read_only_fields = ('user', 'submitted_at')


class SurveySerializer(serializers.ModelSerializer):
    questions = SurveyQuestionSerializer(many=True, read_only=True)
    post = PostSerializer(read_only=True)

    class Meta:
        model = Survey
        fields = ('id', 'post', 'title', 'description', 'end_date',
                  'is_anonymous', 'questions')

class GroupSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'members', 'created_by',
                  'created_at', 'updated_at', 'member_count')
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def get_member_count(self, obj):
        return obj.members.count()

    def create(self, validated_data):
        members_data = self.context['request'].data.get('members', [])
        group = Group.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        if members_data:
            group.members.set(members_data)
        return group


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSerializer(read_only=True)
    related_post = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'notification_type', 'title', 'message',
                  'is_read', 'created_at', 'related_post')
        read_only_fields = ('recipient', 'created_at')

    def create(self, validated_data):
        # Tự động đặt người nhận là người dùng hiện tại nếu không có chỉ định khác
        if 'recipient' not in validated_data:
            validated_data['recipient'] = self.context['request'].user
        return super().create(validated_data)


class GroupMembershipSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    action = serializers.ChoiceField(
        choices=['add', 'remove'],
        write_only=True
    )

    def validate_user_ids(self, value):
        # Kiểm tra xem tất cả user_ids có tồn tại không
        users = User.objects.filter(id__in=value)
        if len(users) != len(value):
            raise serializers.ValidationError("Some user IDs do not exist")
        return value


class NotificationBulkCreateSerializer(serializers.Serializer):
    recipients = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    notification_type = serializers.ChoiceField(
        choices=Notification.NotificationType.choices
    )
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    related_post = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(),
        required=False
    )
    send_email = serializers.BooleanField(default=False)

    def validate_recipients(self, value):
        users = User.objects.filter(id__in=value)
        if len(users) != len(value):
            raise serializers.ValidationError("Some recipient IDs do not exist")
        return value

    def create(self, validated_data):
        recipients = validated_data.pop('recipients')
        send_email = validated_data.pop('send_email', False)
        notifications = []

        for recipient_id in recipients:
            recipient = User.objects.get(id=recipient_id)
            notification = Notification.objects.create(
                recipient=recipient,
                **validated_data
            )
            notifications.append(notification)

            if send_email and recipient.email:
                # Gửi email thông báo
                from django.core.mail import send_mail
                send_mail(
                    validated_data['title'],
                    validated_data['message'],
                    'admin@ou.edu.vn',
                    [recipient.email],
                )

        return notifications