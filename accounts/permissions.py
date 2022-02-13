from rest_framework.permissions import IsAuthenticated, AllowAny

from accounts.models import User


class ActionBasedPermission(AllowAny):
    """
    Grant or deny access to a view, based on a mapping in view.action_permissions
    """
    def has_permission(self, request, view):
        for klass, actions in getattr(view, 'action_permissions', {}).items():
            if view.action in actions:
                return klass().has_permission(request, view)
        return False


class IsBasicVerified(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.user.verification >= User.BASIC_VERIFIED
