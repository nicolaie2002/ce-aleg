interface NavigatorConnectionInfo {
  effectiveType?: string;
  saveData?: boolean;
}

interface Navigator {
  connection?: NavigatorConnectionInfo;
  mozConnection?: NavigatorConnectionInfo;
  webkitConnection?: NavigatorConnectionInfo;
  deviceMemory?: number;
}

interface Window {
  gtag?: (...args: any[]) => void;
  fbq?: (...args: any[]) => void;
  ttq?: {
    page: () => void;
    track: (eventName: string, metadata?: Record<string, unknown>) => void;
    grantConsent?: () => void;
    revokeConsent?: () => void;
  };
  SpeechRecognition?: new () => any;
  webkitSpeechRecognition?: new () => any;
}
