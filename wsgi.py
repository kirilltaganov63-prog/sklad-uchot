import sys
import os

# Путь к папке с проектом
path = '/home/leks/складской-учет'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
