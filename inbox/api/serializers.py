from notifications.models import Notification
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType


class NotificationSerializer(serializers.ModelSerializer):
    actor_content_type = serializers.SerializerMethodField()
    action_object_content_type = serializers.SerializerMethodField()
    target_content_type = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            'id',
            'actor_content_type',
            'actor_object_id',
            'verb',
            'action_object_content_type',
            'action_object_object_id',
            'target_content_type',
            'target_object_id',
            'timestamp',
            'unread',
        )

    def get_actor_content_type(self, obj):
        return ContentType.objects.get_for_model(obj.actor).name

    def get_action_object_content_type(self, obj):
        if obj.action_object:
            return ContentType.objects.get_for_model(obj.action_object).name
        return None

    def get_target_content_type(self, obj):
        if obj.target:
            return ContentType.objects.get_for_model(obj.target).name
        return None


class NotificationSerializerForUpdate(serializers.ModelSerializer):
    unread = serializers.BooleanField()

    class Meta:
        model = Notification
        fields = ('unread',)

    def update(self, instance, validated_data):
        instance.unread = validated_data['unread']
        instance.save()
        return instance
