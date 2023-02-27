""" GNodeRegistry Models Definition """

import logging
import time
import uuid

from django.db import models


LOG_FORMAT = (
    "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) "
    "-35s %(lineno) -5d: %(message)s"
)
LOGGER = logging.getLogger(__name__)


def rand_guid():
    uuid_value = uuid.uuid4()
    string_value = uuid_value.urn[9:]
    return string_value


def now_unix_s():
    return int(time.time())


class MessageDb(models.Model):
    time_created_unix_ns = models.BigIntegerField()
    payload_id = models.CharField(max_length=210, primary_key=True)
    from_alias = models.CharField(max_length=210, primary_key=True)
    type_name = models.CharField(max_length=210, primary_key=True)
    id = models.CharField(max_length=210, primary_key=True)


class PayloadDb(models.Model):
    id = models.CharField(max_length=210, primary_key=True)
    content = models.BinaryField()
