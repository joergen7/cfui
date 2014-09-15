# -*- coding: utf-8 -*-

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL('sqlite://storage.sqlite',pool_size=1,check_reserved=['all'])
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'
#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Crud, Service, PluginManager, prettydate
auth = Auth(db)
crud, service, plugins = Crud(db), Service(), PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables(username=False, signature=False)

## configure email
mail = auth.settings.mailer
mail.settings.server = 'logging' or 'smtp.gmail.com:587'
mail.settings.sender = 'you@gmail.com'
mail.settings.login = 'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
# from gluon.contrib.login_methods.rpx_account import use_janrain
# use_janrain(auth, filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

# Workflow
db.define_table(
  'Workflow',
  Field( 'title', unique=True, requires=IS_NOT_EMPTY() ),
  Field( 'script', 'upload', requires=IS_NOT_EMPTY() ),
  Field( 'descr', 'text' ),
  Field( 'created_by', 'reference auth_user', default=auth.user_id ),
  Field( 'created_on', 'datetime', default=request.now ),
  Field.Virtual( 'Action', lambda row: A( 'Run ...', _href=URL( 'default', 'prepare', vars=dict( workflow_id=row.Workflow.id ) ) ) ),
  format='%(title)s',
  common_filter=lambda query: db.Workflow.created_by==auth.user_id )

db.Workflow.id.readable = False
db.Workflow.created_by.readable = db.Workflow.created_by.writable = False
db.Workflow.created_on.writable = False


# Param
db.define_table(
  'Param',
  Field( 'workflow_id', 'reference Workflow' ),
  Field( 'name', requires = IS_NOT_EMPTY() ),
  format='%(name)s' )

db.Param.id.readable = False
db.Param.workflow_id.writable = db.Param.workflow_id.readable = False


# Target
db.define_table(
  'Target',
  Field( 'workflow_id', 'reference Workflow' ),
  Field( 'name' ),
  format='%(name)s' )

db.Target.id.readable = False
db.Target.workflow_id.writable = db.Target.workflow_id.readable = False

# Runconf
db.define_table(
  'Runconf',
  Field( 'workflow_id', 'reference Workflow', notnull=True ),
  Field( 'tstart', 'datetime' ) )



# Userfile
db.define_table(
  'Userfile',
  Field( 'title', unique=True, requires = IS_NOT_EMPTY() ),
  Field( 'reffile', 'upload', requires = IS_NOT_EMPTY() ),
  Field( 'descr', 'text' ),
  Field( 'created_by', 'reference auth_user', default=auth.user_id ),
  Field( 'created_on', default=request.now ),
  format='%(title)s',
  common_filter=lambda query: db.Userfile.created_by==auth.user_id )

db.Userfile.id.readable = False
db.Userfile.created_by.readable = db.Userfile.created_by.writable = False
db.Userfile.created_on.writable = False


# Parambind
db.define_table(
  'Parambind',
  Field( 'pos', 'integer', notnull=True ),
  Field( 'param_id', 'reference Param', notnull=True ),
  Field( 'userfile_id', 'reference Userfile', notnull=True ),
  Field( 'runconf_id', 'reference Runconf', notnull=True ) )


# Targetbind
db.define_table(
  'Targetbind',
  Field( 'target_id', 'reference Target', notnull=True ),
  Field( 'runconf_id', 'reference Runconf', notnull=True ) )








## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)
