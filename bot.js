import { Bot } from "grammy";
import http from "node:http";
import { moderateMessage, aiChat } from "./moderation.js";

const BOT_TOKEN = process.env.BOT_TOKEN;
const MISTRAL_API_KEY = process.env.MISTRAL_API_KEY;
const ADMIN_IDS = (process.env.ADMIN_IDS || "")
  .split(",")
  .map((id) => id.trim())
  .filter(Boolean);
const ALLOWED_GROUP_IDS = (process.env.ALLOWED_GROUP_IDS || "")
  .split(",")
  .map((id) => id.trim())
  .filter(Boolean);
const WARNING_MESSAGE =
  process.env.WARNING_MESSAGE ||
  "⚠️ Message removed: severe profanity is not allowed here.";
const WARNING_TTL = Number(process.env.WARNING_TTL || 5) * 1000;
const OTHER_MSGS = (process.env.OTHER_MSGS || "")
  .split(",")
  .map((w) => w.trim().toLowerCase())
  .filter(Boolean);

console.log(`[config] OTHER_MSGS loaded: ${OTHER_MSGS.length ? JSON.stringify(OTHER_MSGS) : "(empty)"}`);
console.log(`[config] ADMIN_IDS: ${JSON.stringify(ADMIN_IDS)}`);
console.log(`[config] ALLOWED_GROUP_IDS: ${JSON.stringify(ALLOWED_GROUP_IDS)}`);

if (!BOT_TOKEN || !MISTRAL_API_KEY) {
  console.error("Missing BOT_TOKEN or MISTRAL_API_KEY. Set them in your environment.");
  process.exit(1);
}

const bot = new Bot(BOT_TOKEN);

bot.catch((err) => {
  console.error("[bot] error:", err.error);
});

bot.command("ping", async (ctx) => {
  await ctx.reply("pong 🏓");
});

bot.command("start", async (ctx) => {
  if (ADMIN_IDS.includes(String(ctx.from.id))) {
    await ctx.reply("Nothing started, will delete broski's bad bad messeges");
  }
});

bot.command("ai", async (ctx) => {
  const question = ctx.match;
  if (!question) {
    await ctx.reply("ask me something broski, like /ai how are you");
    return;
  }
  try {
    const answer = await aiChat(question, MISTRAL_API_KEY);
    await ctx.reply(answer);
  } catch (err) {
    await ctx.reply("my bad broski, brain ain't working rn 😅");
    console.error(`[ai] error: ${err.message}`);
  }
});bot.command("id", async (ctx) => {
  await ctx.reply(`Your user ID: ${ctx.from.id}\nThis chat ID: ${ctx.chat.id}`);
});

bot.on("message:text", async (ctx) => {
  const msg = ctx.message;

  if (ctx.chat.type === "private") return;
  if (ALLOWED_GROUP_IDS.length && !ALLOWED_GROUP_IDS.includes(String(msg.chat.id))) return;
  if (ADMIN_IDS.includes(String(msg.from.id))) return;

  try {
    const lower = msg.text.toLowerCase();
    const hit = OTHER_MSGS.find((w) => {
      if (!w) return false;
      const found = lower.includes(w);
      if (found) console.log(`[blocked-word] match: "${w}" in "${lower}"`);
      return found;
    });

    if (hit) {
      await ctx.deleteMessage();
      const warning = await ctx.reply(
        `${WARNING_MESSAGE}\n— <i>${msg.from.first_name}</i>`,
        { parse_mode: "HTML" }
      );
      setTimeout(async () => {
        try {
          await bot.api.deleteMessage(ctx.chat.id, warning.message_id);
        } catch {
          /* warning already gone */
        }
      }, WARNING_TTL);
      console.log(
        `[blocked-word] chat=${ctx.chat.id} user=${msg.from.id} word="${hit}"`
      );
      return;
    }

    const { category } = await moderateMessage(msg.text, MISTRAL_API_KEY);

    if (category === "severe") {
      await ctx.deleteMessage();

      const warning = await ctx.reply(
        `${WARNING_MESSAGE}\n— <i>${msg.from.first_name}</i>`,
        { parse_mode: "HTML" }
      );

      setTimeout(async () => {
        try {
          await bot.api.deleteMessage(ctx.chat.id, warning.message_id);
        } catch {
          /* warning already gone */
        }
      }, WARNING_TTL);

      console.log(
        `[moderated] chat=${ctx.chat.id} user=${msg.from.id}`
      );
    }
  } catch (err) {
    console.error(`[moderation] skipped message ${msg.message_id}: ${err.message}`);
  }
});

const PORT = process.env.PORT || 3000;
http
  .createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("Ten moderation bot is running.");
  })
  .listen(PORT, () => {
    console.log(`[health] listening on :${PORT}`);
  });

bot.start({
  onStart: (botInfo) => console.log(`[bot] started as @${botInfo.username}`),
});

process.on("SIGINT", () => process.exit(0));
process.on("SIGTERM", () => process.exit(0));
