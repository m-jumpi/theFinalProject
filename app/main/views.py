from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, abort, request
from . import main
from .forms import NameForm, FeedbackForm, SibmitForm, SignUpForm, EditProfileForm, EditProfileAdminForm, PostForm
from .. import db
from ..models import User, Order, Course, Permission, Role, Post
from flask_login import login_required, current_user
from ..email import send_email
from ..decorators import admin_required, permission_required
from flask import current_app


@main.route('/', methods=['GET', 'POST'])
def index():
    # form = NameForm()
    # if form.validate_on_submit():
    #     user = User.query.filter_by(username=form.name.data).first()
    #     if user is None:
    #         user = User(username=form.name.data)
    #         db.session.add(user)
    #         db.session.commit()
    #         session['known'] = False
    #     else:
    #         session['known'] = True
    #     session['name'] = form.name.data
    #     form.name.data = ''
    #     return redirect(url_for('.index'))
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    # posts = Post.query.order_by(Post.timestamp.desc()).all()

    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           pagination=pagination, current_time=datetime.utcnow())

    # return render_template('index.html',
    #                        # form=form, name=session.get('name'),
    #                        # known=session.get('known', False),
    #                        current_time=datetime.utcnow())
    # return render_template('index.html', form=form, posts=posts, current_time=datetime.utcnow())


@main.route('/cources')
def cources():
    return render_template('cources.html')


@main.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        flash('Form is valid')
    return render_template('feedback.html', form=form)


@main.route('/about')
def about():
    return render_template('about.html')


@main.route('/ActiveDirectoryCource', methods=['GET', 'POST'])
def ActiveDirectoryCource():
    form = SibmitForm()
    if form.validate_on_submit():
        return redirect(url_for('main.signup'))
    return render_template('ActiveDirectoryCource.html', form=form)


@main.route('/signup', methods=['GET', 'POST'])
@login_required
def signup():
    form = SignUpForm()
    # form.courseName.query=Course.query.all()
    if form.validate_on_submit():
        order = Order(firstname=form.firstName.data,
                      lastname=form.lastName.data,
                      email=current_user.email,
                      user_id=current_user.id,
                      # course_id=form.courseName.data.id,
                      course_order=Course.query.get(form.courseName.data),
                      mobile=form.mobile.data,
                      payment=form.payment.data)

        # order.firstname = form.firstName.data
        # order.lastname = form.lastName.data
        # order.email = current_user.email
        # order.course_id = Course.query.get(form.courseName.data)
        # order.mobile = form.mobile.data
        # order.payment = form.payment.data

        db.session.add(order)
        db.session.commit()
        send_email(order.email, 'Course Registration',
                   '/email/registration', order=order, coursename=Course.query.get(form.courseName.data))
        flash(
            f'You have successfully registered for the course. A confirmation email has been sent to {current_user.email}')
        return redirect(url_for('main.index'))
        # print(form.courseName.data.id)
        # print(current_user.email)
        # return '<h1>{}</h1>'.format(form.courseName.data)
    return render_template('signup.html', form=form)


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    # posts = user.posts.order_by(Post.timestamp.desc()).all()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts, pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    return render_template('post.html', posts=[post])


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/admin')
@login_required
@admin_required
def for_admins_only():
    return "For administrators!"


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def for_moderators_only():
    return "For comment moderators!"
