"""共享 pytest fixture"""

import sys
from pathlib import Path

import pytest

# 确保 src 可导入
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class StubLogger:
    """测试用空 logger,避免污染 stdout"""

    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def success(self, msg): pass
    def evidence(self, msg): pass


@pytest.fixture
def stub_logger():
    return StubLogger()
