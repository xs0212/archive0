from rest_framework.permissions import BasePermission


class RBACPermission(BasePermission):
    required_permission: str | None = None
    require_mfa: bool = False

    def has_permission(self, request, view):
        perm = getattr(view, "required_permission", self.required_permission)
        require_mfa = getattr(view, "require_mfa", self.require_mfa)
        if not request.user.is_authenticated or not perm:
            return False
        if not request.user.has_permission(perm):
            return False
        if require_mfa:
            auth_payload = getattr(request, "auth", None) or {}
            if not auth_payload.get("mfa_verified"):
                return False
        return True
