FROM  python:3.11
WORKDIR /STAGING_APP
RUN apt-get update && apt-get -y upgrade &&  apt-get install -y git ca-certificates curl gnupg
RUN curl -sSL https://get.docker.com/ | sh
ENV PYTHONUNBUFFERED 1
EXPOSE 8000
COPY requirements.txt ./
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . ./