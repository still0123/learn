from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path


_CJK_FONT_NAMES = ("宋体", "黑体", "等线", "微软雅黑", "仿宋", "楷体")


def patch_xml(data: bytes, font_name: str) -> bytes:
    """只替换字体名称，保留原 WordprocessingML 的命名空间前缀和顺序。"""

    text = data.decode("utf-8")
    for old_name in _CJK_FONT_NAMES:
        text = text.replace(old_name, font_name)
    return text.encode("utf-8")


def patch_docx(path: Path, font_name: str) -> None:
    with tempfile.TemporaryDirectory(prefix="docx-font-") as tmp:
        tmp_path = Path(tmp) / path.name
        with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(
            tmp_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    data = patch_xml(data, font_name)
                zout.writestr(item, data)
        shutil.copy2(tmp_path, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--font", default="PingFang SC")
    args = parser.parse_args()
    patch_docx(args.docx.resolve(), args.font)
    print(args.docx.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
