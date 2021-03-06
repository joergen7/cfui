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

    # define private path
    priv = os.path.join( request.folder, 'private' )

    # call cuneiform
    cwd = os.path.join( request.folder, 'uploads' )
    summary = os.path.join( priv, str( runconf_id )+'_summary.json' )
    stdout = os.path.join( priv, str( runconf_id )+'_stdout.txt' )
    stderr = os.path.join( priv, str( runconf_id )+'_stderr.txt' )
    with open( stdout, 'w' )as so:
        with open( stderr, 'w' )as se:
            try:
                retval = subprocess.call( ['cuneiform', '-s', summary, wf], cwd=cwd, stdout=so, stderr=se )
            except OSError:
                retval = -1

    db( db.Runconf.id==runconf_id ).update( ended_on=request.now, retval=retval )

    # gather summary
    with open( summary, 'r' )as f:
        s = json.load( f )
    output = s.get( "output" )
    runid = s.get( "runId" )
    t = s.get( "type" )

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


def task_cf_hiway( runconf_id, wf ):

    import subprocess
    import os
    import shutil
    import ntpath
    import json

    db( db.Runconf.id==runconf_id ).update( started_on=request.now )
    db.commit()

    # define private path
    priv = os.path.join( request.folder, 'private' )

    # call cuneiform
    cwd = priv
    wf = ntpath.basename( wf )
    summary = str( runconf_id )+'_summary.json'
    try:
        retval = subprocess.call( ['yarn', 'jar', '/home/hiway/software/hiway-0.2.0-SNAPSHOT/hiway-core-0.2.0-SNAPSHOT.jar', '-workflow', wf, '-s', summary], cwd=cwd )
    except OSError:
        retval = -1

    db( db.Runconf.id==runconf_id ).update( ended_on=request.now, retval=retval )
    db.commit()

    # gather summary
    summary = os.path.join( priv, summary )
    with open( summary, 'r' )as f:
        s = json.load( f )

    stderr_link = s.get( 'stderr' )
    stdout_link = s.get( 'stdout' )
    output = s.get( 'output' )
    statlog_link = s.get( 'statlog' )

    # gather stdout
    stdout = str( runconf_id )+'_stdout.txt'
    copy_to_private( stdout_link, stdout )

    # gather stderr
    stderr = str( runconf_id )+'_stderr.txt'
    copy_to_private( stderr_link, stderr )

    # gather statistics log
    statlog = str( runconf_id )+'_stat.log'
    copy_to_private( statlog_link, statlog )

    # copy output files
    for src in output:
        basename = ntpath.basename( src )
        copy_to_private( src, basename )
        db.Outputfile.insert( reffile=basename, runconf_id=runconf_id )

    db.commit()



def task_copy_from_uploads( filename ):

    import os
    import subprocess

    cwd = os.path.join( request.folder, 'uploads' )
    subprocess.call( ['hdfs', 'dfs', '-copyFromLocal', filename, filename], cwd=cwd )

def copy_from_uploads( filename ):
    scheduler.queue_task( task_copy_from_uploads, pvars=dict( filename=filename ) )

def copy_to_private( link, filename ):

    import subprocess
    import os

    subprocess.call( ['hdfs', 'dfs', '-copyToLocal', link, os.path.join( request.folder, 'private', filename )] )

def cfrun( runconf_id ):

    wf = createWf( runconf_id )
    db( db.Runconf.id==runconf_id ).update( committed_on=request.now )
    pvars=dict( runconf_id=runconf_id, wf=wf )

    # scheduler.queue_task( task_cf_local, pvars=pvars )
    scheduler.queue_task( task_cf_hiway, pvars=pvars )



from gluon.scheduler import Scheduler
scheduler = Scheduler( db )
