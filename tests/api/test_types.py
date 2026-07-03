"""Tests de construccion para los tipos base de la api (Decision 1 y 5 del design).

api/types.py no debe depender de nada fuera de la stdlib: estos tests solo
verifican que los dataclasses son construibles y que Block.provider_metadata
tiene default opaco {} (Decision 2 del design -- thought signatures).
"""

from erickfp.api.types import Block, Entry, HookResult, Message, Response, ToolDef


def test_block_default_provider_metadata_is_empty_dict() -> None:
    block = Block(type="text", text="hola")
    assert block.provider_metadata == {}


def test_block_provider_metadata_is_opaque_dict() -> None:
    block = Block(
        type="tool_use",
        tool_name="bash",
        provider_metadata={"raw_tool_call_id": "call_1__thought__abc123"},
    )
    assert block.provider_metadata == {"raw_tool_call_id": "call_1__thought__abc123"}


def test_message_is_constructible_with_blocks() -> None:
    msg = Message(role="user", content=[Block(type="text", text="hola")])
    assert msg.role == "user"
    assert len(msg.content) == 1


def test_tooldef_is_constructible() -> None:
    tool_def = ToolDef(
        name="bash",
        description="ejecuta un comando shell",
        input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
        required=["command"],
    )
    assert tool_def.name == "bash"
    assert tool_def.required == ["command"]


def test_response_is_constructible() -> None:
    response = Response(content=[Block(type="text", text="ok")], stop_reason="end_turn")
    assert response.stop_reason == "end_turn"
    assert response.content[0].text == "ok"


def test_hookresult_default_reason_is_empty_string() -> None:
    result = HookResult(decision="allow")
    assert result.reason == ""


def test_hookresult_deny_carries_reason() -> None:
    result = HookResult(decision="deny", reason="core/* protegido")
    assert result.decision == "deny"
    assert result.reason == "core/* protegido"


def test_entry_is_constructible_with_default_tags() -> None:
    entry = Entry(kind="fact", content="dato")
    assert entry.tags == []
    assert entry.id is None
