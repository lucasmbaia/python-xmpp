import sys
import threading
import Queue
import time


class ExcThread(threading.Thread):
    def __init__(self, interval, target, args=()):
        threading.Thread.__init__(self)
        self.interval = interval
	self.target = target
	self.args = args

    def run(self):
	self.success = None
	self.error = None

	try:
	    time.sleep(self.interval)
	    self.success = self.target(*self.args)
	except Exception as e:
	    self.error = sys.exc_info()
    def join(self):
	threading.Thread.join(self)
	if self.error:
	    #msg = "Thread '%s' threw an exception: %s" % (self.getName(), self.error[1])
	    raise Exception(self.error[1])

	if self.success:
	    return self.success

def pepeca(application_name, container_name):
    print(application_name, container_name)
    raise Exception("Retorna erro")

def main():
    #bucket = Queue.Queue()
    thread_obj = ExcThread(0, pepeca, ('lucas', 'mama'))
    thread_obj.start()

    while True:
        try:
	    exc = thread_obj.join()
	    print(exc)
        except Queue.Empty:
            pass
	except Exception as e:
	    print(e)
        if thread_obj.isAlive():
            continue
        else:
            break


if __name__ == '__main__':
    main()
