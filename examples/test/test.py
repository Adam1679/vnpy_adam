# coding:utf-8
from apscheduler.schedulers.blocking import BlockingScheduler
import datetime
from threading import Event
import logging


def run():
    print 111
    while True:
        print 666
        can_done2 = Event()
        can_done2.wait(timeout=1)

def control():
    print 222
    if datetime.datetime.now().second in [0, 20, 40]:
        print scheduler.get_jobs()
        scheduler.pause_job('my_job_id')
    elif datetime.datetime.now().second in [10, 30, 50]:
        print scheduler.get_jobs()
        scheduler.resume_job('my_job_id')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datafmt='%a, %d %b %Y %H:%M:%S', filename='/home/hadoop/aaa.txt', filemode='a')
    scheduler = BlockingScheduler()
    date = datetime.datetime.now()
    scheduler.add_job(func=run, trigger='interval', id='my_job_id')
    scheduler.add_job(func=control, trigger='interval')
    scheduler.start()
