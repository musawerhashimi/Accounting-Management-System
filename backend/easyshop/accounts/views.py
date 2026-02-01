from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import update_session_auth_hash
from django.core.files.storage import default_storage
from django.db import models
from core.models import Permission

from core.permissions import (
    IsSelfOrHasPermission, IsTenantUser,
    TenantPermissionMixin, IsTenantOwnerOrAdmin
)
from .models import (
    User, UserPermission, UserProductPreference
)
from .serializers import (
    UserListSerializer, UserProfileSerializer,
    ChangePasswordSerializer, LoginSerializer,
    UserProductPreferenceSerializer, CreateUserSerializer
)

# views.py or viewsets.py


class UserViewSet(TenantPermissionMixin, viewsets.ModelViewSet):
    """ViewSet for User management"""
    serializer_class = UserProfileSerializer
    permission_module = 'users'
    parser_classes = [MultiPartParser, FormParser, JSONParser] 
    
    def get_queryset(self):

        user = self.request.user
        if user.role_name and user.role_name == 'admin':
            # Admin can see all users
            # return User.objects.annotate(
            #     allowed=models.Case(
            #         models.When(role_name='admin', then=0), default=1
            #     )
            # ).filter(allowed=1).select_related('location', 'preferred_currency').all()
            return User.objects.select_related('location', 'preferred_currency').all()
        else:
            # Regular users can only see themselves
            return User.objects.filter(id=user.id).select_related('location', 'preferred_currency')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        elif self.action == "list":
            return UserListSerializer
        return UserProfileSerializer
        
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate user"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': 'User deactivated successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTenantOwnerOrAdmin])
    def activate(self, request, pk=None):
        """Activate user"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'message': 'User activated successfully'})

    @action(
        detail=True,
        methods=['post'], 
        parser_classes=[MultiPartParser, FormParser],
        url_path='upload-photo',
        permission_classes=[IsTenantUser, IsSelfOrHasPermission]
    )
    def upload_photo(self, request, pk=None):
        """Upload user profile photo"""
        user = self.get_object()
        print("PHOTO")
        # Check permission - admin or own profile
        if not (request.user == user or (request.user.role_name and request.user.role_name == 'admin')):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if 'photo' not in request.FILES:
            return Response(
                {'error': 'No photo file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        photo = request.FILES['photo']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if photo.content_type not in allowed_types:
            return Response(
                {'error': 'Only JPEG and PNG images are allowed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (5MB limit)
        if photo.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'File size must be less than 5MB'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete old photo if exists
        if user.photo:
            if default_storage.exists(user.photo.name):
                default_storage.delete(user.photo.name)
        
        # Save new photo
        user.photo = photo
        user.save()
        serializer = self.get_serializer(user)
        avatar_url = request.build_absolute_uri(serializer.data['avatarUrl'])
        return Response({
            'message': 'Photo uploaded successfully',
            'avatar_url': avatar_url
        })
    
    @action(detail=True, methods=['delete'], url_path='delete-photo')
    def delete_photo(self, request, pk=None):
        """Delete user profile photo"""
        user = self.get_object()
        
        # Check permission
        if not (request.user == user or (request.user.role_name and request.user.role_name == 'admin')):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user.photo:
            if default_storage.exists(user.photo.name):
                default_storage.delete(user.photo.name)
            user.photo = None
            user.save()
        
        serializer = self.get_serializer(user)
        return Response({
            'message': 'Photo deleted successfully',
            'avatar_url': serializer.data['avatarUrl']
        })
    
    @action(detail=False, methods=['get', 'patch'], permission_module=None)
    def me(self, request):
        if self.action == "get":
            """Get current user profile"""
            
            serializer = self.get_serializer(request.user, context={'request': request})
            return Response(serializer.data)

        """Update current user profile"""
        serializer = self.get_serializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'])
    def permissions(self, request, pk=None):
        user: User = self.get_object()
        selected_modules = set(request.data.get("permissions", []))

        if not selected_modules:
            return Response({"details": "Permissions Not Provided!"}, status=status.HTTP_400_BAD_REQUEST)

        # Clear all previous permissions (start clean)
        UserPermission.objects.filter(user=user).delete()

        # Apply permission per module (override role)
        for module, _ in Permission.MODULES:
            permissions = Permission.objects.filter(module=module)
            allow = module in selected_modules

            for p in permissions:
                UserPermission.objects.create(user=user, permission=p, allow=allow)

        return Response({"message": "Permissions set successfully"}, status=200)


class UserProductPreferenceViewSet(TenantPermissionMixin, viewsets.ViewSet):
    """User product preferences viewset"""

    def create(self, request):
        serializer = UserProductPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        product_id = data.get("product_id")
        preference_type = data.get("preference_type")
        
        value = data.get("value", None)
        preferences, _ = UserProductPreference.objects.get_or_create(
            user=request.user,
            variant=product_id
        )
        if not value:
            value = not getattr(preferences, preference_type)
        setattr(preferences, preference_type, value)
        preferences.save()
        return Response({preference_type: getattr(preferences, preference_type)})


class AuthViewSet(viewsets.ViewSet):
    """Authentication viewset"""
    from django.core.handlers.wsgi import WSGIRequest
    @action(detail=False, methods=['post'])
    def login(self, request: WSGIRequest):
        """User login"""
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]

        # ✅ Check user tenant matches request.tenant
        if not hasattr(request, "tenant") or user.tenant_id != request.tenant.id:
            return Response({"detail": "Invalid Credentials."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Set JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # ✅ Update last login
        user_timezone = request.headers.get('X-TIMEZONE', None)
        print("user_timezone:", user_timezone)
        if user_timezone:
            user.timezone = user_timezone
        user.last_login = timezone.now()
        user.save(update_fields=["last_login", "timezone"])

        # ✅ Return response with user data and access token
        res = Response({
            "access": access_token,
            "user": UserProfileSerializer(user, context={"request": request}).data,
            "message": "Login successful"
        })

        # ✅ Set httpOnly cookie for refresh token
        res.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,  # Use False if not using HTTPS in dev
            samesite="Lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )

        return res
        
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """User logout"""
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()

            response = Response({"detail": "Logged out"})
            response.delete_cookie("refresh_token")
            return response
        except Exception:
            return Response({"detail": "Invalid token"}, status=400)
        # logout(request)
        # return Response({'message': 'Logout successful'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user info"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Change user password"""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Keep user logged in after password change
            update_session_auth_hash(request, user)
            
            return Response({
                'message': 'Password changed successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status

class CookieTokenRefreshView(TokenRefreshView):
    """
    Refresh access token using refresh token from httpOnly cookie.
    Also, sets the new rotated refresh token in the cookie.
    """
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"detail": "Refresh token not found in cookie."}, status=status.HTTP_401_UNAUTHORIZED)

        # We are using the default serializer, which expects the refresh token in the body.
        # So we pass it in the data dictionary.
        serializer = self.get_serializer(data={"refresh": refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # The token is invalid or expired
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        
        # The serializer.validated_data contains the new access and refresh tokens
        access_token = serializer.validated_data["access"]
        new_refresh_token = serializer.validated_data["refresh"]

        res = Response({"access": access_token, "message": "Token refreshed successfully"})

        # ✅ Set the new refresh token in the httpOnly cookie
        res.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,  # Set to False if not using HTTPS in development
            samesite="Lax",
            max_age=7 * 24 * 60 * 60  # Should match REFRESH_TOKEN_LIFETIME
        )
        
        return res