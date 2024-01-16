import sys
import os

port = sys.argv[1]
prefix = sys.argv[2]
suffix = sys.argv[3]    # will be of format staging_iris-nitk_iris_*
container = sys.argv[4]

current_path = os.path.dirname(os.path.abspath(__file__))
template_path  = os.path.join(current_path,'dev-template.conf')

with open(template_path, 'r') as template_file:
    template_content = template_file.read()

template_content = template_content.replace('<PORT>', port)
template_content = template_content.replace('<PREFIX>', prefix)
template_content = template_content.replace('<SUFFIX>', suffix)
template_content = template_content.replace('<CONTAINER>', container)

config_directory = f'{current_path}/configs/'
if not os.path.exists(config_directory):
    os.makedirs(config_directory)

with open(f'{config_directory}/dev-{suffix}.conf', 'w') as branch_file:
    branch_file.write(template_content)
