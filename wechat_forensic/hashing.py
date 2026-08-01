"""哈希工具"""

import hashlib


class Hasher:
    @staticmethod
    def sha256_file(filepath: str, chunk_size: int = 4 * 1024 * 1024) -> str:
        """计算文件 SHA-256"""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def md5_file(filepath: str, chunk_size: int = 4 * 1024 * 1024) -> str:
        """计算文件 MD5"""
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify(filepath: str, expected_sha256: str) -> bool:
        actual = Hasher.sha256_file(filepath)
        return actual.lower() == expected_sha256.lower()
