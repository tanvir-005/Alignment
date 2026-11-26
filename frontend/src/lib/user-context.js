"use client";

import { createContext, useContext } from "react";

export const UserContext = createContext(null);

/** The signed-in user from /auth/me: { id, name, email, is_admin, memberships, pm_team_ids, ... } */
export function useUser() {
  return useContext(UserContext);
}

export function isPmOf(user, teamId) {
  return Boolean(user?.pm_team_ids?.includes(Number(teamId)));
}
