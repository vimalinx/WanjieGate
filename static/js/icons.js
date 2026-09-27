const paths = {
  plus:'<path d="M12 5v14M5 12h14"/>', 'arrow-up':'<path d="m6 11 6-6 6 6M12 5v14"/>',
  chart:'<path d="M4 4v16h16M8 15l4-5 4 2 4-7"/>', note:'<path d="M14 3H5v18h14V8zM14 3v5h5M8 12h8M8 16h6"/>',
  check:'<rect x="3" y="3" width="18" height="18" rx="5"/><path d="m7 12 3 3 7-7"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  route:'<circle cx="5" cy="6" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 6h8a4 4 0 0 1 0 8H9a4 4 0 0 0 0 8M17 18H9"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  sliders:'<path d="M4 7h7m4 0h5M4 17h3m4 0h9"/><circle cx="13" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
  pin:'<path d="m9 3 6 0-1 6 4 4v2H6v-2l4-4zM12 15v6"/>',
  table:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 14h18M10 4v16"/>',
  space:'<path d="M5 21V10a7 7 0 0 1 14 0v11M11 21V10h8"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
};
export const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.space}</svg>`;
export function hydrateIcons(root = document) {root.querySelectorAll('[data-icon]').forEach(el => {el.innerHTML = icon(el.dataset.icon);});}
