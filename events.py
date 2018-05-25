import subprocess
import sys

def events():
    comand = ['docker', 'events']

    try:
	docker_events = subprocess.Popen(comand, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	while True:
	    event = docker_events.stdout.readline()
	    if docker_events.poll() is not None:
		break
	    sys.stdout.write(event)
	    sys.stdout.flush()
	
	(out, err) = docker_events.communicate()

	print(out, err)
    except OSError as e:
	print(e)

if __name__ == '__main__':
    events()
