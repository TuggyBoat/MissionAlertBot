# To build a new docker image

$ docker build -t yourname/missionalertbot:latest .

# To run in a container

Make a local dir to store your .env and database files

$ mkdir /opt/missionalertbot
$ cp .env /opt/missionalertbot/
$ cp praw.ini /opt/missionalertbot/

Run the container:

$ docker run -d --restart unless-stopped --name missionalertbot -v /opt/missionalertbot:/root/mab yourname/missionalertbot:latest
