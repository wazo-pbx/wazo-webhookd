# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.rest_api_helpers import APIException


class TokenWithUserUUIDRequiredError(APIException):

    def __init__(self):
        super(TokenWithUserUUIDRequiredError, self).__init__(
            status_code=400,
            message='A valid token with a user UUID is required',
            error_id='token-with-user-uuid-required',
        )


class HookRetry(Exception):
    def __init__(self, detail):
        self.detail = detail
        super(HookRetry, self).__init__()
