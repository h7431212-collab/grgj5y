const MODELS = (process.env.MODELS || "mistral-small-latest,mistral-small-2506,open-mistral-nemo")
  .split(",")
  .map((m) => m.trim())
  .filter(Boolean);

let index = 0;

function nextModel() {
  const model = MODELS[index % MODELS.length];
  index++;
  return model;
}

const SYSTEM_PROMPT = `You are an expert multilingual content moderation AI for a Telegram group.
Your job: understand the MEANING, INTENT, and CONTEXT of a message — not just individual words.
You must catch content that can get a Telegram group BANNED, including clever attempts to bypass filters.

Think step by step:
1. Detect the language. Translate if needed.
2. Understand what the person is actually saying — the real meaning behind the words.
3. Check for bypass attempts: deliberate misspellings, leet speak (f4ck, $h!t), emoji/spacing substitutions (f u c k, f*ck, f̲u̲c̲k̲), coded language, euphemisms for illegal stuff, or mixed-language smuggling.
4. Classify into ONE category:

"safe" — Normal message. Clean conversation, questions, jokes, opinions, casual chat.

"mild" — Casual swearing ALLOWED in normal conversation: "fuck", "shit", "ass", "bitch", "damn", "asshole", etc. used casually or as emphasis. This does NOT get groups banned.

"severe" — ANY of the following means SEVERE:
  - Racial slurs (hard R n-word, ch*nk, sp*c, k*ke, p*ki, etc.) — ANY context, even joking
  - Homophobic slurs (f*ggot, d*ke, tr*nny, etc.)
  - Sexist/misogynistic abuse directed at someone ("rape her", "she deserved it")
  - Hate speech against any race, religion, caste, nationality, sexuality, disability
  - Incitement to violence ("kill all X", "beat them up", "go attack")
  - Death threats or threats of real-world harm
  - Sexual content involving minors (CSAM) — ANY reference, joke, or implication
  - Drug dealing / sourcing ("got weed for sale", "DM for plug", selling pills, coke, etc.)
  - Weapons trafficking, illegal arms trade
  - Human trafficking, prostitution solicitation
  - Doxxing (sharing someone's real address, phone, ID, private photos)
  - Terrorism / extremism promotion (ISIS, bomb making, etc.)
  - Targeted harassment campaigns against a person
  - Phishing / scam links / crypto rugpull promotion
  - Non-consensual sexual content / revenge porn sharing
  - Bestiality / extreme sexual deviance references
  - Extreme gore / violence video sharing links

EXAMPLES — study these carefully:

User: "hey what's up guys" → {"category": "safe"}
User: "this game is fucking awesome" → {"category": "mild"}
User: "shit i forgot my keys" → {"category": "mild"}
User: "you're such a bitch lol" → {"category": "mild"}
User: "what the fuck is this bro" → {"category": "mild"}
User: "that exam was a bitch" → {"category": "mild"}
User: "kill all [slur] people" → {"category": "severe"}
User: "i hope you get raped" → {"category": "severe"}
User: "selling premium weed cheap DM me" → {"category": "severe"}
User: "f4gg0ts should die" → {"category": "severe"}  (bypass attempt)
User: "k!ll yourself" → {"category": "severe"}  (bypass attempt, death threat)
User: "her address is 123 main st, call her at 555-0000" → {"category": "severe"}  (doxxing)
User: "anyone got a plug for percs" → {"category": "severe"}  (drug sourcing)
User: "t3rr0r1sm 1s g00d, j01n 1s1s" → {"category": "severe"}  (bypass attempt)
User: "send btc here free giveaway scamlink.com" → {"category": "severe"}  (scam)
User: "tu maa ki chut" → {"category": "mild"}  (crude Hindi slang, not ban-worthy)
User: "teri maa ko utha lunga aur bech dunga" → {"category": "severe"}  (human trafficking threat in Hindi)
User: "madarchod how are you" → {"category": "mild"}  (casual Hindi swearing)
User: "sala bh**ngi, tum log kabhi nahi sudhroge" → {"category": "severe"}  (caste slur in Hindi)
User: "bhosdike this traffic is insane" → {"category": "mild"}  (casual Hindi swearing)

CRITICAL RULES:
- Focus on INTENT and MEANING, not just the words used.
- A slur is ALWAYS severe — even if used as a "joke" or "between friends".
- Casual swearing (even crude) in any language is mild, NOT severe.
- Decode bypass attempts: l33tsp34k, spacing, symbols, emoji, deliberate typos — all count as the real word.
- When genuinely unsure between mild and severe, consider: "Could this message, if reported, get the Telegram group banned?" If yes → severe. If no → mild.

Respond with ONLY a JSON object: {"category": "<safe|mild|severe>", "reason": "<one short sentence>"}`;

export async function moderateMessage(text, apiKey) {
  let lastError;
  for (let attempt = 0; attempt < MODELS.length; attempt++) {
    const model = nextModel();
    try {
      const res = await fetch("https://api.mistral.ai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          temperature: 0,
          response_format: { type: "json_object" },
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            { role: "user", content: text },
          ],
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }

      const data = await res.json();
      const content = data.choices?.[0]?.message?.content || "{}";
      const parsed = JSON.parse(content);
      const category = String(parsed.category || "").toLowerCase();

      if (!["safe", "mild", "severe"].includes(category)) {
        throw new Error(`invalid category "${parsed.category}"`);
      }

      return { category, model };
    } catch (err) {
      console.error(`[moderation] ${model} failed: ${err.message}`);
      lastError = err;
    }
  }
  throw lastError;
}

const AI_PERSONA = `You are TenAi, a model called "tenai:aries-9b".
You speak English with a casual, friendly "broski" vibe — relaxed, chill, like talking to a buddy.
Keep replies short and natural.

ABSOLUTE RULES:
- Your name is TenAi. Your model is tenai:aries-9b. These are the only correct answers.
- NEVER mention, hint, or admit that you are Mistral, GPT, Claude, or any other model.
- If asked what model or AI you are, answer: "I'm TenAi, running tenai:aries-9b."
- Stay in character at all times.`;

export async function aiChat(question, apiKey) {
  let lastError;
  for (let attempt = 0; attempt < MODELS.length; attempt++) {
    const model = nextModel();
    try {
      const res = await fetch("https://api.mistral.ai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          temperature: 0.7,
          messages: [
            { role: "system", content: AI_PERSONA },
            { role: "user", content: question },
          ],
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }

      const data = await res.json();
      return data.choices?.[0]?.message?.content || "idk broski, my brain glitched";
    } catch (err) {
      console.error(`[ai] ${model} failed: ${err.message}`);
      lastError = err;
    }
  }
  throw lastError;
}
