from pathlib import Path

import pytest

from escudeiro.misc.pathx import (
    autopath,
    get_extension,
    is_extension,
    is_valid_link,
    is_valid_path,
    valid_or_new,
)


class TestAutopath:
    def test_autopath(self):
        path = "test.py"
        assert autopath(path) == Path(path)

    def test_autopath_with_pathlib(self):
        path = Path("test.py")
        assert autopath(path) is path


class TestGetExtension:
    def test_get_extension(self):
        path = "test.py"
        assert get_extension(path) == "py"

    def test_get_extension_with_pathlib(self):
        path = Path("test.py")
        assert get_extension(path) == "py"

    def test_get_extension_no_extension(self):
        path = "test"
        assert get_extension(path) == ""

    def test_get_extension_with_dot(self):
        path = "test.tar.gz"
        assert get_extension(path) == "gz"

    def test_get_extension_with_multiple_dots(self):
        path = "test.file/inner.tar.gz"
        assert get_extension(path) == "gz"


class TestIsExtension:
    def test_is_extension(self):
        path = "test.py"
        assert is_extension(path, "py") is True

    def test_is_extension_with_pathlib(self):
        path = Path("test.py")
        assert is_extension(path, "py") is True

    def test_is_extension_no_match(self):
        path = "test.py"
        assert is_extension(path, "txt") is False

    def test_is_extension_no_extension(self):
        path = "test"
        assert is_extension(path, "py") is False

    def test_is_extension_with_dot(self):
        path = "test.tar.gz"
        assert is_extension(path, "gz") is True

    def test_is_extension_with_multiple_dots(self):
        path = "test.file/inner.tar.gz"
        assert is_extension(path, "gz") is True

    def test_is_extension_multiple_extensions(self):
        path = "test.file/inner.tar.gz"
        assert is_extension(path, "tar", "file", "gz") is True


class TestIsValidPath:
    def test_is_valid_path(self, tmp_path: Path):
        valid_path = tmp_path / "valid_path.txt"
        valid_path.touch()
        assert is_valid_path(valid_path) is True

    def test_is_valid_path_invalid(self):
        invalid_path = Path("invalid_path.txt")
        assert is_valid_path(invalid_path) is False


class TestValidOrNew:
    def test_valid_or_new(self, tmp_path: Path):
        valid_path = valid_or_new(tmp_path / "valid_path.txt")

        assert is_valid_path(valid_path)

    def test_valid_path_guess_mode(self, tmp_path: Path):
        valid_file = valid_or_new(tmp_path / "valid_file.txt", mode="guess")
        valid_dir = valid_or_new(tmp_path / "valid_dir", mode="guess")

        assert is_valid_path(valid_file) and valid_file.is_file()
        assert is_valid_path(valid_dir) and not valid_dir.is_file()

    def test_valid_or_new_dir_mode(self, tmp_path: Path):
        valid_dir = valid_or_new(tmp_path / "valid_dir", mode="dir")
        valid_dir2 = valid_or_new(tmp_path / "valid_dir2.txt", mode="dir")

        assert is_valid_path(valid_dir) and not valid_dir.is_file()
        assert is_valid_path(valid_dir2) and not valid_dir2.is_file()

    def test_valid_or_new_file_mode(self, tmp_path: Path):
        valid_file = valid_or_new(tmp_path / "valid_file.txt", mode="file")
        valid_file2 = valid_or_new(tmp_path / "valid_file2", mode="file")

        assert is_valid_path(valid_file) and valid_file.is_file()
        assert is_valid_path(valid_file2) and valid_file2.is_file()

    def test_valid_or_new_invalid_mode(self, tmp_path: Path):
        with pytest.raises(ValueError) as excinfo:
            _ = valid_or_new(
                tmp_path / "invalid_path",
                mode="invalid_mode",  # pyright: ignore[reportArgumentType]
            )

        assert str(excinfo.value) == "Invalid mode: invalid_mode"


class TestIsValidLink:
    def test_is_valid_link(self, tmp_path: Path):
        (tmp_path / "target.txt").touch()
        valid_link = tmp_path / "valid_link.txt"
        valid_link.symlink_to(tmp_path / "target.txt")
        assert is_valid_path(valid_link) is True

    def test_is_valid_link_invalid(self, tmp_path: Path):
        (tmp_path / "target.txt").touch()
        valid_link = tmp_path / "valid_link.txt"
        valid_link.symlink_to(tmp_path / "target.txt")
        (tmp_path / "target.txt").unlink()  # Break the link
        assert is_valid_path(valid_link) is False

    def test_is_valid_link_not_a_link(self, tmp_path: Path):
        valid_file = tmp_path / "valid_file.txt"
        valid_file.touch()
        assert is_valid_link(valid_file) is False
