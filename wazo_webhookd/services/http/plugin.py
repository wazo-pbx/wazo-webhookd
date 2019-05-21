# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
import requests
import socket
import urllib.parse

from jinja2 import Environment

from wazo_webhookd.exceptions import HookRetry


logger = logging.getLogger(__name__)

REQUESTS_TIMEOUT = 5  # seconds


class Service:
    def load(self, dependencies):
        pass

    @classmethod
    def run(cls, task, config, subscription, event):
        options = subscription['config']
        headers = {}
        values = {
            'event_name': event['name'],
            'event': event['data'],
            'wazo_uuid': event['origin_uuid'],
        }

        url = options['url']
        template = url
        url = Environment().from_string(template).render(values)

        if subscription['owner_user_uuid'] and cls.url_is_localhost(url):
            # some services only listen on 127.0.0.1 and should not be accessible to users
            logger.warning('Rejecting callback from user "%s" to url "%s": remote host is localhost!',
                           subscription['owner_user_uuid'],
                           url)
            return

        content_type = options.get('content_type')

        body = options.get('body')
        if body:
            template = body
            body = Environment().from_string(template).render(values)
            body = body.encode('utf-8')
        else:
            body = json.dumps(event['data'])
            content_type = 'application/json'

        if content_type:
            headers['Content-Type'] = content_type

        verify = options.get('verify_certificate')
        if verify:
            verify = True if verify == 'true' else verify
            verify = False if verify == 'false' else verify

        try:
            with requests.request(
                options['method'],
                url,
                data=body,
                verify=verify,
                headers=headers,
                # NOTE(sileht): This is only about TCP timeout issue, not the
                # while HTTP call
                timeout=REQUESTS_TIMEOUT,
                # NOTE(sileht): We don't care of the body, and we don't want to
                # download gigabytes of data for nothing or having the http
                # connection frozen because the server doesn't return the full
                # body. So stream the response, and the context manager with
                # close the request a soon as it return or raise a exception.
                # No body will be read ever.
                stream=True
            ) as r:
                r.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if exc.response.status_code == 410:
                logger.info("http request fail, service is gone ({}/{}): "
                            "'{} {} [{}]' {}".format(
                                task.request.retries,
                                task.max_retries,
                                options['method'],
                                url,
                                exc.response.status_code,
                                exc.response.text
                            ))
            else:
                logger.info("http request fail, retrying ({}/{}): "
                            "'{} {} [{}]' {}".format(
                                task.request.retries,
                                task.max_retries,
                                options['method'],
                                url,
                                exc.response.status_code,
                                exc.response.text
                            ))
                raise HookRetry({
                    "error": str(exc),
                    "method": options["method"],
                    "url": url,
                    "status_code": exc.response.status_code,
                    "headers": dict(exc.response.headers),
                    "body": exc.response.text,
                })

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects
        ) as exc:
            logger.info("http request fail, retrying ({}/{}): {}".format(
                task.request.retries,
                task.max_retries,
                options['method'],
                url,
                exc
            ))
            raise HookRetry({
                "error": str(exc),
                "method": options["method"],
                "url": url,
                "status_code": None,
                "headers": {},
                "body": "",
            })

    @staticmethod
    def url_is_localhost(url):
        remote_host = urllib.parse.urlparse(url).hostname
        remote_address = socket.gethostbyname(remote_host)
        return remote_address == '127.0.0.1'
