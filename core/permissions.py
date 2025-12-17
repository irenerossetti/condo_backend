from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated: return False
        if hasattr(u, "profile"): return u.profile.role == "ADMIN"
        return u.is_staff or u.is_superuser

class IsOwnerOrAdmin(BasePermission):
    """
    Permiso para permitir que solo el dueño de un objeto o un admin lo edite/elimine.
    """
    def has_object_permission(self, request, view, obj):
        # Los admins pueden hacer todo
        if request.user and request.user.is_authenticated:
            if request.user.is_staff:
                return True
            if hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
                return True
        
        # El dueño del objeto puede hacer todo sobre su objeto
        # Asume que el objeto tiene un campo 'user'.
        return hasattr(obj, 'user') and obj.user == request.user