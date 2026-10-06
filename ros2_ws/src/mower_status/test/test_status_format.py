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

from mower_status.status_format import DEFAULT_PUBLISH_RATE
from mower_status.status_format import format_status_message
from mower_status.status_format import validate_publish_rate


def test_format_status_message():
    assert format_status_message('mower-01', 'nominal') == 'mower-01: nominal'
    assert format_status_message('mower-02', 'degraded') == 'mower-02: degraded'


def test_validate_publish_rate():
    assert validate_publish_rate(3.0) == 3.0
    assert validate_publish_rate(2.0) == 2.0
    assert validate_publish_rate(0.0) == DEFAULT_PUBLISH_RATE
    assert validate_publish_rate(-1.5) == DEFAULT_PUBLISH_RATE
