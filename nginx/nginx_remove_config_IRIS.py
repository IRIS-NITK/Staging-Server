import sys
import os

suffix = sys.argv[1]

current_path = os.path.dirname(os.path.abspath(__file__))
config_directory = f'{current_path}/configs/'

if os.path.exists(f'{config_directory}/dev-{suffix}.conf'):
  os.remove(f'{config_directory}/dev-{suffix}.conf')
else:
  print("The file does not exist")
