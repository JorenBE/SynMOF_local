import os

FOLDER = '/home/jorenvanherck/Documents/synmofWeb/local_loop/test'

FOLDER_CALCULATED = '/home/jorenvanherck/Documents/synmofWeb/local_loop/test_calculated'
if not os.path.exists(FOLDER_CALCULATED):
    os.mkdir(FOLDER_CALCULATED)