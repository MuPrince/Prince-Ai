"""file_service 测试。"""
import pytest

from api_view.services.file_service import (
    _sanitize_filename,
    delete,
    read_upload,
    upload,
)


class TestSanitizeFilename:
    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("report.pdf", "report.pdf"),
            ("../../etc/passwd", "passwd"),
            ("", "unnamed"),
            ("  file.txt  ", "file.txt"),
            ("path/to/file.csv", "file.csv"),
        ],
    )
    def test_sanitize(self, input_name, expected):
        assert _sanitize_filename(input_name) == expected


class TestFileUpload:
    @pytest.mark.asyncio
    async def test_upload_and_read(self, tmp_upload_dir):
        content = b"hello world"
        result = await upload(content, "test.txt", "org1")
        assert result["file_id"].startswith("file-")
        assert result["filename"] == "test.txt"

        data, filename = read_upload(result["file_id"])
        assert data == content
        assert filename == "test.txt"

    @pytest.mark.asyncio
    async def test_upload_sanitizes_filename(self, tmp_upload_dir):
        result = await upload(b"data", "../../evil.txt", "org1")
        assert result["filename"] == "evil.txt"

    def test_read_invalid_file_id(self, tmp_upload_dir):
        with pytest.raises(FileNotFoundError, match="非法 file_id"):
            read_upload("bad-id")

    def test_read_nonexistent_file(self, tmp_upload_dir):
        with pytest.raises(FileNotFoundError, match="上传文件不存在"):
            read_upload("file-abc12345")

    def test_delete_file(self, tmp_upload_dir):
        import asyncio

        async def _upload():
            return await upload(b"data", "test.txt", "org1")

        result = asyncio.run(_upload())
        file_id = result["file_id"]
        delete(file_id)

        with pytest.raises(FileNotFoundError):
            read_upload(file_id)

    def test_delete_invalid_file_id(self, tmp_upload_dir):
        # 不抛异常，静默返回
        delete("bad-id")
        delete("")
