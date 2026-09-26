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
    out.append(node('p', r.status === 'customer_name_required'
      ? 'Hvilken virksomhet gjelder det? Skriv navn eller organisasjonsnummer, for eksempel Asker kommune.'
      : 'Ingen treff i denne kopien. Det er ikke bevis på manglende avropsrett. Kontroller navn, organisasjonsnummer og originalkilden.'));
    return;
  }
  if (r.customer_match_type !== 'agreement' && r.customer_rows.length <= 8) {
    if (r.customer_rows.length > 1) {
      out.append(node('p', 'Flere virksomhetsrader passer. Kontroller navn og organisasjonsnummer. Ingen rader er slått sammen.'));
    }
    for (const row of r.customer_rows) {
      out.append(node('h3', row[1]));
      out.append(node('p', 'Organisasjonsnummer: ' + (row[0] || 'Ikke oppgitt'), 'small'));
      const joined = r.customer_columns.filter(c => c.id !== 'vm'
        && (row[c.index] === 'Ja' || row[c.index].startsWith('Via ')));
      out.append(node('p', joined.length
        ? 'Registrert med Ja eller Via for: ' + joined.map(c => c.title).join(', ') + '.'
        : 'Ingen av de seks inngåtte avtaleområdene er merket Ja eller Via for denne virksomheten i den lagrede kundelisten.'));
      const table = node('table', '', 'membership-table');
      table.append(node('caption', 'Tilslutning per avtaleområde – verdiene fra kundelisten'));
      const head = node('thead', '');
      const tr = node('tr', '');
      for (const label of ['Avtaleområde', 'Tilslutning']) {
        const th = node('th', label); th.scope = 'col'; tr.append(th);
      }
      head.append(tr); table.append(head);
      const body = node('tbody', '');
      for (const col of r.customer_columns) {
        const item = node('tr', '');
        const name = node('th', col.title + (col.id === 'vm' ? ' (kommende)' : ''));
        name.scope = 'row';
        item.append(name, node('td', row[col.index] || 'Ikke oppgitt'));
        body.append(item);
      }
      table.append(body); out.append(table);
    }
    out.append(node('p', 'VM er en kommende anskaffelse. Ja i VM-kolonnen betyr ikke at avtalen er inngått eller åpen for avrop. CRS: bekreft gjeldende forlengelse før nytt avrop.', 'small'));
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

function renderPlan(r, out) {
  if (!r.vm_plan) return;
  const box = node('div', '', 'notice');
  box.append(node('strong', r.vm_plan.display));
  box.append(node('p', r.vm_plan.provenance, 'small'));
  box.append(node('p', r.vm_plan.notice, 'small'));
  out.append(box);
}

function renderOverview(r, out) {
  out.append(node('p', 'Seks inngåtte avtaleområder i det daterte kildegrunnlaget. Kontroller gjeldende avtale og tilslutning før avrop.'));
  const list = node('ol', '');
  for (const area of r.agreement_catalogue) {
    const item = node('li', '');
    const link = node('a', area.title);
    link.href = area.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    item.append(link, node('p', area.status, 'small'));
    list.append(item);
  }
  out.append(list, node('h3', 'Kommende: Vulnerability Management (VM)'));
  out.append(node('p', 'VM inngår ikke i listen over de seks inngåtte områdene. Velg «Spør om VM» for innhold og status.'));
  renderPlan(r, out);
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
    no_customer_match: 'Ingen treff i den lagrede kundelisten',
    customer_name_required: 'Oppgi virksomheten du vil slå opp',
    agreement_overview: 'Avtaleoversikt – uten KI',
    vm_details: 'Vulnerability Management (VM) – kommende anskaffelse'
  };
  out.append(node('h3', names[r.status]));
  if (r.mode === 'customers') renderCustomers(r, out);
  if (r.mode === 'agreements') renderOverview(r, out);
  if (r.mode === 'vm') renderPlan(r, out);
  if (r.answer && !r.answer.abstain) {
    for (const c of r.answer.claims) out.append(node('p', c.text + ' [' + c.source_ids.join(', ') + ']'));
  }
  if (r.status === 'no_source_match' || r.status === 'abstained') out.append(node('p', 'Kildeutvalget gir ikke et tilstrekkelig svar. Avgrens spørsmålet eller finn flere godkjente kilder.'));
  for (const s of r.sources) {
    const box = node('details', '');
    box.open = r.mode === 'sources' || r.mode === 'vm';
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
const quickButtons = [...document.querySelectorAll('[data-q]')];
quickButtons.forEach(button => button.addEventListener('click', () => {
  if (!token || $('ask').disabled) return;
  $('question').value = button.dataset.q;
  $('mode').value = button.dataset.mode || 'sources';
  setMode();
  $('question').focus();
  if (button.dataset.q) {
    submitQuestion();
  } else {
    last = null;
    $('download').hidden = true;
    $('result').replaceChildren();
    $('status').textContent = 'Skriv virksomhetsnavn eller et spørsmål om tilslutning, og trykk «Slå opp kundeliste».';
  }
}));
async function submitQuestion() {
  if (!token || $('ask').disabled) return;
  $('ask').disabled = true;
  $('mode').disabled = true;
  $('question').disabled = true;
  quickButtons.forEach(button => { button.disabled = true; });
  $('download').hidden = true;
  last = null;
  $('result').replaceChildren();
  $('status').textContent = 'Behandler spørsmålet. Oppslag gjøres uten KI; modellspørsmål kan ta lengre tid.';
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
    $('question').disabled = false;
    quickButtons.forEach(button => { button.disabled = false; });
  }
}
$('ask').addEventListener('click', submitQuestion);
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
