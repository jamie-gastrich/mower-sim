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

from math import pi as math_pi

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


@pytest.mark.parametrize('angle', [3.5, -3.5, 10.0, -10.0, 3.1415926535])
def test_wrap_angle_rad_stays_in_range(angle: float) -> None:
    assert -math_pi < wrap_angle_rad(angle) <= math_pi
