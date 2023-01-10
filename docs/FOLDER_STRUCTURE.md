## Folder Structure

```
└── PATH_TO_HOME_DIR
    ├── IRIS
    │   ├── DEFAULT
    │   │   └── IRIS
    │   └── master
    │       ├── IRIS
    │       └── master.txt
    ├── org1
    │   ├── Project_1
    │   │   ├── branch1
    │   │   │   ├── branch1.txt
    │   │   │   └── Project_1
    │   │   ├── branch2
    │   │   │   ├── branch2.txt
    │   │   │   └── Project_1
    │   │   └── DEFAULT
    │   │       └── Project_1
    │   └── Project_2
    │       ├── branch1
    │       │   ├── branch1.txt
    │       │   └── Project_2
    │       ├── branch2
    │       │   ├── branch2.txt
    │       │   └── Project_2
    │       └── DEFAULT
    │           └── Project_2
    └── user1
        ├── Project_11
        │   ├── branch1
        │   │   ├── branch1.txt
        │   │   └── Project_11
        │   ├── branch2
        │   │   ├── branch2.txt
        │   │   └── Project_11
        │   └── DEFAULT
        │       └── Project_11
        └── Project_12
            ├── branch1
            │   ├── branch1.txt
            │   └── Project_12
            ├── branch2
            │   ├── branch2.txt
            │   └── Project_12
            └── DEFAULT
                └── Project_12

```

The code for deployment is stored in a directory hierarchy with the following structure locally. The base directory to this can be set using the environment variable ``PATH_TO_HOME_DIR`` .

- The top level directory is the ``PATH_TO_HOME_DIR`` . The next level is the organization name or the username (usually the same one as github / gitlab).
- Project name ( Repository Name )
  - The project name refers to repository name. Under this there is a folder called ``DEFAULT_BRANCH`` created for every git based deployment
  - `DEFAULT_BRANCH` , this folder is used to pull changes for deploying new branches.
- Under project there are individual folders for each branch that is created by pulling changes in DEFAULT_BRANCH and copying them into these folders. It also contains a log file which is named according the branch name for logs of that particular deployment/instance.