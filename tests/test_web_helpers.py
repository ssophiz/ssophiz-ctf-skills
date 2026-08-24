from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ssophiz_ctf.web import (
    ScopedWebSession,
    TargetScope,
    build_ffmpeg_hls_probe_cases,
    itsdangerous_dump,
    itsdangerous_load,
    jwt_decode,
    jwt_sign_hs256,
    run_bounded_race,
    target_operations_enabled,
)


class _Response:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body
        self.headers = {"Content-Type": "text/plain"}

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return self._body


class _Opener:
    def __init__(self) -> None:
        self.calls = 0

    def open(self, request: object, timeout: float) -> _Response:
        self.calls += 1
        return _Response(502 if self.calls == 1 else 200, b"ok")


class WebHelperTests(unittest.TestCase):
    def test_jwt_hs256_round_trip_and_tamper_rejection(self) -> None:
        token = jwt_sign_hs256({"sub": "admin"}, "challenge-secret")
        self.assertEqual(jwt_decode(token, "challenge-secret")["payload"]["sub"], "admin")
        unverified = jwt_decode(token, verify_signature=False)
        self.assertFalse(unverified["signature_verified"])
        with self.assertRaises(ValueError):
            jwt_decode(token, "wrong-secret")

    def test_jwt_headers_cannot_override_algorithm(self) -> None:
        with self.assertRaises(ValueError):
            jwt_sign_hs256({"sub": "x"}, "secret", {"alg": "none"})

    def test_itsdangerous_round_trip(self) -> None:
        token = itsdangerous_dump({"role": "admin"}, "challenge-secret", salt="cookie")
        self.assertEqual(itsdangerous_load(token, "challenge-secret", salt="cookie"), {"role": "admin"})
        with self.assertRaises(ValueError):
            itsdangerous_load(token, "wrong-secret", salt="cookie")

    def test_target_scope_is_opt_in_and_exact_origin_locked(self) -> None:
        with self.assertRaises(PermissionError):
            TargetScope(("https://ctf.example",), enabled=False).validate_url("https://ctf.example/a")
        scope = TargetScope(("https://ctf.example", "web.ctf.example:8080"), enabled=True)
        self.assertEqual(scope.validate_url("https://ctf.example/a?x=1"), "https://ctf.example/a?x=1")
        self.assertEqual(scope.validate_url("http://web.ctf.example:8080/x"), "http://web.ctf.example:8080/x")
        with self.assertRaises(PermissionError):
            scope.validate_url("https://outside.example/a")

    def test_session_retries_transient_gateway_status(self) -> None:
        session = ScopedWebSession(TargetScope(("https://ctf.example",), enabled=True), retries=1, backoff_seconds=0)
        opener = _Opener()
        session.opener = opener  # type: ignore[assignment]
        response = session.request("GET", "https://ctf.example/status")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.attempts, 2)
        self.assertEqual(opener.calls, 2)
        with self.assertRaises(ValueError):
            session.request("GET", "https://ctf.example/status", headers={"Host": "outside.example"})

    def test_bounded_race_caps_attempts(self) -> None:
        result = run_bounded_race(lambda index, deadline: index, attempts=6, workers=3, timeout_seconds=1)
        self.assertEqual(len(result["attempts"]), 6)
        self.assertEqual(result["completed"], 6)
        with self.assertRaises(ValueError):
            run_bounded_race(lambda index, deadline: index, attempts=129, workers=1)

    def test_ffmpeg_matrix_uses_only_supplied_dummy_uri(self) -> None:
        cases = build_ffmpeg_hls_probe_cases("file:///workspace/dummy.bin")
        self.assertIn("ext-x-map", cases)
        self.assertIn("cache-segment", cases)
        self.assertTrue(all("http://" not in value and "https://" not in value for value in cases.values()))

    def test_target_gate_requires_contract_and_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(target_operations_enabled(True))
        with patch.dict(os.environ, {"SSOPHIZ_ENABLE_TARGETS": "1"}, clear=True):
            self.assertTrue(target_operations_enabled(True))
            self.assertFalse(target_operations_enabled(False))


if __name__ == "__main__":
    unittest.main()
