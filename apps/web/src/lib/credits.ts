export function isCreditsDisabled() {
  return process.env.CREDITS_DISABLED !== "false";
}

export function isCreditsUiDisabled() {
  return process.env.NEXT_PUBLIC_CREDITS_DISABLED !== "false";
}
