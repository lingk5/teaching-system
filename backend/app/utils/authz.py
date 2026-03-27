from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from ..models import User


ROLE_ADMIN = 'admin'
ROLE_TEACHER = 'teacher'
ROLE_ASSISTANT = 'assistant'


def get_current_user():
    identity = get_jwt_identity()

    if isinstance(identity, dict):
        user_id = identity.get('id')
        if user_id is not None:
            try:
                return User.query.get(int(user_id))
            except (TypeError, ValueError):
                pass
        username = identity.get('username')
        if username:
            return User.query.filter_by(username=username).first()

    if isinstance(identity, int):
        return User.query.get(identity)

    if isinstance(identity, str):
        if identity.isdigit():
            return User.query.get(int(identity))
        return User.query.filter_by(username=identity).first()

    return None


def get_current_role():
    claims = get_jwt()
    role = claims.get('role') if claims else None
    if role:
        return role
    user = get_current_user()
    return user.role if user else None


def role_required(*roles):
    """Ensure current user role is in roles."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401
            if user.role not in roles:
                return jsonify({'success': False, 'message': '权限不足'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def ensure_course_access(course_id, user):
    """Check whether user can access a course."""
    if not user:
        return False, ('用户不存在或未登录', 401)
    if user.role == ROLE_ADMIN:
        return True, None

    from ..models import Course, AssistantCourseAssignment
    course = Course.query.get(course_id)
    if not course:
        return False, ('课程不存在', 404)

    if user.role == ROLE_TEACHER:
        if course.teacher_id != user.id:
            return False, ('无权限访问该课程', 403)
        return True, None

    if user.role == ROLE_ASSISTANT:
        assignment = AssistantCourseAssignment.query.filter_by(
            assistant_id=user.id,
            course_id=course_id,
        ).first()
        if not assignment:
            return False, ('助教未被指派到该课程', 403)
        return True, None

    return False, ('角色无权限访问该课程', 403)


def get_accessible_course_ids(user):
    """Return accessible course ids for teacher/assistant; None for admin."""
    if not user:
        return []
    if user.role == ROLE_ADMIN:
        return None

    from ..models import Course, AssistantCourseAssignment
    if user.role == ROLE_TEACHER:
        return [row[0] for row in Course.query.with_entities(Course.id).filter_by(teacher_id=user.id).all()]
    if user.role == ROLE_ASSISTANT:
        return [
            row[0]
            for row in AssistantCourseAssignment.query.with_entities(AssistantCourseAssignment.course_id)
            .filter_by(assistant_id=user.id)
            .all()
        ]
    return []



def scope_courses_query(query, user):
    """Scope course query by user role."""
    if not user:
        return query
    if user.role == ROLE_ADMIN:
        return query
    from ..models import Course
    if user.role == ROLE_TEACHER:
        return query.filter(Course.teacher_id == user.id)

    if user.role == ROLE_ASSISTANT:
        from ..models import AssistantCourseAssignment
        return query.join(
            AssistantCourseAssignment, AssistantCourseAssignment.course_id == Course.id
        ).filter(
            AssistantCourseAssignment.assistant_id == user.id
        )

    return query.filter(Course.id == -1)
