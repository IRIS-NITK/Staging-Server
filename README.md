<br/>
<p align="center">
  <h3 align="center">Staging-Server</h3>

-------------------

![](/docs/images/repo.png)
  <p align="center">
    Developed by IRIS-NITK, Staging-Server is a Django based web platform designed to streamline the deployment and testing of dockerized applications using Docker and Nginx. This project aims to simplify the testing process for developers and testers, ensuring that applications are thoroughly examined before they go into production.
  </p>
</p>


[Setup Instructions](/docs/SETUP.md)

[Report Bug / Request Feature](https://github.com/iris-NITK/Staging-Server/issues)

![Contributors](https://img.shields.io/github/contributors/iris-NITK/Staging-Server?color=dark-green) ![Issues](https://img.shields.io/github/issues/iris-NITK/Staging-Server) ![License](https://img.shields.io/github/license/iris-NITK/Staging-Server) 

---------------------
## Features:

- Deploy your code to a staging area with just a few clicks using a GUI.
- Deploy with any GIT clone URL.
- Configure nginx automatically for your deployments at a subdomain.
- View real-time deployment and container logs with a text search feature.
- Have finer control over deployments, including passing environmental variables and connecting a database container.
- Access the container through an interactive xterm.js based terminal.
- Deploy asynchronously.
- Pass mounts to the container.
- Configure pre and post deployment scripts.

## Limitations:

- Not meant to be used for production.
- It does not handle scaling of different services.
- There are no database backups.

---------------------

## Screenshots

#### Repository Dashboard with finer control over deployments

![](/docs/images/repo_dashboard.png)