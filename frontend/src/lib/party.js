// Map UK party names to their usual colours.
export function getPartyColor(partyName) {
  if (!partyName) return '#cccccc';

  const p = partyName.toLowerCase();

  if (p.includes('conservative')) return '#0087DC';
  if (p.includes('labour')) return '#DC241F';
  if (p.includes('liberal')) return '#FDBB30';
  if (p.includes('green')) return '#6AB023';
  if (p.includes('scottish national') || p.includes('snp')) return '#FFF200';
  if (p.includes('plaid cymru')) return '#3FB637';
  if (p.includes('democratic unionist') || p.includes('dup')) return '#D46A28';
  if (p.includes('sinn féin') || p.includes('sinn fein')) return '#326C29';
  if (p.includes('social democratic') || p.includes('sdlp')) return '#008A51';
  if (p.includes('ukip')) return '#70147A';
  if (p.includes('reform')) return '#12E0BA';
  if (p.includes('independent')) return '#aaaaaa';

  return '#cccccc';
}

// Black or white text, whichever reads better on a #rrggbb background.
export function textOn(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? '#111' : '#fff';
}
