#!/usr/bin/env node
/**
 * System monitor, for Claude, on this Mac.
 *
 * A tiny MCP server (no dependencies) that runs sysmon.py on the Mac itself, so any
 * Claude session, including cloud ones, can check the machine and clean up without
 * anyone opening a terminal.
 *
 *   system_scan     look: memory, swap, heavy processes, leftover dev processes, worktrees
 *   system_details  one full section of the last scan
 *   system_cleanup  act: prune dead worktree records, remove unused worktrees, stop pids
 *
 * What it deliberately cannot do: force-remove a worktree, delete a branch, force-kill
 * a process, or stop anything the last scan did not list as a leftover dev process.
 */
import { execFile } from "node:child_process";
import { readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), "..", "skills", "system-monitor", "scripts", "sysmon.py");
const PLAN = join(homedir(), ".sysmon", "plan.json");
const SECTIONS = ["system", "top_cpu", "top_memory", "top_apps", "dev_processes", "worktrees", "scratch"];

const TOOLS = [
  {
    name: "system_scan",
    description:
      "Check this Mac: memory, swap, load, disk, the heaviest processes and apps, leftover dev processes (dev servers, MCP servers, headless browsers, agent CLIs) and every git worktree with a verdict (prune, remove, review, keep). Changes nothing. Saves the full result to ~/.sysmon/plan.json and returns a summary. Can take a minute.",
    inputSchema: {
      type: "object",
      properties: { stale_days: { type: "number", description: "Days untouched before a clean worktree counts as unused. Default 14." } },
    },
    annotations: { readOnlyHint: true },
  },
  {
    name: "system_details",
    description: "Return one full section of the last scan: " + SECTIONS.join(", ") + ".",
    inputSchema: { type: "object", properties: { section: { type: "string", enum: SECTIONS } }, required: ["section"] },
    annotations: { readOnlyHint: true },
  },
  {
    name: "system_cleanup",
    description:
      "Act on the last scan (it must be under an hour old). Only does what is asked: prune clears git records of worktrees whose folder is gone; remove_unused_worktrees removes every worktree the scan marked 'remove', or only worktree_paths if given (never forced, branch kept, .env and other ignored local files copied to ~/.sysmon/saved first); stop_pids sends a polite stop to those pids, only if each is still the leftover dev process the scan saw. Ask the person which items first.",
    inputSchema: {
      type: "object",
      properties: {
        prune: { type: "boolean" },
        remove_unused_worktrees: { type: "boolean" },
        worktree_paths: { type: "array", items: { type: "string" } },
        stop_pids: { type: "array", items: { type: "number" } },
      },
    },
    annotations: { destructiveHint: true },
  },
];

const py = (args, timeout) =>
  new Promise((resolve) =>
    execFile("python3", [SCRIPT, ...args], { timeout, maxBuffer: 20e6 }, (err, stdout, stderr) =>
      resolve({ ok: !err, text: (stdout || "").trim() || (stderr || "").trim() || String(err || "") })
    )
  );

async function call(name, a = {}) {
  if (name === "system_scan") {
    const days = Number.isFinite(a.stale_days) ? String(Math.max(0, Math.round(a.stale_days))) : "14";
    return py(["scan", "--stale-days", days], 600_000);
  }
  if (name === "system_details") {
    if (!SECTIONS.includes(a.section)) return { ok: false, text: "section must be one of: " + SECTIONS.join(", ") };
    try {
      return { ok: true, text: JSON.stringify(JSON.parse(readFileSync(PLAN, "utf8"))[a.section], null, 1) };
    } catch {
      return { ok: false, text: "No scan yet. Run system_scan first." };
    }
  }
  if (name === "system_cleanup") {
    let age;
    try {
      age = Date.now() - statSync(PLAN).mtimeMs;
    } catch {
      return { ok: false, text: "No scan yet. Run system_scan first." };
    }
    if (age > 3_600_000) return { ok: false, text: "The last scan is over an hour old. Run system_scan again first." };
    const only = [];
    const args = ["apply", PLAN];
    if (a.prune) only.push("prune");
    const paths = (a.worktree_paths || []).filter((p) => typeof p === "string" && p && !p.includes(","));
    if (a.remove_unused_worktrees || paths.length) only.push("worktrees");
    if (paths.length) args.push("--worktrees", paths.join(","));
    const pids = (a.stop_pids || []).filter(Number.isInteger);
    if (pids.length) {
      only.push("processes");
      args.push("--pids", pids.join(","));
    }
    if (!only.length) return { ok: false, text: "Nothing asked for. Set prune, remove_unused_worktrees, worktree_paths or stop_pids." };
    return py([...args, "--only", only.join(",")], 900_000);
  }
  return { ok: false, text: "Unknown tool: " + name };
}

const send = (msg) => process.stdout.write(JSON.stringify({ jsonrpc: "2.0", ...msg }) + "\n");

createInterface({ input: process.stdin }).on("line", async (line) => {
  let req;
  try {
    req = JSON.parse(line);
  } catch {
    return;
  }
  const { id, method, params } = req;
  if (id === undefined) return; // notifications need no reply
  if (method === "initialize") {
    send({
      id,
      result: {
        protocolVersion: params?.protocolVersion || "2025-06-18",
        capabilities: { tools: {} },
        serverInfo: { name: "system-monitor", version: "0.1.0" },
      },
    });
  } else if (method === "ping") {
    send({ id, result: {} });
  } else if (method === "tools/list") {
    send({ id, result: { tools: TOOLS } });
  } else if (method === "tools/call") {
    const r = await call(params?.name, params?.arguments);
    send({ id, result: { content: [{ type: "text", text: r.text }], isError: !r.ok } });
  } else {
    send({ id, error: { code: -32601, message: "Method not found: " + method } });
  }
});
