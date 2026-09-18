from rest_framework.authentication import BaseAuthentication, CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import AuthToken, Applicant, Staff, Administrator, hash_auth_token


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

    def authenticate_header(self, request):
        return 'Bearer realm="api"'

    def authenticate(self, request):
        # Support test factory requests that preset request.user on the underlying Django request
        underlying = getattr(request, '_request', None)
        direct_user = getattr(underlying, 'user', None) if underlying else None
        if direct_user and not getattr(direct_user, 'is_anonymous', False):
            if isinstance(direct_user, AuthToken):
                if not direct_user.is_active:
                    raise AuthenticationFailed("Session expired or revoked.")
                try:
                    if direct_user.user_type == "applicant":
                        u = Applicant.objects.get(applicant_id=direct_user.user_id)
                        if u.email_verified_at is None:
                            raise AuthenticationFailed("Please verify your email before logging in.")
                    elif direct_user.user_type == "staff":
                        u = Staff.objects.get(staff_id=direct_user.user_id)
                    elif direct_user.user_type == "administrator":
                        u = Administrator.objects.get(admin_id=direct_user.user_id)
                        if not u.is_active:
                            raise AuthenticationFailed("Administrator account is inactive.")
                    else:
                        raise AuthenticationFailed("Invalid user type.")
                except (Applicant.DoesNotExist, Staff.DoesNotExist, Administrator.DoesNotExist) as exc:
                    raise AuthenticationFailed("Account not found.") from exc
                return (CustomUser(u, direct_user.user_type), direct_user)
            elif isinstance(direct_user, CustomUser):
                return (direct_user, getattr(underlying, 'auth', None))

        auth_header = request.headers.get("Authorization")
        token = None
        cookie_authenticated = False

        if auth_header:
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                raise AuthenticationFailed(
                    "Invalid Authorization header. Use Bearer <token>."
                )
            token = parts[1]

        if not token:
            token = request.COOKIES.get(settings.AUTH_TOKEN_COOKIE_NAME)
            cookie_authenticated = bool(token)

        if not token:
            return None

        # Browsers send cookies automatically, so unsafe cookie-authenticated
        # requests must also pass Django's CSRF validation. Explicit Bearer
        # clients remain supported for non-browser API integrations.
        if cookie_authenticated and request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            check = CSRFCheck(lambda req: None)
            check.process_request(request)
            reason = check.process_view(request, None, (), {})
            if reason:
                raise PermissionDenied(f"CSRF validation failed: {reason}")

        try:
            auth_token = AuthToken.objects.get(token_hash=hash_auth_token(token))
        except AuthToken.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")

        now = timezone.now()
        if auth_token.revoked_at is not None:
            raise AuthenticationFailed("Session has been revoked.")
        if auth_token.expires_at <= now:
            auth_token.revoke()
            raise AuthenticationFailed("Session has expired.")

        # Find the actual user
        if auth_token.user_type == "applicant":

            try:
                user = Applicant.objects.get(
                    applicant_id=auth_token.user_id
                )
            except Applicant.DoesNotExist:
                raise AuthenticationFailed("Applicant not found.")
            if user.email_verified_at is None:
                raise AuthenticationFailed("Please verify your email before logging in.")

        elif auth_token.user_type == "staff":

            try:
                user = Staff.objects.get(
                    staff_id=auth_token.user_id
                )
            except Staff.DoesNotExist:
                raise AuthenticationFailed("Staff not found.")

        elif auth_token.user_type == "administrator":

            try:
                user = Administrator.objects.get(
                    admin_id=auth_token.user_id
                )
            except Administrator.DoesNotExist:
                raise AuthenticationFailed("Administrator not found.")

            if not user.is_active:
                raise AuthenticationFailed("Administrator account is inactive.")

        else:
            raise AuthenticationFailed("Invalid user type.")

        custom_user = CustomUser(user, auth_token.user_type)

        if not auth_token.last_used_at or auth_token.last_used_at < now - timedelta(minutes=5):
            AuthToken.objects.filter(pk=auth_token.pk).update(last_used_at=now)
            auth_token.last_used_at = now

        return (custom_user, auth_token)
