FROM python:3.10-slim-buster
RUN mkdir -p /usr/src/bot
WORKDIR /usr/src/bot
COPY setup.py .
COPY README.md .
COPY ptn ptn
RUN pip3 install .
RUN mkdir /root/.config
RUN mkdir /root/mab
RUN ln -s /root/mab/praw.ini /root/.config/praw.ini
RUN ln -s /root/mab/.env /root/.env
ENV PTN_MAB_RESOURCE_DIR=/usr/src/bot/ptn/missionalertbot/resources
ENV PTN_MAB_DATA_DIR=/root/mab
WORKDIR /root/mab
ENTRYPOINT ["/usr/local/bin/missionalertbot"]
