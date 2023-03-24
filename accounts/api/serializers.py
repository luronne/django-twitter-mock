from django.contrib.auth.models import User
from rest_framework import serializers, exceptions


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class UserSerializerForTweet(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username')


class UserSerializerForComment(UserSerializerForTweet):
    pass


class UserSerializerForFriendship(UserSerializerForTweet):
    pass


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        # missing username
        if not data.get('username'):
            raise exceptions.ValidationError({
                'username': "This field may not be blank."
            })
        # missing password
        if not data.get('password'):
            raise exceptions.ValidationError({
                'username': "This field may not be blank."
            })
        # non-exist username
        username = data['username'].lower()
        if not User.objects.filter(username=username).exists():
            raise exceptions.ValidationError({
                'username': "User does not exist."
            })
        data['username'] = username
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
