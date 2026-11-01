#!/usr/bin/env node
/**
 * Proton Mail, for Claude, through Proton Mail Bridge.
 *
 * Bridge decrypts mail on this Mac and serves it over IMAP on 127.0.0.1.
 * This server talks to that, and only that, and gives Claude a few careful
 * tools: list folders, search, read, move, label, flag, and write drafts.
 *
 * What it deliberately cannot do:
 *   - send anything. Drafts land in Proton's Drafts folder; you send them.
 *   - permanently delete. "Trash" is a move, and Proton empties it, not this.
 *
 * Reading never marks mail as read (BODY.PEEK, read-only mailbox).
 *
 * Setup: see README.md. The Bridge password is read from the macOS Keychain
 * (service "proton-bridge"), or PROTON_BRIDGE_PASSWORD if you prefer env.
 */
import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ImapFlow } from "imapflow";
import { simpleParser } from "mailparser";
import { z } from "zod";

const HOST = process.env.PROTON_BRIDGE_HOST || "127.0.0.1";
const PORT = Number(process.env.PROTON_BRIDGE_IMAP_PORT || 1143);
/**
 * The Bridge username: from PROTON_BRIDGE_USER, or else the account name on
 * the "proton-bridge" Keychain item, so a plugin install needs no settings.
 */
const keychainAccount = () => {
  try {
    const out = execFileSync(
      "/usr/bin/security",
      ["find-generic-password", "-s", "proton-bridge"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }
    );
    return out.match(/"acct"<blob>="([^"]*)"/)?.[1] ?? "";
  } catch {
    return "";
  }
};
const USER = process.env.PROTON_BRIDGE_USER || keychainAccount();
const FROM = process.env.PROTON_FROM || USER;
const MAX_BODY = 20_000;
const MAX_RESULTS = 200;

const password = () => {
  if (process.env.PROTON_BRIDGE_PASSWORD) {
    return process.env.PROTON_BRIDGE_PASSWORD;
  }
  // With the account name first, then any item under the service, so a
  // small mismatch in the account name doesn't stop it.
  const attempts = [
    ["find-generic-password", "-a", USER, "-s", "proton-bridge", "-w"],
    ["find-generic-password", "-s", "proton-bridge", "-w"],
  ];
  const reasons = [];
  for (const args of attempts) {
    try {
      const found = execFileSync("/usr/bin/security", args, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      }).trim();
      if (found) {
        return found;
      }
    } catch (err) {
      reasons.push(
        `${String(err?.stderr || err?.message || "").trim()} (exit ${err?.status})`
      );
    }
  }
  throw new Error(
    `No Bridge password found in the Keychain under "proton-bridge": ${reasons.join("; ")}`
  );
};

/** One short-lived connection per call: Bridge is local, so it's quick. */
const withImap = async (fn) => {
  if (!USER) {
    throw new Error(
      'No Bridge username: add the Bridge password to the Keychain with `security add-generic-password -a "<Bridge username>" -s proton-bridge -w`, or set PROTON_BRIDGE_USER.'
    );
  }
  const client = new ImapFlow({
    auth: { pass: password(), user: USER },
    host: HOST,
    logger: false,
    port: PORT,
    secure: false,
    // Bridge's certificate is self-signed, and the connection never leaves
    // this machine, so it is accepted for 127.0.0.1 only.
    tls: { rejectUnauthorized: !["127.0.0.1", "localhost"].includes(HOST) },
  });
  await client.connect();
  try {
    return await fn(client);
  } finally {
    await client.logout().catch(() => undefined);
  }
};

const ok = (data) => ({
  content: [{ text: JSON.stringify(data, null, 2), type: "text" }],
});

/**
 * IMAP errors arrive as a bare "Command failed"; the reason is in
 * responseText. Say what actually went wrong, and what usually fixes it.
 */
const explain = (err) => {
  if (!(err instanceof Error)) {
    return String(err);
  }
  const detail = [err.responseText, err.serverResponseCode, err.code]
    .filter(Boolean)
    .join(" | ");
  if (err.authenticationFailed) {
    return `Bridge refused the login${detail ? ` (${detail})` : ""}. Check that PROTON_BRIDGE_USER is the username Bridge shows, and that the Keychain item holds Bridge's password, not your Proton password.`;
  }
  if (err.code === "ECONNREFUSED") {
    return `Nothing is listening on ${HOST}:${PORT}. Is Proton Mail Bridge running, and is that its IMAP port?`;
  }
  return detail ? `${err.message}: ${detail}` : err.message;
};

/** Failures go to error.log beside this file, without any password. */
const LOG = new URL("./error.log", import.meta.url);

const record = (err) => {
  try {
    appendFileSync(
      LOG,
      `${JSON.stringify({
        at: new Date().toISOString(),
        authenticationFailed: err?.authenticationFailed,
        code: err?.code,
        host: HOST,
        message: err?.message,
        port: PORT,
        responseStatus: err?.responseStatus,
        responseText: err?.responseText,
        stack: err?.stack?.split("\n").slice(0, 6).join(" | "),
        user: USER,
      })}\n`
    );
  } catch {
    // Logging must never be why a tool fails.
  }
};

const fail = (err) => {
  record(err);
  return { content: [{ text: explain(err), type: "text" }], isError: true };
};

const safe =
  (fn) =>
  async (...args) => {
    try {
      return await fn(...args);
    } catch (err) {
      return fail(err);
    }
  };

const addr = (list) =>
  (list || [])
    .map((a) => (a.name ? `${a.name} <${a.address}>` : a.address))
    .join(", ");

const summary = (msg) => ({
  date:
    (msg.internalDate ?? msg.envelope?.date)?.toISOString?.() ?? null,
  flagged: msg.flags?.has("\\Flagged") ?? false,
  from: addr(msg.envelope?.from),
  read: msg.flags?.has("\\Seen") ?? false,
  size: msg.size,
  subject: msg.envelope?.subject ?? "",
  to: addr(msg.envelope?.to),
  uid: msg.uid,
});

const uidList = z
  .array(z.number().int().positive())
  .min(1)
  .max(500)
  .describe("Message UIDs from search_messages, in that folder");

const server = new McpServer({ name: "proton-mail", version: "1.0.0" });

server.registerTool(
  "list_folders",
  {
    description:
      "List mail folders and labels with total and unread counts. Proton folders appear as 'Folders/<name>', labels as 'Labels/<name>'.",
    inputSchema: {},
  },
  safe(() =>
    withImap(async (client) => {
      const boxes = await client.list({
        statusQuery: { messages: true, unseen: true },
      });
      return ok(
        boxes.map((b) => ({
          messages: b.status?.messages ?? null,
          path: b.path,
          unread: b.status?.unseen ?? null,
        }))
      );
    })
  )
);

/** Search filters shared by the search, summary and bulk tools. */
const filterShape = {
  before: z.string().optional().describe("ISO date: received before"),
  folder: z.string().default("INBOX"),
  from: z.string().optional().describe("Sender name or address contains"),
  since: z.string().optional().describe("ISO date: received on or after"),
  starred: z.boolean().optional().describe("true: only starred; false: skip starred"),
  subject: z.string().optional(),
  text: z.string().optional().describe("Anywhere in the message (slower)"),
  unread: z.boolean().optional().describe("true: only unread; false: only read"),
};

const toQuery = ({ from, subject, text, since, before, unread, starred }) => {
  const query = {};
  if (from) query.from = from;
  if (subject) query.subject = subject;
  if (text) query.text = text;
  if (since) query.since = new Date(since);
  if (before) query.before = new Date(before);
  if (unread === true) query.seen = false;
  if (unread === false) query.seen = true;
  if (starred === true) query.flagged = true;
  if (starred === false) query.flagged = false;
  if (Object.keys(query).length === 0) query.all = true;
  return query;
};

/** Proton's UIDs don't follow date order, so dates come from the messages. */
const SORT_CAP = 3000;

const senderOf = (msg) => {
  const a = msg.envelope?.from?.[0];
  return a ? (a.address || a.name || "").toLowerCase() : "(unknown)";
};

server.registerTool(
  "sender_summary",
  {
    description:
      "Who is filling a folder: counts by sender and by sender domain for messages matching the filters, biggest first. Use before bulk moves.",
    inputSchema: {
      ...filterShape,
      top: z.number().int().min(1).max(300).default(60),
    },
  },
  safe((args) =>
    withImap(async (client) => {
      const lock = await client.getMailboxLock(args.folder, { readOnly: true });
      try {
        const uids = (await client.search(toQuery(args), { uid: true })) || [];
        const bySender = new Map();
        const byDomain = new Map();
        const unreadBy = new Map();
        if (uids.length > 0) {
          for await (const msg of client.fetch(
            uids.join(","),
            { envelope: true, flags: true, uid: true },
            { uid: true }
          )) {
            const s = senderOf(msg);
            const d = s.includes("@") ? s.split("@")[1] : s;
            bySender.set(s, (bySender.get(s) ?? 0) + 1);
            byDomain.set(d, (byDomain.get(d) ?? 0) + 1);
            if (!msg.flags?.has("\\Seen")) {
              unreadBy.set(s, (unreadBy.get(s) ?? 0) + 1);
            }
          }
        }
        const rank = (m) =>
          [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, args.top);
        return ok({
          domains: rank(byDomain).map(([domain, count]) => ({ count, domain })),
          matched: uids.length,
          senders: rank(bySender).map(([sender, count]) => ({
            count,
            sender,
            unread: unreadBy.get(sender) ?? 0,
          })),
        });
      } finally {
        lock.release();
      }
    })
  )
);

server.registerTool(
  "move_matching",
  {
    description:
      "Move EVERY message matching the filters to another folder in one go (e.g. archive everything older than a date). Always run with dryRun: true first to see the count. Nothing is deleted; Archive and Trash are recoverable.",
    inputSchema: {
      ...filterShape,
      dryRun: z.boolean().default(true),
      max: z
        .number()
        .int()
        .min(1)
        .max(5000)
        .default(600)
        .describe(
          "Most to move in this call. Bridge moves roughly 1,000 a minute and calls time out at 60s, so keep it under ~800 and call again until `remaining` is 0."
        ),
      to: z.string().describe("Destination folder, e.g. 'Archive'"),
    },
  },
  safe((args) =>
    withImap(async (client) => {
      if (["All Mail", "Starred"].includes(args.to)) {
        throw new Error(`'${args.to}' is a view, not a folder you can move into.`);
      }
      const lock = await client.getMailboxLock(args.folder);
      try {
        const uids = (await client.search(toQuery(args), { uid: true })) || [];
        if (args.dryRun || uids.length === 0) {
          return ok({ dryRun: args.dryRun, from: args.folder, matched: uids.length, to: args.to });
        }
        // At most `max` per call, in chunks of 200, so each call finishes
        // inside the caller's timeout; the caller loops until none remain.
        const batch = uids.slice(0, args.max);
        let moved = 0;
        for (let i = 0; i < batch.length; i += 200) {
          const chunk = batch.slice(i, i + 200);
          await client.messageMove(chunk.join(","), args.to, { uid: true });
          moved += chunk.length;
        }
        return ok({
          from: args.folder,
          moved,
          remaining: uids.length - moved,
          to: args.to,
        });
      } finally {
        lock.release();
      }
    })
  )
);

server.registerTool(
  "search_messages",
  {
    description:
      "Search a folder, newest first. Returns uid, from, to, subject, date, read and flagged. Combine filters freely; with none, returns the latest messages.",
    inputSchema: {
      ...filterShape,
      limit: z.number().int().min(1).max(MAX_RESULTS).default(50),
    },
  },
  safe((args) =>
    withImap(async (client) => {
      const lock = await client.getMailboxLock(args.folder, { readOnly: true });
      try {
        const uids = (await client.search(toQuery(args), { uid: true })) || [];
        if (uids.length === 0) {
          return ok({ matched: 0, messages: [] });
        }
        // Dates first (cheap), then full details for the newest `limit`.
        // Past SORT_CAP matches, the highest UIDs stand in: narrow with
        // since/before for exact date order on huge folders.
        const pool = uids.sort((a, b) => b - a).slice(0, SORT_CAP);
        const dated = [];
        for await (const msg of client.fetch(
          pool.join(","),
          { internalDate: true, uid: true },
          { uid: true }
        )) {
          dated.push([msg.uid, msg.internalDate?.getTime?.() ?? 0]);
        }
        const pick = dated
          .sort((a, b) => b[1] - a[1])
          .slice(0, args.limit)
          .map(([uid]) => uid);
        const messages = [];
        for await (const msg of client.fetch(
          pick.join(","),
          { envelope: true, flags: true, internalDate: true, size: true, uid: true },
          { uid: true }
        )) {
          messages.push(summary(msg));
        }
        const order = new Map(pick.map((uid, i) => [uid, i]));
        messages.sort((a, b) => order.get(a.uid) - order.get(b.uid));
        return ok({ matched: uids.length, messages, shown: messages.length });
      } finally {
        lock.release();
      }
    })
  )
);

server.registerTool(
  "read_message",
  {
    description:
      "Read one message's text (HTML is converted to text). Does not mark it as read.",
    inputSchema: {
      folder: z.string().default("INBOX"),
      uid: z.number().int().positive(),
    },
  },
  safe(({ folder, uid }) =>
    withImap(async (client) => {
      // Bridge marks a message read when its body is fetched, even with
      // PEEK, so an unread message is put back to unread afterwards.
      const lock = await client.getMailboxLock(folder);
      try {
        const before = await client.fetchOne(
          String(uid),
          { flags: true, uid: true },
          { uid: true }
        );
        if (!before) {
          throw new Error(`No message ${uid} in ${folder}`);
        }
        const wasUnread = !before.flags?.has("\\Seen");
        const msg = await client.fetchOne(
          String(uid),
          { flags: true, source: true, uid: true },
          { uid: true }
        );
        if (wasUnread) {
          await client
            .messageFlagsRemove(String(uid), ["\\Seen"], { uid: true })
            .catch(() => undefined);
        }
        const mail = await simpleParser(msg.source);
        const body = (mail.text || mail.html?.replace(/<[^>]+>/g, " ") || "")
          .replace(/\n{3,}/g, "\n\n")
          .trim();
        return ok({
          attachments: (mail.attachments || []).map((a) => ({
            filename: a.filename,
            size: a.size,
            type: a.contentType,
          })),
          body:
            body.length > MAX_BODY
              ? `${body.slice(0, MAX_BODY)}\n…[truncated]`
              : body,
          cc: mail.cc?.text ?? "",
          date: mail.date?.toISOString() ?? null,
          from: mail.from?.text ?? "",
          messageId: mail.messageId ?? null,
          read: !wasUnread,
          subject: mail.subject ?? "",
          to: mail.to?.text ?? "",
          uid,
        });
      } finally {
        lock.release();
      }
    })
  )
);

server.registerTool(
  "move_messages",
  {
    description:
      "Move messages to another folder, e.g. 'Archive', 'Spam', 'Trash' or 'Folders/Clients'. Trash is recoverable; nothing here deletes permanently.",
    inputSchema: {
      folder: z.string().default("INBOX").describe("Where they are now"),
      to: z.string().describe("Destination folder path from list_folders"),
      uids: uidList,
    },
  },
  safe(({ folder, to, uids }) =>
    withImap(async (client) => {
      const lock = await client.getMailboxLock(folder);
      try {
        const result = await client.messageMove(uids.join(","), to, {
          uid: true,
        });
        return ok({ moved: uids.length, to, uidMap: result?.uidMap ? Object.fromEntries(result.uidMap) : null });
      } finally {
        lock.release();
      }
    })
  )
);

server.registerTool(
  "label_messages",
  {
    description:
      "Add a Proton label to messages without moving them. Use a 'Labels/<name>' path from list_folders.",
    inputSchema: {
      folder: z.string().default("INBOX"),
      label: z.string().describe("e.g. 'Labels/Clients'"),
      uids: uidList,
    },
  },
  safe(({ folder, label, uids }) =>
    withImap(async (client) => {
      if (!label.startsWith("Labels/")) {
        throw new Error("Labels live under 'Labels/'. Use move_messages for folders.");
      }
      const lock = await client.getMailboxLock(folder);
      try {
        await client.messageCopy(uids.join(","), label, { uid: true });
        return ok({ label, labelled: uids.length });
      } finally {
        lock.release();
      }
    })
  )
);

server.registerTool(
  "create_folder",
  {
    description:
      "Create a folder ('Folders/<name>') or a label ('Labels/<name>').",
    inputSchema: { path: z.string() },
  },
  safe(({ path }) =>
    withImap(async (client) => {
      if (!(path.startsWith("Folders/") || path.startsWith("Labels/"))) {
        throw new Error("Start the path with 'Folders/' or 'Labels/'.");
      }
      const result = await client.mailboxCreate(path);
      return ok({ created: result.created, path: result.path });
    })
  )
);

server.registerTool(
  "set_flags",
  {
    description: "Mark messages read or unread, and starred or not.",
    inputSchema: {
      flagged: z.boolean().optional().describe("Starred"),
      folder: z.string().default("INBOX"),
      read: z.boolean().optional(),
      uids: uidList,
    },
  },
  safe(({ folder, uids, read, flagged }) =>
    withImap(async (client) => {
      const lock = await client.getMailboxLock(folder);
      try {
        const range = uids.join(",");
        if (read === true) await client.messageFlagsAdd(range, ["\\Seen"], { uid: true });
        if (read === false) await client.messageFlagsRemove(range, ["\\Seen"], { uid: true });
        if (flagged === true) await client.messageFlagsAdd(range, ["\\Flagged"], { uid: true });
        if (flagged === false) await client.messageFlagsRemove(range, ["\\Flagged"], { uid: true });
        return ok({ flagged, read, updated: uids.length });
      } finally {
        lock.release();
      }
    })
  )
);

/**
 * Unsubscribing, the standard way: the List-Unsubscribe header a sender puts
 * on its mail (RFC 2369), and its one-click form (RFC 8058), which is a POST
 * with a fixed body and nothing about you in it. Only https URLs are used,
 * and never to a private or local address.
 */
const PRIVATE_HOST =
  /^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|\[?::1\]?|0\.)/i;

const unsubscribeOptions = async (client, folder, from) => {
  const lock = await client.getMailboxLock(folder, { readOnly: true });
  try {
    const uids = (await client.search({ from }, { uid: true })) || [];
    if (uids.length === 0) {
      throw new Error(`No mail from "${from}" in ${folder}.`);
    }
    // The newest message carries the current unsubscribe link. UIDs don't
    // follow date order on Proton, so dates decide.
    const newest = [];
    for await (const msg of client.fetch(
      uids.slice(-SORT_CAP).join(","),
      { internalDate: true, uid: true },
      { uid: true }
    )) {
      newest.push(msg);
    }
    newest.sort((a, b) => (b.internalDate?.getTime() ?? 0) - (a.internalDate?.getTime() ?? 0));
    const msg = await client.fetchOne(
      String(newest[0].uid),
      {
        envelope: true,
        headers: ["list-unsubscribe", "list-unsubscribe-post"],
        uid: true,
      },
      { uid: true }
    );
    const raw = msg.headers?.toString() ?? "";
    const unfolded = raw.replace(/\r?\n[ \t]+/g, " ");
    const list = /^list-unsubscribe:\s*(.*)$/im.exec(unfolded)?.[1] ?? "";
    const post = /^list-unsubscribe-post:\s*(.*)$/im.exec(unfolded)?.[1] ?? "";
    const targets = [...list.matchAll(/<([^>]+)>/g)].map((m) => m[1].trim());
    const https = targets.filter((t) => {
      try {
        const u = new URL(t);
        return u.protocol === "https:" && !PRIVATE_HOST.test(u.hostname);
      } catch {
        return false;
      }
    });
    const mailto = targets.find((t) => t.toLowerCase().startsWith("mailto:"));
    return {
      from: addr(msg.envelope?.from),
      https: https[0] ?? null,
      mailto: mailto ?? null,
      oneClick: Boolean(https[0]) && /List-Unsubscribe=One-Click/i.test(post),
      subject: msg.envelope?.subject ?? "",
      uid: msg.uid,
    };
  } finally {
    lock.release();
  }
};

server.registerTool(
  "unsubscribe",
  {
    description:
      "Unsubscribe from a sender using its own List-Unsubscribe header. With one-click support it unsubscribes immediately (a standard POST, no personal data). Otherwise it returns the link to open in a browser, or for mailto-only senders saves an unsubscribe email to Drafts. Use only for senders Dallas has approved, and never for spam (unsubscribing confirms the address).",
    inputSchema: {
      check: z
        .boolean()
        .default(false)
        .describe("true: only report what's available, change nothing"),
      folder: z.string().default("Archive").describe("Where that sender's mail is"),
      from: z.string().min(3).describe("Sender address or domain, as in sender_summary"),
    },
  },
  safe(({ from, folder, check }) =>
    withImap(async (client) => {
      const opt = await unsubscribeOptions(client, folder, from);
      const base = { from: opt.from, subject: opt.subject };
      if (check) {
        return ok({ ...base, link: opt.https, mailto: opt.mailto, oneClick: opt.oneClick });
      }
      if (opt.oneClick) {
        const res = await fetch(opt.https, {
          body: "List-Unsubscribe=One-Click",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          method: "POST",
          redirect: "follow",
          signal: AbortSignal.timeout(15_000),
        });
        return ok({ ...base, method: "one-click", status: res.status, unsubscribed: res.ok });
      }
      if (opt.https) {
        return ok({ ...base, method: "link", note: "No one-click support. Open this link to finish.", url: opt.https });
      }
      if (opt.mailto) {
        const target = new URL(opt.mailto);
        const to = decodeURIComponent(target.pathname);
        const subject = target.searchParams.get("subject") || "unsubscribe";
        const body = target.searchParams.get("body") || "unsubscribe";
        const message = [
          `From: ${FROM}`,
          `To: ${to}`,
          `Subject: ${subject}`,
          `Date: ${new Date().toUTCString()}`,
          "MIME-Version: 1.0",
          "Content-Type: text/plain; charset=utf-8",
          "",
          body,
        ].join("\r\n");
        await client.append("Drafts", message, ["\\Draft", "\\Seen"]);
        return ok({ ...base, method: "mailto", note: "Saved an unsubscribe email to Drafts. Send it from Proton.", to });
      }
      return ok({ ...base, method: "none", note: "This sender offers no unsubscribe header. Filter or block it in Proton instead." });
    })
  )
);

/** RFC 2047 for non-ASCII headers. */
const header = (value) =>
  /^[\x20-\x7e]*$/.test(value)
    ? value
    : `=?UTF-8?B?${Buffer.from(value, "utf8").toString("base64")}?=`;

server.registerTool(
  "create_draft",
  {
    description:
      "Save a plain-text draft in Proton's Drafts folder. It is NOT sent: Dallas reviews and sends it from Proton. Pass replyToUid (and its folder) to thread it as a reply.",
    inputSchema: {
      body: z.string().min(1),
      cc: z.string().optional(),
      folder: z.string().default("INBOX").describe("Folder of replyToUid"),
      replyToUid: z.number().int().positive().optional(),
      subject: z.string().optional(),
      to: z.string().optional().describe("Defaults to the original sender when replying"),
    },
  },
  safe(({ to, cc, subject, body, replyToUid, folder }) =>
    withImap(async (client) => {
      let inReplyTo = null;
      let references = "";
      let replySubject = subject;
      let replyTo = to;
      if (replyToUid) {
        const lock = await client.getMailboxLock(folder, { readOnly: true });
        try {
          const msg = await client.fetchOne(
            String(replyToUid),
            { envelope: true, headers: ["references"], uid: true },
            { uid: true }
          );
          if (!msg) {
            throw new Error(`No message ${replyToUid} in ${folder}`);
          }
          inReplyTo = msg.envelope?.messageId ?? null;
          const prior = msg.headers?.toString().replace(/^references:\s*/i, "").trim() ?? "";
          references = [prior, inReplyTo].filter(Boolean).join(" ");
          const original = msg.envelope?.subject ?? "";
          replySubject ??= /^re:/i.test(original) ? original : `Re: ${original}`;
          replyTo ??= addr(msg.envelope?.replyTo?.length ? msg.envelope.replyTo : msg.envelope?.from);
        } finally {
          lock.release();
        }
      }
      if (!replyTo) {
        throw new Error("Who is it to? Pass `to`, or replyToUid.");
      }
      const lines = [
        `From: ${FROM}`,
        `To: ${header(replyTo)}`,
        cc ? `Cc: ${header(cc)}` : null,
        `Subject: ${header(replySubject ?? "")}`,
        `Date: ${new Date().toUTCString()}`,
        inReplyTo ? `In-Reply-To: ${inReplyTo}` : null,
        references ? `References: ${references}` : null,
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=utf-8",
        "Content-Transfer-Encoding: base64",
        "",
        Buffer.from(body.replace(/\r?\n/g, "\r\n"), "utf8")
          .toString("base64")
          .replace(/.{76}/g, "$&\r\n"),
      ].filter((l) => l !== null);
      const result = await client.append(
        "Drafts",
        lines.join("\r\n"),
        ["\\Draft", "\\Seen"]
      );
      return ok({
        note: "Saved to Drafts. Not sent.",
        saved: true,
        subject: replySubject,
        to: replyTo,
        uid: result?.uid ?? null,
      });
    })
  )
);

await server.connect(new StdioServerTransport());
