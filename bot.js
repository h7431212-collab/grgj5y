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

async function checkBlocked(text) {
  const lower = text.toLowerCase();
  const hit = OTHER_MSGS.find((w) => {
    if (!w) return false;
    const found = lower.includes(w);
    if (found) console.log(`[blocked-word] match: "${w}" in "${lower}"`);
    return found;
  });
  if (hit) return { blocked: true, reason: "word", hit };

  const { category, reason } = await moderateMessage(text, MISTRAL_API_KEY);
  if (category === "severe") return { blocked: true, reason: reason || "severe" };

  return { blocked: false };
}

async function deleteAndWarn(ctx, firstName) {
  await ctx.deleteMessage();
  const warning = await ctx.reply(
    `${WARNING_MESSAGE}\n— <i>${firstName}</i>`,
    { parse_mode: "HTML" }
  );
  setTimeout(async () => {
    try {
      await bot.api.deleteMessage(ctx.chat.id, warning.message_id);
    } catch {
      /* warning already gone */
    }
  }, WARNING_TTL);
}

async function shouldModerate(ctx) {
  if (ctx.chat.type === "private") return false;
  if (ALLOWED_GROUP_IDS.length && !ALLOWED_GROUP_IDS.includes(String(ctx.chat.id))) return false;
  if (ADMIN_IDS.includes(String(ctx.from.id))) return false;
  return true;
}

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

  if (await shouldModerate(ctx)) {
    try {
      const result = await checkBlocked(question);
      if (result.blocked) {
        await deleteAndWarn(ctx, ctx.from.first_name);
        console.log(
          `[blocked-ai] chat=${ctx.chat.id} user=${ctx.from.id} reason=${result.reason}`
        );
        return;
      }
    } catch (err) {
      console.error(`[moderation] ai check skipped: ${err.message}`);
    }
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
  if (!(await shouldModerate(ctx))) return;

  try {
    const result = await checkBlocked(ctx.message.text);
    if (result.blocked) {
      await deleteAndWarn(ctx, ctx.from.first_name);
      console.log(
        `[moderated] chat=${ctx.chat.id} user=${ctx.from.id} reason=${result.reason}`
      );
    }
  } catch (err) {
    console.error(`[moderation] skipped message: ${err.message}`);
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
