import crypto from "crypto";

export function validateTelegram(initData: string, botToken: string): boolean {
  const urlParams = new URLSearchParams(initData);

  const hash = urlParams.get("hash");
  if (!hash) {
    return false;
  }

  urlParams.delete("hash");

  const dataCheckString = [...urlParams.entries()]
    .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  const secret = crypto.createHmac("sha256", "WebAppData").update(botToken).digest();

  const hmac = crypto.createHmac("sha256", secret).update(dataCheckString).digest("hex");

  return hmac === hash;
}
