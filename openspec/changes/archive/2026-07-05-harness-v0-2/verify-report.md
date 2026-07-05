## Verification Report

**Change**: harness-v0-2
**Version**: N/A (concatenado, 11 dominios)
**Mode**: Strict TDD (orchestrator-injected, authoritative)

---

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 113 checkbox items across 9 Lotes (106 tareas numeradas + encabezados de resumen) |
| Tasks complete | 113 |
| Tasks incomplete | 0 |

No incomplete tasks. `openspec/changes/harness-v0-2/tasks.md` shows all 9 Lotes marked `[x] COMPLETO`, `state.yaml` shows `apply.status: done`, `batches_done: [1..9]`.

---

### Build & Tests Execution (REAL, executed in this verify pass)

**Build/Type Check (mypy)**: Passed
```
Success: no issues found in 47 source files
```

**Tests (pytest -q)**: 247 passed / 0 failed / 0 skipped
```
247 passed in 2.93s
```
Matches the apply-phase report exactly (247 tests).

**ruff check .**: Passed — `All checks passed!`

**lint-imports**: Passed — `Analyzed 47 files, 97 dependencies. Contracts: 1 kept, 0 broken.`

**Coverage** (`pytest --cov=erickfp --cov-report=term`): **95%** (1236 stmts, 64 miss) / threshold 85% → Above threshold.
Per-file low spot: `src/erickfp/tools/mcp.py` 74% (see WARNING below, known/accepted risk).

All 5 canonical commands re-executed live in this verify pass and confirmed green with the exact same numbers reported by apply (247 tests, 95% coverage).

---

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | Yes | Found in `apply-progress`, Lote 9 table (RED/GREEN/REFACTOR for tasks 9.1-9.4) |
| All tasks have tests | Yes | 55/55 real spec scenarios mapped 1:1 to a named passing test (`docs/smoke-e2e-v0-2.md` §8) |
| RED confirmed (tests exist) | Yes | Spot-checked 5 test files/functions referenced in the traceability table — all exist and collect |
| GREEN confirmed (tests pass) | Yes | Spot-checked subset executed directly: 13/13 passed (core_guard_policy, subagents/research, agent/loop mcp gate, compaction safe_split x5, litellm stop_reason x4) |
| Triangulation adequate | Yes | `_STOP_REASON_MAP` fix triangulated with 4 parametrized cases (tool_calls, stop, length, None) + 2 corrected existing assertions |
| Safety Net for modified files | Yes | Lote 9 reports suite went 243→247 without regressions; full suite re-run here confirms 247/247 |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | ~230 | ~55 | pytest, unittest.mock/fakes |
| Integration (CLI/Typer runner + real SQLite + real pty for banner) | ~15 | `tests/cli/*`, `tests/ui/test_banner.py` (pty real) | `typer.testing.CliRunner`, real `sqlite3` file, `pty` |
| E2E (real network, real Gemini/Gemma) | 0 automated (1 manual, documented) | `docs/smoke-e2e-v0-2.md` | Manual smoke, GEMINI_API_KEY, not part of `pytest -q` |
| **Total** | **247** | **60 test files** | |

The single most important E2E validation of this cycle (real Provider ↔ real Agent boundary) is manual/documented, not part of the automated suite — this is architecturally correct (no CI should depend on a live paid/rate-limited API), and is exactly the boundary that the automated suite structurally cannot cover (see stop_reason finding below).

---

### Changed File Coverage (representative sample, files touched by the two explicit reviews)
| File | Line % | Uncovered Lines | Rating |
|------|--------|------------------|--------|
| `src/erickfp/provider/litellm_gemini.py` | 98% | 2 lines (unreachable `AssertionError` guard, `# pragma: no cover`) | Excellent |
| `src/erickfp/cli.py` | 93% | 18 lines | Acceptable |
| `src/erickfp/hooks/core_guard.py` | 91% | 3 lines | Acceptable |
| `src/erickfp/tools/mcp.py` | 74% | `_discover_server_tools` body (206-234) + `_StdioSession.call_tool` (160-168) + `discover_tools` warn branches (198-202) | Low — see WARNING (accepted/documented risk, deferred to Ciclo 3) |

**Average of these 4 files**: 89%

---

### Assertion Quality
No CRITICAL or WARNING-level trivial assertions found in the sampled test files (`tests/compaction/test_summarize.py`, `tests/hooks/test_core_guard*.py`, `tests/cli/test_chat.py`, `tests/provider/test_litellm_gemini.py`, `tests/tools/test_mcp.py`). No tautologies, no unguarded loops over possibly-empty collections (the one loop-over-slice case in `test_summarize_condenses_old_turns_and_drops_stale_signatures` has an explicit `assert collapsed_part` guard immediately before the loop). No mock-heavy files found in this sample.

**Assertion quality**: ✅ All sampled assertions verify real behavior

---

### Quality Metrics
**Linter (ruff)**: ✅ No errors
**Type Checker (mypy)**: ✅ No errors

---

### Spec Compliance Matrix

Full detail lives in `docs/smoke-e2e-v0-2.md` §8 (55 rows, one per `Scenario:` header across the 11 spec files). Summary by domain, all COMPLIANT (test exists and passed — re-verified live in this pass):

| Requirement (domain) | Scenarios | Result |
|-------------|----------|--------|
| ui-polish | 6 | ✅ COMPLIANT (6/6) |
| permission-policy | 6 | ✅ COMPLIANT (6/6) — includes explicit core_guard-over-policy regression test |
| slash-commands | 5 | ✅ COMPLIANT (5/5) |
| token-viewer | 3 | ✅ COMPLIANT (3/3) |
| memory-store (delta) | 6 | ✅ COMPLIANT (6/6) |
| provider-layer (delta) | 6 | ✅ COMPLIANT (6/6) — includes the corrected stop_reason assertions |
| compaction | 5 | ✅ COMPLIANT (5/5) — includes SafeSplitPoint formal invariant, parametrized |
| subagents | 4 | ✅ COMPLIANT (4/4) |
| mcp-support | 3 | ✅ COMPLIANT (3/3) |
| tool-registry (delta) | 4 | ✅ COMPLIANT (4/4) |
| agent-loop (delta) | 7 | ✅ COMPLIANT (7/7) |
| **Total** | **55** | **55/55 COMPLIANT** |

Note on the "56 vs 55" discrepancy: `tasks.md`'s header count (56) was an estimate written during `sdd-tasks`, before specs were finalized. The real count of `Scenario:` headers across the 11 `spec.md` files, independently recounted in this verify pass (`grep -rn "Scenario:" specs/ | wc -l`), is **55** — matching exactly `docs/smoke-e2e-v0-2.md` §8's per-domain sums (6+6+5+3+6+6+5+4+3+4+7 = 55). This is a documented estimate-vs-actual discrepancy, not a missing scenario. Not reported as a gap, per instructions.

---

### Correctness (Static — Structural Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| All 11 spec domains | ✅ Implemented | Verified against real source, not summaries |
| core_guard prevalece sobre policy | ✅ Implemented | `hooks/core_guard.py` ignores `ctx.phase`, resolves `Path.resolve()` against relative/`..`/symlink trap paths, tested with `AllowList`/`AskOnce` attempting to approve a core write and being overridden |
| chat() wires HookManager+CoreGuardHook | ✅ Implemented | `cli.py:493` `hook_manager = HookManager([CoreGuardHook(root)])`, passed into `run_chat_session` |
| stop_reason normalization | ✅ Implemented | `_STOP_REASON_MAP` in `litellm_gemini.py`, 4-case parametrized test |
| AST no-leak boundaries (litellm, mcp) | ✅ Implemented | `tests/test_no_native_sdk_leak.py` (litellm) + `tests/tools/test_mcp.py::test_only_mcp_module_imports_mcp_sdk` (mcp) — both re-executed, both pass |
| import-linter layer contract | ✅ Implemented | `lint-imports` → 1 kept, 0 broken; contract table matches `design.md` extended layers (ui/compaction/subagents) |

---

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 — Extended layer contract (cli→cogito→subagents→agent→compaction→{hooks|tools|provider|memory|ui}→api) | ✅ Yes | `lint-imports` green, `test_architecture_import_rules.py` asserts the exact layer list from `pyproject.toml` |
| D2 — No native SDK types cross the Provider boundary | ✅ Yes | Extended correctly in Lote 9 to also cover `stop_reason` (see finding below) — this was the one place the axiom had NOT yet been applied |
| D5 — Tool/Provider/Store/Hook protocols (duck typing) | ✅ Yes | `MCPTool`, `MCPSession`, `RecallSource` all follow the same `@runtime_checkable Protocol` pattern |
| D8 — MCP as a Tool, same registry/gate, stdio-only | ✅ Yes | `MCPTool` satisfies `tools.base.Tool` by shape; non-stdio transport rejected with `MCPConfigError`, never attempted |
| D10 — Configurable retry, defaults preserve Ciclo 1 behavior bit-for-bit | ✅ Yes | `max_attempts=2, backoff_seconds=2.0` defaults; only retries on 500/INTERNAL markers |

---

### Explicit Review #1 — chat() core_guard wiring (Lote 4 security fix)

**Confirmed.** `src/erickfp/cli.py::chat()` (line 493) builds `HookManager([CoreGuardHook(root)])` and passes it into `run_chat_session(..., hook_manager=hook_manager, ...)`. Before this fix (per apply-progress), only the Cogito phase orchestrator wired `core_guard`; `chat()`'s REPL had no hook manager at all.

Regression test confirmed present and passing: `tests/cli/test_chat.py::test_run_chat_session_wires_core_guard_via_chat_command` — monkeypatches `run_chat_session` inside the `cli` module, invokes the real `chat` Typer command, and asserts the captured `hook_manager` argument is not `None`. This is a structural/wiring regression test (proves `chat()` constructs and forwards a real hook manager), complemented by the fully separate behavioral test `tests/hooks/test_core_guard_policy.py::test_allowlist_and_askonce_never_bypass_core_guard` which proves, via the real `agent.loop.run_turn` + real `CoreGuardHook`, that a core-directory write is blocked even when `AllowList`/`AskOnce` policies (and a human "y") already approved it. Together these two tests cover both "is the wiring present" and "does the wiring actually block a real write" — both re-executed live in this pass, both pass.

---

### Explicit Review #2 — `_STOP_REASON_MAP` and other domain/provider convention mismatches

**Confirmed and fixed correctly.** `_STOP_REASON_MAP` in `litellm_gemini.py` maps litellm's OpenAI-style `finish_reason` ("tool_calls"→"tool_use", "stop"→"end_turn", unmapped/`None`→"end_turn"), tested with a 4-case parametrized test (`test_stop_reason_is_domain_type_no_litellm_leak`, re-executed here, passes) plus 2 corrected pre-existing assertions.

Additional domain/provider boundary points audited for the same class of bug, all found consistent:
- **`Block.tool_input` (str) vs. `call.function.arguments`**: all four `Tool.execute` implementations (`write_file`, `read_file`, `bash`, `recall`, `mcp`) do `json.loads(input)`, consistent with OpenAI/litellm's convention that `function.arguments` is a JSON-encoded string — no silent type mismatch here (litellm's convention and the domain's convention actually agree on this one).
- **MCP `isError` → domain `is_error`**: `_StdioSession.call_tool` does `bool(result.isError)` — correctly translates the MCP protocol's own boolean flag into the domain tuple shape `tuple[str, bool]`, same discipline as the litellm adapter. This code path is inside the *uncovered* 74% of `mcp.py` (see WARNING below) — it is structurally correct but not exercised by a real unit test, only by manual smoke/architecture review in this pass.
- **Message roles**: the domain `Role` type (`api/types.py`) is `Literal["user", "assistant"]` only; `_user_message` translates domain `tool_result` blocks (carried inside a `role="user"` Message, Anthropic-style) into litellm/OpenAI-style `{"role": "tool", ...}` payload dicts. This translation is one-directional (domain → litellm, outgoing only) and litellm never returns a `role="tool"` message back into `_to_response` — so there is no equivalent incoming-side mismatch to normalize. No fix needed here.
- **`Block.type` values**: `_to_response` only ever constructs `"text"` and `"tool_use"` blocks (matches domain's `BlockType` Literal exactly); `"tool_result"` blocks are constructed elsewhere (agent loop, domain-internal, no provider translation involved).

No additional unfixed convention mismatches of the same class were found. The one remaining structurally-unverified boundary (`MCPSession`/`_StdioSession` against a real MCP server) is flagged as WARNING below (already a known, accepted, documented risk — deferred to Ciclo 3 per the change scope).

---

### Issues Found

**CRITICAL** (must fix before archive):
None.

**WARNING** (should fix, non-blocking):
1. `src/erickfp/tools/mcp.py::_discover_server_tools` (and `_StdioSession.call_tool`, lines 160-168, 206-234) has no direct unit-test coverage — file sits at 74% overall coverage vs. 95% project average. This is the real stdio connection/handshake against an actual MCP server subprocess; testing it requires either a real server binary or heavier async mocking of `anyio`/`mcp.ClientSession` than the current duck-typed `MCPSession` fakes provide. This is a known, already-documented, accepted risk in the change scope (MCP against a real server is explicitly deferred to Ciclo 3). Not a regression, not new — flagging per instructions as a documented WARNING, not CRITICAL.

**SUGGESTION** (nice to have):
1. Consider adding one lightweight integration test for `_discover_server_tools` using a trivial fake MCP server script (stdio echo) to raise `tools/mcp.py` coverage above 80% ahead of Ciclo 3, even without a full real-server smoke test.
2. `tasks.md`'s header docstring says "55 escenarios reales" now (already corrected in Lote 9) — no action needed, just noting it stayed consistent through this verify pass.

---

### Verdict
**PASS**

247/247 tests pass, 95% coverage (≥85% threshold), ruff/mypy/lint-imports clean — all 5 canonical commands re-executed live and match apply's reported numbers exactly. Both explicit reviews (chat() core_guard wiring, `_STOP_REASON_MAP` + broader convention-mismatch audit) confirmed fixed with real regression tests. core_guard's `Path.resolve()`-based trap-path defense confirmed thoroughly tested including against `AllowList`/`AskOnce` bypass attempts. AST boundary tests for both `litellm` and `mcp` SDK isolation confirmed present and passing. The one open WARNING (`tools/mcp.py` coverage gap) is a pre-documented, accepted risk explicitly deferred to Ciclo 3 — not a blocker. No CRITICAL issues found. Ready for `sdd-archive`.
