from flask import Flask, current_app, jsonify, render_template, request, redirect, url_for
from celery import Celery

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379',
    CELERY_WORKER_NAME='celery@MacBook-Air-de-Cecilia.local'
)
celery = make_celery(app)


# ----------------------------- JOB ----------------------------- # 
import time

@celery.task(bind=True)
def do_processing(self):
    """ Get some rest, asynchronously, and update the state all the time """
    for i in range(1000):
        time.sleep(0.1)
        self.update_state(state='PROGRESS',meta={'current': i, 'total': 1000})

# ----------------------------- ROUTES ----------------------------- # 

@app.route('/', methods=['POST', 'GET'])
@app.route('/index', methods=['POST', 'GET'])
def home():
	if request.method == 'GET':
		i = celery.control.inspect()
		return render_template('index.html', tasks=i.active()[current_app.config['CELERY_WORKER_NAME']])
	return redirect(url_for('home'))

@app.route('/run_job', methods=['POST', 'GET'])
def run_job():
	task = do_processing.apply_async()
	return redirect(url_for('home'))

@app.route('/stop_job/<task_id>', methods=['POST', 'GET'])
def stop_job(task_id):
	i = celery.control.revoke(task_id, terminate=True) 
	return redirect(url_for('home'))

@app.route('/status/<task_id>', methods=['GET'])
def taskstatus(task_id):
	task = celery.AsyncResult(task_id)
	if task.state == 'PROGRESS':
		response = {
		'state': task.state,
		'current': task.info.get('current', 0),
		'total': task.info.get('total', 1),
		'status': task.info.get('status', '')
		}
	elif task.state == 'PENDING':
	#job did not start yet
		response = {
			'state': task.state,
			'current': 0,
			'total': 1,
			'status': 'Pending...'
		}
	elif task.state == 'SUCCESS':
	#job did not start yet
		response = {
			'state': task.state,
			'current': 1,
			'total': 1,
			'status': 'Success !'
		}
	else:
		# something went wrong in the background job
		response = {
		'state': task.state,
		'current': 0,
		'total': 0,
		'status': str(task.info),  # this is the exception raised
		}
	return jsonify(response)
# ---------------------------------------------------------------- # 
