import unittest
from unittest.mock import Mock, patch

import requests

from src.review.email_delivery import (
    EMAIL_TIMEOUT_SECONDS,
    RESEND_EMAIL_URL,
    EmailConfigurationError,
    email_delivery_status,
    email_sender_from_env,
    resend_sender_from_env,
)


class ResendEmailDeliveryTests(unittest.TestCase):
    def environment(self, **updates):
        values = {
            "REVIEWER_EMAIL_BACKEND": "resend",
            "REVIEWER_EMAIL_FROM": "DMV Bus Stops <login@dmvbusstop.org>",
            "RESEND_API_KEY": "re_test_secret",
        }
        values.update(updates)
        return values

    @patch("src.review.email_delivery.requests.post")
    def test_success_uses_https_api_and_existing_plain_text_content(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {"id": "email_123"}
        post.return_value = response

        email_sender_from_env(self.environment())(
            "reviewer@example.org",
            "https://dmvbusstop.org/reviewer/verify?token=private-token",
            20,
        )

        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual((RESEND_EMAIL_URL,), args)
        self.assertEqual(EMAIL_TIMEOUT_SECONDS, kwargs["timeout"])
        self.assertEqual("Bearer re_test_secret", kwargs["headers"]["Authorization"])
        self.assertEqual(["reviewer@example.org"], kwargs["json"]["to"])
        self.assertEqual("Sign in to DMV Bus Stops", kwargs["json"]["subject"])
        self.assertIn("private-token", kwargs["json"]["text"])
        self.assertIn("expires in 20 minutes", kwargs["json"]["text"])

    def test_non_success_responses_fail_without_provider_or_message_secrets(self):
        secrets = (
            "re_test_secret", "private-token", "reviewer@example.org",
            "https://dmvbusstop.org/reviewer/verify",
        )
        for status in (400, 500):
            response = Mock(status_code=status)
            response.json.return_value = {"message": "provider detail re_test_secret"}
            with self.subTest(status=status), patch(
                "src.review.email_delivery.requests.post", return_value=response
            ), self.assertRaises(RuntimeError) as raised:
                resend_sender_from_env(self.environment())(
                    "reviewer@example.org",
                    "https://dmvbusstop.org/reviewer/verify?token=private-token", 20,
                )
            rendered = str(raised.exception)
            self.assertTrue(all(secret not in rendered for secret in secrets))

    def test_timeout_and_network_errors_fail_closed(self):
        for failure in (
            requests.Timeout("private-token"),
            requests.exceptions.ProxyError("re_test_secret"),
        ):
            with self.subTest(failure=type(failure).__name__), patch(
                "src.review.email_delivery.requests.post", side_effect=failure
            ), self.assertRaisesRegex(RuntimeError, "^Resend email delivery failed$"):
                resend_sender_from_env(self.environment())(
                    "reviewer@example.org", "https://example.org/?token=private-token", 20
                )

    def test_invalid_configuration_and_missing_api_key_are_unavailable(self):
        invalid = (
            self.environment(RESEND_API_KEY=""),
            self.environment(REVIEWER_EMAIL_FROM=""),
            self.environment(REVIEWER_EMAIL_FROM="not-an-address"),
            self.environment(REVIEWER_EMAIL_FROM="Good <good@example.org> trailing"),
        )
        for environment in invalid:
            with self.subTest(environment=environment), self.assertRaises(
                EmailConfigurationError
            ):
                resend_sender_from_env(environment)
            status = email_delivery_status(environ=environment)
            self.assertFalse(status["available"])
            self.assertEqual("resend", status["backend"])

    @patch("src.review.email_delivery.requests.post")
    def test_malformed_provider_response_fails_closed(self, post):
        responses = []
        for payload in ({}, {"id": ""}, [], None):
            response = Mock(status_code=200)
            response.json.return_value = payload
            responses.append(response)
        invalid_json = Mock(status_code=200)
        invalid_json.json.side_effect = ValueError("private provider response")
        responses.append(invalid_json)
        post.side_effect = responses

        sender = resend_sender_from_env(self.environment())
        for _response in responses:
            with self.assertRaisesRegex(RuntimeError, "^Resend email delivery failed$"):
                sender("reviewer@example.org", "https://example.org/?token=secret", 20)

    def test_resend_does_not_require_smtp_configuration(self):
        status = email_delivery_status(environ=self.environment())
        self.assertEqual({"available": True, "backend": "resend"}, status)


if __name__ == "__main__":
    unittest.main()
