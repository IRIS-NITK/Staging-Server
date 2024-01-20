"""
Helper functions
"""

import re

def extractRepositoryName(str):
    strPattern = ["([^/]+)\\.git$"]
    for i in range(len(strPattern)):
        pattern = re.compile(strPattern[i])
        matcher = pattern.search(str)
        if matcher:
            return (matcher.group(1))
        
def generate_deployment_id(repository_pk, repo_name, branch, domain, subdomain_prefix):
    """
    generates deployment id for a specific deployment.
    """
    id=(f"R-{repository_pk}-{repo_name.lower()[0:9]}-{branch.lower()}")
    id=id[0:63-len(subdomain_prefix)-1-1-len(domain)].lower().replace("_", "-")
    return id