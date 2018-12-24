# -- encoding: UTF-8 --

from __future__ import unicode_literals

import pytest
from django.contrib import auth
from django.core.cache import cache

from qsessions import IP_SESSION_KEY, USER_AGENT_SESSION_KEY
from qsessions.backends.cached_db import SessionStore
from qsessions.models import Session


@pytest.mark.django_db
def test_get_decoded():
    store = SessionStore(user_agent='TestUA/1.1', ip='127.0.0.1')
    store[auth.SESSION_KEY] = 1
    store['foo'] = 'bar'
    store.save()

    session = Session.objects.get(pk=store.session_key)
    assert session.get_decoded() == {
        'foo': 'bar',
        auth.SESSION_KEY: 1,
        IP_SESSION_KEY: '127.0.0.1',
        USER_AGENT_SESSION_KEY: 'TestUA/1.1'
    }


@pytest.mark.django_db
def test_very_long_ua():
    ua = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; ELT; ' \
         'BTRS29395; Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1) ;  ' \
         'Embedded Web Browser from: http://bsalsa.com/; .NET CLR 2.0.50727; ' \
         '.NET CLR 3.0.04506.30; .NET CLR 3.0.04506.648; .NET CLR 3.5.21022; ' \
         '.NET CLR 1.1.4322; ELT; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; FDM; ' \
         '.NET4.0C; .NET4.0E; ELT)'
    store = SessionStore(user_agent=ua, ip='127.0.0.1')
    store.save()

    session = Session.objects.get(pk=store.session_key)
    assert session.user_agent == ua[:300]


def test_location():
    session = Session(ip='89.160.20.112')
    assert session.location() == 'Linköping, Sweden'
    loc_info = session.location_info()
    assert loc_info['city'] == 'Linköping'
    assert loc_info['country_code'] == 'SE'

    # This depends on Django version, so be safe
    assert loc_info.get('continent_code') == 'EU' or loc_info.get('region') == 'E'


def test_device():
    session = Session(user_agent=(
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/70.0.3538.102 Safari/537.36'
    ))
    device = session.device()
    assert device.os.family == 'Mac OS X'
    assert device.browser.family == 'Chrome'


@pytest.mark.django_db
def test_bulk_delete_from_both_cache_and_db():
    s1 = SessionStore(session_key='test1', user_agent='Python/2.7', ip='127.0.0.1')
    s1.create()
    s2 = SessionStore(session_key='test2', user_agent='Python/2.7', ip='127.0.0.1')
    s2.create()
    s3 = SessionStore(session_key='test3', user_agent='TestUA/1.1', ip='127.0.0.1')
    s3.create()
    assert cache.get(SessionStore.cache_key_prefix + s1.session_key) is not None
    assert cache.get(SessionStore.cache_key_prefix + s2.session_key) is not None
    assert cache.get(SessionStore.cache_key_prefix + s3.session_key) is not None

    Session.objects.filter(user_agent='Python/2.7').delete()

    assert cache.get(SessionStore.cache_key_prefix + s1.session_key) is None
    assert cache.get(SessionStore.cache_key_prefix + s2.session_key) is None
    assert cache.get(SessionStore.cache_key_prefix + s3.session_key) is not None
