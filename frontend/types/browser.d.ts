interface CeAlegNativeDetectedBarcode {
  rawValue?: string;
}

interface CeAlegNativeBarcodeDetector {
  detect(source: HTMLVideoElement): Promise<CeAlegNativeDetectedBarcode[]>;
}

interface Window {
  BarcodeDetector?: {
    new (options: { formats: string[] }): CeAlegNativeBarcodeDetector;
    getSupportedFormats?: () => Promise<string[]>;
  };
}
