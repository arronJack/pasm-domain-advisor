"""MCP 适配器（面向 WorkBuddy / ClawHub / Claude Desktop 等 MCP 兼容客户端）。

把泛例领域顾问引擎通过 MCP 暴露：平台出大模型，PASM 出「前提抽取 + 现行规则核验 +
多维剖析 + 自检闸门」，数据/规则留在你本地。零依赖实现 stdio 上的 JSON-RPC 2.0。

暴露的工具：
  · ``da_list_profiles`` 列出已注册领域（开店/跨境/食品许可…）。
  · ``da_advise``        对一段用户原话产出专业清单（含自检结论），可指定 profile_id。

用法：
    pasm-da-mcp                 # 起 stdio 服务
    pasm-da-mcp --selftest      # 本地自检（不起服务）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from .. import __version__, profiles as P
from ..agent import DomainAdvisorAgent

SERVER_NAME = "pasm-da-mcp"
SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2026-07-28")
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
CAPABILITIES = {"tools": {}}

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _negotiate(client_version: Optional[str]) -> str:
    if client_version in SUPPORTED_PROTOCOL_VERSIONS:
        return client_version
    return DEFAULT_PROTOCOL_VERSION


def _initialize_result(client_version: Optional[str]) -> Dict[str, Any]:
    return {
        "protocolVersion": _negotiate(client_version),
        "serverInfo": {"name": SERVER_NAME, "version": __version__},
        "capabilities": CAPABILITIES,
        "instructions": (
            "PASM 泛例领域顾问：先 da_list_profiles 看有哪些领域，再 da_advise "
            "传入 profile_id 与用户原话，得到结合现行规则+真实前提+自检闸门的清单。"
        ),
    }


def _error(req_id, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _result(req_id, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _log(msg: str) -> None:
    if os.environ.get("PASM_DA_MCP_QUIET") == "1":
        return
    print("[pasm-da-mcp] %s" % msg, file=sys.stderr, flush=True)


def _write(out, obj: Dict[str, Any]) -> None:
    out.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    out.flush()


# ----------------------------------------------------------- 工具实现
def tool_list_profiles(_args: Dict[str, Any]) -> Dict[str, Any]:
    return {"count": len(P.list_ids()), "profiles": [
        {"id": pid, "name_zh": P.get(pid).name_zh, "domain": P.get(pid).domain}
        for pid in P.list_ids()
    ], "ok": True}


def tool_advise(args: Dict[str, Any]) -> Dict[str, Any]:
    profile_id = str(args.get("profile_id") or "douyin_pet_store")
    text = str(args.get("text") or "").strip()
    if not text:
        raise ValueError("text 不能为空")
    try:
        agent = DomainAdvisorAgent("mcp", profile_id=profile_id)
    except KeyError as ex:
        raise ValueError(str(ex))
    report = agent.advise(text)
    return {
        "profile_id": report.profile_id,
        "markdown": report.markdown,
        "summary": report.summary(),
        "artifacts": report.artifacts,
        "ok": True,
    }


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "da_list_profiles",
        "description": "列出已注册领域顾问 profile（如 douyin_pet_store / cross_border_ecom / food_business_license）。",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
        "fn": tool_list_profiles,
    },
    {
        "name": "da_advise",
        "description": (
            "对一段用户原话产出专业执行清单（含前提抽取、现行规则核验、自检闸门结论）。"
            "profile_id 见 da_list_profiles；text 为用户原话。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string", "description": "领域 id，默认 douyin_pet_store"},
                "text": {"type": "string", "description": "用户原话，如「我已有个体户执照想开宠物店」"},
            },
            "required": ["text"],
        },
        "fn": tool_advise,
    },
]
TOOL_INDEX = {t["name"]: t for t in TOOLS}


def list_tools() -> List[Dict[str, Any]]:
    return [{"name": t["name"], "description": t["description"],
             "inputSchema": t["inputSchema"]} for t in TOOLS]


def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    tool = TOOL_INDEX.get(name)
    if tool is None:
        raise KeyError(name)
    return tool["fn"](args or {})


def _as_params(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def handle_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    req_id = msg.get("id") if isinstance(msg, dict) else None
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _error(req_id, INVALID_REQUEST, "Invalid Request")
    try:
        return _dispatch(msg)
    except Exception as ex:  # 协议层永不崩
        _log("内部错误：%s" % ex)
        return _error(req_id, INTERNAL_ERROR, "Internal error: %s" % ex)


def _dispatch(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = msg.get("method")
    req_id = msg.get("id")
    params = _as_params(msg.get("params"))

    if isinstance(method, str) and method.startswith("notifications/"):
        return None
    if method == "initialize":
        return _result(req_id, _initialize_result(params.get("protocolVersion")))
    if method == "ping":
        return _result(req_id, {})
    if method == "tools/list":
        return _result(req_id, {"tools": list_tools()})
    if method == "tools/call":
        name = params.get("name")
        a = _as_params(params.get("arguments"))
        try:
            result = call_tool(name, a)
        except KeyError:
            return _error(req_id, INVALID_PARAMS, "Unknown tool: %s" % name)
        except ValueError as ex:
            return _result(req_id, {"content": [{"type": "text", "text": "参数错误：%s" % ex}],
                                  "isError": True})
        except Exception as ex:  # noqa: BLE001
            _log("tool %s failed: %s" % (name, ex))
            return _result(req_id, {"content": [{"type": "text",
                                                "text": "工具执行失败：%s" % ex}], "isError": True})
        payload: Dict[str, Any] = {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            "isError": False, "structuredContent": result,
        }
        return _result(req_id, payload)
    if method == "shutdown":
        return _result(req_id, {})
    return _error(req_id, METHOD_NOT_FOUND, "Method not found: %s" % method)


def serve() -> int:
    stdin = sys.stdin.buffer
    out = sys.stdout.buffer
    _log("starting v%s" % __version__)
    try:
        for raw in stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception:
                _write(out, _error(None, PARSE_ERROR, "Parse error"))
                continue
            try:
                resp = handle_message(msg)
            except Exception as ex:  # 双保险
                _log("帧处理失败（已跳过）：%s" % ex)
                resp = _error(msg.get("id") if isinstance(msg, dict) else None,
                              INTERNAL_ERROR, "Internal error: %s" % ex)
            if resp is not None:
                try:
                    _write(out, resp)
                except (BrokenPipeError, ValueError):
                    break
    except KeyboardInterrupt:  # pragma: no cover
        pass
    return 0


def selftest() -> int:
    ok = True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        print("  %s %s" % ("v" if cond else "x", msg))
        if not cond:
            ok = False

    print("pasm-da-mcp selftest v%s" % __version__)
    r = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"}})
    check(r["result"]["protocolVersion"] == "2024-11-05", "版本协商回显")
    r = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in r["result"]["tools"]]
    check(set(["da_list_profiles", "da_advise"]).issubset(set(names)), "tools/list 含全部工具")
    r = handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "da_list_profiles", "arguments": {}}})
    check(r["result"]["structuredContent"]["count"] >= 1, "da_list_profiles 返回已注册领域")
    r = handle_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                        "params": {"name": "da_advise",
                                   "arguments": {"profile_id": "douyin_pet_store",
                                                 "text": "我已有个体户执照想开宠物店"}}})
    sc = r["result"]["structuredContent"]
    check(sc["ok"] and "自检" in sc["markdown"], "da_advise 产出含自检的清单")
    check(sc["summary"].startswith("profile=douyin_pet_store"), "da_advise 摘要正确")
    # 无 text → isError
    r = handle_message({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                        "params": {"name": "da_advise", "arguments": {}}})
    check(r["result"]["isError"] is True, "da_advise 缺 text 返回 isError")
    # 未知工具
    r = handle_message({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                        "params": {"name": "nope", "arguments": {}}})
    check("error" in r and r["error"]["code"] == INVALID_PARAMS, "未知工具返回协议错误")
    print("pasm-da-mcp selftest:", "通过" if ok else "失败")
    return 0 if ok else 1


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="pasm-da-mcp", description="泛例领域顾问 MCP 服务器（stdio）")
    ap.add_argument("--selftest", action="store_true", help="本地自检（不起服务）")
    ap.add_argument("--version", action="version", version="%(prog)s " + __version__)
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
