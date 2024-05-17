import os
import sys
import yaml


if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.realpath('__file__'))

config = yaml.safe_load(open(os.path.join(ROOT_DIR, 'config.yaml')))