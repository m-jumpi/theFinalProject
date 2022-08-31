from flask import Flask
from flask import request
from flask import redirect
from flask import abort
from flask import render_template
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField, RadioField, widgets
from wtforms.validators import DataRequired, Email
from flask import session
from flask import url_for
from flask import flash
import email_validator
import os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
bootstrap = Bootstrap(app)
moment = Moment(app)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:12345As!@localhost/db1'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     form = NameForm()
#     if form.validate_on_submit():
#         old_name = session.get('name')
#         if old_name is not None and old_name != form.name.data:
#             flash('Looks like you have changed your name!')
#         session['name'] = form.name.data
#         return redirect(url_for('index'))
#     return render_template('index.html',
#                            form=form, name=session.get('name'), current_time=datetime.utcnow())

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)

@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            db.session.commit()
            session['known'] = False
        else:
            session['known'] = True
        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('index'))
    return render_template('index.html',
                           form=form, name=session.get('name'),
                           known=session.get('known', False), current_time=datetime.utcnow())


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    return render_template('feedback.html', form=form)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/cources')
def cources():
    return render_template('courses.html')


@app.route('/ActiveDirectoryCource', methods=['GET', 'POST'])
def ActiveDirectoryCource():
    form = SubmitForm()
    return render_template('ActiveDirectoryCource.html', form=form)


# @app.route('/')
# def index():
#     user_agent = request.headers.get('User-Agent')
#     return '<p>Your browser is {}</p>'.format(user_agent)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class FeedbackForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[Email(), DataRequired()])
    # Gender = RadioField('Gender', choices=[('M', 'Male'), ('F', 'Female')],
    #                     widget=widgets.TableWidget(with_table_tag=True) )

    courceName = SelectField('Cource Name', choices=[('c1', 'Active Directory Protection & Tiering'),
                                                     ('c2',
                                                      'Advanced Implementation and Optimization with Border Gateway'),
                                                     ('c3', 'Advanced Network Automation with Python')])
    feedbackText = TextAreaField('How Can We Improve?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class SubmitForm(FlaskForm):
    submit = SubmitField('Submit')


if __name__ == '__main__':
    app.run()
