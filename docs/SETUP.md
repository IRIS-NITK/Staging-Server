# Staging Server

## Table of Contents
- [Staging Server](#staging-server)
  - [Table of Contents](#table-of-contents)
  - [Setup Instructions](#setup-instructions)
    - [1. Create and activate virtual environment](#1-create-and-activate-virtual-environment)
    - [2. Install dependencies](#2-install-dependencies)
    - [3. Run migrations](#3-run-migrations)
    - [4. Create superuser](#4-create-superuser)
    - [5. Run the app and log in as superuser](#5-run-the-app-and-log-in-as-superuser)
    - [6. Update site name](#6-update-site-name)
    - [7. Add social applications](#7-add-social-applications)
      - [7.1  Add GitLab SSO](#71--add-gitlab-sso)
      - [7.2 Add Github SSO](#72-add-github-sso)
    - [8. Celery Setup](#8-celery-setup)

## Setup Instructions
### 1. Create and activate virtual environment
> `pip install virtualenv`
 
> `python3 -m venv <virtual-environment-name>`

> `source <virtual-environment-name>/bin/activate`

### 2. Install dependencies
> `pip install -r requirements.txt`

### 3. Run migrations
> `python manage.py migrate`

### 4. Create superuser
> `python manage.py createsuperuser`

### 5. Run the app and log in as superuser
> `python manage.py runserver`

The app will be visible on [http://localhost:8000](http://localhost:8000)

Go to [http://localhost:8000/admin](http://localhost:8000/admin)

### 6. Update site name
Click on **Sites** then click on the existing site. Rename as shown and click **SAVE**

![image.png](./images/image.png)

### 7. Add social applications
#### 7.1  Add GitLab SSO
  * Go to User Settings > Applications then create an application as shown
    ![image-2.png](./images/image-2.png)
  * Copy the Application ID and Secret from GitLab into Client ID and Secret key 
  * Double click on [localhost:8000](http://localhost:8000) to move it into **Chosen sites** and click **SAVE**
    ![image-1.png](./images/image-1.png)

#### 7.2 Add Github SSO
* Go to Settings > Developer Settings > OAuth Apps > New OAuth App and fill as shown
  ![image-3.png](./images/image-3.png)
* Copy the Client ID and a Client secret from Github into Client ID and Secret key
* Double click on [localhost:8000](http://localhost:8000) to move it into **Chosen sites** and click **SAVE**
  ![image-4.png](./images/image-4.png)

### 8. Celery Setup
In another terminal in the root of your project directory, run the following command:
> `celery -A "name_of_project" worker -l info`