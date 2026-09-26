'use strict';
const $ = id => document.getElementById(id);
let token = '', last = null;
const node = (tag, text, cls) => {
  const e = document.createElement(tag);
  e.textContent = text;
  if (cls) e.className = cls;
  return e;
};

function renderCustomers(r, out) {
  out.append(node('p', r.customer_notice));
  out.append(node('p', `Kildesidens oppdatertdato: ${r.customer_source_updated_at}. Kopi lest: ${r.customer_read_at}.`, 'small'));
  if (!r.customer_rows.length) {
    out.append(node('p', 'Ingen treff i denne kopien. Det er ikke bevis på manglende avropsrett. Kontroller navn, organisasjonsnummer og originalkilden.'));
    return;
  }
  out.append(node('p', `${r.customer_match_count} treff. ${r.customer_match_type === 'agreement' ? 'Viser kun rader merket Ja eller Via for valgt område.' : 'Navnesøk kan gi flere treff. Kontroller organisasjonsnummeret.'}`));
  if (r.customer_duplicate_names.length) out.append(node('p', 'Like navn forekommer flere ganger: ' + r.customer_duplicate_names.join(', ') + '. Radene er ikke slått sammen.'));
  const wrapper = node('div', '', 'tablewrap');
  const table = node('table', '');
  const caption = node('caption', 'Publiserte kundelisteverdier – tomt felt vises som «Ikke oppgitt»');
  table.append(caption);
  const head = node('thead', '');
  const header = node('tr', '');
  for (const title of ['Organisasjonsnummer', 'Virksomhet', ...r.customer_columns.map(c => c.title)]) {
    const th = node('th', title);
    th.scope = 'col';
    header.append(th);
  }
  head.append(header);
  table.append(head);
  const body = node('tbody', '');
  for (const row of r.customer_rows) {
    const tr = node('tr', '');
    for (const value of [row[0], row[1], ...r.customer_columns.map(c => row[c.index])]) {
      tr.append(node('td', value || 'Ikke oppgitt'));
    }
    body.append(tr);
  }
  table.append(body);
  wrapper.append(table);
  out.append(wrapper);
  for (const col of r.customer_columns) out.append(node('p', col.title + ': ' + col.status, 'small'));
}

function render(r) {
  const out = $('result');
  out.replaceChildren();
  const names = {
    source_matches: 'Kildetreff – ikke et KI-generert svar',
    no_source_match: 'Ikke tilstrekkelig kildegrunnlag',
    abstained: 'Modellen avsto fra å svare',
    model_answer: 'Svar fra lokal modell – må kontrolleres',
    customer_matches: 'Oppslag i kundelisten – uten KI',
    no_customer_match: 'Ingen treff i den lagrede kundelisten'
  };
  out.append(node('h3', names[r.status]));
  if (r.mode === 'customers') renderCustomers(r, out);
  if (r.answer && !r.answer.abstain) {
    for (const c of r.answer.claims) out.append(node('p', c.text + ' [' + c.source_ids.join(', ') + ']'));
  }
  if (r.status === 'no_source_match' || r.status === 'abstained') out.append(node('p', 'Kildeutvalget gir ikke et tilstrekkelig svar. Avgrens spørsmålet eller finn flere godkjente kilder.'));
  for (const s of r.sources) {
    const box = node('details', '');
    box.open = r.mode === 'sources';
    box.append(node('summary', s.id + ' · ' + s.title));
    box.append(node('p', s.text));
    box.append(node('p', 'Redaksjonelt sammendrag · gjennomgått ' + s.reviewed_at + ' · ' + s.section, 'small'));
    const a = node('a', 'Åpne originalkilden ↗');
    a.href = s.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    box.append(a);
    out.append(box);
  }
  out.append(node('p', `Tid: ${r.elapsed_seconds} s · inn-tokens: ${r.input_tokens ?? 'ikke målt'} · ut-tokens: ${r.output_tokens ?? 'ikke målt'} · kostnad: ikke målt`, 'small'));
  if (r.model) out.append(node('p', 'Modell: ' + r.model.name + ' · ' + r.model.quantization, 'small'));
  out.append(node('p', 'Kildeversjon: ' + r.corpus_version + '. Faglig verifikasjon av svar: ikke utført.', 'small'));
}

async function modelList() {
  $('model').replaceChildren();
  $('modelnotice').textContent = 'Henter lokale modeller …';
  try {
    const response = await fetch('/api/models');
    const data = await response.json();
    if (!response.ok) throw Error(data.error);
    for (const m of data.models) {
      const option = node('option', m.name + ' · ' + m.quantization);
      option.value = m.name;
      $('model').append(option);
    }
    $('modelnotice').textContent = data.models.length ? 'Bare rapporterte lokale GGUF-modeller. Kontroller at skyfunksjoner er slått av i Ollama.' : 'Ingen lokale modeller funnet. Kildesøk og kundeliste virker uten modell.';
  } catch (e) { $('modelnotice').textContent = e.message; }
}

function setMode() {
  const mode = $('mode').value;
  $('modelbox').hidden = mode !== 'ollama';
  $('customerhint').hidden = mode !== 'customers';
  $('ask').textContent = mode === 'ollama' ? 'Spør lokal modell' : mode === 'customers' ? 'Slå opp kundeliste' : 'Finn kildegrunnlag';
  if (mode === 'ollama') modelList();
}
$('mode').addEventListener('change', setMode);
document.querySelectorAll('[data-q]').forEach(e => e.addEventListener('click', () => {
  $('question').value = e.dataset.q;
  $('mode').value = e.dataset.mode || ($('mode').querySelector('[value="ollama"]').disabled ? 'sources' : 'ollama');
  setMode();
  $('question').focus();
}));
$('ask').addEventListener('click', async () => {
  $('ask').disabled = true;
  $('mode').disabled = true;
  $('download').hidden = true;
  last = null;
  $('result').replaceChildren(); // Et gammelt svar skal ikke bli stående hvis neste kall feiler.
  $('status').textContent = $('mode').value === 'ollama' ? 'Lokal modell arbeider. På eldre maskiner kan dette ta flere minutter.' : 'Slår opp i lokale data …';
  try {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Demo-Token': token},
      body: JSON.stringify({question: $('question').value, mode: $('mode').value, model: $('model').value})
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error);
    last = result;
    render(result);
    $('download').hidden = false;
    $('status').textContent = 'Ferdig. Kontroller grunnlaget før bruk.';
  } catch (e) {
    $('status').textContent = e.message;
  } finally {
    $('ask').disabled = false;
    $('mode').disabled = false;
  }
});
$('download').addEventListener('click', () => {
  if (!last) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(last, null, 2)], {type: 'application/json'}));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'skyveiviser-resultat.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
(async () => {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) throw Error('Kunne ikke lese lokalt oppsett.');
    const config = await response.json();
    token = config.token;
    $('notice').textContent = config.notice;
    const sourceOption = node('option', 'Kildesøk – uten LLM');
    sourceOption.value = 'sources';
    const customerOption = node('option', 'Kundeliste – uten KI');
    customerOption.value = 'customers';
    const modelOption = node('option', config.ollama_enabled ? 'Lokal språkmodell via Ollama' : 'Lokal språkmodell – krever aktivering');
    modelOption.value = 'ollama';
    modelOption.disabled = !config.ollama_enabled;
    $('mode').replaceChildren(sourceOption, customerOption, modelOption);
    $('mode').value = config.ollama_enabled ? 'ollama' : 'sources';
    setMode();
    $('status').textContent = 'Klar. Kildeversjon ' + config.corpus_version;
    $('ask').disabled = false;
  } catch (e) { $('status').textContent = e.message; }
})();
