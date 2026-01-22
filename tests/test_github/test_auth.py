"""Tests for GitHub App authentication."""

import time
from unittest.mock import patch

from pr_slop_stopper.github.auth import create_jwt

# Sample RSA private key for testing (NOT a real key, just for tests)
TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MfszRBvMqGslP+Ap
NP9P4UM8f5oo/6Q9rdLbqNPDvoP+1zDqcgWvP+ofW1FQAQQhU3nq2f7VZBuVtk9a
2Fw/XT8uzZla2uJWsT+c3eCUWgU8m8HrL8h1y6cXyJEp1zVHQFVvZSHuAGdF7lAm
R1EPDzMBGGk1/E+AMgw/hN1MiPDMEJYBxLQH8pJRssmJvBqZs5ADYR+MeHj1ZMvC
eOMYvoH1Iday7WQpA2LqJ7LIzSdwSPn+rIwsyFnRPbBqxP8i9VgQ8CYvH3EYFa+3
N+B+2H1sHjW4k9VBAVPJ9dq4ThTpSI7KLXkKawIDAQABAoIBAC3r4d2bKuJpxFN3
GR6F7A+p2aYA3x+C5F7F0V6GdR9f5T0M1Kb5SdDPnVD5QzPQ5KAI5r+JXxJkFDqH
MdGHZdPKL+K6BPn3Md6PrMLmHj3WW5nkJMrRxDjvYOhpMm3MKxQDJ5h9dO5HvJCu
c5V3JvRE5JMmIJHAG5F3DlPHDPg+DVhf3R9ZG5E+1XQnJRAKJTMh2n9HgM7QSPXJ
k7JMPnOIKFtL9t6J1SKXB3x3JB3c9b8iAGcRjT3dF3q5A5FQBQW5DFJ1h7hvA6Q5
2nEvPX0XdD5dFd3E5X7rQFi0Z7UPFQK3F3b0q3QaE6A8F2QXJA1s8R8sA5TdXvbD
j2A9NUECgYEA7Yq7n3F+X6F8qF9E5E4zF3J1x3zF7B3F5F3E5F4zF3E5F3E5F3E5
F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5
F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3E5F3ECgYEA4Z3VS5JJ
cds3xfn/ygWyF8PbnGy0AHB7MfszRBvMqGslP+ApNP9P4UM8f5oo/6Q9rdLbqNPD
voP+1zDqcgWvP+ofW1FQAQQhU3nq2f7VZBuVtk9a2Fw/XT8uzZla2uJWsT+c3eCU
WgU8m8HrL8h1y6cXyJEp1zVHQFVvZSHuAGdF7lAmR1ECgYEAx3VS5JJcds3xfn/y
gWyF8PbnGy0AHB7MfszRBvMqGslP+ApNP9P4UM8f5oo/6Q9rdLbqNPDvoP+1zDqc
gWvP+ofW1FQAQQhU3nq2f7VZBuVtk9a2Fw/XT8uzZla2uJWsT+c3eCUWgU8m8HrL
8h1y6cXyJEp1zVHQFVvZSHuAGdF7lAmR1EPDzMBGGk1/E+AMgw/hN1MiPDMEJYBx
LQH8pJRssmJvBqZs5ADYR+MeHj1ZMvCeOMYvoH1Iday7WQpA2LqJ7LIzSdwSPn+r
IwsyFnRPbBqxP8i9VgQ8CYvH3EYFa+3N+B+2H1sHjW4k9VBAVPJ9dq4ThTpSI7KL
XkKawIECgYB5JJcds3xfn/ygWyF8PbnGy0AHB7MfszRBvMqGslP+ApNP9P4UM8f5
oo/6Q9rdLbqNPDvoP+1zDqcgWvP+ofW1FQAQQhU3nq2f7VZBuVtk9a2Fw/XT8uzZ
la2uJWsT+c3eCUWgU8m8HrL8h1y6cXyJEp1zVHQFVvZSHuAGdF7lAmR1EPDzMBGG
k1/E+AMgw/hN1MiPDMEJYBxLQH8pJRssmJvBqZs5ADYR+MeHj1ZMvCeOMYvoH1Id
ay7WQpA2LqJ7LIzSdwSPn+rIwsyFnRPbBqxP8i9VgQ8CYvH3EYFa+3N+B+2H1sHj
W4k9VBA=
-----END RSA PRIVATE KEY-----"""


class TestCreateJWT:
    """Tests for JWT creation."""

    def test_jwt_has_required_claims(self) -> None:
        """Test that JWT contains required claims."""
        # Use mock to avoid needing a real RSA key
        with patch("pr_slop_stopper.github.auth.jwt.encode") as mock_encode:
            mock_encode.return_value = "mock_token"

            create_jwt(app_id=12345, private_key="fake_key")

            # Check that encode was called with correct payload structure
            call_args = mock_encode.call_args
            payload = call_args[0][0]

            assert "iat" in payload
            assert "exp" in payload
            assert "iss" in payload
            assert payload["iss"] == 12345

    def test_jwt_expiration_is_10_minutes(self) -> None:
        """Test that JWT expires in ~10 minutes."""
        with patch("pr_slop_stopper.github.auth.jwt.encode") as mock_encode:
            mock_encode.return_value = "mock_token"

            create_jwt(app_id=12345, private_key="fake_key")

            call_args = mock_encode.call_args
            payload = call_args[0][0]

            # exp should be ~10 minutes after iat
            # iat is now - 60, exp is now + 600
            # So exp - iat should be about 660 seconds
            time_diff = payload["exp"] - payload["iat"]
            assert 650 <= time_diff <= 670

    def test_jwt_uses_rs256_algorithm(self) -> None:
        """Test that JWT uses RS256 algorithm."""
        with patch("pr_slop_stopper.github.auth.jwt.encode") as mock_encode:
            mock_encode.return_value = "mock_token"

            create_jwt(app_id=12345, private_key="fake_key")

            call_args = mock_encode.call_args
            assert call_args[1]["algorithm"] == "RS256"

    def test_jwt_iat_has_clock_skew_adjustment(self) -> None:
        """Test that iat is backdated for clock skew."""
        with patch("pr_slop_stopper.github.auth.jwt.encode") as mock_encode:
            mock_encode.return_value = "mock_token"

            before = int(time.time())
            create_jwt(app_id=12345, private_key="fake_key")

            call_args = mock_encode.call_args
            payload = call_args[0][0]

            # iat should be about 60 seconds before current time
            assert payload["iat"] < before
            assert payload["iat"] >= before - 62  # Allow 2 second tolerance
