import tempfile
import unittest
from pathlib import Path

from skill_learning.runtime import RuntimePolicy
from skill_learning.traex_runtime import TraeXRuntime, _ServerRun


SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


class FakeServer:
    def __init__(self, actions, *, forbidden=()):
        self.actions = actions
        self.forbidden = forbidden
        self.calls = []
        self.closed = False

    def run(self, *, thread_params, turn_params, tool_handler, timeout):
        self.calls.append((thread_params, turn_params, timeout))
        for name, arguments, expected_success in self.actions:
            success, _ = tool_handler(name, arguments)
            if success != expected_success:
                raise AssertionError(
                    f"expected {name} success={expected_success}, got {success}"
                )
        return _ServerRun(
            messages=[{"type": "agentMessage", "text": "done"}],
            usage={"input_tokens": 12, "output_tokens": 3},
            forbidden_items=self.forbidden,
        )

    def close(self):
        self.closed = True


class TraeXRuntimeTests(unittest.TestCase):
    def test_submit_result_contract_and_thread_configuration(self):
        server = FakeServer([("submit_result", {"answer": "ok"}, True)])
        runtime = TraeXRuntime(model="gpt-5.5", timeout=30, _server=server)
        with tempfile.TemporaryDirectory() as temp:
            result = runtime.run(
                role="task-executor",
                system_prompt="Submit an answer.",
                user_prompt="Return ok.",
                result_schema=SCHEMA,
                workdir=Path(temp),
            )

        self.assertEqual(result.payload, {"answer": "ok"})
        self.assertEqual(result.usage, {"input_tokens": 12, "output_tokens": 3})
        thread, turn, timeout = server.calls[0]
        self.assertEqual(thread["permissionProfile"]["type"], "managed")
        self.assertFalse(thread["permissionProfile"]["network"]["enabled"])
        entries = thread["permissionProfile"]["fileSystem"]["entries"]
        self.assertEqual(entries[0]["access"], "read")
        self.assertEqual(thread["approvalPolicy"], "never")
        self.assertTrue(thread["ephemeral"])
        self.assertEqual(
            [tool["name"] for tool in thread["dynamicTools"]],
            ["submit_result"],
        )
        self.assertEqual(turn["input"][0]["text"], "Return ok.")
        self.assertEqual(timeout, 30)

    def test_required_reads_are_enforced_before_submission(self):
        server = FakeServer([
            ("submit_result", {"answer": "too early"}, False),
            ("read_file", {"path": "traces/one.json"}, True),
            ("read_file", {"path": "traces/two.json"}, True),
            ("submit_result", {"answer": "ready"}, True),
        ])
        runtime = TraeXRuntime(_server=server)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "traces").mkdir()
            (root / "traces" / "one.json").write_text("{}", encoding="utf-8")
            (root / "traces" / "two.json").write_text("{}", encoding="utf-8")
            result = runtime.run(
                role="skill-proposer",
                system_prompt="Read evidence.",
                user_prompt="Inspect traces.",
                result_schema=SCHEMA,
                workdir=root,
                policy=RuntimePolicy(
                    allowed_tools=("read_file", "glob", "submit_result"),
                    required_read_prefix="traces",
                    min_required_reads=2,
                ),
            )

        self.assertEqual(result.payload, {"answer": "ready"})

    def test_forbidden_native_tool_item_fails_closed(self):
        server = FakeServer(
            [("submit_result", {"answer": "ok"}, True)],
            forbidden=("commandExecution",),
        )
        runtime = TraeXRuntime(_server=server)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, "forbidden TraeX item"):
                runtime.run(
                    role="task-executor",
                    system_prompt="Submit.",
                    user_prompt="Return ok.",
                    result_schema=SCHEMA,
                    workdir=Path(temp),
                )

    def test_close_stops_injected_server(self):
        server = FakeServer([])
        runtime = TraeXRuntime(_server=server)
        runtime.close()
        self.assertTrue(server.closed)


if __name__ == "__main__":
    unittest.main()
