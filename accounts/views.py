from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, update_session_auth_hash, user_logged_in
from django.contrib.auth.models import Group

from .models import User
from .serializers import (
    UserSerializer, UserCreateSerializer, UserPasswordChangeSerializer,
    GroupSerializer, UserSummarySerializer,
)
from .permissions import IsAdminCNS, IsAdminOrTechnicianReadOnlyForConsultant

User = get_user_model()


class LoginTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                username = request.data.get('username')
                if username:
                    user = User.objects.filter(username=username).first()
                    if user:
                        user_logged_in.send(sender=user.__class__, request=request, user=user)
            except Exception:
                pass
        return response


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrTechnicianReadOnlyForConsultant]
    filterset_fields = ['role', 'service', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'matricule']
    ordering_fields = ['username', 'date_joined', 'role']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            self.permission_classes = [IsAdminCNS]
        return super().get_permissions()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request, pk=None):
        user = self.get_object()
        if request.user.pk != user.pk and not request.user.is_admin_cns():
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserPasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.is_admin_cns():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'old_password': 'Ancien mot de passe incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        return Response({'detail': 'Mot de passe modifié avec succès.'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def technicians(self, request):
        techs = User.objects.filter(role__in=[User.ROLE_ADMIN, User.ROLE_TECHNICIAN], is_active=True)
        serializer = UserSummarySerializer(techs, many=True)
        return Response(serializer.data)


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [IsAdminCNS]
