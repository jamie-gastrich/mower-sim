# Copyright 2026 Jamie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mower_math.math_utils import clamp, wrap_angle_rad
import pytest


@pytest.mark.parametrize(
    """value, low, high, expected""",
    [
        (5.0, 0.0, 3.0, 3.0),   # above the range
        (-1.0, 0.0, 3.0, 0.0),  # below the range
        (2.0, 0.0, 3.0, 2.0),   # inside the range
    ],
)
def test_clamp(value: float, low: float, high: float, expected: float) -> None:
    assert clamp(value, low, high) == expected


def test_wrap_angle_rad_keeps_range() -> None:
    angle = wrap_angle_rad(3.0 * 3.14)
    assert -3.141593 <= angle <= 3.141593
