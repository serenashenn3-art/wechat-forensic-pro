"""跨平台工具函数测试"""

import pytest

from wechat_forensic.utils import human_bytes, is_admin


@pytest.mark.parametrize(
    "raw,expected",
    [
        (0, "0.0B"),
        (1023, "1023.0B"),
        (1024, "1.0KB"),
        (1024 ** 2, "1.0MB"),
        (1024 ** 3, "1.0GB"),
        (1024 ** 4, "1.0TB"),
        (2 * 1024 ** 3, "2.0GB"),
    ],
)
def test_human_bytes(raw, expected):
    assert human_bytes(raw) == expected


def test_human_bytes_garbage():
    assert human_bytes("abc") == "abc"


def test_is_admin_returns_bool():
    # 在测试环境里不应抛异常
    assert isinstance(is_admin(), bool)
