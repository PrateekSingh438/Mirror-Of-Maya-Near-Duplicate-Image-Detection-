"""Regression test for the Manager tab's selection controls.

Guards a real bug: Streamlit ignores a checkbox's `value=` once the widget
has persisted state under its key, so 'Select all' / 'Clear selection' used
to be silently undone by the stale visible checkboxes on the next rerun.
The fix keys checkboxes with a generation counter; this test drives the
actual tab UI to make sure the flow keeps working."""
import os

from streamlit.testing.v1 import AppTest

HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "harness_manager.py")


def _button(at, label):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"button {label!r} not found"
    return matches[0]


def _run_harness():
    at = AppTest.from_file(HARNESS, default_timeout=120).run()
    assert not at.exception, at.exception
    return at


def test_select_all_checks_every_visible_box_and_fills_queue():
    at = _run_harness()
    assert len(at.checkbox) == 3
    assert all(not b.value for b in at.checkbox)

    _button(at, "Select all duplicates").click()
    at.run()
    assert not at.exception, at.exception
    assert all(b.value for b in at.checkbox)
    assert len(at.session_state["deletion_queue"]) == 3
    assert any("Move 3 files to trash" in b.label for b in at.button)


def test_unchecking_one_box_removes_it_from_queue():
    at = _run_harness()
    _button(at, "Select all duplicates").click()
    at.run()

    list(at.checkbox)[0].uncheck()
    at.run()
    assert not at.exception, at.exception
    assert len(at.session_state["deletion_queue"]) == 2


def test_clear_selection_empties_queue_and_stays_empty():
    at = _run_harness()
    _button(at, "Select all duplicates").click()
    at.run()

    _button(at, "Clear selection").click()
    at.run()
    assert not at.exception, at.exception
    assert all(not b.value for b in at.checkbox)

    # with the old bug, stale widget state re-added files on the NEXT rerun
    at.run()
    assert len(at.session_state["deletion_queue"]) == 0


def test_manual_check_adds_to_queue():
    at = _run_harness()
    list(at.checkbox)[1].check()
    at.run()
    assert not at.exception, at.exception
    assert len(at.session_state["deletion_queue"]) == 1
