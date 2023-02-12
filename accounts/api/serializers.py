from django.contrib.auth.models import User
from rest_framework import serializers, exceptions


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        # user existence
        if not User.objects.filter(username=data['username'].lower()).exists():
            raise exceptions.ValidationError({
                'username': "Username does not exist."
            })
        return data


class SignupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=20, min_length=6)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=20, min_length=6)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    # will be called when is_valid is called
    def validate(self, data):
        if User.objects.filter(username=data['username'].lower()).exists():
            raise exceptions.ValidationError({
                'username': "Username already taken."
            })
        if User.objects.filter(username=data['email'].lower()).exists():
            raise exceptions.ValidationError({
                'email': "Email already signed up."
            })
        return data

    def create(self, validated_data):
        username = validated_data['username'].lower()
        email = validated_data['email'].lower()
        password = validated_data['password']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return user
