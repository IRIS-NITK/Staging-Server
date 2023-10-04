import sys
import os

branch = sys.argv[1]

current_path = os.path.dirname(os.path.abspath(__file__))
config_directory = f'{current_path}/../configs/'

if os.path.exists(f'{config_directory}/dev-{branch}.conf'):
  os.remove(f'{config_directory}/dev-{branch}.conf')
else:
  print("The file does not exist")
