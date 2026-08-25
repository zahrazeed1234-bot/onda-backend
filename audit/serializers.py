from rest_framework import serializers
from .models import AuditLog
from accounts.serializers import UserSummarySerializer


class AuditLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    utilisateur_info = UserSummarySerializer(source='utilisateur', read_only=True)
    content_type_label = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = '__all__'

    def get_content_type_label(self, obj):
        if obj.content_type:
            return f'{obj.content_type.app_label}.{obj.content_type.model}'
        return None
