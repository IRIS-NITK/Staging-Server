import sys
import os

branch = sys.argv[1]
port = sys.argv[2]
container_name = sys.argv[3] # staging_iris-nitk_iris

current_path = os.path.dirname(os.path.abspath(__file__))
template_path  = os.path.join(current_path,'dev-template.conf')

with open(template_path, 'r') as template_file:
    template_content = template_file.read()

template_content = template_content.replace('<BRANCH_NAME>', branch)
template_content = template_content.replace('<PORT>', port)
template_content = template_content.replace('<CONTAINER_NAME>', container_name)

config_directory = f'{current_path}/../configs/'
if not os.path.exists(config_directory):
    os.makedirs(config_directory)

with open(f'{config_directory}/dev-{branch}.conf', 'w') as branch_file:
    branch_file.write(template_content)
