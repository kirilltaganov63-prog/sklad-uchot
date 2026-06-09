import sys
import os

# Путь к папке с проектом
<<<<<<< HEAD
path = '/home/leks/складской-учет'
=======
path = '/home/ВАШ_ЛОГИН/складской-учет'
>>>>>>> 35c4b0614cfa159926cc56d4380408f4052bc8e9
if path not in sys.path:
    sys.path.append(path)

from app import app as application
