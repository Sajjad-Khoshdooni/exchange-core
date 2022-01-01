from django.contrib.auth.backends import ModelBackend

from account.models import User


class AuthenticationBackend(ModelBackend):

    def authenticate(self, request, **credentials):
        login = credentials.get('login') or credentials.get('username')
        password = credentials.get('password')

        if not login or not password:
            return

        user = User.get_user_from_login(login)
        if not user:
            User().set_password(password)
            return

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
