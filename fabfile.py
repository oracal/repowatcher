from fabric.api import env, run, put, cd

env.hosts = ['************']
env.warn_only = True

def deploy():
    put('repowatcher/','/home/oracal/webapps/repowatcher/')
    with cd('/home/oracal/webapps/repowatcher/'):
        run('rm -r logs')
        run('mkdir logs')
        run('touch logs/django_complete.log')
        run('touch logs/django.log')
        #run('/home/oracal/.virtualenvs/repowatcher/bin/python manage.py sqlclear main | /home/oracal/.virtualenvs/repowatcher/bin/python manage.py dbshell')
        #run('/home/oracal/.virtualenvs/repowatcher/bin/python manage.py sqlclear social_auth | /home/oracal/.virtualenvs/repowatcher/bin/python manage.py dbshell')
        #run('/home/oracal/.virtualenvs/repowatcher/bin/python manage.py sqlclear djcelery | /home/oracal/.virtualenvs/repowatcher/bin/python manage.py dbshell')
        #run('/home/oracal/.virtualenvs/repowatcher/bin/python manage.py flush --noinput')
        #run('/home/oracal/.virtualenvs/repowatcher/bin/python manage.py syncdb --noinput')
    put('media/*','/home/oracal/webapps/static_media/')
    put('bin/','/home/oracal/')
    run('/home/oracal/bin/redis_daemon.sh')
    run('/home/oracal/bin/celery_daemon.sh')
    restart()

def restart():
    run('/home/oracal/webapps/repowatcher/apache2/bin/restart')