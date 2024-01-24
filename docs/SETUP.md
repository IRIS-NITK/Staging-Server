# Staging Server

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup Instructions For Local](#setup-instructions-for-local)
   * [1. Repository cloning ( OSS Version )](#1-repository-cloning-oss-version-)
   * [2. First time setup](#2-first-time-setup)
   * [3. Developer Notes:](#3-developer-notes)
   * [4. Create superuser](#4-create-superuser)
   * [5. Update site name](#5-update-site-name)
   * [6. Add social applications](#6-add-social-applications)
      + [6.1.  FOR GitLab SSO based deployments](#61-for-gitlab-sso-based-deployments)
      + [6.2. Add Github SSO (Needs to be developed/worked on)](#62-add-github-sso-needs-to-be-developedworked-on)
   * [7. Testing Deployments Locally](#7-testing-deployments-locally)

> Note: Installation guide is for dockerized version. manual deployment of staging server's services can be figured out on own but is completely unnecessary as staging server itself uses docker to deploy repositories.

## Prerequisites

Docker engine must be installed (you can use inbuilt docker compose or install docker-compose).

Refer to the following guide on how to install if it's not installed: [docs.docker.com](https://docs.docker.com/engine/install/)

## Setup Instructions For Local
### 1. Repository cloning ( OSS Version )
> `git clone https://github.com/IRIS-NITK/Staging-Server.git`

to clone with IRIS modules (for IRIS developers):
> `git clone --recurse-submodules https://github.com/IRIS-NITK/Staging-Server.git`

### 2. First time setup

enter staging server's directory
```sh
cd staging-server
```
build docker image for staging-server's services
```sh
docker-compose build
```

create environment file, copy `.env.example` to `.env`.

- change domain to your root domain of choice for staging server and deployments.
- change HOST_PARENT_WD to current working directory on your host.
- change GITLAB_URL to your instance of gitlab if you want to setup SSO with gitlab and deploy with it.

Important: comment out database mount in `docker-compose.yaml` to generate a fresh database file.
```yaml
- "./db.sqlite3:/STAGING_APP/db.sqlite3:rw"
```
you can use the following sed command to do so.
```sh
sed -i '/\.\/db\.sqlite3:\/STAGING_APP\/db\.sqlite3:rw/s/^/#/' docker-compose.yml
```

start staging-server. (use `-d` arg to run as daemon on subsequent deployments if required)
```sh
docker-compose up
```

copy database file to host:
```sh
docker-compose cp gunicorn:/STAGING_APP/db.sqlite3 ./db.sqlite3
```

uncomment database mount (Important), or your data will not persist on restarts.

shutdown staging server or (use `ctrl+c`)
```sh
docker-compose down
```

### 3. Developer Notes:

uncomment staging-server app's mounts for easier development so you won't have to rebuild everytime.(There are multiple mounts) Make sure to comment it back again before commiting/pushing to the repository.

```sh
- "./:/STAGING_APP:rw"  
```

### 4. Create superuser

exec into staging-server:
```sh
docker-compose exec -it gunicorn bash
```
create superuser:
```sh
python manage.py createsuperuser
```

The app will be visible on [http://localhost:9000](http://localhost:9000) by default.

Go to [http://localhost:9000/admin](http://localhost:9000/admin)

### 5. Update site name
Click on **Sites** then click on the existing site. Rename as shown and click **SAVE**

![image.png](./images/image.png)

### 6. Add social applications
#### 6.1.  FOR GitLab SSO based deployments
  * Go to User Settings > Applications then create an application as shown
    ![image-2.png](./images/image-2.png)
  * Copy the Application ID and Secret from GitLab into Client ID and Secret key 
  * Double click on [localhost:9000](http://localhost:9000) to move it into **Chosen sites** and click **SAVE**
    ![image-1.png](./images/image-1.png)

#### 6.2. Add Github SSO (Needs to be developed/worked on)
* Go to Settings > Developer Settings > OAuth Apps > New OAuth App and fill as shown
  ![image-3.png](./images/image-3.png)
* Copy the Client ID and a Client secret from Github into Client ID and Secret key
* Double click on [localhost:9000](http://localhost:9000) to move it into **Chosen sites** and click **SAVE**
  ![image-4.png](./images/image-4.png)

### 7. Testing Deployments Locally

Exposed ports feature is disabled and staging-server now only exposes deployments through nginx so in order to access deployments without a valid domain. You'll need to modify `/etc/hosts` and add the particular domain for each deployments and access it.