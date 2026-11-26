// Keys must match TEAM_COLORS in todos/models.py
export const TEAM_COLORS = {
  blue: "#3946d6",
  teal: "#0b8f9e",
  green: "#2b9a4b",
  amber: "#c98200",
  orange: "#e0561b",
  rose: "#d12f66",
  violet: "#7b3fe4",
  slate: "#566180",
};

export const TEAM_COLOR_KEYS = Object.keys(TEAM_COLORS);

export function teamColor(key) {
  return TEAM_COLORS[key] || TEAM_COLORS.blue;
}
