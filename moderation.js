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

const SYSTEM_PROMPT = `You are a strict multilingual chat moderation classifier.
Classify the user's message into exactly ONE category:

- "safe": No profanity, or a clean/normal message.
- "mild": Common or light profanity / casual swearing used in everyday speech. This is ALLOWED and must NOT be flagged.
- "severe": Severe profanity including slurs, racial / homophobic / sexist insults, hate speech, extreme vulgarity, or aggressive directed abuse. This must be REMOVED.

Rules:
- Evaluate the message in ANY language (translate first if needed).
- Choose "severe" ONLY for genuinely very offensive content, never for casual swearing.
- Slang, jokes, or mild cursing are "mild", not "severe".

Respond with ONLY a JSON object, no extra text: {"category": "<safe|mild|severe>"}`;

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
