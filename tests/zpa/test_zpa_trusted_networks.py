# -*- coding: utf-8 -*-

# Copyright (c) 2023, Zscaler Inc.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import pytest
import responses
from box import Box, BoxList

from tests.conftest import stub_sleep


# Don't need to test the data structure as we just have list and get
# methods available. id will suffice until add/update endpoints are available.
@pytest.fixture(name="trusted_networks")
def fixture_trusted_networks():
    return {"totalPages": 1, "list": [{"id": "1"}, {"id": "2"}]}


@responses.activate
@stub_sleep
def test_list_networks(zpa, trusted_networks):
    responses.add(
        responses.GET,
        url="https://config.private.zscaler.com/mgmtconfig/v2/admin/customers/1/network?page=1",
        json=trusted_networks,
        status=200,
    )
    responses.add(
        responses.GET,
        url="https://config.private.zscaler.com/mgmtconfig/v2/admin/customers/1/network?page=2",
        json=[],
        status=200,
    )
    resp = zpa.trusted_networks.list_networks()
    assert isinstance(resp, BoxList)
    assert len(resp) == 2
    assert resp[0].id == "1"


@responses.activate
def test_get_network(zpa, trusted_networks):
    responses.add(
        responses.GET,
        url="https://config.private.zscaler.com/mgmtconfig/v1/admin/customers/1/network/1",
        json=trusted_networks["list"][0],
        status=200,
    )
    resp = zpa.trusted_networks.get_network("1")
    assert isinstance(resp, Box)
    assert resp.id == "1"