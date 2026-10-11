import os
import sys

port = sys.argv[1]
prefix = sys.argv[2]
suffix = sys.argv[3]
container = sys.argv[4]
domain = os.getenv("NGINX_DOMAIN", os.getenv("DOMAIN", "localhost")).split(":", 1)[0]

current_path = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(current_path, "dev-template.conf")

with open(template_path, "r", encoding="utf-8") as template_file:
    template_content = template_file.read()

template_content = template_content.replace("<PORT>", port)
template_content = template_content.replace("<PREFIX>", prefix)
template_content = template_content.replace("<SUFFIX>", suffix)
template_content = template_content.replace("<CONTAINER>", container)
template_content = template_content.replace("<DOMAIN>", domain)

config_directory = os.path.join(current_path, "configs")
os.makedirs(config_directory, exist_ok=True)

with open(os.path.join(config_directory, f"dev-{suffix}.conf"), "w", encoding="utf-8") as branch_file:
    branch_file.write(template_content)
