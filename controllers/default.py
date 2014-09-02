# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################

def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html

    if you need a simple wiki simply replace the two lines below with:
    return auth.wiki()
    """

    return dict()

@auth.requires_login()
def workflow():
    """
    Manages a users workflows.
    """
    grid = SQLFORM.smartgrid(
      db.Workflow,
      linked_tables=['Param', 'Target'],
      details=False,
      searchable=False,
      csv=False,
      headers={'Workflow.descr' : 'Description'},
    )
    return dict( grid=grid )

@auth.requires_login()
def prepare():
    """
    Sets up a single workflow for running it.
    """

    # retrieve workflow id from request
    workflow_id = request.vars.workflow_id

    if workflow_id == None:
        response.flash = 'Error: Variable workflow_id not defined.'
        return dict( form=T( 'Error' ) )

    # retrieve workflow title and description
    tuple = db( db.Workflow.id == workflow_id ).select( db.Workflow.title, db.Workflow.descr ).first()
    workflow_title = tuple.title
    workflow_descr = tuple.descr


    # create new runconf tuple if necessary
    if request.vars.runconf_id == None:
        runconf_id = db.Runconf.insert( workflow_id=workflow_id )
    else:
        runconf_id = request.vars.runconf_id

    # find next pos value for current run configuration
    col = db.Parambind.pos.max()
    nextpos = db( db.Parambind.runconf_id == runconf_id ).select( col ).first()[ col ]

    if nextpos == None:
        nextpos = 0
    else:
        nextpos += 1

    # create and process parameter form
    paramForm = SQLFORM(
      db.Parambind,
      fields=['param_id', 'userfile_id'],
      hidden=dict( runconf_id=runconf_id ),
      submit_button='Add' )

    paramForm.vars.pos=nextpos
    paramForm.vars.runconf_id=runconf_id

    if paramForm.accepts( request, session ):
        response.flash = 'Parameter added.'

    # create and process target form
    targetForm = SQLFORM(
      db.Targetbind,
      fields=['target_id'],
      hidden=dict( runconf_id=runconf_id ),
      submit_button='Add' )

    targetForm.vars.runconf_id=runconf_id

    if targetForm.accepts( request, session ):
        response.flash='Target added.'

    # create and process run form
    runForm = FORM(
      INPUT( _type='hidden', _name='run', _value='True', ),
      INPUT( _type='submit', _value='Run ...' ) )

    if request.vars.run != None:
        redirect( URL( 'history' ) )

    # fetch parameter bindings
    paramDict = dict()

    paramSet = db( db.Param.workflow_id == workflow_id ).select( db.Param.id, db.Param.name )

    for param in paramSet:

        userfileSet = db(
          ( db.Parambind.param_id == db.Param.id )&
          ( db.Parambind.userfile_id == db.Userfile.id )&
          ( db.Param.id == param.id )&
          ( db.Parambind.runconf_id == runconf_id ) ).select( db.Userfile.title )

        ufa = []
        for userfile in userfileSet:
            ufa.append( userfile.title )

        paramDict[ param.name ] = ufa

    # fetch target bindings
    targetSet = db( ( db.Targetbind.target_id == db.Target.id )&( db.Targetbind.runconf_id == runconf_id ) ).select( db.Target.name )

    targetList = []
    for target in targetSet:
        targetList.append( target.name )

    return dict(
      workflow_title=workflow_title,
      workflow_descr=workflow_descr,
      paramDict=paramDict,
      targetList=targetList,
      paramForm=paramForm,
      targetForm=targetForm,
      runForm=runForm )

@auth.requires_login()
def userfile():
    """
    Manages a users data.
    """
    grid = SQLFORM.smartgrid(
      db.Userfile,
      linked_tables=[],
      details=False,
      searchable=False,
      csv=False,
      headers={ 'Userfile.reffile' : 'File' }
    )

    return dict( grid=grid )


def history():
    return locals()


def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/manage_users (requires membership in
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())

@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())