from pathlib import Path

import pytest

from saas_video_engine import _clip_window


def test_clip_windows_are_spread_across_source():
    starts = [_clip_window(120.0, i, 4)[0] for i in range(4)]
    assert starts[0] == pytest.approx(0.0)
    assert starts[-1] == pytest.approx(90.0)
    assert starts == sorted(starts)


def test_short_source_stays_inside_bounds():
    start, length = _clip_window(4.0, 0, 3)
    assert start == 0.0
    assert length == 4.0
