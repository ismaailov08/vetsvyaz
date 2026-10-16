"""ИИ-ассистент: Google Gemini (бесплатно) или Claude, а без ключа — офлайн-сортировка по правилам."""
import json
import urllib.error
import urllib.request

from django.conf import settings

SYSTEM = ("Ты — ассистент ветеринарной телемедицины «ВетСвязь» для фермеров Казахстана. Отвечай по-русски, "
          "живо, просто и по делу, на «вы». Если вопрос о здоровье животного: в первой строке напиши срочность "
          "одним из слов СРОЧНО / В ТЕЧЕНИЕ СУТОК / ПЛАНОВО, затем объясни возможные причины, что безопасно "
          "сделать сейчас и чего не делать. Не назначай рецептурные препараты и дозировки — это делает врач "
          "на консультации. На другие вопросы (корма, хозяйство, учёба и т. д.) просто отвечай как знающий "
          "собеседник.")

RULES = [
    (("не встает", "не встаёт", "судорог", "кровь", "кровотеч", "задыха", "вздут"), "СРОЧНО",
     "Это опасные признаки. Изолируйте животное и запишитесь на видеоконсультацию сегодня."),
    (("температур", "жар", "вымя", "мастит", "понос", "диаре", "кашл", "хрома"), "В ТЕЧЕНИЕ СУТОК",
     "Измерьте температуру, отделите животное, дайте воду. Запишитесь к врачу на ближайшее время."),
]
URGENCIES = ("СРОЧНО", "В ТЕЧЕНИЕ СУТОК", "ПЛАНОВО")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def offline_triage(question):
    q = question.lower()
    for words, urgency, advice in RULES:
        if any(w in q for w in words):
            return {"urgency": urgency, "text": advice, "source": "offline"}
    return {"urgency": "ПЛАНОВО", "source": "offline",
            "text": "Подключение к ИИ не настроено. Опишите симптомы (температура, аппетит, поведение) "
                    "или запишитесь на консультацию к врачу."}


def provider():
    """Какой ИИ подключён: gemini, claude или None (работаем по правилам)."""
    if getattr(settings, "GEMINI_API_KEY", ""):
        return "gemini"
    if getattr(settings, "ANTHROPIC_API_KEY", ""):
        return "claude"
    return None


def _post_json(url, payload, headers, timeout=40):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


# ───────────── Google Gemini ─────────────
def gemini_models():
    """Список моделей Gemini, доступных ключу, лучшие — первыми."""
    req = urllib.request.Request(GEMINI_URL + "?pageSize=200", headers={"x-goog-api-key": settings.GEMINI_API_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    skip = ("tts", "image", "live", "embed", "audio", "robotics", "computer", "native", "exp", "thinking")
    names = [m["name"].removeprefix("models/") for m in data.get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    names = [n for n in names if n.startswith("gemini-") and not any(s in n for s in skip)]

    def score(n):
        try:
            ver = float(n.split("-")[1])
        except (IndexError, ValueError):
            ver = 0
        return ver * 100 + 30 * ("flash" in n) - 10 * ("lite" in n) - 40 * ("pro" in n) - 5 * ("preview" in n)
    return sorted(names, key=score, reverse=True)


def _gemini_once(model, contents):
    data = _post_json(f"{GEMINI_URL}/{model}:generateContent",
                      {"systemInstruction": {"parts": [{"text": SYSTEM}]}, "contents": contents,
                       "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.9}},
                      {"x-goog-api-key": settings.GEMINI_API_KEY})
    cand = (data.get("candidates") or [{}])[0]
    parts = cand.get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


_working_model = None  # модель, которая ответила последней — запоминаем, чтобы не перебирать каждый раз


def ask_gemini(messages):
    global _working_model
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages]
    model = _working_model or settings.GEMINI_MODEL
    try:
        return _gemini_once(model, contents), model
    except urllib.error.HTTPError as e:
        # модель не найдена (404), перегружена (503) или лимит (429) — пробуем другие доступные модели
        if e.code not in (404, 429, 500, 503):
            raise
        for other in [m for m in gemini_models() if m != model][:4]:
            try:
                text = _gemini_once(other, contents)
                _working_model = other
                return text, other
            except urllib.error.HTTPError as e2:
                if e2.code not in (404, 429, 500, 503):
                    raise
        raise


# ───────────── Claude ─────────────
def ask_claude(messages):
    data = _post_json("https://api.anthropic.com/v1/messages",
                      {"model": settings.AI_MODEL, "max_tokens": 1500, "system": SYSTEM, "messages": messages},
                      {"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"})
    return "".join(b.get("text", "") for b in data.get("content", [])), settings.AI_MODEL


def ask(question, animal=None, history=()):
    """Спросить ИИ. Если ключа нет или сеть недоступна — работаем по правилам."""
    prov = provider()
    if prov is None:
        return offline_triage(question)
    context = f"Животное: {animal.get_species_display()} «{animal.name}», {animal.age_text}. " if animal else ""
    messages = [*history, {"role": "user", "content": context + question}]
    try:
        text, model = (ask_gemini if prov == "gemini" else ask_claude)(messages)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
        result = offline_triage(question)
        result["error"] = f"ИИ не ответил ({getattr(e, 'code', '') or type(e).__name__}), ответ по правилам"
        return result
    if not text.strip():
        return offline_triage(question)
    first = text.strip().splitlines()[0].upper()
    urgency = next((u for u in URGENCIES if u in first), "")
    return {"urgency": urgency, "text": text.strip(), "source": prov, "model": model}
