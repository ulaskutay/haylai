import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export const GUEST_EMAIL = "guest@hayl.local";

export type AppUser = {
  id: string;
  email: string | null;
};

export function isAuthDisabled() {
  return process.env.AUTH_DISABLED !== "false";
}

let guestCache: AppUser | null = null;

async function ensureGuest(): Promise<AppUser> {
  if (guestCache) return guestCache;

  const admin = createAdminClient();
  const { data: list, error: listError } = await admin.auth.admin.listUsers({
    page: 1,
    perPage: 200,
  });
  if (listError) {
    throw new Error(`Guest user lookup failed: ${listError.message}`);
  }

  let authUser = list.users.find((u) => u.email === GUEST_EMAIL);
  if (!authUser) {
    const { data, error } = await admin.auth.admin.createUser({
      email: GUEST_EMAIL,
      email_confirm: true,
      password: crypto.randomUUID(),
    });
    if (error || !data.user) {
      throw new Error(error?.message ?? "Guest user could not be created");
    }
    authUser = data.user;
  }

  await admin.from("users").upsert(
    {
      id: authUser.id,
      email: GUEST_EMAIL,
    },
    { onConflict: "id", ignoreDuplicates: true },
  );

  guestCache = { id: authUser.id, email: GUEST_EMAIL };
  return guestCache;
}

export async function requireUser(): Promise<AppUser | null> {
  if (isAuthDisabled()) {
    return ensureGuest();
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;
  return { id: user.id, email: user.email ?? null };
}
