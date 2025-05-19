from django.utils.module_loading import import_string
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import TokenViewBase

class customTokenObtainPairView(TokenViewBase):
    permission_classes = ()
    authentication_classes = ()
 
    serializer_class = None
    _serializer_class = ""
 
    www_authenticate_realm = "api"
 
    def get_serializer_class(self) -> Serializer:
        """
        If serializer_class is set, use it directly. Otherwise get the class from settings.
        """
        if self.serializer_class:
            return self.serializer_class
        try:
            return import_string(self._serializer_class)
        except ImportError:
            msg = "Could not import serializer '%s'" % self._serializer_class
            raise ImportError(msg)
 
    def get_authenticate_header(self, request: Request) -> str:
        return '{} realm="{}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,
        )
 
    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
 
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
 
        user = serializer.validated_data['user']
        if user.is_superuser:
            token = api_settings.JWT_AUTH_TOKEN_CLASSES['access']().for_user(user)
            return Response({
                'access': str(token.access_token),
                'refresh': str(token),
            })
        elif user.is_staff and user.is_active:
            token = api_settings.JWT_AUTH_TOKEN_CLASSES['access']().for_user(user)
            return Response({
                'access': str(token.access_token),
                'refresh': str(token),
            })
 
        return Response({'error': 'User does not meet criteria'}, status=status.HTTP_400_BAD_REQUEST)
 
class TokenObtainPairView(TokenViewBase):
    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """
    _serializer_class = api_settings.TOKEN_OBTAIN_SERIALIZER
 
 
class TokenRefreshView(TokenViewBase):
    """
    Takes a refresh type JSON web token and returns an access type JSON web
    token if the refresh token is valid.
    """
 
    _serializer_class = api_settings.TOKEN_REFRESH_SERIALIZER