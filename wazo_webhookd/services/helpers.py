# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import contextlib
import json
import logging

# TODO(sileht): move the http plugin to httpx too.
import requests
import httpx

logger = logging.getLogger(__name__)


class HookExpectedError(Exception):
    def __init__(self, detail):
        self.detail = detail
        super().__init__()


class HookRetry(Exception):
    def __init__(self, detail):
        self.detail = detail
        super().__init__()


def _decode(data):
    if isinstance(data, bytes):
        text = data.decode()
    else:
        text = data

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


@contextlib.contextmanager
def requests_automatic_hook_retry(task):
    try:
        yield
    except (requests.exceptions.HTTPError, httpx.exceptions.HTTPError) as exc:
        if isinstance(exc.request, requests.PreparedRequest):
            req_data = exc.request.body
        else:
            req_data = exc.request.content
        if exc.response.status_code == 410:
            logger.info(
                "http request fail, service is gone (%d/%d): '%s %s [%s]' %s",
                task.request.retries,
                task.max_retries,
                exc.request.method,
                exc.request.url,
                exc.response.status_code,
                _decode(exc.response.text),
            )
            raise HookExpectedError(
                {
                    "error": str(exc),
                    "request_method": exc.request.method,
                    "request_url": str(exc.request.url),
                    "request_body": _decode(req_data),
                    "request_headers": dict(exc.request.headers),
                    "response_status_code": exc.response.status_code,
                    "response_headers": dict(exc.response.headers),
                    "response_body": _decode(exc.response.text),
                }
            )
        else:
            logger.info(
                "http request fail, retrying (%s/%s): '%s %s [%s]' %s",
                task.request.retries,
                task.max_retries,
                exc.request.method,
                exc.request.url,
                exc.response.status_code,
                _decode(exc.response.text),
            )
            raise HookRetry(
                {
                    "error": str(exc),
                    "request_method": exc.request.method,
                    "request_url": str(exc.request.url),
                    "request_body": _decode(req_data),
                    "request_headers": dict(exc.request.headers),
                    "response_status_code": exc.response.status_code,
                    "response_headers": dict(exc.response.headers),
                    "response_body": _decode(exc.response.text),
                }
            )

    except (
        httpx.exceptions.Timeout,
        httpx.exceptions.TooManyRedirects,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.TooManyRedirects,
    ) as exc:
        logger.info(
            "http request fail, retrying (%s/%s): '%s %s [%s]'",
            task.request.retries,
            task.max_retries,
            exc.request.method,
            exc.request.url,
            exc,
        )
        if isinstance(exc.request, requests.PreparedRequest):
            req_data = exc.request.body
        else:
            req_data = exc.request.content
        raise HookRetry(
            {
                "error": str(exc),
                "request_method": exc.request.method,
                "request_url": str(exc.request.url),
                "request_body": _decode(req_data),
                "request_headers": dict(exc.request.headers),
                "response_status_code": None,
                "response_headers": {},
                "response_body": "",
            }
        )


def requests_automatic_detail(response):
    if isinstance(response.request, requests.PreparedRequest):
        req_data = response.request.body
    else:
        req_data = response.request.content
    return {
        "request_method": response.request.method,
        "request_url": str(response.request.url),
        "request_body": _decode(req_data),
        "request_headers": dict(response.request.headers),
        "response_status_code": response.status_code,
        "response_headers": dict(response.headers),
        "response_body": _decode(response.text),
    }
