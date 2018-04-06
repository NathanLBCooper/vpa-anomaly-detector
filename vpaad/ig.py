# -*- coding:utf-8 -*-
import logging
import traceback
from trading_ig import IGService, IGStreamService

LOGGER = logging.getLogger(__name__)


def create_ig_service(credentials):
    LOGGER.info(
        "Creating service with user:%s, api_key:%s, password:<hidden>",
        credentials["username"], credentials["api_key"])
    return IGService(
        credentials["username"],
        credentials["password"],
        credentials["api_key"])


def create_ig_stream_service(ig_service):
    return IGStreamService(ig_service)


def create_ig_session(ig_service):
    try:
        return ig_service.create_session()
    except KeyError:
        LOGGER.error(traceback.format_exc())
        LOGGER.error(
            "Error establishing IG session. Check that your credentials "
            "are correct in your configuration JSON file. If it's correct, "
            "your account might be blacklisted. Contact ig.com to fix it.")
        raise


def verify_stream_service_account(ig_stream_service, credentials):
    ig_session = create_ig_session(ig_stream_service)
    # Ensure configured account is selected
    accounts = ig_session[u'accounts']
    accountId = None

    for account in accounts:
        if account[u'accountId'] == credentials["acc_number"]:
            return account[u'accountId']

    if accountId is None:
        raise ValueError(
           'Account not found: {0} in {1}'.format(
               credentials["acc_number"], accounts))
