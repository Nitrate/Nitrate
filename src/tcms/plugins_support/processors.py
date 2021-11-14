# -*- coding: utf-8 -*-
import threading
from importlib import import_module

from django.conf import settings


class NewThread(threading.Thread):
    def __init__(self, command, args):
        self.command = command
        self.args = args
        super().__init__()

    def run(self):
        # The actual code we want to run
        return self.command(self.args)


class PushSignalToPlugins:
    def __init__(self):
        self.plugins = []

    def import_plugins(self):
        if not hasattr(settings, "SIGNAL_PLUGINS") or not settings.SIGNAL_PLUGINS:
            return

        for p in settings.SIGNAL_PLUGINS:
            self.plugins.append(import_module(p))

    def push(self, model, instance, signal):
        for p in self.plugins:
            NewThread(p.receiver, {"model": model, "instance": instance, "signal": signal}).start()


# Create the PushSignalToPlugins instance
pstp = PushSignalToPlugins()
pstp.import_plugins()
