# -*- coding: utf-8 -*-

def getSuffix( runconf_id ):

    suffix = '// Suffix created by Cfui\n'

    #fetch workflow id
    workflow_id = db( db.Runconf.id == runconf_id ).select( db.Runconf.workflow_id ).first().workflow_id

    # fetch parameter name set
    paramSet = db( db.Param.workflow_id == workflow_id ).select( db.Param.id, db.Param.name )

    for param in paramSet:

        suffix += param.name+' ='

        parambindSet = db(
          ( db.Parambind.userfile_id == db.Userfile.id )&
          ( db.Parambind.param_id == param.id )&
          ( db.Parambind.runconf_id == runconf_id ) ).select( db.Userfile.reffile )

        isnil = True
        for parambind in parambindSet:
            suffix += " '"+parambind.reffile+"'"
            isnil = False

        if isnil:
            suffix += ' nil'

        suffix += ';\n'

    suffix += '\n';

    targetSet = db(
      ( db.Targetbind.target_id == db.Target.id )&
      ( db.Targetbind.runconf_id == runconf_id ) ).select( db.Target.name )

    comma = False
    for target in targetSet:

        if comma:
            suffix += ' '
        comma = True

        suffix += target.name
        isnil = False

    if comma:
        suffix += ';'

    return suffix

def createWf( runconf_id ):

    import os

    filename = db( ( db.Workflow.id==db.Runconf.workflow_id )&( db.Runconf.id==runconf_id ) ).select( db.Workflow.script ).first().script
    filename = os.path.join( request.folder, 'uploads', filename )

    with open( filename )as f:
        script = f.read()

    suffix = getSuffix( runconf_id )

    filename = os.path.join( request.folder, 'private', runconf_id+'_workflow.cf' )
    with open( filename, 'w' )as f:
        f.write( script )
        f.write( '\n' )
        f.write( suffix )

    return filename


def task_cf_local( runconf_id, wf ):

    import subprocess
    import os
    import shutil
    import ntpath
    import json


    db( db.Runconf.id==runconf_id ).update( started_on=request.now )
    db.commit()

    # call cuneiform
    cwd = os.path.join( request.folder, 'uploads' )
    summary = os.path.join( '..', 'private', str( runconf_id )+'_summary.json' )
    stdout = os.path.join( request.folder, 'private', str( runconf_id )+'_stdout.txt' )
    stderr = os.path.join( request.folder, 'private', str( runconf_id )+'_stderr.txt' )
    with open( stdout, 'w' )as so:
        with open( stderr, 'w' )as se:
            retval = subprocess.call( ['cuneiform', '-s', summary, wf], cwd=cwd, stdout=so, stderr=se )

    db( db.Runconf.id==runconf_id ).update( ended_on=request.now, retval=retval )

    # gather summary
    summary = os.path.join( request.folder, 'private', str( runconf_id )+'_summary.json' )
    with open( summary, 'r' )as f:
        s = json.load( f )
    output = s.get( "output" )
    runid = s.get( "runId" )
    t = s.get( "type" )

    # define private path
    priv = os.path.join( request.folder, 'private' )

    # gather statistics log
    statlog = str( runconf_id )+'_stat.log'
    subprocess.call( 'cat /tmp/cuneiform-stat.log | grep '+runid+' > '+statlog, shell=True, cwd=priv )

    # copy output files
    if t == "File":
        for src in output:
            basename = ntpath.basename( src )
            dest = os.path.join( priv, basename )
            shutil.copyfile( src, dest )
            db.Outputfile.insert( reffile=basename, runconf_id=runconf_id )

    # commit database alterations
    db.commit()

def cfrun( runconf_id ):

    wf = createWf( runconf_id )
    db( db.Runconf.id==runconf_id ).update( committed_on=request.now )

    scheduler.queue_task( task_cf_local, pvars=dict( runconf_id=runconf_id, wf=wf ) )



from gluon.scheduler import Scheduler
scheduler = Scheduler( db )
