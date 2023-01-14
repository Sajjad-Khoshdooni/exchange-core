from django.core.management.base import BaseCommand
from subprocess import Popen
from sys import stdout, stdin, stderr
import time
import os
import signal


class Command(BaseCommand):
    help = 'Run WebSocket Server'

    def handle(self, *args, **options):
        proc_list = []

        command = 'python socket_handler.py'
        print("$ " + command)
        proc = Popen(command, shell=True, stdin=stdin,
                     stdout=stdout, stderr=stderr)
        proc_list.append(proc)

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            for proc in proc_list:
                os.kill(proc.pid, signal.SIGKILL)
