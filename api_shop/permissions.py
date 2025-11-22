from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        return bool(user.is_authenticated and hasattr(user, 'role') and user.role.name == 'Администратор')