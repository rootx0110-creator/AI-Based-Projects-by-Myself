import { PORTFOLIO, categoryById, rightCol } from "./data.js";

const esc = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

let cards = [];

/*
 * Renders the full portfolio as a scrollable, theme-matched card grid inside
 * #fallback. Used when WebGL is unavailable so the site never breaks.
 */
export function build2DGrid(root, { onSelect }) {
  const sections = PORTFOLIO.categories
    .map((cat) => {
      const list = PORTFOLIO.skills.filter((s) => s.category === cat.id);
      if (!list.length) return "";
      const cardsHtml = list
        .map(
          (s) => `
        <article class="fcard" data-skill="${esc(s.id)}" style="--fc-color:${cat.color}">
          <div class="fcard-accent"></div>
          <h4>${esc(s.name)}</h4>
          <p>${esc(s.description)}</p>
          <div class="fcard-foot">
            <span class="fcard-cat" style="background:${cat.color};color:${rightCol(cat.color)}">${esc(cat.name)}</span>
            <span class="fcard-cta">open →</span>
          </div>
        </article>`
        )
        .join("");
      return `
      <section class="fsection" data-cat="${cat.id}">
        <h3><span class="fdot" style="background:${cat.color}"></span>${esc(cat.name)} <span class="fcount">${list.length}</span></h3>
        <div class="fgrid">${cardsHtml}</div>
      </section>`;
    })
    .join("");

  root.innerHTML = `
    <div class="fb-notice">
      <strong>3D scene inactive</strong> — WebGL is disabled in this browser, so the galaxy view could not start.
      You are seeing the 2D portfolio instead. To get the full 3D experience, enable hardware acceleration
      (Chrome: <code>chrome://settings/system</code> · Edge: <code>edge://settings/system</code>) and reload.
      Search, filters and the HTML report still work below.
    </div>
    <div class="fb-app">
      ${sections}
      <div class="fb-empty" hidden>No skills match your search.</div>
    </div>
  `;

  cards = [...root.querySelectorAll(".fcard")];
  cards.forEach((c) =>
    c.addEventListener("click", () => onSelect && onSelect(c.dataset.skill))
  );
  return state;
}

const state = {
  mode: "2d",
  applyFilter(id) {
    document.querySelectorAll(".fsection").forEach((sec) => {
      sec.style.display = id === "all" || sec.dataset.cat === id ? "" : "none";
    });
    apply2DSearch(document.getElementById("search-input").value);
  },
  applySearch(q) {
    apply2DSearch(q);
  },
  focusSkill() {},
};

function apply2DSearch(q) {
  const query = q.trim().toLowerCase();
  cards.forEach((c) => {
    const skill = skillByCard(c);
    const text = (skill ? skill.name + " " + skill.tech + " " + skill.description : "").toLowerCase();
    c.style.display = !query || text.includes(query) ? "" : "none";
  });

  let anyVisible = false;
  document.querySelectorAll(".fsection").forEach((sec) => {
    let sectionVisible = false;
    [...sec.querySelectorAll(".fcard")].forEach((c) => {
      if (c.style.display !== "none") sectionVisible = true;
    });
    sec.style.display = sectionVisible ? "" : "none";
    if (sectionVisible) anyVisible = true;
  });

  const empty = document.querySelector(".fb-empty");
  if (empty) empty.hidden = anyVisible || !query;
}

function skillByCard(card) {
  const id = card.dataset.skill;
  return PORTFOLIO.skills.find((s) => s.id === id) || null;
}