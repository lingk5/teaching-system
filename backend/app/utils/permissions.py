from flask_jwt_extended import get_jwt


ROLE_CAPABILITIES = {
    'admin': {
        'manage_users',
        'manage_courses',
        'manage_students',
        'import_data',
        'process_warnings',
        'generate_warnings',
    },
    'teacher': {
        'manage_courses',
        'manage_students',
        'import_data',
        'process_warnings',
        'generate_warnings',
    },
    'assistant': set(),
}


def normalize_role(role):
    if not isinstance(role, str):
        return ''
    return role.strip().lower()


def current_role():
    claims = get_jwt()
    return normalize_role(claims.get('role'))


def role_has_capability(role, capability):
    normalized_role = normalize_role(role)
    if not capability:
        return False
    return capability in ROLE_CAPABILITIES.get(normalized_role, set())


def current_user_can(capability):
    return role_has_capability(current_role(), capability)
