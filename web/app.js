const form = document.querySelector("#query");
const input = document.querySelector("#question");
const history = document.querySelector("#history");
const output = document.querySelector("#output");
const reset = document.querySelector("#reset");
const submit = document.querySelector("#submit");
const examples = [...document.querySelectorAll("[data-question]")];
const number = new Intl.NumberFormat("es-GT", { maximumFractionDigits: 2 });
let previous = null;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function addMessage(kind, message) {
  history.hidden = false;
  reset.hidden = false;
  history.append(element("p", message, kind));
  history.scrollTop = history.scrollHeight;
}

function chartOf(values, title) {
  const chart = element("div", undefined, "chart");
  chart.setAttribute("role", "group");
  chart.setAttribute("aria-label", `Gráfica de barras · ${title}`);
  const max = Math.max(1, ...values.map(([, value]) => value));
  for (const [name, value] of values) {
    const bar = element("div", undefined, "bar");
    const track = element("div", undefined, "track");
    const fill = element("div", undefined, "fill");
    track.setAttribute("aria-hidden", "true");
    fill.style.width = `${100 * value / max}%`;
    track.append(fill);
    bar.append(element("span", name, "bar-name"), track,
      element("span", number.format(value), "bar-value"));
    chart.append(bar);
  }
  return chart;
}

function tableOf(columns, rows) {
  const container = element("div", undefined, "table-scroll");
  container.tabIndex = 0;
  container.setAttribute("role", "region");
  container.setAttribute("aria-label", "Tabla desplazable de resultados");
  const table = element("table");
  const heading = table.createTHead().insertRow();
  const body = table.createTBody();
  let active = -1;
  let direction = 1;
  function draw(values) {
    body.replaceChildren();
    for (const row of values) {
      const tr = body.insertRow();
      for (const value of row) {
        tr.insertCell().textContent = typeof value === "number" ? number.format(value) : value;
      }
    }
  }
  columns.forEach((label, index) => {
    const th = element("th");
    const button = element("button", `${label} ↕`);
    button.type = "button";
    th.scope = "col";
    button.addEventListener("click", () => {
      direction = active === index ? -direction : 1;
      active = index;
      for (const header of heading.cells) header.removeAttribute("aria-sort");
      th.setAttribute("aria-sort", direction === 1 ? "ascending" : "descending");
      draw([...rows].sort((a, b) => {
        const x = a[index];
        const y = b[index];
        return direction * (typeof x === "number" ? x - y : x.localeCompare(y, "es"));
      }));
    });
    th.append(button);
    heading.append(th);
  });
  draw(rows);
  container.append(table);
  return container;
}

function render(result) {
  output.replaceChildren(
    element("p", `${result.alcance} · ${number.format(result.base)} partidos`, "scope"),
    element("p", result.mensaje, "result-title"),
  );
  if (result.filas.length) {
    output.append(chartOf(result.grafica, result.titulo), tableOf(result.columnas, result.filas));
  }
  const methods = {
    total: "Suma por partido",
    promedio: "Suma dividida por los partidos analizados",
    maximo: "Mayor valor de un partido",
    partidos: "Clasificación de partidos por la métrica consultada",
  };
  const definitions = {
    "2pm": "Tiros de campo anotados menos triples anotados.",
    dd: "Exactamente dos categorías con al menos diez: puntos, rebotes, asistencias, robos y tapones.",
    td: "Tres o más categorías con al menos diez: puntos, rebotes, asistencias, robos y tapones.",
  };
  const detail = element("details", undefined, "method");
  const { operacion, metrica, umbral } = result.plan;
  const method = umbral >= 0 ? `Conteo de partidos que alcanzan ${umbral} o más` : methods[operacion];
  detail.append(element("summary", "Cómo se calculó"),
    element("p", `${method}. ${definitions[metrica] || ""}`),
    element("p", `Interpretación mediante ${result.modo}.`));
  output.append(detail);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question || submit.disabled) return;
  submit.disabled = reset.disabled = true;
  examples.forEach((button) => { button.disabled = true; });
  addMessage("question", question);
  input.value = "";
  const pending = element("p", "Consultando…", "answer");
  history.append(pending);
  history.scrollTop = history.scrollHeight;
  try {
    const response = await fetch("/api/consulta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: question, anterior: previous }),
    });
    const result = await response.json();
    if (!response.ok) {
      addMessage("answer error", result.error);
    } else {
      previous = result.plan;
      render(result);
      addMessage("answer", result.mensaje);
    }
  } catch {
    addMessage("answer error", "Se perdió la conexión con el prototipo. Intenta de nuevo.");
  } finally {
    pending.remove();
    submit.disabled = reset.disabled = false;
    examples.forEach((button) => { button.disabled = false; });
  }
});

for (const button of examples) {
  button.addEventListener("click", () => {
    input.value = button.dataset.question;
    form.requestSubmit();
  });
}

reset.addEventListener("click", () => {
  previous = null;
  input.value = "";
  history.replaceChildren();
  history.hidden = reset.hidden = true;
  output.replaceChildren(element("p", "Aquí aparecerán el alcance de la consulta, los datos y su gráfica.", "tip"));
  input.focus();
});

fetch("/api/estado")
  .then((response) => response.json())
  .then((info) => {
    document.querySelector("#mode").textContent = info.modelo ? `${info.modo} · ${info.modelo}` : info.modo;
  })
  .catch(() => { document.querySelector("#mode").textContent = "Sin conexión"; });
