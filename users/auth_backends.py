from django.contrib.auth.backends import BaseBackend

def _match_perm(user_codes, required):
    # exacto
    if required in user_codes:
        return True
    # wildcard: termina en "*"
    for code in user_codes:
        if code.endswith("*"):
            if required.startswith(code[:-1]):
                return True
    return False

class RolePermissionBackend(BaseBackend):
    def authenticate(self, request, **kwargs):
        return None  # solo permisos

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj or not getattr(user_obj, "role_id", None):
            return False
        codes = set(user_obj.role.permissions.values_list("code", flat=True))
        normalized = perm.split(".", 1)[1] if "." in perm else perm
        return _match_perm(codes, normalized)

    def get_user_permissions(self, user_obj, obj=None):
        if not getattr(user_obj, "role_id", None):
            return set()
        return set(user_obj.role.permissions.values_list("code", flat=True))

    def get_all_permissions(self, user_obj, obj=None):
        return self.get_user_permissions(user_obj, obj)
