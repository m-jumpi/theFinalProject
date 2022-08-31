from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, abort, request, make_response
from . import main
from .forms import NameForm, FeedbackForm, SibmitForm, SignUpForm, EditProfileForm, EditProfileAdminForm, PostForm, \
    ApproveOrder, CommentForm
from .. import db
from ..models import User, Order, Course, Permission, Role, Post, Comment
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
    # pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
    #     page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
    #     error_out=False)
    # posts = pagination.items
    # return render_template('index.html', form=form, posts=posts,
    #                        pagination=pagination, current_time=datetime.utcnow())

    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
                           show_followed=show_followed, pagination=pagination, current_time=datetime.utcnow())


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30 * 24 * 60 * 60)  # 30 days
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30 * 24 * 60 * 60)  # 30 days
    return resp


@main.route('/cources')
def cources():
    courses = Course.query.order_by(Course.id).all()
    page = request.args.get('page', 1, type=int)
    pagination = Course.query.order_by(Course.id).paginate(
        page, per_page=current_app.config['FLASKY_COURSES_PER_PAGE'],
        error_out=False)
    courses = pagination.items

    return render_template('courses.html', courses=courses, pagination=pagination)


@main.route('/cources/<int:id>', methods=['GET', 'POST'])
def cources_description(id):
    course = Course.query.get_or_404(id)
    modules = course.modules.split('%')
    print(modules)
    form = SibmitForm()
    if form.validate_on_submit():
        return redirect(url_for('main.signup'))
    return render_template('course.html', form=form, course=course, modules=modules)


@main.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        flash('Form is valid')
    return render_template('feedback.html', form=form)


@main.route('/about')
def about():
    return render_template('about.html')


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

    orders = Order.query.order_by().all()

    return render_template('user.html', user=user, posts=posts, pagination=pagination, orders=orders)


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


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
               current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)


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


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    current_user.unfollow(user)
    db.session.commit()
    flash('You have unfollowed %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    followed = [{'user': item.followed, 'timestamp': item.timestamp}
                for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=followed)


@main.route('/approve_order/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_order(id):
    order = Order.query.get_or_404(id)
    form = ApproveOrder(order=order)
    if form.validate_on_submit():
        order.firstname = form.firstName.data
        order.lastname = form.lastName.data
        order.approved = form.approved.data
        order.course_order = Course.query.get(form.courseName.data)
        order.mobile = form.mobile.data
        order.payment = form.payment.data
        db.session.add(order)
        db.session.commit()
        if form.approved.data:
            flash('The order has been approved.')
        return redirect(url_for('.user', username=current_user.username))
    form.firstName.data = order.firstname
    form.lastName.data = order.lastname
    form.approved.data = order.approved
    form.courseName.data = order.course_id
    form.mobile.data = order.mobile
    form.payment.data = order.payment
    return render_template('approve_order.html', form=form, order=order)


@main.route('/enrolled_course/<int:id>', methods=['GET', 'POST'])
@login_required
def enrolled_course(id):
    order = Order.query.get_or_404(id)
    if (current_user.id == order.user_id and order.approved):
        return render_template('enrolled_course.html', order=order)
    abort(404)


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
