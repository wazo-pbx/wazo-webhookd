FROM python:3.7-slim-buster AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get -q update
RUN apt-get -yq install gcc

COPY . /usr/src/wazo-webhookd
WORKDIR /usr/src/wazo-webhookd
RUN pip install -r requirements.txt
RUN python setup.py install

FROM python:3.7-slim-buster AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-webhookd /etc/wazo-webhookd
RUN true \
    && adduser --quiet --system --group wazo-webhookd \
    && mkdir -p /etc/wazo-webhookd/conf.d \
    && install -o wazo-webhookd -g wazo-webhookd -d /run/wazo-webhookd \
    && install -o wazo-webhookd -g wazo-webhookd /dev/null /var/log/wazo-webhookd.log

EXPOSE 9300

# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-webhookd"]
