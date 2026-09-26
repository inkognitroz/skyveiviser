"""Eksakte tabellverdier fra kundelisten. Ingen modell eller nettverkskall."""
from __future__ import annotations

import re
import unicodedata
from datetime import date

COLUMNS = ['orgnr', 'name', 'crs', 'cloud_ra', 'training', 'tppcm', 'cips', 'cti', 'vm']
SOURCE_URL = 'https://markedsplassen.anskaffelser.no/avtaler/kundeliste'


def normalized(text: str) -> str:
    """Normaliser kun søket. Originale navn og tabellverdier beholdes i resultatet."""
    text = unicodedata.normalize('NFKC', text).casefold()
    return ' '.join(re.findall(r'\w+', text))


def validate_register(register: dict | None, source_ids: set[str]) -> None:
    if register is None:  # Eldre kildefiler kan fortsatt brukes uten kundeliste.
        return
    if not isinstance(register, dict) or register.get('columns') != COLUMNS:
        raise ValueError('Ugyldige kundelistekolonner.')
    if register.get('source_url') != SOURCE_URL or register.get('source_id') not in source_ids:
        raise ValueError('Kundelisten mangler gyldig kilde.')
    for field in ('read_at', 'source_displayed_updated_at'):
        try:
            date.fromisoformat(register[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Kundelisten mangler gyldig dato.') from exc
    if not isinstance(register.get('note'), str) or not register['note'].strip():
        raise ValueError('Kundelisten mangler kildeforbehold.')
    agreements = register.get('agreements')
    if not isinstance(agreements, list) or len(agreements) != len(COLUMNS) - 2:
        raise ValueError('Kundelisten mangler avtaleoversikt.')
    if [a.get('id') for a in agreements if isinstance(a, dict)] != COLUMNS[2:]:
        raise ValueError('Avtalenes rekkefølge samsvarer ikke med kolonnene.')
    for a in agreements:
        if (not all(isinstance(a.get(k), str) and a[k] for k in ('title', 'status'))
                or not isinstance(a.get('aliases'), list)
                or not all(isinstance(s, str) and normalized(s) for s in a['aliases'])):
            raise ValueError('Ugyldig avtaleetikett.')
    rows = register.get('rows')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2000:
        raise ValueError('Kundelisten er tom eller for stor.')
    for row in rows:
        if (not isinstance(row, list) or len(row) != len(COLUMNS)
                or not all(isinstance(x, str) and len(x) <= 250 for x in row)
                or not row[1].strip()):
            raise ValueError('Ugyldig kundelisterad.')
        for value in row[2:]:
            if value not in ('Ja', 'Nei', '') and not value.startswith('Via '):
                raise ValueError('Ukjent tabellverdi; kontroller kundelisten.')


def lookup(query: str, register: dict | None) -> dict:
    if register is None:
        raise ValueError('Denne kildefilen inneholder ingen kundeliste.')
    key = normalized(query)
    if not key:
        raise ValueError('Skriv virksomhetsnavn, organisasjonsnummer eller avtalenavn.')
    all_rows = register['rows']
    agreements = register['agreements']
    # Eksakt avtalenavn er en listeforespørsel. Ja/Via gjengis, uten rettighetsdom.
    selected_agreement = next((a for a in agreements
        if key in {normalized(x) for x in a['aliases']}), None)
    if selected_agreement:
        index = COLUMNS.index(selected_agreement['id'])
        rows = [r for r in all_rows if r[index] == 'Ja' or r[index].startswith('Via ')]
        match_type = 'agreement'
        shown_columns = [{'id': selected_agreement['id'], 'index': index,
                          'title': selected_agreement['title'], 'status': selected_agreement['status']}]
    else:
        # Organisasjonsnummer match-es eksakt; navn kan søkes delvis.
        digits = re.sub(r'\s', '', query)
        if re.fullmatch(r'\d{9}', digits):
            rows = [r for r in all_rows if r[0] == digits]
            match_type = 'orgnr'
        else:
            exact = [r for r in all_rows if normalized(r[1]) == key]
            rows = exact or [r for r in all_rows if key in normalized(r[1])]
            match_type = 'name'
        shown_columns = [dict(a, index=i+2) for i, a in enumerate(agreements)]
    names = [normalized(r[1]) for r in rows]
    duplicate_names = sorted({r[1] for r in rows if names.count(normalized(r[1])) > 1})
    # Ingen rader slås sammen; uklarheter og ulike organisasjonsnumre er synlige.
    return {
        'customer_rows': rows, 'customer_columns': shown_columns,
        'customer_match_type': match_type, 'customer_match_count': len(rows),
        'customer_duplicate_names': duplicate_names,
        'customer_source_updated_at': register['source_displayed_updated_at'],
        'customer_read_at': register['read_at'], 'customer_note': register['note'],
        'customer_notice': ('Oppføring i datert kundeliste – ikke avropsgodkjenning. '
            'Tomme felt er ukjente, ikke Nei. Via beholdes som i originalen. '
            'VM er ikke bekreftet inngått i dette kildegrunnlaget.'),
        'status': 'customer_matches' if rows else 'no_customer_match',
    }
