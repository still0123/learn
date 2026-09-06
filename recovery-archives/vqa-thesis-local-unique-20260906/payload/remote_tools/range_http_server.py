#!/usr/bin/env python3
"""Serve files with HTTP byte-range support."""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import shutil


class RangeHandler(SimpleHTTPRequestHandler):
    byte_range: tuple[int, int] | None = None

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            source = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        size = os.fstat(source.fileno()).st_size
        match = re.fullmatch(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else size - 1
            if start >= size or end < start:
                source.close()
                self.send_error(416, "Invalid byte range")
                return None
            end = min(end, size - 1)
            self.byte_range = (start, end)
            source.seek(start)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            length = end - start + 1
        else:
            self.byte_range = None
            self.send_response(200)
            length = size
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        return source

    def copyfile(self, source, outputfile):
        if self.byte_range is None:
            shutil.copyfileobj(source, outputfile)
            return
        remaining = self.byte_range[1] - self.byte_range[0] + 1
        while remaining:
            block = source.read(min(1024 * 1024, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    os.chdir(args.directory.resolve())
    ThreadingHTTPServer(("0.0.0.0", args.port), RangeHandler).serve_forever()


if __name__ == "__main__":
    main()
