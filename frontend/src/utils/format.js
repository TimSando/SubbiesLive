/**
 * Formats division names for display.
 * Numeric divisions are prefixed with "Division " (e.g., "1" -> "Division 1").
 * Named divisions are formatted cleanly without "Division" (e.g., "Mens" -> "Men's").
 * 
 * @param {string|number} div The raw division value from the source.
 * @returns {string} The formatted division name.
 */
export function formatDivisionName(div) {
  if (!div) return '';
  const d = String(div).trim();
  const lower = d.toLowerCase();
  
  if (lower === 'mens') return "Men's";
  if (lower === 'womens') return "Women's";
  if (lower === 'halligans') return 'Halligans';
  
  // If it is numeric, prefix with "Division "
  if (/^\d+$/.test(d)) {
    return `Division ${d}`;
  }
  
  return d;
}
