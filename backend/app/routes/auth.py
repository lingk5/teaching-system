from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from ..models import db, User
from ..utils.permissions import current_user_can, normalize_role
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def validate_json(*required_fields):
    """JSON数据验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'success': False, 'message': 'Content-Type必须是application/json'}), 400
            
            data = request.get_json()
            
            # 检查必填字段
            missing_fields = [field for field in required_fields if field not in data or not data[field]]
            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'缺少必填字段: {"，".join(missing_fields)}'
                }), 400
            
            # 字段长度验证示例
            if 'username' in data and (len(data['username']) < 3 or len(data['username']) > 20):
                return jsonify({'success': False, 'message': '用户名长度必须在3-20个字符之间'}), 400
                
            if 'password' in data and len(data['password']) < 6:
                return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/register', methods=['POST'])
@validate_json('username', 'password', 'name')
def register():
    """教师注册"""
    data = request.get_json()

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    user = User(
        username=data['username'],
        password_hash=generate_password_hash(data['password']),
        name=data['name'],
        email=data.get('email'),
        role='teacher'
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '注册成功',
        'data': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
@validate_json('username', 'password')
def login():
    """登录 - 返回JWT Token"""
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    if not user.is_active:
        return jsonify({'success': False, 'message': '账号已停用，请联系管理员'}), 403

    # 生成JWT Token（有效期7天）
    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(days=7),
        additional_claims={
            'username': user.username,
            'name': user.name,
            'role': user.role
        }
    )

    return jsonify({
        'success': True,
        'message': '登录成功',
        'data': {
            'token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.name,
                'role': user.role
            }
        }
    })


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前登录用户信息"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    return jsonify({
        'success': True,
        'data': user.to_dict()
    })


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """管理员获取用户列表"""
    if not current_user_can('manage_users'):
        return jsonify({'success': False, 'message': '仅管理员可访问用户管理'}), 403

    users = User.query.order_by(User.id.asc()).all()
    return jsonify({
        'success': True,
        'data': [u.to_dict() for u in users]
    })


@auth_bp.route('/users', methods=['POST'])
@jwt_required()
@validate_json('username', 'password', 'name', 'role')
def create_user():
    """管理员创建用户"""
    if not current_user_can('manage_users'):
        return jsonify({'success': False, 'message': '仅管理员可创建用户'}), 403

    data = request.get_json()
    role = normalize_role(data.get('role'))
    if role not in {'admin', 'teacher', 'assistant'}:
        return jsonify({'success': False, 'message': '角色不合法'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    email = data.get('email') or None
    if email and User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '邮箱已存在'}), 400

    user = User(
        username=data['username'],
        password_hash=generate_password_hash(data['password']),
        name=data['name'],
        email=email,
        role=role
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户创建成功',
        'data': user.to_dict()
    }), 201


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """管理员更新用户信息/角色"""
    if not current_user_can('manage_users'):
        return jsonify({'success': False, 'message': '仅管理员可更新用户'}), 403

    data = request.get_json() or {}
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    if 'name' in data and data['name']:
        user.name = data['name']

    if 'email' in data:
        email = data['email'] or None
        if email:
            existing = User.query.filter(User.email == email, User.id != user_id).first()
            if existing:
                return jsonify({'success': False, 'message': '邮箱已存在'}), 400
        user.email = email

    if 'role' in data:
        role = normalize_role(data.get('role'))
        if role not in {'admin', 'teacher', 'assistant'}:
            return jsonify({'success': False, 'message': '角色不合法'}), 400
        user.role = role

    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    if data.get('password'):
        if len(data['password']) < 6:
            return jsonify({'success': False, 'message': '密码长度不能少于6位'}), 400
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()

    return jsonify({
        'success': True,
        'message': '用户更新成功',
        'data': user.to_dict()
    })
