const ICON_COLORS = {
  projects: '--cat-projects',
  dashboards: '--cat-dashboards',
  research: '--cat-research',
  skills: '--cat-skills',
  certificates: '--cat-certificates',
  contact: '--cat-contact',
  'case-studies': '--cat-case-studies',
  recommendation: '--brand-pink',
  default: '--brand-accent',
};

function iconColor(key) {
  const varName = ICON_COLORS[key] || ICON_COLORS.default;
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return value || '#7c3aed';
}