from rest_framework.permissions import BasePermission

from .models import Staff


def _staff_is_on_duty(user):
    if getattr(user, "user_type", None) != "staff":
        return True

    staff_id = getattr(user, "user_id", None)
    if staff_id is None and isinstance(getattr(user, "user", None), Staff):
        staff_id = user.user.staff_id
    # Duty can change during an existing session, so always use the current
    # database value instead of the account object loaded at login time.
    staff = Staff.objects.filter(staff_id=staff_id).only(
        "is_active", "status"
    ).first()
    return bool(staff and staff.is_active and staff.status == "Active")


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


class IsOnDutyStaffOrAdministrator(BasePermission):
    message = "Go active on the staff dashboard before using staff operations."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.user_type == "administrator":
            return True
        return request.user.user_type == "staff" and _staff_is_on_duty(request.user)


class IsAuthenticatedWithStaffOnDuty(BasePermission):
    """Allow authenticated citizens/admins, but require staff to be on duty."""

    message = "Go active on the staff dashboard before using staff operations."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _staff_is_on_duty(request.user)
        )
