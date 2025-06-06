"""
Copyright (c) 2023, Zscaler Inc.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

import pytest

from tests.integration.zia.conftest import MockZIAClient
from tests.test_utils import generate_random_string


@pytest.fixture
def fs():
    yield


class TestURLFilteringRule:
    """
    Integration Tests for the ZIA URL Filtering Rule
    """

    def test_url_filtering_rule(self, fs):
        client = MockZIAClient(fs)
        errors = []
        rule_id = None

        try:
            # Create a url filtering Rule
            rule_name = "tests-" + generate_random_string()
            rule_description = "tests-" + generate_random_string()
            created_rule, _, error = client.zia.url_filtering.add_rule(
                name=rule_name,
                description=rule_description,
                enabled=True,
                action="BLOCK",
                order=1,
                rank=7,
                url_categories=["ANY"],
                protocols=["ANY_RULE"],
                device_trust_levels=[
                    "UNKNOWN_DEVICETRUSTLEVEL",
                    "LOW_TRUST",
                    "MEDIUM_TRUST",
                    "HIGH_TRUST",
                ],
                user_agent_types=[
                    "OPERA",
                    "FIREFOX",
                    "MSIE",
                    "MSEDGE",
                    "CHROME",
                    "SAFARI",
                    "MSCHREDGE",
                    "OTHER",
                ],
                user_risk_score_levels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                request_methods=[
                    "CONNECT",
                    "DELETE",
                    "GET",
                    "HEAD",
                    "OPTIONS",
                    "OTHER",
                    "POST",
                    "PUT",
                    "TRACE",
                ],
            )
            assert error is None, f"URL Filtering Rule creation failed: {error}"
            assert created_rule is not None, "URL Filtering Rule creation returned None"
            rule_id = created_rule.id
        except Exception as exc:
            errors.append(f"URL Filtering Rule creation failed: {exc}")

        # Step 4: Retrieve the URL Filtering Rule by ID
        try:
            retrieved_rule, _, error = client.zia.url_filtering.get_rule(rule_id)
            assert error is None, f"Error retrieving URL Filtering Rule: {error}"
            assert retrieved_rule is not None, "Retrieved URL Filtering Rule is None"
            assert retrieved_rule.id == rule_id, "Incorrect rule retrieved"
        except Exception as exc:
            errors.append(f"Retrieving URL Filtering Rule failed: {exc}")

            # Step 5: Update the URL Filtering Rule
            try:
                updated_description = "Updated integration test URL Filtering Rule"
                updated_rule, _, error = client.zia.url_filtering.update_rule(
                    rule_id=rule_id,
                    name=rule_name,
                    description=updated_description,
                    enabled=True,
                    action="BLOCK",
                    order=1,
                    rank=7,
                    url_categories=["ANY"],
                    protocols=["ANY_RULE"],
                    device_trust_levels=[
                        "UNKNOWN_DEVICETRUSTLEVEL",
                        "LOW_TRUST",
                        "MEDIUM_TRUST",
                        "HIGH_TRUST",
                    ],
                    user_agent_types=[
                        "OPERA",
                        "FIREFOX",
                        "MSIE",
                        "MSEDGE",
                        "CHROME",
                        "SAFARI",
                        "MSCHREDGE",
                        "OTHER",
                    ],
                    user_risk_score_levels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    request_methods=[
                        "CONNECT",
                        "DELETE",
                        "GET",
                        "HEAD",
                        "OPTIONS",
                        "OTHER",
                        "POST",
                        "PUT",
                        "TRACE",
                    ],
                )
                assert error is None, f"Error updating URL Filtering Rule: {error}"
                assert updated_rule is not None, "Updated URL Filtering Rule is None"
                assert (
                    updated_rule.description == updated_description
                ), f"URL Filtering Rule update failed: {updated_rule.as_dict()}"
            except Exception as exc:
                errors.append(f"Updating URL Filtering Rule failed: {exc}")

            # Step 6: List URL Filtering and verify the rule is present
            try:
                rules, _, error = client.zia.url_filtering.list_rules()
                assert error is None, f"Error listing URL Filtering Rules: {error}"
                assert rules is not None, "URL Filtering list is None"
                assert any(rule.id == rule_id for rule in rules), "Newly created rule not found in the list of rules."
            except Exception as exc:
                errors.append(f"Listing URL Filtering Rules failed: {exc}")

        finally:
            cleanup_errors = []
            try:
                if rule_id:
                    # Delete the URL Filtering Rule
                    _, _, error = client.zia.url_filtering.delete_rule(rule_id)
                    assert error is None, f"Error deleting URL Filtering Rule: {error}"
            except Exception as exc:
                cleanup_errors.append(f"Deleting URL Filtering Rule failed: {exc}")

            errors.extend(cleanup_errors)

        if errors:
            raise AssertionError(f"Integration Test Errors:\n{chr(10).join(errors)}")
