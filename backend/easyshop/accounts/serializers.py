from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import ROLE_CHOICES, User, RolePermission
from core.models import Permission, Currency
# serializers.py

from inventory.models import Location


class UserProductPreferenceSerializer(serializers.Serializer):
    """User product preference serializer"""
    product_id = serializers.IntegerField(source="variant_id")
    preference_type = serializers.ChoiceField(
        choices=[
            'is_loved',
            'is_bookmarked',
            'is_favorite',
        ]
    )
    value = serializers.BooleanField(required=False)
    

class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password.')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for User profile data"""
    avatar_url = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    
    # Write fields for updates
    location_id = serializers.CharField(write_only=True, required=False)
    preferred_currency_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'username', 'email', 'phone',
            'role_name', 'location', 'location_id', 'avatar_url', 'permissions',
            'preferred_currency', 'preferred_currency_id', 'language_preference', 
            'timezone', 'theme', 'is_active', 'last_login'
        ]
        read_only_fields = ['id', 'last_login']
    
    def get_avatar_url(self, obj):
        request = self.context['request']
        if obj.photo:
            photo = obj.photo.url
        else:
            photo = f"/media/user_avatar.jpeg"
        photo_url = request.build_absolute_uri(photo)
        return photo_url
    
    def get_permissions(self, obj):
        """Get all permissions for this user through roles and direct permissions"""
        permissions = set()
        
        # Get permissions from role
        if obj.role_name:
            role_name = obj.role_name
            role_permissions = RolePermission.objects.filter(role_name=role_name)
            
            for rp in role_permissions:
                permissions.add(rp.permission.module)
        
        # Get direct user permissions
        user_permissions = obj.users_permissions.filter(allow=True).select_related('permission')
        for up in user_permissions:
            permissions.add(up.permission.module)
        
        # Remove denied permissions
        denied_permissions = obj.users_permissions.filter(allow=False).select_related('permission')
        for dp in denied_permissions:
            permissions.discard(dp.permission.module)
        
        return list(permissions)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': str(data['id']),
            'firstName': data['first_name'],
            'lastName': data['last_name'],
            'username': data['username'],
            'email': data['email'],
            'phone': data['phone'],
            'location': data['location'],
            'role': data['role_name'] if data['role_name'] else None,
            'avatarUrl': data['avatar_url'],
            'permissions': data['permissions'],
            'preferences': {
                'language': data['language_preference'],
                'timezone': data['timezone'] or 'UTC',
                'currency': data['preferred_currency'] if data['preferred_currency'] else Currency.get_base_currency().id,
                'theme': data['theme']
            }
        }
    
    def update(self, instance, validated_data):
        # Handle role update
        if 'role_name' in validated_data:
            role_name = validated_data.pop('role_name')
            if role_name:
                if role_name in ROLE_CHOICES:
                    instance.role_name = role_name
                else:
                    raise serializers.ValidationError({'role_name': 'Invalid role Name'})
        
        # Handle location update
        if 'location_id' in validated_data:
            location_id = validated_data.pop('location_id')
            if location_id:
                try:
                    location = Location.objects.get(id=location_id)
                    instance.location = location
                except Location.DoesNotExist:
                    raise serializers.ValidationError({'location_id': 'Invalid location ID'})
        
        # Handle currency update
        if 'preferred_currency_id' in validated_data:
            currency_id = validated_data.pop('preferred_currency_id')
            if currency_id:
                try:
                    currency = Currency.objects.get(id=currency_id)
                    instance.preferred_currency = currency
                except Currency.DoesNotExist:
                    raise serializers.ValidationError({'preferred_currency_id': 'Invalid currency ID'})
        
        return super().update(instance, validated_data)


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for User profile data"""
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name',  'last_name', 'username', 'email', 'phone',
            'role_name', 'avatar_url', 'location',
        ]
    
    def get_avatar_url(self, obj):
        request = self.context['request']
        if obj.photo:
            photo = obj.photo.url
        else:
            photo = f"/media/user_avatar.jpeg"
        photo_url = request.build_absolute_uri(photo)
        return photo_url


class CreateUserSerializer(serializers.ModelSerializer):
    """Serializer for creating new users (admin only)"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    location_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email', 'photo', 'phone', 'password',
            'role_name', 'location_id',
        ]
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def validate_role_name(self, role_name):
        if role_name == 'admin':
            raise serializers.ValidationError("Invalid Role Name")
        for role in ROLE_CHOICES:
            if role_name == role[0]:
                break
        else:
            raise serializers.ValidationError("Invalid Role Name")
        return role_name
        
    def create(self, validated_data):
        role_name = validated_data.pop('role_name')
        location_id = validated_data.pop('location_id')
        password = validated_data.pop('password')
        
        # Get role and location
        try:
            location = Location.objects.get(id=location_id)
            if location.location_type != "store":
                raise Location.DoesNotExist
        except Location.DoesNotExist:
            raise serializers.ValidationError("Invalid location ID")
        
        # Create user
        user = User.objects.create_user(
            password=password,
            role_name=role_name,
            location=location,
            **validated_data
        )
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
