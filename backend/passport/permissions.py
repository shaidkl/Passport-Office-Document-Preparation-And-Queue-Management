from rest_framework.permissions import BasePermission


class IsAdministrator(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "administrator"
        )


class IsStaff(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "staff"
        )


class IsApplicant(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "applicant"
        )


class IsStaffOrAdministrator(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type in [
                "staff",
                "administrator"
            ]
        )