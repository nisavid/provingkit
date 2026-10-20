"""Project a bounded subset of strace text; never infer resolved paths."""

import argparse
import json
import os
import re
import sys
import time


class Unsupported(ValueError):
    pass


def known(value):
    return {"state": "known", "value": value}


def path_operand(text):
    if len(text) < 2 or text[0] != '"' or text[-1] != '"':
        raise Unsupported("unsupported_path")
    content = text[1:-1]
    data = bytearray()
    escaped = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12,
               "r": 13, '"': 34, "\\": 92}
    pos = 0
    while pos < len(content):
        char = content[pos]
        if char == "\\":
            pos += 1
            if pos == len(content):
                raise Unsupported("incomplete_escape")
            char = content[pos]
            if char in escaped:
                data.append(escaped[char])
            elif char == "x" and re.fullmatch(r"[0-9a-fA-F]{2}", content[pos + 1:pos + 3]):
                data.append(int(content[pos + 1:pos + 3], 16))
                pos += 2
            elif char in "01234567":
                match = re.match(r"[0-7]{1,3}", content[pos:])
                value = int(match[0], 8)
                if value > 255:
                    raise Unsupported("invalid_escape")
                data.append(value)
                pos += len(match[0]) - 1
            else:
                raise Unsupported("unsupported_escape")
        elif char == '"' or not 32 <= ord(char) <= 126:
            raise Unsupported("unsupported_path")
        else:
            data.append(ord(char))
        pos += 1
    if 0 in data:
        raise Unsupported("nul_path")
    return {"state": "known", "hex": data.hex(), "complete": True}


def arguments(text):
    pieces, start, quoted, escape = [], 0, False, False
    nested = []
    for pos, char in enumerate(text):
        if escape:
            escape = False
        elif quoted and char == "\\":
            escape = True
        elif char == '"':
            quoted = not quoted
        elif not quoted and char in "({[":
            nested.append(char)
            if len(nested) > 16:
                raise Unsupported("structure_depth_limit")
        elif not quoted and char in ")}]":
            if not nested or nested.pop() != {")": "(", "}": "{", "]": "["}[char]:
                raise Unsupported("malformed_structure")
        elif char == "," and not quoted and not nested:
            pieces.append(text[start:pos].strip())
            start = pos + 1
    if quoted or escape or nested:
        raise Unsupported("incomplete_string")
    pieces.append(text[start:].strip())
    return pieces


def symbols(text):
    if text == "0":
        return {"state": "known", "symbols": [], "numeric": known("0")}
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*(?:\|[A-Z_][A-Z0-9_]*)*", text):
        raise Unsupported("unsupported_flags")
    return {"state": "known", "symbols": text.split("|"), "numeric": {"state": "unavailable"}}


def number(text):
    if not re.fullmatch(r"-?[0-9]+", text):
        raise Unsupported("unsupported_number")
    return known(text)


def structure(text, required, optional):
    if not text.startswith("{") or not text.endswith("}"):
        raise Unsupported("unsupported_structure")
    result = {}
    for item in arguments(text[1:-1]):
        key, sep, value = item.partition("=")
        if not sep or key in result or key not in required | optional:
            raise Unsupported("unsupported_structure")
        result[key] = value
    if not required <= result.keys():
        raise Unsupported("unsupported_structure")
    return result


def open_operands(name, args):
    pieces = arguments(args)
    operands = {}
    if name in ("openat", "openat2"):
        if not pieces or not re.fullmatch(r"AT_FDCWD|-?[0-9]+", pieces[0]):
            raise Unsupported("unsupported_dirfd")
        operands["dirfd"] = known(pieces.pop(0))
    if name == "openat2":
        if len(pieces) != 3:
            raise Unsupported("unsupported_operands")
        how = structure(pieces[1], {"flags", "resolve"}, {"mode"})
        operands.update({"path": path_operand(pieces[0]),
                         "size": number(pieces[2]),
                         "how": {"flags": symbols(how["flags"]), "resolve": symbols(how["resolve"])}})
        if "mode" in how:
            if not re.fullmatch(r"0[0-7]+", how["mode"]):
                raise Unsupported("unsupported_mode")
            operands["how"]["mode"] = {"state": "known", "octal": how["mode"]}
        return operands
    if len(pieces) not in (2, 3):
        raise Unsupported("unsupported_operands")
    operands["path"] = path_operand(pieces[0])
    if not re.fullmatch(r"O_[A-Z0-9_]+(?:\|O_[A-Z0-9_]+)*", pieces[1]):
        raise Unsupported("unsupported_flags")
    operands["open_flags"] = {"state": "known", "symbols": pieces[1].split("|"),
                               "numeric": {"state": "unavailable"}}
    if len(pieces) == 3:
        if not re.fullmatch(r"0[0-7]+", pieces[2]):
            raise Unsupported("unsupported_mode")
        operands["mode"] = {"state": "known", "octal": pieces[2]}
    else:
        operands["mode"] = {"state": "inapplicable"}
    return operands


class TraceAdapter:
    def __init__(self, output, root_pid, max_records=16384, max_bytes=4194304):
        if type(root_pid) is not int or not 0 < root_pid <= 2147483647:
            raise ValueError("invalid root identity")
        if not 2 <= max_records <= 16384 or not 8192 <= max_bytes <= 4194304:
            raise ValueError("invalid trace bounds")
        self.output = output
        self.root_pid = root_pid
        self.max_records = max_records
        self.max_bytes = max_bytes
        self.buffer = bytearray()
        self.raw_bytes = 0
        self.line = 0
        self.records = 0
        self.bytes = 0
        self.exited = False
        self.pending = None
        self.terminal = None
        self.emit({"kind": "header", "schema": 1, "binding": "strace-source-subset/v1",
                   "root_pid": str(root_pid), "clock": "monotonic_ns",
                   "timestamp_source": "collector_receipt",
                   "backend_execution_qualified": False})

    def emit(self, value):
        value = {**value, "seq": self.records, "observed_ns": str(time.monotonic_ns())}
        raw = (json.dumps(value, separators=(",", ":")) + "\n").encode()
        if len(raw) > 4096:
            raise Unsupported("normalized_record_limit")
        if value["kind"] != "terminal":
            if self.records >= self.max_records - 1:
                raise Unsupported("record_limit")
            if self.bytes + len(raw) > self.max_bytes - 4096:
                raise Unsupported("normalized_byte_limit")
        self.output.write(raw)
        self.records += 1
        self.bytes += len(raw)

    def feed(self, chunk):
        if self.terminal is not None:
            return
        if len(chunk) > 4096:
            self.finish("raw_chunk_limit")
            return
        remaining = 4194304 - self.raw_bytes
        chunk = chunk[:remaining]
        self.raw_bytes += len(chunk)
        self.buffer.extend(chunk)
        while b"\n" in self.buffer and self.terminal is None:
            line, _, tail = self.buffer.partition(b"\n")
            self.buffer[:] = tail
            self.line += 1
            if len(line) + 1 > 4096:
                self.finish("raw_line_limit")
                break
            try:
                self.parse(line.decode("ascii"))
            except Unsupported as error:
                self.finish(str(error))
            except (ValueError, UnicodeError):
                self.finish("unsupported_shape")
        if self.terminal is None:
            if len(self.buffer) >= 4096:
                self.finish("raw_line_limit")
            elif self.raw_bytes >= 4194304:
                self.finish("raw_byte_limit")

    def parse(self, line):
        prefix = re.match(r"\[pid\s+([0-9]+)\]\s+", line)
        if prefix:
            if int(prefix[1]) != self.root_pid:
                raise Unsupported("unobserved_identity")
            line = line[prefix.end():]
        if self.exited:
            raise Unsupported("record_after_exit")
        receipts = [self.line]
        call = f"root-1/c{self.line}"
        phase = "complete"
        if line.endswith(" <unfinished ...>"):
            beginning = re.match(r"(open|openat|openat2)\(", line)
            if self.pending is not None or beginning is None:
                raise Unsupported("unmatched_begin")
            self.pending = (beginning[1], line[:-len(" <unfinished ...>")], self.line, call)
            self.emit({"kind": "operation", "name": beginning[1], "phase": "begin",
                       "lifetime": "root-1", "call": call, "source_receipts": receipts,
                       "operands": {}, "result": {"state": "unavailable", "reason": "unfinished"},
                       "interpretation": "observed_operands_only"})
            return
        resumed = re.match(r"<\.\.\. ([a-z0-9_]+) resumed>\s*", line)
        if resumed:
            if self.pending is None or resumed[1] != self.pending[0]:
                raise Unsupported("unmatched_resume")
            _, start, receipt, call = self.pending
            self.pending = None
            line = start + line[resumed.end():]
            if len(line) > 4096:
                raise Unsupported("assembled_call_limit")
            receipts = [receipt, self.line]
            phase = "end"
        elif self.pending is not None:
            raise Unsupported("unresolved_call")
        exit_match = re.fullmatch(r"\+\+\+ exited with ([0-9]+) \+\+\+", line)
        if exit_match:
            self.exited = True
            self.emit({"kind": "identity", "lifetime": "root-1", "event": "exit",
                       "source_receipts": [self.line],
                       "outcome": {"kind": "exit_status", "value": exit_match[1]}})
            return
        match = re.fullmatch(r"(open|openat|openat2)\((.*)\)\s+= ([0-9]+|-1 [A-Z][A-Z0-9]+ \([^\n]*\))", line)
        if not match:
            raise Unsupported("unsupported_shape")
        result = match[3]
        if result.startswith("-1 "):
            outcome = {"state": "error", "value": "-1", "errno": result.split(" ")[1]}
        else:
            outcome = {"state": "success", "value": result}
        self.emit({"kind": "operation", "name": match[1], "phase": phase,
                   "lifetime": "root-1", "call": call,
                   "source_receipts": receipts, "operands": open_operands(match[1], match[2]),
                   "result": outcome, "interpretation": "observed_operands_only"})

    def finish(self, reason=None):
        if self.terminal is not None:
            return self.terminal
        reason = reason or ("partial_line" if self.buffer else "unresolved_call" if self.pending else
                            "observed_identity_unclosed" if not self.exited else "eof")
        self.terminal = {"kind": "terminal", "status": "complete" if reason == "eof" else "incomplete",
                         "reason": reason, "raw_bytes_consumed": self.raw_bytes,
                         "normalized_bytes_emitted_before_terminal": self.bytes,
                         "records_emitted_before_terminal": self.records,
                         "descendant_closure": "unknown"}
        self.emit(self.terminal)
        self.buffer.clear()
        return self.terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-pid", type=int, required=True)
    parser.add_argument("--max-records", type=int, default=16384)
    parser.add_argument("--max-bytes", type=int, default=4194304)
    args = parser.parse_args()
    try:
        adapter = TraceAdapter(sys.stdout.buffer, args.root_pid, args.max_records, args.max_bytes)
    except ValueError:
        parser.error("invalid identity or bounds")
    while adapter.terminal is None:
        chunk = os.read(sys.stdin.fileno(), 4096)
        if not chunk:
            break
        adapter.feed(chunk)
    return 0 if adapter.finish()["status"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
