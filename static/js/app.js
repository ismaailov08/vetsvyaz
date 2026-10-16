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

// Простой линейный график на <canvas> без сторонних библиотек.
// opts: color — цвет линии, lo/hi — границы нормы (рисуются зелёной полосой)
function lineChart(id, values, opts) {
  opts = opts || {};
  const c = document.getElementById(id);
  if (!c || !values.length) return;
  const w = (c.width = c.clientWidth * 2), h = (c.height = c.clientHeight * 2), ctx = c.getContext("2d");
  const all = values.concat(opts.lo != null ? [opts.lo, opts.hi] : []);
  let min = Math.min(...all), max = Math.max(...all);
  const padV = (max - min) * 0.08 || 1; min -= padV; max += padV;
  const pad = 46, x = (i) => pad + (i * (w - pad - 10)) / Math.max(values.length - 1, 1);
  const y = (v) => h - 24 - ((v - min) * (h - 40)) / (max - min);
  if (opts.lo != null) { ctx.fillStyle = "rgba(63,125,92,.10)"; ctx.fillRect(pad, y(opts.hi), w - pad - 10, y(opts.lo) - y(opts.hi)); }
  ctx.strokeStyle = "#dde4dc"; ctx.fillStyle = "#6b7a72"; ctx.font = "20px sans-serif"; ctx.lineWidth = 1;
  for (let k = 0; k <= 4; k++) {
    const v = min + ((max - min) * k) / 4;
    ctx.beginPath(); ctx.moveTo(pad, y(v)); ctx.lineTo(w - 10, y(v)); ctx.stroke();
    ctx.fillText(Math.abs(v) >= 100 ? Math.round(v) : v.toFixed(1), 0, y(v) + 6);
  }
  ctx.strokeStyle = opts.color || "#3f7d5c"; ctx.lineWidth = 3; ctx.beginPath();
  values.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
  ctx.stroke();
  const lv = values[values.length - 1];
  ctx.fillStyle = opts.color || "#3f7d5c"; ctx.beginPath(); ctx.arc(x(values.length - 1), y(lv), 6, 0, 7); ctx.fill();
}

// Таймер видеозвонка
function startTimer(id) {
  const el = document.getElementById(id), t0 = Date.now();
  setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    el.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
  }, 1000);
}
