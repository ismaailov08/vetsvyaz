from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.permissions import visible_animals

from .forms import AskForm
from .services import ask, provider


@login_required
def chat(request):
    """Чат с ИИ: история хранится в сессии пользователя."""
    history = request.session.get("ai_history", [])
    if request.method == "POST" and "clear" in request.POST:
        request.session["ai_history"] = []
        return redirect("assistant:chat")
    form = AskForm(request.POST or None, animals=visible_animals(request.user))
    if request.method == "POST" and form.is_valid():
        q = form.cleaned_data["question"]
        api_history = [{"role": m["role"], "content": m["text"]} for m in history[-6:]]
        answer = ask(q, form.cleaned_data["animal"], api_history)
        history += [{"role": "user", "text": q},
                    {"role": "assistant", "text": answer["text"], "urgency": answer["urgency"],
                     "source": answer["source"], "model": answer.get("model", ""), "error": answer.get("error", "")}]
        request.session["ai_history"] = history[-20:]
        return redirect("assistant:chat")
    return render(request, "assistant/chat.html", {"form": form, "history": history, "provider": provider()})
