from __future__ import annotations

import glob as globlib
import json
import queue
import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .models import RuntimeResult
from .runtime import RuntimePolicy
from .schema import validate_schema


_DYNAMIC_TOOL_METHOD = "item/tool/call"
_FORBIDDEN_ITEM_TYPES = {
    "commandExecution",
    "fileChange",
    "mcpToolCall",
    "collabAgentToolCall",
    "webSearch",
    "imageGeneration",
}


@dataclass(frozen=True)
class _ServerRun:
    messages: list[dict[str, Any]]
    usage: dict[str, int]
    forbidden_items: tuple[str, ...]


class TraeXRuntime:
    """Least-privilege runtime backed by a persistent local TraeX app-server."""

    def __init__(
        self,
        *,
        binary: str | Path = "traex",
        model: str = "gpt-5.5",
        timeout: float = 180.0,
        _server: Any | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("TraeX timeout must be positive")
        self.binary = str(binary)
        self.model = model
        self.timeout = timeout
        self._server = _server

    def describe(self) -> dict[str, object]:
        return {
            "runtime": "traex",
            "model": self.model,
            "transport": "app-server-stdio",
            "binary": self.binary,
            "permission_profile": "workspace-read-only-network-off",
            "ephemeral_threads": True,
            "timeout": self.timeout,
        }

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def run(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        result_schema: dict,
        workdir: Path,
        policy: RuntimePolicy | None = None,
    ) -> RuntimeResult:
        root = Path(workdir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        policy = policy or RuntimePolicy()
        submissions: list[dict[str, Any]] = []
        successful_reads: set[str] = set()
        duplicate_submission = False

        def handle_tool(name: str, arguments: Any) -> tuple[bool, str]:
            nonlocal duplicate_submission
            if name not in policy.allowed_tools:
                return False, f"tool {name!r} is not allowed for role {role!r}"
            if not isinstance(arguments, dict):
                return False, "tool arguments must be a JSON object"
            try:
                if name == "read_file":
                    path = arguments.get("path")
                    if not isinstance(path, str):
                        raise ValueError("read_file.path must be a string")
                    limit = arguments.get("limit", 50_000)
                    if not isinstance(limit, int) or isinstance(limit, bool):
                        raise ValueError("read_file.limit must be an integer")
                    target = _safe_path(root, path)
                    text = target.read_text(encoding="utf-8")
                    relative = target.relative_to(root).as_posix()
                    if _matches_required_prefix(relative, policy.required_read_prefix):
                        successful_reads.add(relative)
                    return True, text[: max(0, min(limit, 200_000))]

                if name == "glob":
                    pattern = arguments.get("pattern")
                    if not isinstance(pattern, str):
                        raise ValueError("glob.pattern must be a string")
                    if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                        raise ValueError(f"glob escapes workspace: {pattern}")
                    matches = sorted(globlib.glob(pattern, root_dir=str(root), recursive=True))
                    return True, "\n".join(matches[:500]) if matches else "(no matches)"

                if name == "submit_result":
                    if submissions:
                        duplicate_submission = True
                        raise ValueError("submit_result may be called exactly once")
                    if len(successful_reads) < policy.min_required_reads:
                        raise ValueError(
                            f"read at least {policy.min_required_reads} distinct files under "
                            f"{policy.required_read_prefix!r} before submitting; "
                            f"read {len(successful_reads)}"
                        )
                    validate_schema(arguments, result_schema)
                    submissions.append(arguments)
                    return True, "Structured result accepted. End the task now."
            except (OSError, UnicodeError, ValueError) as exc:
                return False, str(exc)
            return False, f"unknown tool {name!r}"

        tools = _tool_specs(policy, result_schema)
        instructions = (
            f"Role: {role}\n\n{system_prompt}\n\n"
            "Runtime constraints: use only the dynamic tools provided for this thread. "
            "Do not invoke shell, file-editing, MCP, web, collaboration, or other built-in tools. "
            "Complete the task by calling submit_result exactly once."
        )
        server = self._get_server()
        server_run = server.run(
            thread_params={
                "model": self.model,
                "cwd": str(root),
                "approvalPolicy": "never",
                "permissionProfile": {
                    "type": "managed",
                    "network": {"enabled": False},
                    "fileSystem": {
                        "type": "restricted",
                        "entries": [{
                            "path": {"type": "path", "path": str(root)},
                            "access": "read",
                        }],
                    },
                },
                "baseInstructions": instructions,
                "developerInstructions": None,
                "ephemeral": True,
                "environments": [],
                "dynamicTools": tools,
                "experimentalRawEvents": False,
                "persistExtendedHistory": False,
            },
            turn_params={
                "input": [{"type": "text", "text": user_prompt, "text_elements": []}],
            },
            tool_handler=handle_tool,
            timeout=self.timeout,
        )
        if server_run.forbidden_items:
            names = ", ".join(server_run.forbidden_items)
            raise RuntimeError(f"{role} used forbidden TraeX item types: {names}")
        if duplicate_submission or len(submissions) != 1:
            raise RuntimeError(f"{role} must submit exactly one structured result")
        validate_schema(submissions[0], result_schema)
        return RuntimeResult(
            payload=submissions[0],
            messages=server_run.messages,
            usage=server_run.usage,
        )

    def _get_server(self) -> Any:
        if self._server is None:
            self._server = _TraeXAppServer(self.binary)
        return self._server


class _TraeXAppServer:
    def __init__(self, binary: str) -> None:
        self.binary = binary
        self._process: subprocess.Popen[str] | None = None
        self._stdout: queue.Queue[str | None] = queue.Queue()
        self._stderr: deque[str] = deque(maxlen=80)
        self._next_id = 1

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def run(
        self,
        *,
        thread_params: dict[str, Any],
        turn_params: dict[str, Any],
        tool_handler: Callable[[str, Any], tuple[bool, str]],
        timeout: float,
    ) -> _ServerRun:
        self._ensure_started(timeout)
        thread_response, _ = self._request("thread/start", thread_params, timeout)
        thread_id = thread_response["thread"]["id"]
        turn_request = dict(turn_params)
        turn_request["threadId"] = thread_id
        _, pending = self._request("turn/start", turn_request, timeout)
        return self._wait_for_turn(thread_id, pending, tool_handler, timeout)

    def _ensure_started(self, timeout: float) -> None:
        if self._process is not None:
            if self._process.poll() is not None:
                raise RuntimeError(self._process_error("TraeX app-server exited"))
            return
        command = [
            self.binary,
            "app-server",
            "--listen",
            "stdio://",
            "--disable",
            "plugins",
            "--disable",
            "apps",
            "--disable",
            "memories",
            "--disable",
            "hooks",
            "--disable",
            "multi_agent",
            "--disable",
            "multi_agent_v2",
            "--disable",
            "shell_snapshot",
            "--disable",
            "workspace_dependencies",
            "-c",
            "skills=[]",
        ]
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except OSError as exc:
            raise RuntimeError(f"cannot start TraeX app-server: {exc}") from exc
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        threading.Thread(
            target=self._drain_stdout,
            args=(self._process.stdout,),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._drain_stderr,
            args=(self._process.stderr,),
            daemon=True,
        ).start()
        self._request(
            "initialize",
            {
                "clientInfo": {
                    "name": "skill-learning-engine",
                    "title": "Skill Learning Engine",
                    "version": "0.2.0",
                },
                "capabilities": {
                    "experimentalApi": True,
                    "requestAttestation": False,
                    "optOutNotificationMethods": [],
                },
            },
            timeout,
        )
        self._send({"method": "initialized", "params": {}})

    def _request(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        request_id = self._next_id
        self._next_id += 1
        self._send({"id": request_id, "method": method, "params": params})
        pending: list[dict[str, Any]] = []
        while True:
            message = self._receive(timeout)
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(f"TraeX {method} failed: {message['error']}")
                return message.get("result") or {}, pending
            pending.append(message)

    def _wait_for_turn(
        self,
        thread_id: str,
        pending: list[dict[str, Any]],
        tool_handler: Callable[[str, Any], tuple[bool, str]],
        timeout: float,
    ) -> _ServerRun:
        messages: list[dict[str, Any]] = []
        forbidden: list[str] = []
        usage: dict[str, int] = {}
        inbox = deque(pending)
        while True:
            message = inbox.popleft() if inbox else self._receive(timeout)
            method = message.get("method")
            params = message.get("params") or {}
            if "id" in message and method == _DYNAMIC_TOOL_METHOD:
                success, text = tool_handler(params.get("tool", ""), params.get("arguments"))
                self._send({
                    "id": message["id"],
                    "result": {
                        "contentItems": [{"type": "inputText", "text": text}],
                        "success": success,
                    },
                })
                continue
            if "id" in message:
                self._deny_server_request(message)
                continue
            if method == "item/completed" and params.get("threadId") == thread_id:
                item = params.get("item") or {}
                messages.append(item)
                item_type = item.get("type")
                if item_type in _FORBIDDEN_ITEM_TYPES:
                    forbidden.append(str(item_type))
            elif method == "thread/tokenUsage/updated" and params.get("threadId") == thread_id:
                last = ((params.get("tokenUsage") or {}).get("last") or {})
                usage = {
                    "input_tokens": int(last.get("inputTokens", 0)),
                    "cache_creation_input_tokens": int(last.get("cacheCreationInputTokens", 0)),
                    "cached_input_tokens": int(last.get("cachedInputTokens", 0)),
                    "output_tokens": int(last.get("outputTokens", 0)),
                    "reasoning_output_tokens": int(last.get("reasoningOutputTokens", 0)),
                }
            elif method == "turn/completed" and params.get("threadId") == thread_id:
                turn = params.get("turn") or {}
                if turn.get("status") != "completed":
                    raise RuntimeError(f"TraeX turn ended with status {turn.get('status')!r}")
                return _ServerRun(
                    messages=messages,
                    usage=usage,
                    forbidden_items=tuple(sorted(set(forbidden))),
                )
            elif method == "error":
                raise RuntimeError(f"TraeX app-server error: {params}")

    def _deny_server_request(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        if method in {
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
        }:
            result: dict[str, Any] = {"decision": "decline"}
        elif method in {"execCommandApproval", "applyPatchApproval"}:
            result = {"decision": "denied"}
        else:
            self._send({
                "id": message["id"],
                "error": {"code": -32601, "message": f"request {method!r} is not supported"},
            })
            return
        self._send({"id": message["id"], "result": result})

    def _send(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise RuntimeError(self._process_error("TraeX app-server is not running"))
        process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def _receive(self, timeout: float) -> dict[str, Any]:
        try:
            line = self._stdout.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(f"TraeX app-server did not respond within {timeout:g}s") from exc
        if line is None:
            raise RuntimeError(self._process_error("TraeX app-server closed stdout"))
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid TraeX app-server JSON: {line[:200]!r}") from exc
        if not isinstance(message, dict):
            raise RuntimeError(f"invalid TraeX app-server message: {message!r}")
        return message

    def _drain_stdout(self, stream: Any) -> None:
        for line in stream:
            self._stdout.put(line)
        self._stdout.put(None)

    def _drain_stderr(self, stream: Any) -> None:
        for line in stream:
            self._stderr.append(line.rstrip())

    def _process_error(self, message: str) -> str:
        details = "\n".join(self._stderr)
        return f"{message}:\n{details}" if details else message


def _tool_specs(policy: RuntimePolicy, result_schema: dict) -> list[dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {
        "read_file": {
            "name": "read_file",
            "description": "Read a UTF-8 file inside the assigned workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        "glob": {
            "name": "glob",
            "description": "List files inside the assigned workspace using a glob pattern.",
            "inputSchema": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
                "additionalProperties": False,
            },
        },
        "submit_result": {
            "name": "submit_result",
            "description": "Submit the final machine-readable result exactly once.",
            "inputSchema": result_schema,
        },
    }
    return [specs[name] for name in policy.allowed_tools]


def _safe_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError(f"path escapes workspace: {relative}")
    target = (root / path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes workspace: {relative}") from exc
    return target


def _matches_required_prefix(relative: str, prefix: str | None) -> bool:
    if prefix is None:
        return True
    normalized = prefix.rstrip("/")
    return relative == normalized or relative.startswith(normalized + "/")
