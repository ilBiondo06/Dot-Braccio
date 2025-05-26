import pytest
from unittest.mock import MagicMock, patch
from registration import parse_args, PAYLOAD_MODES, prompt_for_new_params

def test_payload_modes_contains_expected():
    expected = [
        "custom4", "orientQuat", "completeQuat", "extQuat", "orientEul", "mfm"
    ]
    for mode in expected:
        assert mode in PAYLOAD_MODES

def test_parse_args_valid(monkeypatch):
    test_args = ["registration.py", "General", "custom4", "10", "30", "show"]
    monkeypatch.setattr("sys.argv", test_args)
    args = parse_args()
    assert args.filter_profile == "General"
    assert args.payload_mode == "custom4"
    assert args.duration == 10
    assert args.output_rate == 30
    assert args.show == "show"

def test_prompt_for_new_params_keep_all(monkeypatch):
    inputs = ["", "", "", "", ""]
    monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))
    current = {
        "payload_mode": "custom4",
        "duration": 10,
        "output_rate": 30,
        "show": "show"
    }
    updated = prompt_for_new_params(current.copy())
    assert updated == current
