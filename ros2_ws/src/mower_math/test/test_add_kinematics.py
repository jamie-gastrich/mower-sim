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

import math

from mower_math.add_kinematics import (
    expand_covariance_diagonal,
    limit_twist,
    step_unicycle,
    yaw_to_quaternion
)

import pytest


@pytest.mark.parametrize(
    'v, w, max_linear, max_angular, min_radius, expected',
    [
        (0.3, 0.4, 1.0, 2.0, 0.5, (0.3, 0.4)),
        (0.5, 5.0, 1.0, 2.0, 0.5, (0.5, 1.0)),
        (1.0, 5.0, 1.0, 2.0, 0.1, (1.0, 2.0)),
        (-0.5, 1.5, 1.0, 2.0, 0.5, (-0.5, 1.0)),
        (0.5, -5.0, 1.0, 2.0, 0.5, (0.5, -1.0)),
        (0.0, 5.0, 1.0, 2.0, 0.5, (0.0, 2.0)),
        (2.5, 0.0, 1.0, 2.0, 0.5, (1.0, 0.0))
    ],
)
def test_limit_twist(v, w, max_linear, max_angular, min_radius, expected):
    assert limit_twist(v, w, max_linear, max_angular, min_radius) == expected


@pytest.mark.parametrize(
    'x, y, yaw, v, w, dt, expected',
    [
        (0, 0, 0, 1.0, 0.0, 0.5, (0.5, 0.0, 0.0)),
        (0, 0, 0, 0.0, 1.0, 0.5, (0.0, 0.0, 0.5)),
        (0, 0, 0, 1.0, 0.5, 1.0, (1.0, 0.0, 0.5)),
        (1, 1, 0, -1.0, 0.0, 1.0, (0.0, 1.0, 0.0)),
        (0, 0, 3.0, 0.0, 1.0, 0.25, (0.0, 0.0, -3.0331853071795867))
    ],
)
def test_step_unicycle(x, y, yaw, v, w, dt, expected):
    assert step_unicycle(x, y, yaw, v, w, dt) == pytest.approx(expected)


@pytest.mark.parametrize(
    'yaw, expected',
    [
        (0.0, (0.0, 0.0, 0.0, 1.0)),
        (math.pi / 2, (0.0, 0.0, 0.7071067811865475, 0.7071067811865476))
    ],
)
def test_yaw_to_quaternion(yaw, expected):
    assert yaw_to_quaternion(yaw) == pytest.approx(expected)


@pytest.mark.parametrize(
    'covariance, expected',
    [
        (
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            [
                1.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 2.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 3.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 4.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 5.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 6.0,
            ],
        ),
    ]
)
def test_expand_covariance_diagonal(covariance, expected):
    assert expand_covariance_diagonal(covariance) == expected


def test_expand_covariance_diagonal_rejects_wrong_length():
    with pytest.raises(ValueError):
        expand_covariance_diagonal([1.0, 2.0, 3.0, 4.0, 5.0])
