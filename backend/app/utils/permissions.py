from flask_jwt_extended import get_jwt, get_jwt_identity


ROLE_CAPABILITIES = {
    'admin': {
        'manage_users',
        'manage_courses',
        'manage_students',
        'import_data',
        'process_warnings',
        'generate_warnings',
        'export_reports',
    },
    'teacher': {
        'manage_courses',
        'manage_students',
        'import_data',
        'process_warnings',
        'generate_warnings',
        'export_reports',
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


def current_user_id():
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        identity = identity.get('id')
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def role_has_capability(role, capability):
    normalized_role = normalize_role(role)
    if not capability:
        return False
    return capability in ROLE_CAPABILITIES.get(normalized_role, set())


def current_user_can(capability):
    return role_has_capability(current_role(), capability)


def accessible_course_query():
    from ..models import Course
    from ..models.assistant_assignment import AssistantCourseAssignment

    role = current_role()
    user_id = current_user_id()
    query = Course.query

    if role == 'admin':
        return query
    if role == 'teacher':
        return query.filter(Course.teacher_id == user_id)
    if role == 'assistant':
        return query.join(
            AssistantCourseAssignment,
            AssistantCourseAssignment.course_id == Course.id
        ).filter(
            AssistantCourseAssignment.assistant_id == user_id
        ).distinct()
    return query.filter(Course.id == -1)


def accessible_course_ids():
    from ..models import Course

    return [
        course_id
        for (course_id,) in accessible_course_query().with_entities(Course.id).all()
    ]


def can_access_course(course_id):
    if not course_id:
        return False
    from ..models import Course

    return accessible_course_query().filter(Course.id == course_id).first() is not None


def can_access_class(class_id):
    if not class_id:
        return False

    from ..models import Class, Course
    from ..models.assistant_assignment import AssistantCourseAssignment

    role = current_role()
    user_id = current_user_id()
    query = Class.query.join(Course, Class.course_id == Course.id)

    if role == 'teacher':
        query = query.filter(Course.teacher_id == user_id)
    elif role == 'assistant':
        query = query.join(
            AssistantCourseAssignment,
            AssistantCourseAssignment.course_id == Course.id
        ).filter(
            AssistantCourseAssignment.assistant_id == user_id
        )
    elif role != 'admin':
        return False

    return query.filter(Class.id == class_id).first() is not None


def can_access_student(student_id):
    if not student_id:
        return False

    from ..models import Student, Class, Course
    from ..models.assistant_assignment import AssistantCourseAssignment

    role = current_role()
    user_id = current_user_id()
    query = Student.query.join(Class, Student.class_id == Class.id).join(
        Course,
        Class.course_id == Course.id
    )

    if role == 'teacher':
        query = query.filter(Course.teacher_id == user_id)
    elif role == 'assistant':
        query = query.join(
            AssistantCourseAssignment,
            AssistantCourseAssignment.course_id == Course.id
        ).filter(
            AssistantCourseAssignment.assistant_id == user_id
        )
    elif role != 'admin':
        return False

    return query.filter(Student.id == student_id).first() is not None


def course_id_for_class(class_id):
    from ..models import Class

    class_obj = Class.query.get(class_id)
    return class_obj.course_id if class_obj else None


def course_id_for_student(student_id):
    from ..models import Student, Class

    student = Student.query.get(student_id)
    if not student:
        return None
    class_obj = Class.query.get(student.class_id)
    return class_obj.course_id if class_obj else None
