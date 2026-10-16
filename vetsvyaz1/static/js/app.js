// Открытие и закрытие всплывающих окон <dialog>
document.addEventListener("click", (e) => {
  const opener = e.target.closest("[data-open]");
  if (opener) document.getElementById(opener.dataset.open).showModal();
  const closer = e.target.closest("[data-close]");
  if (closer) closer.closest("dialog").close();
});
// Если форма в окне вернулась с ошибками — открыть окно снова
document.querySelectorAll("dialog .has-error").forEach((el) => el.closest("dialog").showModal());
// Сообщения исчезают через 5 секунд
setTimeout(() => document.querySelectorAll(".toast").forEach((t) => t.remove()), 5000);

// Простой линейный график на <canvas> без сторонних библиотек
function lineChart(id, values) {
  const c = document.getElementById(id);
  if (!c || !values.length) return;
  const w = (c.width = c.clientWidth * 2), h = (c.height = c.clientHeight * 2), ctx = c.getContext("2d");
  const min = Math.min(...values) - 0.3, max = Math.max(...values) + 0.3, pad = 30;
  const x = (i) => pad + (i * (w - 2 * pad)) / Math.max(values.length - 1, 1);
  const y = (v) => h - pad - ((v - min) * (h - 2 * pad)) / (max - min);
  ctx.strokeStyle = "#dde4dc"; ctx.fillStyle = "#6b7a72"; ctx.font = "22px sans-serif";
  for (let k = 0; k <= 4; k++) {
    const v = min + ((max - min) * k) / 4;
    ctx.beginPath(); ctx.moveTo(pad, y(v)); ctx.lineTo(w - pad, y(v)); ctx.stroke();
    ctx.fillText(v.toFixed(1), 0, y(v) - 4);
  }
  ctx.strokeStyle = "#3f7d5c"; ctx.lineWidth = 4; ctx.beginPath();
  values.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
  ctx.stroke();
}

// Таймер видеозвонка
function startTimer(id) {
  const el = document.getElementById(id), t0 = Date.now();
  setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    el.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
  }, 1000);
}
