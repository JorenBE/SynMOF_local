import os

FOLDER = '/home/jorenvanherck/Documents/synmofWeb/local_loop/PRISMA'

FOLDER_CALCULATED = '/home/jorenvanherck/Documents/synmofWeb/local_loop/calculated_PRISMA'
if not os.path.exists(FOLDER_CALCULATED):
    os.mkdir(FOLDER_CALCULATED)