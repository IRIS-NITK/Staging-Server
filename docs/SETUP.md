# Staging-Sever

## Setup Instructions

 1. Create and activate virtual environment 

> `pip install virtualenv`

> `python3 -m venv <virtual-environment-name>`

> `source <virtual-environment-name>/bin/activate`

2. Install dependencies

> `pip install -r requirements.txt`

3. Run migrations

> `python manage.py migrate`

4. Create superuser
> `python manage.py createsuperuser`

5. Run the app. The app will be visible on http://localhost:8000
> `python manage.py runserver`

6. Log in using superuser at http://localhost:8000/admin

7. Click on **Sites** then click on the existing site. Rename as shown and click **SAVE**

![image.png](./images/image.png)

8. Click on **Social applications** then click on **ADD SOCIAL APPLICATION**

9. Add GitLab SSO as follows -
    * Go to User Settings > Applications then create an application as shown
        ![image-2.png](./images/image-2.png)
    * Copy the Application ID and Secret from GitLab into Client ID and Secret key 
    * Double click on localhost:8000 to move it into **Chosen sites** and click **SAVE**
        ![image-1.png](./images/image-1.png)

10. Add Github SSO as follows -
    * Go to Settings > Developer Settings > OAuth Apps > New OAuth App and fill as shown
        ![image-3.png](./images/image-3.png)
    * Copy the Client ID and a Client secret from Github into Client ID and Secret key
    * Double click on localhost:8000 to move it into **Chosen sites** and click **SAVE**
        ![image-4.png](./images/image-4.png)
