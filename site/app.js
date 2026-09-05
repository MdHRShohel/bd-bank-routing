/**
 * bd-bank-routing — the site.
 *
 * No framework, no build step. The validation logic below is a deliberate,
 * literal port of `packages/js/src/index.ts`; if the two ever disagree, this
 * file is the one that is wrong. Districts are never read from a stored field —
 * they are derived from digits 4-5 through `districtByCode`, so the page
 * demonstrates the structural claim it opens with instead of restating it.
 */

const DATA = "data";

/** Wording that marks a BACH settlement endpoint rather than a branch anyone
 *  banks at. `HEAD OFFICE` is deliberately absent: some head offices are
 *  genuinely payable branches, so a regex there would be a guess. */
const SETTLEMENT =
  /truncation\s+point|rtgs|clearing\s+house|agent\s+banking|remittance|card\s+division|interbank/i;

/** Words naming a company's legal form, not which company it is. */
const CORPORATE_FORM = /\b(THE|LIMITED|LTD|PLC|COMPANY|CO|INCORPORATED|INC)\b\.?/gi;

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const state = {
  meta: null,
  byCode: new Map(),   // "225" -> bank meta
  names: new Map(),    // "225150135" -> "Agrabad Branch"
  byBank: new Map(),   // "225" -> [[routing, name], ...]
  all: [],             // [[routing, name], ...] in dataset order
  branchesReady: false,
  sort: { key: "code", dir: 1 },
  filter: "",
};

/* ------------------------------------------------------------------ helpers */

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const icon = {
  ok: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.7-9.3a1 1 0 0 0-1.4-1.4L9 10.58 7.7 9.3a1 1 0 0 0-1.4 1.4l2 2a1 1 0 0 0 1.4 0l4-4Z" clip-rule="evenodd"/></svg>`,
  bad: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM9 5a1 1 0 0 1 2 0v6a1 1 0 1 1-2 0V5Zm1 10.5a1.25 1.25 0 1 0 0-2.5 1.25 1.25 0 0 0 0 2.5Z" clip-rule="evenodd"/></svg>`,
  warn: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M8.49 2.96a1.75 1.75 0 0 1 3.02 0l6.28 10.78A1.75 1.75 0 0 1 16.28 16.5H3.72a1.75 1.75 0 0 1-1.51-2.76L8.49 2.96ZM10 6a1 1 0 0 1 1 1v3.5a1 1 0 1 1-2 0V7a1 1 0 0 1 1-1Zm0 8.25a1.15 1.15 0 1 0 0-2.3 1.15 1.15 0 0 0 0 2.3Z" clip-rule="evenodd"/></svg>`,
  caret: `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7 4.5 14 10l-7 5.5v-11Z"/></svg>`,
};

/* --------------------------------------------------------- the library port */

function districtOf(routing) {
  const r = String(routing ?? "").trim();
  if (!/^\d{9}$/.test(r)) return null;
  return state.meta?.districtByCode[r.slice(3, 5)] ?? null;
}

function lookup(routing) {
  const r = String(routing ?? "").trim();
  if (!/^\d{9}$/.test(r)) return null;
  const name = state.names.get(r);
  if (name === undefined) return null;
  const bank = state.byCode.get(r.slice(0, 3));
  return {
    routing: r,
    name,
    district: districtOf(r),
    bankCode: bank.code,
    bankName: bank.name,
    payable: bank.payable,
  };
}

const isSettlementEndpoint = (name) => SETTLEMENT.test(name ?? "");

const normalise = (name) =>
  String(name ?? "").toUpperCase().replace(CORPORATE_FORM, " ").replace(/[^A-Z0-9]/g, "");

function namesAgree(stored, official) {
  const a = normalise(stored);
  const b = normalise(official);
  if (!a || !b) return true; // nothing stored cannot disagree
  return a.includes(b) || b.includes(a);
}

function check(routing, storedName) {
  const r = String(routing ?? "").trim();
  if (!/^\d{9}$/.test(r)) return { routing: r, ok: false, problems: ["not nine digits"], branch: null };

  const br = lookup(r);
  if (!br) {
    return {
      routing: r,
      ok: false,
      branch: null,
      problems: [
        state.byCode.has(r.slice(0, 3))
          ? "not a known branch — the dataset may simply be behind, because banks open branches faster than any dataset is updated"
          : `prefix ${r.slice(0, 3)} belongs to no bank in the dataset`,
      ],
    };
  }

  const problems = [];
  const bank = state.byCode.get(br.bankCode);
  if (!br.payable) problems.push(`${br.bankName} cannot receive a salary — ${bank.payableReason ?? ""}`.trim());
  if (isSettlementEndpoint(br.name))
    problems.push(`“${br.name}” is a settlement endpoint, not a branch — no salary can be paid into it`);
  if (storedName && !namesAgree(storedName, br.bankName))
    problems.push(
      `stored bank name “${storedName}” disagrees with routing ${r} (prefix ${r.slice(0, 3)} is “${br.bankName}”)`
    );

  return { routing: r, ok: problems.length === 0, problems, branch: br };
}

/* -------------------------------------------------------------------- data */

async function loadMeta() {
  const meta = await (await fetch(`${DATA}/meta.json`)).json();
  state.meta = meta;
  for (const b of meta.banks) state.byCode.set(b.code, b);
  return meta;
}

let branchesPromise = null;
function loadBranches() {
  if (!branchesPromise) {
    branchesPromise = fetch(`${DATA}/branches.txt`)
      .then((r) => r.text())
      .then((text) => {
        for (const line of text.split("\n")) {
          if (!line) continue;
          const cut = line.indexOf("|");
          const routing = line.slice(0, cut);
          const name = line.slice(cut + 1);
          state.names.set(routing, name);
          state.all.push([routing, name]);
          const code = routing.slice(0, 3);
          let bucket = state.byBank.get(code);
          if (!bucket) state.byBank.set(code, (bucket = []));
          bucket.push([routing, name]);
        }
        state.branchesReady = true;
      });
  }
  return branchesPromise;
}

/* ----------------------------------------------------------------- anatomy */

function renderAnatomy(digits) {
  const parts = { bank: [0, 3], dist: [3, 5], branch: [5, 8], check: [8, 9] };
  const labels = {
    bank: (v) => (state.byCode.get(v)?.name ?? (v.length === 3 ? "no bank on this prefix" : "digits 1–3")),
    dist: (v) => (state.meta?.districtByCode[v] ?? (v.length === 2 ? "no district on this code" : "digits 4–5")),
    branch: () => "digits 6–8",
    check: () => "digit 9",
  };
  for (const [key, [from, to]] of Object.entries(parts)) {
    const value = digits.slice(from, to);
    const seg = $(`.seg--${key === "dist" ? "dist" : key}`, $("#anatomy"));
    const box = $(`[data-seg="${key}"]`, seg);
    const filled = value.length === to - from;
    box.textContent = value.padEnd(to - from, "·");
    seg.classList.toggle("seg--on", filled);
    $(`[data-label="${key}"]`, seg).textContent = filled ? labels[key](value) : labels[key]("");
  }
}

/* ------------------------------------------------------------------ result */

function factsHtml(br, bank) {
  return `
    <dl class="facts">
      <div><dt>Bank</dt><dd>${esc(br.bankName)} <span class="mono">(${esc(br.bankCode)})</span></dd></div>
      <div><dt>Branch</dt><dd>${esc(br.name)}</dd></div>
      <div><dt>District</dt><dd class="num">${esc(br.district ?? "—")}</dd></div>
      <div><dt>Can receive a salary</dt><dd>${
        br.payable && !isSettlementEndpoint(br.name)
          ? '<span class="tag tag--ok">yes</span>'
          : '<span class="tag tag--no">no</span>'
      }</dd></div>
    </dl>
    <p class="provenance">
      Read from <a href="${esc(bank.source.url)}" rel="noreferrer noopener">${esc(bank.source.url)}</a>
      on <span class="mono">${esc(bank.source.checked)}</span> ·
      ${
        bank.source.kind === "first_party"
          ? '<span class="tag tag--ok">the bank&rsquo;s own site</span>'
          : '<span class="tag tag--info">consolidated BACH table</span>'
      }
    </p>`;
}

function renderResult(html) {
  $("#result").innerHTML = html ? `<div class="result__body">${html}</div>` : "";
}

function showRouting(routing, storedName) {
  const res = check(routing, storedName);
  const br = res.branch;

  if (!br) {
    // Not found is not nothing. The prefix and the district digits still mean
    // something, and saying so is how a reader spots a routing whose bank is not
    // the bank they expected — which is the whole argument of this page.
    const prefixBank = state.byCode.get(routing.slice(0, 3));
    const district = districtOf(routing);
    renderResult(`
      <div class="verdict verdict--unknown">${icon.warn}
        <div><strong>Not in the dataset</strong>
        <p>${esc(res.problems[0])}</p></div>
      </div>
      <dl class="facts">
        <div><dt>What digits 1–3 say</dt><dd>${
          prefixBank
            ? `${esc(prefixBank.name)} <span class="mono">(${esc(prefixBank.code)})</span>`
            : `<span class="mono">${esc(routing.slice(0, 3))}</span> — no bank holds this prefix`
        }</dd></div>
        <div><dt>What digits 4–5 say</dt><dd class="num">${esc(district ?? "no district on this code")}</dd></div>
      </dl>
      <p class="provenance">Both answers come from the number&rsquo;s own structure, not from a lookup — so they hold even for a routing this dataset has never seen.</p>`);
    return;
  }

  const bank = state.byCode.get(br.bankCode);
  const unreachable = !br.payable || isSettlementEndpoint(br.name);
  const bad = res.problems.length > 0;

  // Three different answers, and collapsing them into one loses the useful half.
  // A routing that resolves to a real, payable branch while the name stored
  // beside it names a different bank is not a broken routing — it is a broken
  // record, and the fix is somewhere else entirely.
  const verdict = !bad
    ? { cls: "ok", mark: icon.ok, title: "Resolved, and payable",
        sub: "The number, the branch and the name you gave all agree." }
    : unreachable
      ? { cls: "bad", mark: icon.bad, title: "Not a destination a salary can reach",
          sub: "This is a real routing number, and it resolves. Money still cannot land here." }
      : { cls: "bad", mark: icon.bad, title: "The routing is fine. The name beside it is not.",
          sub: "The branch resolves and can receive a salary — but your record names a different institution." };

  renderResult(`
    <div class="verdict verdict--${verdict.cls}">${verdict.mark}
      <div><strong>${esc(verdict.title)}</strong>
      <p>${esc(verdict.sub)}</p></div>
    </div>
    ${
      bad
        ? `<ul class="problems">${res.problems
            .map((p) => `<li>${icon.bad}<span>${esc(p)}</span></li>`)
            .join("")}</ul>`
        : ""
    }
    ${factsHtml(br, bank)}`);
}

function showSearch(query) {
  const q = query.trim().toUpperCase();
  if (q.length < 2) return renderResult("");

  if (!state.branchesReady) {
    renderResult(`<p class="help">Loading the branch index…</p>`);
    loadBranches().then(() => showSearch(query));
    return;
  }

  const bankHits = state.meta.banks.filter(
    (b) => b.name.toUpperCase().includes(q) || b.code === q
  );
  const hits = [];
  for (const [routing, name] of state.all) {
    if (name.toUpperCase().includes(q)) {
      hits.push([routing, name]);
      if (hits.length >= 40) break;
    }
  }

  if (!bankHits.length && !hits.length) {
    renderResult(`
      <div class="verdict verdict--unknown">${icon.warn}
        <div><strong>Nothing matches “${esc(query.trim())}”</strong>
        <p>Branch names are stored as the bank publishes them, in capitals and often abbreviated. Try a shorter fragment.</p></div>
      </div>`);
    return;
  }

  renderResult(`
    ${
      bankHits.length
        ? `<p class="eyebrow" style="margin-bottom:.6rem">Institutions</p>
           <ul class="hits" style="margin-bottom:1.25rem">${bankHits
             .map(
               (b) => `<li><button type="button" data-bank="${esc(b.code)}">
                 <span class="r">${esc(b.code)}</span>
                 <span class="n">${esc(b.name)}</span>
                 <span class="b">${b.branchCount.toLocaleString("en")} branches</span>
               </button></li>`
             )
             .join("")}</ul>`
        : ""
    }
    ${
      hits.length
        ? `<p class="eyebrow" style="margin-bottom:.6rem">Branches${
            hits.length >= 40 ? " (first 40)" : ""
          }</p>
           <ul class="hits">${hits
             .map(
               ([routing, name]) => `<li><button type="button" data-routing="${esc(routing)}">
                 <span class="r">${esc(routing)}</span>
                 <span class="n">${esc(name)}</span>
                 <span class="b">${esc(state.byCode.get(routing.slice(0, 3)).name)}</span>
               </button></li>`
             )
             .join("")}</ul>`
        : ""
    }`);
}

/* ------------------------------------------------------------------- input */

function run() {
  const raw = $("#q").value.trim();
  const stored = $("#stored").value.trim();
  const digits = raw.replace(/\D/g, "");
  const numeric = raw !== "" && /^[\d\s-]+$/.test(raw);

  renderAnatomy(numeric ? digits.slice(0, 9) : "");
  $("#anatomy").style.opacity = numeric || raw === "" ? "1" : "0.45";

  if (raw === "") return renderResult("");

  if (numeric) {
    if (digits.length !== 9) {
      renderResult(
        `<p class="help">${digits.length} of 9 digits. A Bangladesh routing number is always nine.</p>`
      );
      return;
    }
    if (!state.branchesReady) {
      renderResult(`<p class="help">Loading the branch index…</p>`);
      loadBranches().then(run);
      return;
    }
    history.replaceState(null, "", `#/r/${digits}`);
    showRouting(digits, stored);
    return;
  }

  showSearch(raw);
}

function fill(q, stored = "") {
  $("#q").value = q;
  $("#stored").value = stored;
  run();
  $("#lookup").scrollIntoView({ behavior: "smooth", block: "start" });
  $("#q").focus({ preventScroll: true });
}

/* ------------------------------------------------------------- banks table */

const SORTERS = {
  code: (b) => b.code,
  name: (b) => b.name,
  branchCount: (b) => b.branchCount,
  districtCount: (b) => b.districtCount,
  kind: (b) => b.source.kind,
  checked: (b) => b.source.checked,
};

function renderBanks() {
  const { key, dir } = state.sort;
  const f = state.filter.trim().toUpperCase();
  const rows = state.meta.banks
    .filter((b) => !f || b.name.toUpperCase().includes(f) || b.code.includes(f))
    .sort((a, b) => {
      const x = SORTERS[key](a);
      const y = SORTERS[key](b);
      return (x < y ? -1 : x > y ? 1 : 0) * dir;
    });

  $("#banks-body").innerHTML = rows
    .map(
      (b) => `
      <tr class="bank-row" data-code="${esc(b.code)}" aria-expanded="false">
        <td class="num">${esc(b.code)}</td>
        <td class="name"><button type="button" class="row-toggle">${icon.caret}<span>${esc(b.name)}</span></button></td>
        <td class="num">${b.branchCount.toLocaleString("en")}</td>
        <td class="num">${b.districtCount}</td>
        <td>${
          b.source.kind === "first_party"
            ? '<span class="tag tag--ok">own site</span>'
            : '<span class="tag tag--info">BACH</span>'
        }</td>
        <td class="num">${esc(b.source.checked)}</td>
        <td>${
          b.payable
            ? '<span class="tag tag--ok">payable</span>'
            : '<span class="tag tag--warn">no salaries</span>'
        }</td>
      </tr>`
    )
    .join("");

  $("#bank-count").textContent =
    rows.length === state.meta.banks.length
      ? `${rows.length} institutions`
      : `${rows.length} of ${state.meta.banks.length} institutions`;
}

async function toggleBank(tr) {
  const open = tr.getAttribute("aria-expanded") === "true";
  const next = tr.nextElementSibling;
  if (open) {
    tr.setAttribute("aria-expanded", "false");
    if (next?.classList.contains("branches")) next.remove();
    return;
  }
  $$("#banks-body tr.branches").forEach((r) => r.remove());
  $$("#banks-body tr.bank-row").forEach((r) => r.setAttribute("aria-expanded", "false"));
  tr.setAttribute("aria-expanded", "true");

  const code = tr.dataset.code;
  const bank = state.byCode.get(code);
  const row = document.createElement("tr");
  row.className = "branches";
  row.innerHTML = `<td colspan="7"><div class="branch-panel"><p class="help">Loading branches…</p></div></td>`;
  tr.after(row);

  await loadBranches();
  const branches = state.byBank.get(code) ?? [];
  let shown = 100;
  const paint = () => {
    const slice = branches.slice(0, shown);
    $(".branch-panel", row).innerHTML = `
      <div class="branch-list">${slice
        .map(
          ([routing, name]) => `<div>
            <span class="r">${esc(routing)}</span>
            <span>${esc(name)}</span>
            <span class="d">${esc(districtOf(routing) ?? "—")}</span>
          </div>`
        )
        .join("")}</div>
      <p class="help">${
        bank.payable
          ? `Showing ${slice.length.toLocaleString("en")} of ${branches.length.toLocaleString("en")}.`
          : `Showing ${slice.length.toLocaleString("en")} of ${branches.length.toLocaleString(
              "en"
            )}. ${esc(bank.payableReason ?? "")}`
      }</p>
      ${
        shown < branches.length
          ? `<button type="button" class="branch-more">Show all ${branches.length.toLocaleString("en")}</button>`
          : ""
      }`;
    const more = $(".branch-more", row);
    if (more)
      more.addEventListener("click", () => {
        shown = branches.length;
        paint();
        $(".branch-list", row)?.focus?.();
      });
  };
  paint();
}

/* -------------------------------------------------------------------- boot */

function renderMeta(meta) {
  const first = meta.banks.filter((b) => b.source.kind === "first_party").length;
  const bach = meta.banks.length - first;
  const stat = {
    banks: meta.counts.banks.toLocaleString("en"),
    branches: meta.counts.branches.toLocaleString("en"),
    districts: `${meta.counts.districts} / 64`,
    firstParty: `${first} / ${meta.counts.banks}`,
    generated: meta.generated,
  };
  for (const [k, v] of Object.entries(stat)) $(`[data-stat="${k}"]`).textContent = v;

  const pct = (first / meta.banks.length) * 100;
  $("#source-bar .first").style.width = `${pct}%`;
  $("#source-bar .bach").style.width = `${100 - pct}%`;
  $("#legend-first").textContent = `${first} read from the bank's own website`;
  $("#legend-bach").textContent = `${bach} from the consolidated BACH table`;
}

let timer;
function onInput() {
  clearTimeout(timer);
  timer = setTimeout(run, 120);
}

async function main() {
  await loadMeta();
  renderMeta(state.meta);
  renderBanks();

  $("#q").addEventListener("input", onInput);
  $("#stored").addEventListener("input", onInput);
  $("#lookup-form").addEventListener("submit", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    run();
  });

  document.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-q]");
    if (chip) return fill(chip.dataset.q, chip.dataset.stored ?? "");

    const hit = e.target.closest("[data-routing]");
    if (hit) return fill(hit.dataset.routing);

    const bankHit = e.target.closest("[data-bank]");
    if (bankHit) {
      const b = state.byCode.get(bankHit.dataset.bank);
      $("#banks").scrollIntoView({ behavior: "smooth", block: "start" });
      $("#bank-filter").value = b.name;
      state.filter = b.name;
      renderBanks();
      return;
    }

    const row = e.target.closest("tr.bank-row");
    if (row) return toggleBank(row);
  });

  $$("thead [data-sort]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const key = btn.dataset.sort;
      state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : 1 };
      $$("thead th").forEach((th) => th.removeAttribute("aria-sort"));
      btn.closest("th").setAttribute("aria-sort", state.sort.dir === 1 ? "ascending" : "descending");
      $$("thead .arrow").forEach((a) => (a.textContent = "↑"));
      $(".arrow", btn).textContent = state.sort.dir === 1 ? "↑" : "↓";
      renderBanks();
    })
  );

  $("#bank-filter").addEventListener("input", (e) => {
    state.filter = e.target.value;
    renderBanks();
  });

  const systemDark = () => matchMedia("(prefers-color-scheme: dark)").matches;
  const currentTheme = () => document.documentElement.dataset.theme || (systemDark() ? "dark" : "light");
  const syncToggleLabel = () =>
    $("#theme-toggle").setAttribute(
      "aria-label",
      currentTheme() === "dark" ? "Switch to light theme" : "Switch to dark theme"
    );
  syncToggleLabel();
  $("#theme-toggle").addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("bdbr-theme", next);
    } catch (e) {
      /* private mode: the choice just does not persist */
    }
    syncToggleLabel();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncToggleLabel);

  // The branch index is what makes the box above work, so start it immediately
  // rather than on the first keystroke.
  loadBranches();

  // A hash arriving after load — the reader pressing Back, or pasting a link
  // into a tab that is already open — has to work exactly like a cold load.
  const applyHash = async () => {
    const deep = location.hash.match(/^#\/r\/(\d{9})$/);
    if (!deep || deep[1] === $("#q").value.replace(/\D/g, "")) return false;
    await loadBranches();
    $("#q").value = deep[1];
    run();
    return true;
  };
  window.addEventListener("hashchange", applyHash);

  if (!(await applyHash())) renderAnatomy("");
}

main().catch((err) => {
  console.error(err);
  renderResult(
    `<div class="verdict verdict--bad">${icon.bad}<div><strong>The dataset did not load</strong><p>This page reads <code>data/meta.json</code> and <code>data/branches.txt</code> over HTTP, so it needs to be served rather than opened from the filesystem. Try <code>python3 -m http.server</code> from the <code>site/</code> directory.</p></div></div>`
  );
});
