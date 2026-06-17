export type TelegramWebAppUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
};

export type TelegramWebApp = {
  initData: string;
  initDataUnsafe?: { user?: TelegramWebAppUser };
  ready: () => void;
  expand: () => void;
  close: () => void;
  setBackgroundColor: (color: string) => void;
  setHeaderColor: (color: string) => void;
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
  };
  openLink?: (url: string) => void;
  sendData?: (data: string) => void;
};

export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") {
    return null;
  }

  return (window as any).Telegram?.WebApp ?? null;
}
