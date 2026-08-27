from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import AuthToken, Applicant, Staff, Administrator


class CustomUser:
    def __init__(self, user, user_type):
        self.user = user
        self.user_type = user_type
        self.is_authenticated = True

        # Useful for accessing the ID later
        if user_type == "applicant":
            self.user_id = user.applicant_id
        elif user_type == "staff":
            self.user_id = user.staff_id
        elif user_type == "administrator":
            self.user_id = user.admin_id


class CustomTokenAuthentication(BaseAuthentication):

    def authenticate(self, request):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationFailed(
                "Invalid Authorization header. Use Bearer <token>."
            )

        token = parts[1]

        try:
            auth_token = AuthToken.objects.get(token=token)
        except AuthToken.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")

        # Find the actual user
        if auth_token.user_type == "applicant":

            try:
                user = Applicant.objects.get(
                    applicant_id=auth_token.user_id
                )
            except Applicant.DoesNotExist:
                raise AuthenticationFailed("Applicant not found.")

        elif auth_token.user_type == "staff":

            try:
                user = Staff.objects.get(
                    staff_id=auth_token.user_id
                )
            except Staff.DoesNotExist:
                raise AuthenticationFailed("Staff not found.")

            if user.status != "Active":
                raise AuthenticationFailed("Staff account is inactive.")

        elif auth_token.user_type == "administrator":

            try:
                user = Administrator.objects.get(
                    admin_id=auth_token.user_id
                )
            except Administrator.DoesNotExist:
                raise AuthenticationFailed("Administrator not found.")

        else:
            raise AuthenticationFailed("Invalid user type.")

        custom_user = CustomUser(user, auth_token.user_type)

        return (custom_user, auth_token)