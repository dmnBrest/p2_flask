# -*- coding: utf-8 -*-

from flask import Flask, request_started, session, request
from flask_debugtoolbar import DebugToolbarExtension
from flask_redis import Redis
from flask.ext.sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask_security.forms import ConfirmRegisterForm
from wtforms import StringField, validators
from flask_wtf import RecaptchaField
from flask_wtf.csrf import CsrfProtect
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

import bbcode

app = Flask(__name__)
app.config.from_object('config')

redis_store = Redis(app)

app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

db = SQLAlchemy(app)
mail = Mail(app)

CsrfProtect(app)

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


# ----------- LOGGER ----------------------
if not app.debug:
	import logging
	from logging.handlers import SMTPHandler
	mail_handler = SMTPHandler(mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
								fromaddr='server-error@salesforce-developer.net',
								toaddrs=app.config['ADMINS_MAILS'],
								subject='Salesforce-Developer.NET Failed',
								credentials=(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']),
								secure=()
	)
	mail_handler.setLevel(logging.ERROR)
	app.logger.addHandler(mail_handler)
	file_handler = logging.FileHandler(filename=app.config['LOG_FILE'])
	file_handler.setLevel(logging.WARNING)
	app.logger.addHandler(file_handler)


# ------------ BBCODE PARSER CUSTOM TAGS -----------
bbcode_parser = bbcode.Parser()
bbcode_parser.add_simple_formatter('h2', '<h2>%(value)s</h2>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('h3', '<h3>%(value)s</h3>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('h4', '<h4>%(value)s</h4>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('p', '<p>%(value)s</p>', swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('br', '<br />', standalone=True)
bbcode_parser.add_simple_formatter('img', '<span class="article-img"><img src="%(value)s"></span>', replace_links=False, swallow_trailing_newline=True)
bbcode_parser.add_simple_formatter('code', '<pre class="prettyprint linenums"><code>%(value)s</code></pre>', render_embedded=False, transform_newlines=False, swallow_trailing_newline=True)

def render_quote(tag_name, value, options, parent, context):
	author = u''
	# [quote author=Somebody]
	if 'author' in options:
		author = options['author']
	# [quote=Somebody]
	elif 'quote' in options:
		author = options['quote']
	# [quote Somebody]
	elif len(options) == 1:
		key, val = options.items()[0]
		if val:
			author = val
		elif key:
			author = key
	# [quote Firstname Lastname]
	elif options:
		author = ' '.join([k for k in options.keys()])
	extra = '<div class="quote_author"><u>%s</u>:</div>' % author if author else ''
	return '<blockquote>%s<p>%s</p></blockquote>' % (extra, value)

# Now register our new quote tag, telling it to strip off whitespace, and the newline after the [/quote].
bbcode_parser.add_formatter('quote', render_quote, strip=True, swallow_trailing_newline=True)


# administrator list
ADMINS = ['admin@p2.dev']

from app import views, models

class ExtendedRegisterForm(ConfirmRegisterForm):
	username = StringField('Username',
						   [validators.DataRequired(message='Username not provided'),
							validators.Length(min=4, max=25),
							validators.Regexp('^[a-zA-Z0-9_-]+$',  message='Wrong Username format. "a-z", "A-Z", "0-9", "_" and "-" characters are allowed. Min 4 character')])
	recaptcha = RecaptchaField('Captcha')

	def validate(self):
		#check for username
		success = True
		if not super(ExtendedRegisterForm, self).validate():
			success = False
		if models.User.query.filter_by(username = self.username.data.strip()).first():
			self.username.errors.append("Username already taken")
			success = False
		return success

user_datastore = SQLAlchemyUserDatastore(db, models.User, models.Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

# TOOLBAR
toolbar = DebugToolbarExtension(app)

from seed import seed_db
@manager.command
def seed():
	seed_db()
	print('Seed FINISHED successfully.')

@manager.shell
def make_shell_context():
	return dict(app=app, db=db, models=models)


@request_started.connect_via(app)
def before_request_started(app, **extra):
	if not request.path.startswith('/static') and \
			not request.path.startswith('/_') and \
			not request.path.startswith('/pictures') and \
			not request.path.startswith('/favicon.ico') and \
			not request.path.startswith('/auth'):
		r = request.path
		session['prev_url'] = request.path
