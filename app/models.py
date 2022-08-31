from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import URLSafeSerializer as Serializer
from flask import current_app
from . import db
import hashlib
from markdown import markdown
import bleach


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return '<Role %r>' % self.name

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT,
                          Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT,
                              Permission.WRITE, Permission.MODERATE,
                              Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    orders = db.relationship('Order', backref='user_order', lazy='dynamic')
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://s.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    modules = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    orders = db.relationship('Order', backref='course_order')

    @staticmethod
    def insert_corses():
        courses = {'Active Directory Protection & Tiering': ["This on-demand course is intended for IT and security \
professionals who want to understand the most common attack vectors and security pitfolds in Active Directory such as \
Kerberoast, kerberos delegation, credential caching and others. We will discuss the best practice recommendations to \
design a new Active Directory or protect an existing one against security threats. The course focuses on the most \
abused escalation misconfiguration and the tools available to discover them, the Active Directory Tiering model, \
Privileged Access Workstations, ESAE forests, and different password policies based on account categorization and \
others.", "Introduction %Overview of AD Attacks & Tools %Attacks %Tools %AD Tiering %Passwords \
%AD Features %Hardening %Conclusion", 1],
                   'Advanced Implementation and Optimization with Border Gateway': ["This course covers understanding, optimizing and configuring BGP. In \
this course, you will learn about different BGP Path attributes as well \
as how to do path manipulation in BGP using attributes like...", "", 1],
                   'Advanced Network Automation with Python': ["This course covers advanced Python scripting required for Network automation and \
managing network devices. In this course, you will learn about taking backups \
of network devices using Netmiko, Built-in function, Built-in input function, \
SysArgv, Argparse, matching RAW data using Regex, Parsing Data using Regex, \
and TextFSM. Students who want to deepen their understanding of Network Automation \
using Python3 will benefit from this course", "", 1],
                   'AWS Cloud Architect Bootcamp': ["Join us for this 12 Week AWS Cloud Architect Bootcamp and prepare for the AWS Solutions Architect \
Associate certification by BUILDING 54 PROJECTS.", "", 1],
                   'AWS Management Concepts': ["Understanding AWS is more than just services. It's also about best practices when it comes to billing, \
architectures, monitoring, and so on. This course will cover the fundamentals needed to become effective \
in those areas. We will look at support plans, cost and billing, as well as the Well-Architected \
framework. When completed, you will have a solid foundation to begin building, monitoring, and \
controlling costs in AWS.", "", 1],
                   'AWS Security & Compliance': ["AWS is not only a game-changer for companies looking to innovate faster. AWS Cloud also helps you \
significantly improve your security and compliance practice in ways that would be difficult or \
financially impossible for most organizations outside AWS. This course gives you the fundamentals for \
understanding security and compliance in the AWS Cloud. You will review the basics of security using \
IAM, including entities and evaluation of policy statements. The essential services you can use to \
improve security and compliance, including those using AI/ML, are also covered.", "", 1]
                   }
        for key, value in courses.items():
            course = Course.query.filter_by(title=key).first()
            if course is None:
                course = Course(title=key, description=value[0], modules=value[1], author_id=value[2])
                db.session.add(course)
        db.session.commit()

    def __repr__(self):
        return self.title


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    email = db.Column(db.String(64), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    mobile = db.Column(db.String(64), index=True)
    payment = db.Column(db.String(64))
    approved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Order %r>' % self.id


class Author(db.Model):
    __tablename__ = 'author'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    about_auth = db.Column(db.Text)
    courses = db.relationship('Course', backref='author_course')

    @staticmethod
    def insert_authors():
        authors = {'Ivanov Ivan': "Ivan has specialized in both offensive and defensive security. \
On the offensive side, he has performed numerous Red Team engagements and penetration tests, \
targeting both Active Directory, web and network infrastructures, and applications. Ivan has also been part of \
multiple full TIBER-DK engagements executed in Denmark. On the defensive side, he has specialized in improving Cyber \
Security maturity and resilience against modern attacks in Active Directory and related Windows \
infrastructure. His previous roles include Senior Consultant, where he handled Digital Forensics and Incident Response, \
Vulnerability Management, IP Theft Investigations, and more. He later transitioned to Senior IT Security Researcher \
where he focused on developing Information Security courses. This role was followed by working as a Security Advisor \
where he handled Network Security, SecOps Management, Web Application Security, Critical Security Controls, and more. \
Certifications: eCTHP, eCPTX, OSCE, OSCP, GCFA, AZ-500, Microsoft INF260x"}
        for key, value in authors.items():
            author = Author.query.filter_by(name=key).first()
            if author is None:
                author = Author(name=key, about_auth=value)
                db.session.add(author)
        db.session.commit()

    def __repr__(self):
        return '<Author %r>' % self.id


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))


db.event.listen(Comment.body, 'set', Comment.on_changed_body)

db.event.listen(Post.body, 'set', Post.on_changed_body)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
