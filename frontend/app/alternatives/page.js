"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Flag, Heart, Loader2, Search, ShoppingCart } from "lucide-react";
import { API_URL } from "../config";
import { getImageUrl } from "../utils/getImageUrl";
import { trackEvent } from "../utils/analytics";
import { ExpandableText } from "../components/ExpandableText";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";
import { getActiveProfile, getActiveProfilePayload, readProfilePreferences } from "../utils/profilePreferences";

const criteriaLabels = {
  cheap: "mai ieftin",
  protein: "mai multă proteină",
  low_calorie: "mai puține calorii",
  low_sugar: "mai puțin zahăr",
  vegan: "de post",
  lactose_free: "fără lactoză",
  natural: "ingrediente mai curate",
  caffeine: "mai multă cafeină",
  value: "best value",
};

const goalCriteriaMap = {
  balanced: ["value"],
  budget: ["cheap"],
  fitness: ["protein", "low_sugar", "low_calorie"],
  clean: ["natural"],
};

const allergenKeywords = {
  gluten: ["gluten", "grau", "wheat", "barley", "orz", "rye", "secara"],
  lactose: ["lapte", "milk", "lactoza", "lactose", "whey", "zer", "smantana", "cream"],
  peanuts: ["arahide", "peanuts", "peanut"],
  nuts: ["alune", "hazelnut", "hazelnuts", "migdale", "almond", "cashew", "nuci", "walnut"],
  soy: ["soia", "soy", "soya"],
  egg: ["ou", "egg", "eggs"],
  fish: ["peste", "fish", "ton", "tuna", "somon", "salmon"],
  sesame: ["susan", "sesame"],
};

const allergyLabels = {
  gluten: "Gluten",
  lactose: "Lactoză",
  peanuts: "Arahide",
  nuts: "Fructe cu coajă",
  soy: "Soia",
  egg: "Ou",
  fish: "Pește",
  sesame: "Susan",
};

function getStoreName(storeId) {
  const stores = {
    lidl: "Lidl",
    kaufland: "Kaufland",
    carrefour: "Carrefour",
    mega: "Mega Image",
    profi: "Profi",
    penny: "Penny",
    local: "Market local",
    any: "Fără magazin ales",
  };

  return stores[storeId] || "Fără magazin ales";
}

function normalizeText(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function normalizeCategory(category) {
  const text = normalizeText(category);

  if (text.includes("lactate")) return "lactate";
  if (text.includes("snacks")) return "snacks";
  if (text.includes("bauturi")) return "bauturi";
  if (text.includes("carne")) return "carne";
  if (text.includes("paste") || text.includes("noodles")) return "noodles";

  return text;
}

function getProductFamily(product) {
  const text = productSearchText(product);

  if (/\b(apa|water|mineral)\b/.test(text)) return "water";
  if (text.includes("energy") || text.includes("energiz") || text.includes("taurina")) return "energy_drink";
  if (text.includes("cafea") || text.includes("coffee") || text.includes("cappuccino") || text.includes("latte")) return "coffee_drink";
  if (text.includes("cola") || text.includes("pepsi")) return "cola";
  if (text.includes("suc") || text.includes("juice") || text.includes("soft drink")) return "soft_drink";
  if (text.includes("iaurt") || text.includes("yogurt") || text.includes("yoghurt")) return "yogurt";
  if (text.includes("lapte") || text.includes("milk") || text.includes("branza") || text.includes("cheese")) return "dairy";
  if (text.includes("muschi") || text.includes("sunca") || text.includes("ham") || text.includes("salam") || text.includes("prosciutto")) return "meat";
  if (text.includes("buldak") || text.includes("noodle") || text.includes("noodles") || text.includes("ramen")) return "noodles";
  if (text.includes("ciocolata") || text.includes("chocolate") || text.includes("nutella")) return "sweets";
  if (text.includes("biscuit") || text.includes("wafer") || text.includes("napolit")) return "biscuits";
  if (text.includes("chips") || text.includes("snack") || text.includes("crisps")) return "snacks";
  if (text.includes("inghetata") || text.includes("ice cream") || text.includes("gelato")) return "ice_cream";
  if (text.includes("sos") || text.includes("sauce") || text.includes("ketchup") || text.includes("mustar")) return "sauce";
  if (text.includes("cereale") || text.includes("cereal") || text.includes("granola")) return "cereal";

  return normalizeCategory(product.category || "");
}

function areCompatibleFamilies(scannedProduct, candidate) {
  if (!scannedProduct) return true;

  const scannedFamily = getProductFamily(scannedProduct);
  const candidateFamily = getProductFamily(candidate);

  if (!scannedFamily || !candidateFamily) return true;
  if (scannedFamily === candidateFamily) return true;

  const familyGroups = [
    ["energy_drink", "coffee_drink", "cola", "soft_drink"],
    ["yogurt", "dairy"],
    ["snacks", "biscuits", "sweets"],
  ];

  return familyGroups.some(
    (group) => group.includes(scannedFamily) && group.includes(candidateFamily)
  );
}

function normalizeProductName(name) {
  const ignoredWords = new Set([
    "bautura",
    "can",
    "cu",
    "doza",
    "drink",
    "energy",
    "energizant",
    "energizanta",
    "fara",
    "produs",
  ]);

  return normalizeText(name)
    .replace(/\b\d+(?:[.,]\d+)?\s*(?:g|gr|kg|ml|l)\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .split(" ")
    .filter((word) => word && !ignoredWords.has(word))
    .join(" ");
}

function getNameTokens(name) {
  return new Set(normalizeProductName(name).split(" ").filter(Boolean));
}

function calculateTokenSimilarity(firstName, secondName) {
  const firstTokens = getNameTokens(firstName);
  const secondTokens = getNameTokens(secondName);

  if (firstTokens.size === 0 || secondTokens.size === 0) return 0;

  const sharedTokens = [...firstTokens].filter((token) =>
    secondTokens.has(token)
  ).length;

  return (2 * sharedTokens) / (firstTokens.size + secondTokens.size);
}

function isSameProductVariant(product, scannedProduct) {
  if (!scannedProduct) return false;

  if (
    product.barcode &&
    scannedProduct.barcode &&
    product.barcode === scannedProduct.barcode
  ) {
    return true;
  }

  const productName = normalizeProductName(product.name);
  const scannedName = normalizeProductName(scannedProduct.name);

  if (!productName || !scannedName) return false;
  if (productName === scannedName) return true;

  const productTokens = getNameTokens(product.name);
  const scannedTokens = getNameTokens(scannedProduct.name);
  const shorterTokens =
    productTokens.size <= scannedTokens.size ? productTokens : scannedTokens;
  const longerTokens =
    productTokens.size > scannedTokens.size ? productTokens : scannedTokens;
  const shorterNameIsContained =
    shorterTokens.size >= 2 &&
    [...shorterTokens].every((token) => longerTokens.has(token));

  return (
    shorterNameIsContained ||
    calculateTokenSimilarity(product.name, scannedProduct.name) >= 0.8
  );
}

function getProductIdentityKey(product) {
  const barcode = String(product.barcode || "").trim();
  if (barcode) return `barcode:${barcode}`;

  const name = normalizeProductName(product.name || "");
  const brand = normalizeText(product.brand || "");
  const quantity = normalizeText(product.quantity || "");
  const category = normalizeCategory(product.category || "");

  return [brand, name, quantity, category].filter(Boolean).join("|");
}

function areDuplicateProducts(firstProduct, secondProduct) {
  if (!firstProduct || !secondProduct) return false;

  const firstKey = getProductIdentityKey(firstProduct);
  const secondKey = getProductIdentityKey(secondProduct);

  if (firstKey && secondKey && firstKey === secondKey) return true;

  const sameBrand =
    normalizeText(firstProduct.brand || "") &&
    normalizeText(firstProduct.brand || "") === normalizeText(secondProduct.brand || "");
  const sameQuantity =
    normalizeText(firstProduct.quantity || "") &&
    normalizeText(firstProduct.quantity || "") === normalizeText(secondProduct.quantity || "");
  const sameCategory =
    normalizeCategory(firstProduct.category || "") &&
    normalizeCategory(firstProduct.category || "") === normalizeCategory(secondProduct.category || "");
  const verySimilarName =
    calculateTokenSimilarity(firstProduct.name || "", secondProduct.name || "") >= 0.76;

  return verySimilarName && (sameBrand || sameQuantity || sameCategory);
}

function dedupeProductList(productList, scannedProduct = null) {
  const uniqueProducts = [];

  for (const product of productList) {
    if (scannedProduct && isSameProductVariant(product, scannedProduct)) {
      continue;
    }

    const duplicate = uniqueProducts.some((existingProduct) =>
      areDuplicateProducts(existingProduct, product)
    );

    if (!duplicate) {
      uniqueProducts.push(product);
    }
  }

  return uniqueProducts;
}

function inferCriteriaFromRequest(requestText) {
  const text = normalizeText(requestText);
  const inferred = [];

  if (
    text.includes("ieftin") ||
    text.includes("pret mic") ||
    text.includes("sub ")
  ) {
    inferred.push("cheap");
  }

  if (text.includes("proteina") || text.includes("protein")) {
    inferred.push("protein");
  }

  if (
    text.includes("cafeina") ||
    text.includes("cofeina") ||
    text.includes("caffeine") ||
    text.includes("energiz") ||
    text.includes("energie") ||
    text.includes("taurina")
  ) {
    inferred.push("caffeine");
  }

  if (
    text.includes("calorii") ||
    text.includes("slabit") ||
    text.includes("dieta")
  ) {
    inferred.push("low_calorie");
  }

  if (text.includes("zahar") || text.includes("fara zahar")) {
    inferred.push("low_sugar");
  }

  if (
    text.includes("post") ||
    text.includes("vegan") ||
    text.includes("vegetal")
  ) {
    inferred.push("vegan");
  }

  if (text.includes("lactoza") || text.includes("fara lactoza")) {
    inferred.push("lactose_free");
  }

  if (
    text.includes("natural") ||
    text.includes("curat") ||
    text.includes("ingrediente")
  ) {
    inferred.push("natural");
  }

  if (
    text.includes("calitate") ||
    text.includes("value") ||
    text.includes("raport")
  ) {
    inferred.push("value");
  }

  return inferred;
}

const blockedSearchWords = [
  "pula",
  "pizda",
  "muie",
  "cacat",
  "prost",
  "proasta",
  "idiot",
  "dracu",
  "dracului",
  "fuck",
  "shit",
];

function validateAlternativeSearch(requestText) {
  const text = normalizeText(requestText).trim();

  if (!text) return "";

  if (blockedSearchWords.some((word) => text.includes(word))) {
    return "Foloseste cuvinte normale si spune ce caracteristici vrei la produs.";
  }

  const words = text
    .replace(/[^a-z0-9\s]+/g, " ")
    .split(/\s+/)
    .filter((word) => word.length >= 3);

  if (words.length === 0) {
    return "Descrie produsul dorit: de exemplu mai ieftin, fără zahăr sau mai multă proteină.";
  }

  if (text.length < 4) {
    return "Scrie putin mai clar ce cauti.";
  }

  return "";
}

async function readJsonResponse(response, sourceLabel) {
  const text = await response.text();

  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(
      `${sourceLabel} nu a trimis un răspuns valid. Reîncărcăm recomandările disponibile.`
    );
  }
}

function productSearchText(product) {
  return normalizeText(
    [
      product.name,
      product.brand,
      product.category,
      product.store,
      product.tag,
      product.reason,
      product.ingredients,
      product.nutriScore,
    ]
      .filter(Boolean)
      .join(" ")
  );
}

function productIngredientText(product) {
  return normalizeText(
    [
      product.ingredients,
      product.reason,
      product.name,
      product.category,
      product.labels,
      product.tag,
    ]
      .filter(Boolean)
      .join(" ")
  );
}

function splitAvoidIngredients(value) {
  return normalizeText(value)
    .split(/[,;\n]+/)
    .map((item) => item.trim())
    .filter((item) => item.length >= 3);
}

function getCriteriaFromGoal(goal) {
  return goalCriteriaMap[goal] || [];
}

function productViolatesPreferences(product, preferences) {
  if (!preferences) return false;

  const text = productIngredientText(product);
  const selectedAllergies = Array.isArray(preferences.allergies)
    ? preferences.allergies
    : [];
  const avoids = splitAvoidIngredients(preferences.avoidIngredients || "");

  for (const allergy of selectedAllergies) {
    const keywords = allergenKeywords[allergy] || [];
    if (keywords.some((keyword) => text.includes(keyword))) {
      return true;
    }
  }

  return avoids.some((keyword) => text.includes(keyword));
}

function filterProductsBySearch(products, requestText) {
  const text = normalizeText(requestText).trim();
  if (!text) return products;

  const inferredCriteria = inferCriteriaFromRequest(text);
  const words = text
    .replace(/[^a-z0-9\s]+/g, " ")
    .split(/\s+/)
    .filter((word) => word.length >= 3);

  if (words.length === 0 && inferredCriteria.length === 0) return products;

  const scoredProducts = products.map((product) => {
    const haystack = productSearchText(product);
    const wordMatches = words.filter((word) => haystack.includes(word)).length;
    let score = wordMatches * 4;

    if (inferredCriteria.includes("low_sugar") && Number(product.sugar) <= 5) score += 8;
    if (inferredCriteria.includes("protein") && Number(product.protein) >= 8) score += 8;
    if (inferredCriteria.includes("low_calorie") && Number(product.calories) <= 150) score += 8;
    if (inferredCriteria.includes("caffeine")) {
      if (haystack.includes("energiz") || haystack.includes("energy") || haystack.includes("taurina")) {
        score += 14;
      } else if (haystack.includes("cafea") || haystack.includes("coffee") || haystack.includes("caffeine") || haystack.includes("cafeina")) {
        score += 10;
      } else if (haystack.includes("cola")) {
        score -= 16;
      } else {
        score -= 20;
      }
    }
    if (inferredCriteria.includes("vegan") && product.vegan) score += 8;
    if (inferredCriteria.includes("lactose_free") && product.lactoseFree) score += 8;
    if (inferredCriteria.includes("natural") && product.natural) score += 8;
    if (inferredCriteria.includes("cheap") && getNumericValue(product, "price") !== null) score += 3;

    return { product, score };
  });

  const matchedProducts = scoredProducts
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((item) => item.product);

  if (matchedProducts.length > 0) return matchedProducts;

  return inferredCriteria.length > 0 ? [] : products;
}

function getNumericValue(product, field) {
  if (field === "price" && product.priceSource && !product.priceIsLocal) {
    return null;
  }

  if (product[field] === null || product[field] === undefined || product[field] === "") {
    return null;
  }

  const value = Number(product[field]);
  return Number.isFinite(value) ? value : null;
}

function getNormalizedPreferenceScore(products, product, field, preferHigher) {
  const values = products
    .map((item) => getNumericValue(item, field))
    .filter((value) => value !== null);
  const value = getNumericValue(product, field);

  if (value === null || values.length === 0) return 0;

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);

  if (minimum === maximum) return 1;

  const normalized = (value - minimum) / (maximum - minimum);
  return preferHigher ? normalized : 1 - normalized;
}

function calculateAlternativeScore(products, product, criteriaList) {
  let score = Number(product.score) || 0;

  if (criteriaList.includes("cheap")) {
    score += getNormalizedPreferenceScore(products, product, "price", false) * 10;
  }

  if (criteriaList.includes("protein")) {
    score += getNormalizedPreferenceScore(products, product, "protein", true) * 10;
  }

  if (criteriaList.includes("low_calorie")) {
    score += getNormalizedPreferenceScore(products, product, "calories", false) * 10;
  }

  if (criteriaList.includes("low_sugar")) {
    score += getNormalizedPreferenceScore(products, product, "sugar", false) * 10;
  }

  if (criteriaList.includes("caffeine")) {
    const haystack = productSearchText(product);

    if (haystack.includes("energiz") || haystack.includes("energy") || haystack.includes("taurina")) {
      score += 12;
    } else if (haystack.includes("cafea") || haystack.includes("coffee") || haystack.includes("caffeine") || haystack.includes("cafeina")) {
      score += 9;
    } else if (haystack.includes("cola")) {
      score -= 8;
    }
  }

  if (criteriaList.includes("value")) {
    score += (Number(product.score) || 0) * 1.5;
  }

  return score;
}

function formatNutritionValue(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) return "-";

  return number.toFixed(1).replace(/\.0$/, "");
}

function formatScore(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) return "-";

  return number.toFixed(1).replace(/\.0$/, "");
}

function getPriceLabel(product) {
  return product.priceText && product.priceText !== "preț necunoscut"
    ? product.priceText
    : "Verifică prețul în magazin";
}

function getPriceDetails(product) {
  if (!product.priceSource) return "";

  const details = [
    product.priceStore,
    product.priceDate ? `observat la ${product.priceDate}` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return product.priceIsLocal === false
    ? `${details} · observație din altă piață`
    : details;
}

function getNutritionDifference(product, scannedProduct, field, preferHigher) {
  const productValue = getNumericValue(product, field);
  const scannedValue = getNumericValue(scannedProduct, field);

  if (productValue === null || scannedValue === null) return null;

  const difference = productValue - scannedValue;

  if (Math.abs(difference) < 0.05) return null;

  const better = preferHigher ? difference > 0 : difference < 0;
  const sign = difference > 0 ? "+" : "";

  return {
    better,
    text: `${sign}${formatNutritionValue(difference)}`,
  };
}

function filterProductsByCriteria(
  allProducts,
  storeName,
  criteriaList,
  scannedProduct,
  profilePreferences = null
) {
  let filteredProducts = [...allProducts];

  if (scannedProduct) {
    filteredProducts = filteredProducts.filter((product) => {
      const hasSameId =
        scannedProduct.id &&
        Number(product.id) === Number(scannedProduct.id);

      return !hasSameId && !isSameProductVariant(product, scannedProduct);
    });

    const compatibleProducts = filteredProducts.filter((product) =>
      areCompatibleFamilies(scannedProduct, product)
    );

    if (compatibleProducts.length >= 2) {
      filteredProducts = compatibleProducts;
    }
  }

  if (profilePreferences) {
    const safeProducts = filteredProducts.filter(
      (product) => !productViolatesPreferences(product, profilePreferences)
    );

    if (safeProducts.length > 0) {
      filteredProducts = safeProducts;
    }
  }

  if (
    storeName !== "Fără magazin ales" &&
    filteredProducts.every((product) => product.store !== "Open Food Facts")
  ) {
    filteredProducts = filteredProducts.filter(
      (product) => product.store === storeName
    );
  }

  if (scannedProduct?.category) {
    const scannedCategory = normalizeCategory(scannedProduct.category);

    const sameCategoryProducts = filteredProducts.filter(
      (product) => normalizeCategory(product.category) === scannedCategory
    );

    if (sameCategoryProducts.length > 0) {
      filteredProducts = sameCategoryProducts;
    }
  }

  if (criteriaList.includes("vegan")) {
    filteredProducts = filteredProducts.filter((product) => product.vegan);
  }

  if (criteriaList.includes("lactose_free")) {
    filteredProducts = filteredProducts.filter(
      (product) => product.lactoseFree
    );
  }

  if (criteriaList.includes("natural")) {
    filteredProducts = filteredProducts.filter((product) => product.natural);
  }

  if (criteriaList.includes("caffeine")) {
    const highCaffeineProducts = filteredProducts.filter((product) => {
      const haystack = productSearchText(product);
      return (
        haystack.includes("energiz") ||
        haystack.includes("energy") ||
        haystack.includes("taurina") ||
        haystack.includes("cafea") ||
        haystack.includes("coffee")
      );
    });

    if (highCaffeineProducts.length > 0) {
      filteredProducts = highCaffeineProducts;
    } else {
      const caffeineTaggedProducts = filteredProducts.filter((product) => {
        const haystack = productSearchText(product);
        return (
          (haystack.includes("caffeine") || haystack.includes("cafeina")) &&
          !haystack.includes("cola") &&
          !haystack.includes("water") &&
          !haystack.includes("apa")
        );
      });

      if (caffeineTaggedProducts.length > 0) {
        filteredProducts = caffeineTaggedProducts;
      }
    }
  }

  filteredProducts = filteredProducts.sort(
    (a, b) =>
      calculateAlternativeScore(filteredProducts, b, criteriaList) -
      calculateAlternativeScore(filteredProducts, a, criteriaList)
  );

  return dedupeProductList(filteredProducts, scannedProduct).slice(0, 18);
}

function AlternativesPageContent() {
  const searchParams = useSearchParams();

  const [user, setUser] = useState(null);
  const [products, setProducts] = useState([]);
  const [addedProduct, setAddedProduct] = useState("");
  const [favoriteProduct, setFavoriteProduct] = useState("");
  const [pendingCartProductKey, setPendingCartProductKey] = useState("");
  const [pendingFavoriteProductKey, setPendingFavoriteProductKey] = useState("");
  const [pendingReportProductKey, setPendingReportProductKey] = useState("");
  const [reportedProductKey, setReportedProductKey] = useState("");
  const [reportMessage, setReportMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [lookupNotice, setLookupNotice] = useState("");
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [scannedProduct, setScannedProduct] = useState(null);
  const [recommendationSource, setRecommendationSource] = useState("local");
  const [billing, setBilling] = useState(null);
  const [alternativeSearch, setAlternativeSearch] = useState("");
  const [showMoreAlternatives, setShowMoreAlternatives] = useState(false);
  const [profilePreferences, setProfilePreferences] = useState(null);

  const criteriaParam = searchParams.get("criteria") || "";
  const requestParam = searchParams.get("request") || "";
  const storeParam = searchParams.get("store") || "any";

  const storeName = getStoreName(storeParam);

  const selectedCriteriaIds = criteriaParam.split(",").filter(Boolean);
  const customRequest = decodeURIComponent(requestParam);
  const profileCriteriaIds = Array.isArray(profilePreferences?.criteria)
    ? profilePreferences.criteria
    : [];
  const profileGoalCriteriaIds = getCriteriaFromGoal(profilePreferences?.goal || "balanced");
  const profileRequest = profilePreferences?.request || "";
  const preferenceRequest = [customRequest, profileRequest].filter(Boolean).join(" ");

  const inferredCriteria = inferCriteriaFromRequest(preferenceRequest);

  const finalCriteriaIds = Array.from(
    new Set([
      ...profileCriteriaIds,
      ...profileGoalCriteriaIds,
      ...selectedCriteriaIds,
      ...inferredCriteria,
    ])
  );

  const selectedCriteria = finalCriteriaIds.map(
    (item) => criteriaLabels[item] || item
  );
  const selectedAllergyLabels = Array.isArray(profilePreferences?.allergies)
    ? profilePreferences.allergies
        .map((item) => allergyLabels[item] || item)
        .filter(Boolean)
    : [];
  const selectedAvoidIngredients = splitAvoidIngredients(profilePreferences?.avoidIngredients || "");

  const currentPlan = billing?.usage?.plan || "free";
  const isPaidPlan = currentPlan === "pro" || currentPlan === "family";
  const searchWarning = isPaidPlan
    ? validateAlternativeSearch(alternativeSearch)
    : "";
  const searchCriteriaIds =
    isPaidPlan && alternativeSearch.trim() && !searchWarning
      ? inferCriteriaFromRequest(alternativeSearch)
      : [];
  const combinedCriteriaIds = Array.from(
    new Set([...finalCriteriaIds, ...searchCriteriaIds])
  );
  const combinedCriteriaKey = combinedCriteriaIds.join(",");

  async function loadProducts(
    currentScannedProduct,
    criteriaIds = finalCriteriaIds,
    requestText = preferenceRequest
  ) {
    let externalLookupWarning = "";

    try {
      setLookupNotice("");

      if (currentScannedProduct) {
        try {
          const externalResponse = await fetch(
            `${API_URL}/alternatives/open-food-facts`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                product: currentScannedProduct,
                criteria: criteriaIds,
                request: requestText,
              }),
            }
          );
          const externalData = await readJsonResponse(
            externalResponse,
            "Open Food Facts"
          );

          if (
            externalResponse.ok &&
            Array.isArray(externalData.products) &&
            externalData.products.length > 0
          ) {
            setProducts(externalData.products);
            setRecommendationSource("openfoodfacts");
            setLookupNotice("");
            return;
          }

          externalLookupWarning =
            externalData.message ||
            "Open Food Facts nu a gasit suficiente variante pentru produsul scanat.";
        } catch (externalError) {
          externalLookupWarning = externalError.message;
        }

        setProducts([]);
        setRecommendationSource("openfoodfacts");
        setErrorMessage("");
        setLookupNotice(
          externalLookupWarning ||
            "Nu am gasit inca suficiente alternative externe pentru produsul scanat."
        );
        return;
      }

      const response = await fetch(`${API_URL}/products`);
      const data = await readJsonResponse(response, "Catalogul local");

      if (!response.ok) {
        throw new Error(data.error || "Nu s-au putut incarca produsele.");
      }

      setProducts(data);
      setRecommendationSource("local");
      setErrorMessage("");

      if (externalLookupWarning) {
        console.warn(externalLookupWarning);
      }
    } catch (error) {
      setErrorMessage(
        error.message ||
          "Nu am putut încărca recomandările. Reîncearcă în câteva secunde."
      );
    } finally {
      setIsLoadingProducts(false);
    }
  }
  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");

      if (savedUser) {
        setUser(JSON.parse(savedUser));
      }

      const savedResult = localStorage.getItem("cealeg_last_result");
      const activeProfile = getActiveProfile();
      const savedPreferences = readProfilePreferences(activeProfile?.id);

      if (savedPreferences) {
        setProfilePreferences(savedPreferences);
      }

      const parsedResult = savedResult ? JSON.parse(savedResult) : null;

      if (parsedResult) {
        setScannedProduct(parsedResult);
      }

      const savedProfileCriteriaIds = Array.isArray(savedPreferences?.criteria)
        ? savedPreferences.criteria
        : [];
      const savedGoalCriteriaIds = getCriteriaFromGoal(savedPreferences?.goal || "balanced");
      const savedPreferenceRequest = [
        customRequest,
        savedPreferences?.request || "",
      ]
        .filter(Boolean)
        .join(" ");
      const savedCriteriaIds = Array.from(
        new Set([
          ...savedProfileCriteriaIds,
          ...savedGoalCriteriaIds,
          ...selectedCriteriaIds,
          ...inferCriteriaFromRequest(savedPreferenceRequest),
        ])
      );

      loadProducts(parsedResult, savedCriteriaIds, savedPreferenceRequest);

      fetch(`${API_URL}/billing/status`)
        .then((response) => (response.ok ? response.json() : null))
        .then((data) => setBilling(data))
        .catch(() => setBilling(null));
    });

    function handleProfileChange(event) {
      const profile = event.detail || getActiveProfile();
      setProfilePreferences(readProfilePreferences(profile?.id));
      setShowMoreAlternatives(false);
    }

    window.addEventListener("cealeg:profile-change", handleProfileChange);
    return () => window.removeEventListener("cealeg:profile-change", handleProfileChange);
    // Produsele se incarca o singura data din rezultatul scanarii curente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!scannedProduct || !isPaidPlan || searchWarning) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      if (alternativeSearch.trim()) {
        setLookupNotice("Actualizam alternativele dupa cererea ta...");
        void loadProducts(scannedProduct, combinedCriteriaIds, alternativeSearch);
      } else {
        setLookupNotice("");
        void loadProducts(scannedProduct, finalCriteriaIds, preferenceRequest);
      }
    }, 450);

    return () => window.clearTimeout(timer);
    // Backend-ul trebuie apelat din nou cand textul Pro schimba criteriile.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alternativeSearch, searchWarning, scannedProduct, isPaidPlan, combinedCriteriaKey]);

  const rankedProducts = filterProductsByCriteria(
    products,
    storeName,
    combinedCriteriaIds,
    scannedProduct,
    profilePreferences
  );
  const recommendedProducts =
    isPaidPlan && alternativeSearch.trim() && !searchWarning
      ? filterProductsBySearch(rankedProducts, alternativeSearch)
      : rankedProducts;
  const initialAlternativeLimit = isPaidPlan ? 3 : 2;
  const visibleAlternativeLimit =
    isPaidPlan && showMoreAlternatives ? 6 : initialAlternativeLimit;
  const visibleProducts = recommendedProducts.slice(0, visibleAlternativeLimit);
  const canShowMoreAlternatives = isPaidPlan && recommendedProducts.length > 3;

  function getProductActionKey(product) {
    return String(product.barcode || product.id || product.name || "");
  }

  async function addToCart(product) {
    const actionKey = getProductActionKey(product);

    if (pendingCartProductKey === actionKey) return;

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");
    setPendingCartProductKey(actionKey);

    try {
      const response = await fetch(`${API_URL}/cart/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: product.name,
          store: storeName,
          score: product.score,
          price: product.priceText || product.price || "preț necunoscut",
          image: product.image || "",
          reason: product.reason || "Produs recomandat ca alternativă.",
          quantity: 1,
          ...getActiveProfilePayload(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut adăuga produsul în coș.");
      }

      setAddedProduct(`${product.name} - ${storeName}`);
      trackEvent("add_to_cart", {
        source: "alternatives",
        product: product.name,
        store: storeName,
      });
      window.dispatchEvent(new CustomEvent("cealeg:cart-updated"));

      setTimeout(() => {
        setAddedProduct("");
      }, 2500);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setPendingCartProductKey("");
    }
  }

  async function addToFavorites(product) {
    const actionKey = getProductActionKey(product);

    if (pendingFavoriteProductKey === actionKey) return;

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");
    setPendingFavoriteProductKey(actionKey);

    try {
      const response = await fetch(`${API_URL}/favorites/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: product.name,
          store: storeName,
          category: product.category,
          score: product.score,
          price: product.priceText || product.price || "preț necunoscut",
          image: product.image || "",
          reason: product.reason || "Produs recomandat ca alternativă.",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Nu s-a putut salva produsul la favorite."
        );
      }

      if (data.message === "Produsul este deja la favorite.") {
        setFavoriteProduct(`${product.name} este deja la favorite.`);
      } else {
        setFavoriteProduct(`${product.name} a fost salvat la favorite.`);
      }
      trackEvent("add_to_favorites", {
        source: "alternatives",
        product: product.name,
        store: storeName,
      });

      setTimeout(() => {
        setFavoriteProduct("");
      }, 2500);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setPendingFavoriteProductKey("");
    }
  }

  async function reportAlternative(product) {
    const actionKey = getProductActionKey(product);

    if (pendingReportProductKey === actionKey || reportedProductKey === actionKey) return;

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");
    setReportMessage("");
    setPendingReportProductKey(actionKey);

    try {
      const response = await fetch(`${API_URL}/feedback/alternative`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          product,
          scannedProduct,
          store: storeName,
          request: alternativeSearch || preferenceRequest || selectedCriteria.join(", "),
          reason: "wrong_recommendation",
        }),
      });
      const data = await readJsonResponse(response, "Raportare alternativă");

      if (!response.ok) {
        throw new Error(data.error || "Raportarea nu a putut fi trimisă.");
      }

      setReportedProductKey(actionKey);
      setReportMessage(data.message || "Raportarea a fost trimisă.");
      trackEvent("alternative_report", {
        source: "alternatives",
        product: product.name,
        scannedProduct: scannedProduct?.name || "",
        store: storeName,
      });

      setTimeout(() => setReportMessage(""), 3000);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setPendingReportProductKey("");
    }
  }

  if (isLoadingProducts) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">Pregătim recomandările potrivite...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel="Scanează alt produs" />
      <section className="ce-shell-lg ce-page">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href={`/result?store=${storeParam}`}
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> Înapoi la rezultat
          </Link>

          <div className="flex flex-col gap-3 sm:flex-row">
          <Link
              href="/favorites"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-yellow-300/30 px-5 py-3 text-center font-semibold text-yellow-300 hover:bg-yellow-300/10"
            >
              <Heart size={17} />
              Favorite
          </Link>

          <Link
              href="/cart"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
            >
              <ShoppingCart size={17} />
              Vezi coșul
          </Link>
          </div>
        </div>

        {addedProduct && (
          <div role="status" aria-live="polite" className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
            Produs adăugat în coș:{" "}
            <span className="font-bold">{addedProduct}</span>
          </div>
        )}

        {favoriteProduct && (
          <div role="status" aria-live="polite" className="mb-6 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4 text-yellow-300">
            {favoriteProduct}
          </div>
        )}

        {reportMessage && (
          <div role="status" aria-live="polite" className="mb-6 rounded-2xl border border-cyan-300/30 bg-cyan-300/10 p-4 text-cyan-100">
            {reportMessage}
          </div>
        )}

        {errorMessage && (
          <div role="alert" className="mb-6 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-red-300">
            {errorMessage}
          </div>
        )}

        {lookupNotice && (
          <div role="status" aria-live="polite" className="mb-6 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4 text-yellow-100">
            {lookupNotice}
          </div>
        )}

        <div className="mb-8">
          <p className="mb-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
            Alternative recomandate
          </p>

          <h1 className="text-4xl font-bold md:text-5xl">
            Variante mai bune pentru produsul scanat.
          </h1>

          <p className="mt-4 max-w-2xl text-gray-300">
            {recommendationSource === "openfoodfacts"
              ? lookupNotice
                ? "Căutăm alternative în surse externe și afișăm doar rezultate cu date suficiente pentru comparație."
                : "Alternativele sunt selectate din catalogul Open Food Facts și ordonate după preferințele tale."
              : "Scanează un produs ca să primești alternative externe comparabile."}
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-black/30 p-5">
              <p className="text-sm text-gray-400">Magazin selectat</p>
              <p className="mt-1 text-2xl font-bold text-emerald-300">
                {storeName}
              </p>
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/30 p-5">
              <p className="text-sm text-gray-400">Produs scanat</p>
              <p className="mt-1 text-2xl font-bold text-white">
                {scannedProduct?.name || "Produs selectat"}
              </p>
            </div>
          </div>

          {(selectedCriteria.length > 0 || selectedAllergyLabels.length > 0 || selectedAvoidIngredients.length > 0 || customRequest) && (
            <div className="mt-6 rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-5">
              <h2 className="font-bold text-emerald-300">Criterii folosite</h2>

              {selectedCriteria.length > 0 && (
                <>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selectedCriteria.map((criteria) => (
                      <span
                        key={criteria}
                        className="rounded-full bg-emerald-400 px-3 py-1 text-sm font-semibold text-black"
                      >
                        {criteria}
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 text-sm text-emerald-100">
                    Ordinea recomandărilor combină toate criteriile selectate.
                  </p>
                </>
              )}

              {(selectedAllergyLabels.length > 0 || selectedAvoidIngredients.length > 0) && (
                <div className="mt-4">
                  <p className="text-sm font-bold text-yellow-100">Filtre de siguranță</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedAllergyLabels.map((item) => (
                      <span key={item} className="rounded-full border border-yellow-300/25 bg-yellow-300/10 px-3 py-1 text-sm font-semibold text-yellow-100">
                        {item}
                      </span>
                    ))}
                    {selectedAvoidIngredients.map((item) => (
                      <span key={item} className="rounded-full border border-yellow-300/25 bg-yellow-300/10 px-3 py-1 text-sm font-semibold text-yellow-100">
                        Evită {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {customRequest && (
                <p className="mt-4 text-sm text-gray-200">
                  Cerință personalizată:{" "}
                  <span className="font-semibold text-white">
                    {customRequest}
                  </span>
                </p>
              )}

              {recommendationSource === "openfoodfacts" &&
                finalCriteriaIds.includes("cheap") && (
                  <p className="mt-4 text-sm text-yellow-200">
                    Folosim prețurile observate în Open Prices când sunt
                    disponibile. Pentru produsele fără raportări recente,
                    verifică prețul afișat în magazin.
                  </p>
                )}
            </div>
          )}

          <div className="mt-6 rounded-3xl border border-white/10 bg-[linear-gradient(135deg,rgba(16,185,129,0.12),rgba(250,204,21,0.08),rgba(15,23,42,0.18))] p-5 shadow-2xl">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-sm font-bold text-emerald-300">
                  {isPaidPlan ? "Căutare Pro" : "Planul tău Free"}
                </p>
                <h2 className="mt-1 text-2xl font-black">
                  {isPaidPlan
                    ? "Caută alternative potrivite."
                    : "Primele 2 alternative sunt incluse gratis."}
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-300">
                  {isPaidPlan
                    ? "Scrie ce contează pentru tine: mai ieftin, fără zahăr, proteină mai multă, ingrediente simple sau un magazin preferat."
                    : "Pentru mai multe recomandări și căutare după preferințe, treci pe Pro când ești pregătit."}
                </p>
              </div>

              {!isPaidPlan && (
                <Link
                  href="/pricing"
                  className="inline-flex justify-center rounded-xl bg-yellow-300 px-5 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-yellow-200"
                >
                  Vezi planurile
                </Link>
              )}
            </div>

            {isPaidPlan && (
              <div className="mt-5">
                <label className="sr-only" htmlFor="alternative-search">
                  Caută alternative
                </label>
                <input
                  id="alternative-search"
                  value={alternativeSearch}
                  onChange={(event) => {
                    setAlternativeSearch(event.target.value);
                    setShowMoreAlternatives(false);
                  }}
                  placeholder="Ex: fără zahăr, mai ieftin, mai multă proteină"
                  className="w-full rounded-2xl border border-white/10 bg-black/35 px-4 py-4 text-white outline-none transition placeholder:text-gray-500 focus:border-emerald-300 focus:ring-2 focus:ring-emerald-300/25"
                />
                {searchWarning && (
                  <p className="mt-3 rounded-xl border border-yellow-300/25 bg-yellow-300/10 px-4 py-3 text-sm text-yellow-100">
                    {searchWarning}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {visibleProducts.length === 0 ? (
          <div className="rounded-3xl border border-white/10 bg-black/30 p-8 text-center">
            <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-cyan-200">
              <Search size={32} />
            </span>
            <h2 className="mt-4 text-2xl font-bold">
              Nu am găsit alternative potrivite
            </h2>
            <p className="mt-3 text-gray-400">
              Nu există încă suficiente produse care să respecte toate
              criteriile selectate.
            </p>

            <Link
              href={`/result?store=${storeParam}`}
              className="mt-6 inline-block rounded-2xl bg-emerald-400 px-6 py-3 font-semibold text-black hover:bg-emerald-300"
            >
              Schimbă criteriile
            </Link>
          </div>
        ) : (
          <>
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {visibleProducts.map((product) => (
              <div
                key={product.barcode || product.id || product.name}
                className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-2xl transition hover:-translate-y-1 hover:bg-white/10"
              >
                <ProductImage
                  src={getImageUrl(product.image)}
                  alt={product.name}
                  containerClassName="h-44 w-full rounded-3xl"
                  imageClassName="object-contain p-4"
                  fallbackClassName="text-5xl"
                />

                <div className="mt-5 flex items-center justify-between gap-3">
                  <span className="rounded-full bg-emerald-400 px-3 py-1 text-sm font-bold text-black">
                    {formatScore(product.score)}/10
                  </span>

                  <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                    {product.tag}
                  </span>
                </div>

                <h2 className="mt-5 text-2xl font-bold">{product.name}</h2>

                {(product.brand || product.quantity) && (
                  <p className="mt-2 text-sm text-gray-400">
                    {[product.brand, product.quantity].filter(Boolean).join(" · ")}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  {product.nutriScore && (
                    <span className="rounded-full border border-white/10 px-3 py-1 text-gray-300">
                      Nutri-Score {String(product.nutriScore).toUpperCase()}
                    </span>
                  )}
                  {product.store === "Open Food Facts" && (
                    <span className="rounded-full border border-emerald-400/30 px-3 py-1 text-emerald-300">
                      Open Food Facts
                    </span>
                  )}
                </div>

                <p className="mt-2 text-sm font-semibold text-emerald-300">
                  {getPriceLabel(product)}
                </p>
                {getPriceDetails(product) && (
                  <p className="mt-1 text-xs text-gray-500">
                    {getPriceDetails(product)}
                  </p>
                )}

                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-xl bg-black/30 p-2">
                    <p className="text-gray-400">Prot.</p>
                    <p className="font-bold">{formatNutritionValue(product.protein)}g</p>
                    {getNutritionDifference(product, scannedProduct, "protein", true) && (
                      <p
                        className={
                          getNutritionDifference(product, scannedProduct, "protein", true).better
                            ? "mt-1 text-emerald-300"
                            : "mt-1 text-red-300"
                        }
                      >
                        {getNutritionDifference(product, scannedProduct, "protein", true).text}
                      </p>
                    )}
                  </div>

                  <div className="rounded-xl bg-black/30 p-2">
                    <p className="text-gray-400">Zahăr</p>
                    <p className="font-bold">{formatNutritionValue(product.sugar)}g</p>
                    {getNutritionDifference(product, scannedProduct, "sugar", false) && (
                      <p
                        className={
                          getNutritionDifference(product, scannedProduct, "sugar", false).better
                            ? "mt-1 text-emerald-300"
                            : "mt-1 text-red-300"
                        }
                      >
                        {getNutritionDifference(product, scannedProduct, "sugar", false).text}
                      </p>
                    )}
                  </div>

                  <div className="rounded-xl bg-black/30 p-2">
                    <p className="text-gray-400">Kcal</p>
                    <p className="font-bold">{formatNutritionValue(product.calories)}</p>
                    {getNutritionDifference(product, scannedProduct, "calories", false) && (
                      <p
                        className={
                          getNutritionDifference(product, scannedProduct, "calories", false).better
                            ? "mt-1 text-emerald-300"
                            : "mt-1 text-red-300"
                        }
                      >
                        {getNutritionDifference(product, scannedProduct, "calories", false).text}
                      </p>
                    )}
                  </div>
                </div>

                <ExpandableText
                  text={product.recommendationReason || product.reason}
                  className="mt-4 text-sm leading-6 text-gray-300"
                />

                <div className="mt-5 grid gap-3">
                  <button
                    onClick={() => addToCart(product)}
                    disabled={pendingCartProductKey === getProductActionKey(product)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100 disabled:cursor-wait disabled:opacity-70"
                  >
                    {pendingCartProductKey === getProductActionKey(product) ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <ShoppingCart size={18} />
                    )}
                    {pendingCartProductKey === getProductActionKey(product)
                      ? "Se adaugă..."
                      : "Adaugă în coș"}
                  </button>

                  <button
                    onClick={() => addToFavorites(product)}
                    disabled={pendingFavoriteProductKey === getProductActionKey(product)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-yellow-300/30 px-4 py-3 font-semibold text-yellow-300 transition hover:-translate-y-0.5 hover:bg-yellow-300/10 disabled:cursor-wait disabled:opacity-70"
                  >
                    {pendingFavoriteProductKey === getProductActionKey(product) ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Heart size={18} />
                    )}
                    {pendingFavoriteProductKey === getProductActionKey(product)
                      ? "Se salvează..."
                      : "Adaugă la favorite"}
                  </button>

                  <button
                    onClick={() => reportAlternative(product)}
                    disabled={
                      pendingReportProductKey === getProductActionKey(product) ||
                      reportedProductKey === getProductActionKey(product)
                    }
                    className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 px-4 py-3 text-sm font-bold text-gray-300 transition hover:-translate-y-0.5 hover:bg-white/10 hover:text-white disabled:cursor-default disabled:opacity-70"
                  >
                    {pendingReportProductKey === getProductActionKey(product) ? (
                      <Loader2 size={17} className="animate-spin" />
                    ) : (
                      <Flag size={17} />
                    )}
                    {reportedProductKey === getProductActionKey(product)
                      ? "Raportat"
                      : pendingReportProductKey === getProductActionKey(product)
                        ? "Se trimite..."
                        : "Nu se potrivește"}
                  </button>
                </div>
              </div>
            ))}
            </div>

            <div className="mt-7 flex flex-col items-center gap-3">
              {canShowMoreAlternatives && (
                <button
                  type="button"
                  onClick={() => setShowMoreAlternatives((value) => !value)}
                  className="rounded-2xl border border-emerald-300/30 bg-emerald-400/10 px-6 py-3 font-black text-emerald-200 transition hover:-translate-y-0.5 hover:bg-emerald-400/20"
                >
                  {showMoreAlternatives ? "Arata mai putine" : "Afiseaza mai multe"}
                </button>
              )}

              {!isPaidPlan && recommendedProducts.length > visibleProducts.length && (
                <p className="max-w-xl text-center text-sm text-gray-400">
                  Free arata 2 alternative. Pro deblocheaza mai multe rezultate
                  și căutarea după preferințe.
                </p>
              )}
            </div>
          </>
        )}

        {visibleProducts.length > 0 && (
          <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-6">
            <h2 className="text-2xl font-bold">Comparație rapidă</h2>

            <div className="mt-5 overflow-x-auto rounded-2xl border border-white/10">
              <div className="grid min-w-[680px] grid-cols-4 bg-white/10 p-4 text-sm font-bold text-gray-200">
                <span>Produs</span>
                <span>Scor</span>
                <span>Avantaj</span>
                <span>Preț disponibil</span>
              </div>

              {visibleProducts.map((product) => (
                <div
                  key={(product.barcode || product.id || product.name) + "-row"}
                  className="grid min-w-[680px] grid-cols-4 border-t border-white/10 p-4 text-sm text-gray-300"
                >
                  <span>{product.name}</span>
                  <span>{formatScore(product.score)}/10</span>
                  <span>{product.tag}</span>
                  <span>{getPriceLabel(product)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

export default function AlternativesPage() {
  return (
    <Suspense fallback={null}>
      <AlternativesPageContent />
    </Suspense>
  );
}

