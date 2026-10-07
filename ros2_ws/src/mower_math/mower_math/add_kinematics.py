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

from mower_math.math_utils import clamp, wrap_angle_rad


def limit_twist(v: float, w: float, max_linear: float, max_angular: float,
                min_radius: float) -> tuple[float, float]:
    """Clamp twist to kinematic limits."""
    v_clamped = clamp(v, -max_linear, max_linear)
    limit_w = max_angular
    if v_clamped != 0.0:
        limit_by_radius = abs(v_clamped) / min_radius if min_radius > 0.0 \
            else max_angular
        limit_w = min(max_angular, limit_by_radius)
    return v_clamped, clamp(w, -limit_w, limit_w)


def step_unicycle(x: float, y: float, yaw: float, v: float, w: float,
                  dt: float) -> tuple[float, float, float]:
    """Integrate unicycle model over dt."""
    x_new = x + v * math.cos(yaw) * dt
    y_new = y + v * math.sin(yaw) * dt
    yaw_new = wrap_angle_rad(yaw + w * dt)
    return x_new, y_new, yaw_new


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    """Convert planar heading to (x,y,z,w) quaternion about z."""
    half = yaw / 2.0
    return (0.0, 0.0, math.sin(half), math.cos(half))


def expand_covariance_diagonal(diagonal) -> list[float]:
    """Expand 6-element diagonal to 36-element row-major covariance."""
    if len(diagonal) != 6:
        raise ValueError('diagonal must have length 6')
    cov = [0.0] * 36
    for i, value in enumerate(diagonal):
        cov[i * 6 + i] = float(value)
    return cov
