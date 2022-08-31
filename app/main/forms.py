from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, widgets, BooleanField, ValidationError
from wtforms.validators import DataRequired, Length, Email, Regexp
from ..models import Course, User, Role
from wtforms_sqlalchemy.fields import QuerySelectField
from flask_pagedown.fields import PageDownField


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


def courses_query():
    return Course.query


class FeedbackForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Length(1, 64),
                                                     Email()])
    # Gender = RadioField('Gender', choices=[('M', 'Male'), ('F', 'Female')],
    #                     widget=widgets.TableWidget(with_table_tag=True) )
    # x=Course.query.all()
    # courseName = SelectField('Course Name', choices=[('c1', 'Active Directory Protection & Tiering'),
    #                                                  ('c2',
    #                                                   'Advanced Implementation and Optimization with Border Gateway'),
    #                                                  ('c3', 'Advanced Network Automation with Python')])
    # courseName = QuerySelectField('Course Name', query_factory=courses_query, get_label='coursename')
    courseName = SelectField('Course Name', coerce=int)
    feedbackText = TextAreaField('How Can We Improve?', validators=[DataRequired()])
    submit = SubmitField('Feedback')

    def __init__(self, *args, **kwargs):
        super(FeedbackForm, self).__init__(*args, **kwargs)
        self.courseName.choices = [(courseName.id, courseName.title)
                                   for courseName in Course.query.order_by(Course.title).all()]


class SibmitForm(FlaskForm):
    submit = SubmitField('Enroll')


class SignUpForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    # email = StringField('Email Address', validators=[DataRequired(), Length(1, 64),
    #                                                  Email()])
    # courseName = SelectField()
    # courseName = QuerySelectField(query_factory=courses_query, get_label='coursename')
    courseName = SelectField('Course Name', coerce=int)
    mobile = StringField('Mobile', validators=[DataRequired(),
                                               Length(1, 12),
                                               Regexp('^[+]\d{11}$', 0,
                                                      'Mobile phone number must have only numbers and must be 11 numbers long')])
    payment = SelectField('Payment Method', choices=['Cash', 'Card'])
    submit = SubmitField('Sign Up')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.courseName.choices = [(course.id, course.title)
                                   for course in Course.query.order_by(Course.title).all()]


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
               'Usernames must have only letters, numbers, dots or '
               'underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class ApproveOrder(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    courseName = SelectField('Course Name', coerce=int)
    approved = BooleanField('Approved')
    mobile = StringField('Mobile', validators=[DataRequired(),
                                               Length(1, 12),
                                               Regexp('^[+]\d{11}$', 0,
                                                      'Mobile phone number must have only numbers and must be 11 numbers long')])
    payment = SelectField('Payment Method', choices=['Cash', 'Card'])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(ApproveOrder, self).__init__(*args, **kwargs)
        self.courseName.choices = [(course.id, course.title)
                                   for course in Course.query.order_by(Course.title).all()]


class PostForm(FlaskForm):
    body = PageDownField("What do you think about our learning platform?", validators=[DataRequired()])
    submit = SubmitField('Submit')


class CommentForm(FlaskForm):
    body = StringField('', validators=[DataRequired()])
    submit = SubmitField('Submit')
