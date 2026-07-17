export function createProductIdentification({ identified = false, product_name = null, brand = null, variant = null, barcode = null, confidence = 0, needs_barcode = false, message = null } = {}) {
  return { identified, product_name, brand, variant, barcode, confidence, needs_barcode, message };
}

class MockAIProvider {
  async identify(image) {
    return createProductIdentification({
      identified: true,
      product_name: "Produs Mock",
      brand: "Mock Brand",
      variant: "Mock Variant",
      barcode: "1234567890123",
      confidence: 85,
      needs_barcode: false,
      message: "Produs identificat (mock).",
    });
  }

  isAvailable() {
    return true;
  }
}

class OpenAIProvider {
  constructor() {
    this.apiUrl = `${process.env.NEXT_PUBLIC_API_URL || "/api/backend"}/ai/identify-product-frame`;
  }

  async identify(image) {
    const formData = new FormData();
    formData.append("frame", image, "camera.jpg");

    const response = await fetch(this.apiUrl, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Identificarea a eșuat.");
    }

    if (data.code === "scan_limit_reached") {
      throw new Error(data.error || "Limita de scanări atinsă.");
    }

    if (!data.identified) {
      return createProductIdentification({
        identified: false,
        message: data.message || "Nu am identificat sigur produsul.",
      });
    }

    return createProductIdentification({
      identified: true,
      product_name: data.product?.name || data.candidate?.name || null,
      brand: data.candidate?.brand || null,
      variant: data.candidate?.variant || null,
      barcode: data.candidate?.barcode || null,
      confidence: data.candidate?.confidence || 0,
      needs_barcode: data.candidate?.needs_barcode ?? true,
      message: data.candidate?.message || "Produs identificat vizual.",
    });
  }

  isAvailable() {
    return true;
  }
}

let cachedProvider = null;

export function getAIProvider() {
  if (cachedProvider) {
    return cachedProvider;
  }

  const visionEnabled = process.env.NEXT_PUBLIC_AI_VISION_ENABLED === "true";

  if (!visionEnabled) {
    cachedProvider = new MockAIProvider();
    return cachedProvider;
  }

  const provider = process.env.NEXT_PUBLIC_AI_VISION_PROVIDER || "mock";

  if (provider === "openai") {
    cachedProvider = new OpenAIProvider();
  } else {
    cachedProvider = new MockAIProvider();
  }

  return cachedProvider;
}