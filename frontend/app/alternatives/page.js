"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Flag, Heart, Loader2, Search, ShoppingCart, Shuffle } from "lucide-react";
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
  different_flavor: "altă aromă",
  value: "raport calitate-preț mai bun",
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
  if (text.includes("snacks")) return "salty_snack";
  if (text.includes("bauturi")) return "beverage";
  if (text.includes("carne")) return "meat";
  if (text.includes("paste")) return "pasta";
  if (text.includes("noodles") || text.includes("taitei")) return "instant_noodles";
  if (text.includes("bere")) return "beer";
  if (text.includes("iaurt")) return "plain_yogurt";
  if (text.includes("sos")) return "sauce";

  return text;
}

function getProductFamily(product) {
  const text = productSearchText(product);
  const hasAny = (tokens) => tokens.some((token) => text.includes(normalizeText(token)));
  const labelText = normalizeText(
    [product.name, product.brand, product.category, product.store, product.tag, product.nutriScore]
      .filter(Boolean)
      .join(" ")
  );
  const labelHasAny = (tokens) => tokens.some((token) => labelText.includes(normalizeText(token)));

  if (hasAny(["buldak", "samyang", "shin ramyun", "ramen", "instant noodles", "taitei instant", "tăiței instant", "cup noodles", "noodles cup", "tăiței la pahar", "taitei la pahar"])) {
    if (hasAny(["cup noodles", "noodles cup", "tăiței la pahar", "taitei la pahar"])) {
      return "cup_noodles";
    }

    return "ramen_noodles";
  }

  if (hasAny(["ice coffee", "iced coffee", "cafea", "coffee", "cappuccino", "capuccino", "latte", "mocha", "espresso", "cold brew", "frappe"])) {
    return "coffee_drink";
  }

  const priorityRules = [
    ["sparkling_water", ["apă minerală", "apa minerala", "apă carbogazoasă", "apa carbogazoasa", "sparkling water", "mineral water"]],
    ["still_water", ["apă plată", "apa plata", "still water", "spring water"]],
    ["flavoured_water", ["apă aromată", "apa aromata", "flavoured water", "flavored water", "vitamin water"]],
    ["zero_energy_drink", ["red bull zero", "redbull zero", "monster zero", "monster ultra", "hell zero", "energy zero", "zero sugar energy", "energizant zero"]],
    ["energy_shot", ["energy shot", "shot energizant"]],
    ["cola_zero", ["cola zero", "coke zero", "coca cola zero", "coca-cola zero", "pepsi max", "pepsi zero"]],
    ["cola_regular", ["coca cola", "coca-cola", "cocacola", "pepsi", "cola original"]],
    ["orange_soda", ["fanta", "mirinda", "orange soda", "băutură portocale", "bautura portocale"]],
    ["lemon_lime_soda", ["sprite", "7up", "seven up", "lemon lime", "băutură lămâie", "bautura lamaie"]],
    ["tonic_soda", ["schweppes", "tonic", "bitter lemon"]],
    ["lemonade", ["limonadă", "limonada", "lemonade"]],
    ["iced_tea", ["ice tea", "iced tea", "ceai rece", "fuzetea", "lipton"]],
    ["kombucha", ["kombucha"]],
    ["cocoa_drink", ["cacao băutură", "cacao bautura", "hot chocolate", "ciocolată caldă", "ciocolata calda", "choco drink"]],
    ["drinkable_yogurt", ["iaurt de băut", "iaurt de baut", "drinkable yogurt", "yogurt drink", "actimel"]],
    ["protein_yogurt", ["iaurt proteic", "protein yogurt", "skyr proteic", "high protein yogurt"]],
    ["greek_yogurt", ["iaurt grecesc", "greek yogurt"]],
    ["sour_cream", ["smântână", "smantana", "sour cream"]],
    ["whipped_cream", ["frișcă", "frisca", "whipping cream", "hulala", "spray cream"]],
    ["cheese_spread", ["cremă de brânză", "crema de branza", "cream cheese", "tartinabil"]],
    ["processed_cheese", ["brânză topită", "branza topita", "processed cheese"]],
    ["hard_cheese", ["cașcaval", "cascaval", "cheddar", "gouda", "emmental", "parmesan"]],
    ["soft_cheese", ["mozzarella", "brie", "camembert", "mascarpone"]],
    ["feta_telemea", ["telemea", "feta"]],
    ["milk_chocolate", ["ciocolată cu lapte", "ciocolata cu lapte", "milk chocolate"]],
    ["dark_chocolate", ["ciocolată neagră", "ciocolata neagra", "dark chocolate", "amăruie", "amaruie"]],
    ["white_chocolate", ["ciocolată albă", "ciocolata alba", "white chocolate"]],
    ["filled_chocolate", ["ciocolată umplută", "ciocolata umpluta", "filled chocolate", "praline"]],
    ["wafers", ["napolitană", "napolitana", "wafer", "wafers"]],
    ["cookies", ["cookies", "biscuiți", "biscuiti", "biscuit"]],
    ["croissant", ["croissant"]],
    ["sweet_bakery", ["gogoașă", "gogoasa", "brioche", "cozonac", "chec", "muffin", "brownie"]],
    ["cereal_bar", ["baton cereale", "baton cu cereale", "cereal bar"]],
    ["protein_bar", ["baton proteic", "protein bar"]],
    ["potato_chips", ["chips cartofi", "cartofi chips", "potato chips", "lays", "lay's", "pringles"]],
    ["tortilla_chips", ["tortilla chips", "nachos", "doritos"]],
    ["puffs", ["pufuleți", "pufuleti", "porumb expandat", "snack porumb"]],
    ["pretzels", ["covrigei", "pretzels", "sticks", "sărățele", "saratele"]],
    ["roasted_nuts", ["arahide prăjite", "arahide prajite", "alune prăjite", "alune prajite", "migdale", "caju", "fistic"]],
    ["dried_fruit", ["fructe uscate", "stafide", "curmale", "prune uscate", "dried fruit"]],
    ["tomato_sauce", ["sos de roșii", "sos de rosii", "tomato sauce", "passata", "bulion"]],
    ["hot_sauce", ["sos iute", "hot sauce", "chili sauce", "sriracha", "tabasco"]],
    ["soy_sauce", ["sos de soia", "soy sauce"]],
    ["salad_dressing", ["dressing", "salad dressing", "vinegret"]],
    ["pesto_sauce", ["pesto"]],
    ["pasta_sauce", ["sos paste", "sos pentru paste", "pasta sauce", "bolognese", "carbonara"]],
    ["olive_oil", ["ulei de măsline", "ulei de masline", "olive oil"]],
    ["sunflower_oil", ["ulei de floarea soarelui", "sunflower oil"]],
    ["tomato_canned", ["conservă roșii", "conserva rosii", "canned tomatoes", "roșii cuburi", "rosii cuburi"]],
    ["corn_canned", ["conservă porumb", "conserva porumb", "canned corn", "porumb dulce"]],
    ["bean_canned", ["conservă fasole", "conserva fasole", "canned beans"]],
    ["tuna_canned", ["conservă ton", "conserva ton", "canned tuna", "ton conservă", "ton conserva"]],
    ["pate", ["pate", "pateu"]],
    ["olives", ["măsline", "masline", "olives"]],
    ["pickled_cucumbers", ["castraveți murați", "castraveti murati", "pickled cucumbers"]],
    ["spaghetti_pasta", ["spaghetti", "spaghete"]],
    ["short_pasta", ["penne", "fusilli", "farfalle", "macaroni", "macaroane"]],
    ["basmati_rice", ["basmati"]],
    ["round_rice", ["orez bob rotund", "round rice", "risotto"]],
    ["wheat_flour", ["făină albă", "faina alba", "wheat flour", "făină grâu", "faina grau"]],
    ["cornmeal", ["mălai", "malai", "cornmeal"]],
    ["cocoa_powder", ["cacao pudră", "cacao pudra", "cocoa powder"]],
    ["yeast_baking", ["drojdie", "yeast", "praf de copt", "baking powder"]],
    ["salami", ["salam", "salami"]],
    ["ham", ["mușchi file", "muschi file", "șuncă", "sunca", "ham", "jambon", "prosciutto"]],
    ["sausages", ["cârnați", "carnati", "sausage", "cremvurști", "crenvursti"]],
    ["chicken_meat", ["pui", "chicken"]],
    ["pork_meat", ["porc", "pork"]],
    ["beef_meat", ["vită", "vita", "beef"]],
    ["turkey_meat", ["curcan", "turkey"]],
    ["minced_meat", ["carne tocată", "carne tocata", "minced meat"]],
    ["smoked_fish", ["pește afumat", "peste afumat", "smoked fish", "somon afumat"]],
    ["frozen_fries", ["cartofi congelați", "cartofi congelati", "frozen fries"]],
    ["frozen_pizza", ["pizza congelată", "pizza congelata", "frozen pizza"]],
    ["ready_pasta", ["paste gata", "ready pasta", "pasta salad"]],
    ["ready_salad", ["salată gata", "salata gata", "ready salad"]],
    ["hummus", ["hummus", "humus"]],
    ["baby_puree_fruit", ["piure fructe bebeluși", "piure fructe bebelusi", "baby fruit puree"]],
    ["baby_puree_vegetable", ["piure legume bebeluși", "piure legume bebelusi", "baby vegetable puree"]],
  ];
  priorityRules.push(
    ["apple_juice", ["suc de mere", "apple juice"]],
    ["orange_juice", ["suc de portocale", "orange juice"]],
    ["multivitamin_juice", ["multivitamin", "multi vitamin", "suc multifruct", "suc tropical"]],
    ["smoothie", ["smoothie"]],
    ["nectar", ["nectar"]],
    ["isotonic_drink", ["isotonic", "izotonic", "gatorade", "powerade", "sport drink", "sports drink"]],
    ["alcohol_free_beer", ["bere fără alcool", "bere fara alcool", "non alcoholic beer", "alcohol free beer", "0.0 beer", "0,0 beer"]],
    ["radler_beer", ["radler"]],
    ["lager_beer", ["lager", "pilsner", "pils", "bere blondă", "bere blonda"]],
    ["wheat_beer", ["bere nefiltrată", "bere nefiltrata", "weissbier", "weizen", "wheat beer"]],
    ["dark_beer", ["bere brună", "bere bruna", "dark beer", "stout", "porter"]],
    ["uht_milk", ["lapte uht", "uht milk"]],
    ["lactose_free_milk", ["lapte fără lactoză", "lapte fara lactoza", "lactose free milk"]],
    ["oat_milk", ["băutură ovăz", "bautura ovaz", "lapte ovăz", "lapte ovaz", "oat drink", "oat milk"]],
    ["almond_milk", ["băutură migdale", "bautura migdale", "lapte migdale", "almond drink", "almond milk"]],
    ["soy_milk", ["băutură soia", "bautura soia", "lapte soia", "soy drink", "soy milk"]],
    ["kefir", ["kefir", "chefir", "sana", "lapte bătut", "lapte batut"]],
    ["protein_pudding", ["budincă proteică", "budinca proteica", "protein pudding"]],
    ["pudding", ["budincă", "budinca", "pudding", "danette"]],
    ["rice_pudding", ["orez cu lapte", "rice pudding"]],
    ["custard_dessert", ["cremă desert", "crema desert", "custard"]],
    ["ice_cream_bar", ["înghețată baton", "inghetata baton", "ice cream bar", "magnum"]],
    ["ice_cream_cone", ["înghețată cornet", "inghetata cornet", "ice cream cone", "cornet"]],
    ["ice_cream_cup", ["înghețată cupă", "inghetata cupa", "ice cream cup", "gelatelli"]],
    ["sorbet", ["sorbet"]],
    ["cornflakes", ["corn flakes", "fulgi de porumb"]],
    ["muesli", ["muesli", "musli"]],
    ["granola", ["granola"]],
    ["oats", ["ovăz", "ovaz", "oat flakes", "fulgi de ovăz", "fulgi de ovaz"]],
    ["rice_cakes", ["rondele orez", "rice cakes", "puffed rice cakes"]],
    ["sunflower_seeds", ["semințe floarea soarelui", "seminte floarea soarelui", "sunflower seeds"]],
    ["pumpkin_seeds", ["semințe dovleac", "seminte dovleac", "pumpkin seeds"]],
    ["trail_mix", ["mix fructe uscate", "trail mix", "student mix"]],
    ["bbq_sauce", ["sos barbeque", "sos barbecue", "bbq sauce"]],
    ["garlic_sauce", ["sos usturoi", "garlic sauce"]],
    ["salsa_sauce", ["salsa", "chunky salsa"]],
    ["sweet_chili_sauce", ["sweet chili", "sos chili dulce"]],
    ["dijon_mustard", ["dijon"]],
    ["light_mayonnaise", ["maioneză light", "maioneza light", "light mayonnaise"]],
    ["salt", ["sare", "salt"]],
    ["pepper", ["piper", "pepper"]],
    ["paprika", ["boia", "paprika"]],
    ["spice_mix", ["mix condimente", "amestec condimente", "seasoning mix", "condimente pentru"]],
    ["stock_cube", ["cub supă", "cub supa", "stock cube", "bouillon"]],
    ["toast_bread", ["pâine toast", "paine toast", "toast bread"]],
    ["sliced_bread", ["pâine feliată", "paine feliata", "sliced bread"]],
    ["wholegrain_bread", ["pâine integrală", "paine integrala", "wholegrain bread", "whole wheat bread"]],
    ["buns", ["chifle", "burger buns", "hot dog buns"]],
    ["tortilla_wrap", ["tortilla wrap", "lipie", "wrap"]],
    ["cup_noodles", ["cup noodles", "noodles cup", "tăiței la pahar", "taitei la pahar"]],
    ["ramen_noodles", ["ramen", "buldak", "samyang", "shin ramyun"]],
    ["whey_protein", ["whey protein", "proteină zer", "proteina zer", "protein powder", "pudră proteică", "pudra proteica"]],
    ["canned_sardines", ["sardine", "sardines"]],
    ["canned_mackerel", ["macrou conservă", "macrou conserva", "canned mackerel"]],
    ["canned_peas", ["mazăre conservă", "mazare conserva", "canned peas"]],
    ["canned_chickpeas", ["năut conservă", "naut conserva", "canned chickpeas"]],
    ["canned_lentils", ["linte conservă", "linte conserva", "canned lentils"]],
    ["vegetable_spread", ["pastă vegetală", "pasta vegetala", "vegetable spread", "zacuscă", "zacusca"]],
    ["jam", ["gem", "dulceață", "dulceata", "marmeladă", "marmelada"]],
    ["honey", ["miere", "honey"]],
    ["frozen_fruit", ["fructe congelate", "frozen fruit"]],
    ["frozen_vegetable_mix", ["mix legume congelate", "amestec legume congelate", "frozen vegetable mix"]],
    ["frozen_dessert", ["desert congelat", "frozen dessert"]],
    ["baby_biscuits", ["biscuiți bebeluși", "biscuiti bebelusi", "baby biscuits"]],
    ["baby_snack", ["snack bebeluși", "snack bebelusi", "baby snack"]]
  );

  for (const [family, tokens] of priorityRules) {
    const labelOnlyFamilies = new Set([
      "sparkling_water",
      "still_water",
      "olive_oil",
      "sunflower_oil",
      "wheat_flour",
      "cornmeal",
      "cocoa_powder",
      "yeast_baking",
    ]);
    const source = labelOnlyFamilies.has(family) ? labelText : text;

    if (tokens.some((token) => source.includes(normalizeText(token)))) {
      return family;
    }
  }

  if (hasAny(["buldak", "samyang", "noodle", "noodles", "ramen", "taitei"])) return "instant_noodles";
  if (hasAny(["bere", "beer", "ursus", "ciuc", "bergenbier", "heineken", "lager", "pilsner"])) return "beer";
  if (hasAny(["alcool", "alcohol", "vin", "wine", "vodka", "whisky", "cidru"])) return "alcoholic_drink";
  if (labelHasAny(["cafea boabe", "cafea macinata", "ground coffee", "coffee beans", "instant coffee", "capsule cafea"])) return "coffee_beans";
  if (labelHasAny(["ceai plic", "ceai plante", "ceai negru", "ceai verde", "herbal tea", "tea bags", "infuzie"]) && !labelHasAny(["ice tea", "iced tea", "ceai rece"])) return "tea_bags";
  if (labelHasAny(["apa aromata", "flavoured water", "flavored water", "vitamin water"])) return "flavoured_water";
  if (/\b(apa|water|mineral)\b/.test(labelText) && !labelHasAny(["energy", "energiz", "coffee", "cafea", "cola", "pepsi", "bere", "beer"])) return "water";
  if (hasAny(["energy", "energiz", "taurina", "red bull", "redbull", "monster", "hell"])) return "energy_drink";
  if (hasAny(["cafea", "coffee", "cappuccino", "latte", "espresso", "iced coffee"])) return "coffee_drink";
  if (hasAny(["cola", "pepsi", "coca-cola", "cocacola"])) return "cola";
  if (hasAny(["fanta", "sprite", "mirinda", "schweppes", "tonic", "7up", "soft drink", "bautura carbogazoasa"])) return "carbonated_soft_drink";
  if (hasAny(["suc", "juice", "nectar", "smoothie"])) return "fruit_juice";
  if (hasAny(["ice tea", "iced tea", "ceai rece", "kombucha"])) return "tea_drink";
  if (hasAny(["sport drink", "isotonic", "gatorade", "powerade"])) return "sports_drink";
  if (hasAny(["sirop", "syrup", "concentrat"])) return "syrup_concentrate";
  if (text.includes("iaurt cu fruct") || text.includes("fruit yogurt") || (text.includes("iaurt") && text.includes("fruct"))) return "fruit_yogurt";
  if (hasAny(["iaurt", "yogurt", "yoghurt", "skyr"])) return "plain_yogurt";
  if (hasAny(["kefir", "chefir", "sana", "lapte batut"])) return "kefir";
  if (labelHasAny(["unt", "butter"])) return "butter";
  if (labelHasAny(["smantana", "sour cream", "frisca", "whipping cream", "cooking cream"])) return "cream";
  if (hasAny(["branza de vaci", "branza proaspata", "cottage cheese", "ricotta", "urda"])) return "cottage_cheese";
  if (hasAny(["branza", "branzeturi", "cascaval", "mozzarella", "telemea", "cheese"])) return "cheese";
  if (hasAny(["lapte vegetal", "bautura vegetala", "oat drink", "almond drink", "soy drink"])) return "plant_milk";
  if (hasAny(["iaurt vegetal", "plant yogurt", "soy yogurt"])) return "plant_yogurt";
  if (hasAny(["lapte", "milk"])) return "milk";
  if (hasAny(["muschi file", "sunca", "ham", "salam", "prosciutto", "bacon", "parizer"])) return "processed_meat";
  if (hasAny(["carne", "porc", "pui", "curcan", "beef", "chicken"])) return "fresh_meat";
  if (labelHasAny(["peste congelat", "frozen fish", "fish fingers"])) return "frozen_fish";
  if (labelHasAny(["carne congelata", "frozen meat"])) return "frozen_meat";
  if (labelHasAny(["legume congelate", "frozen vegetables"])) return "frozen_vegetable";
  if (hasAny(["conserva ton", "canned tuna", "sardine conserva"])) return "canned_fish";
  if (hasAny(["peste", "fish", "ton", "tuna", "somon", "salmon"])) return "fish";
  if (hasAny(["oua", "egg"])) return "eggs";
  if (hasAny(["nutella", "chocolate spread", "hazelnut spread"])) return "chocolate_spread";
  if (hasAny(["peanut butter", "unt arahide", "unt de arahide"])) return "peanut_butter";
  if (hasAny(["gem", "dulceata", "miere", "honey"])) return "jam_honey";
  if (hasAny(["ciocolata", "chocolate", "praline"])) return "chocolate";
  if (hasAny(["biscuit", "wafer", "napolit"])) return "biscuits_wafers";
  if (hasAny(["bomboane", "candy", "jeleuri"])) return "candy";
  if (hasAny(["prajitura", "chec", "cake", "muffin", "brownie"])) return "cakes";
  if (hasAny(["chips", "crisps", "nachos"])) return "chips";
  if (hasAny(["crackers", "covrigei", "sticks"])) return "crackers";
  if (text.includes("popcorn")) return "popcorn";
  if (hasAny(["inghetata", "ice cream", "gelato"])) return "ice_cream";
  if (hasAny(["ketchup"])) return "ketchup";
  if (hasAny(["mustar", "mustard"])) return "mustard";
  if (hasAny(["maioneza", "mayonnaise"])) return "mayonnaise";
  if (hasAny(["sos", "sauce", "salsa", "dressing", "pesto"])) return "sauce";
  if (labelHasAny(["ulei", "olive oil", "sunflower oil"])) return "oil";
  if (labelHasAny(["otet", "vinegar"])) return "vinegar";
  if (labelHasAny(["condiment", "spice", "boia", "piper", "sare"])) return "spices";
  if (hasAny(["ovaz", "oat", "granola", "muesli"])) return "oats_granola";
  if (hasAny(["cereale", "cereal", "corn flakes"])) return "breakfast_cereal";
  if (hasAny(["paste", "pasta", "spaghetti", "penne"])) return "pasta";
  if (hasAny(["orez", "rice", "basmati"])) return "rice";
  if (hasAny(["fasole", "linte", "naut", "chickpeas"])) return "legumes";
  if (hasAny(["conserva porumb", "conserva rosii", "canned tomatoes"])) return "canned_vegetables";
  if (hasAny(["muraturi", "masline", "pickles", "olives"])) return "pickles_olives";
  if (hasAny(["conserva", "canned"])) return "canned_pickles";
  if (labelHasAny(["faina", "flour", "malai", "drojdie", "praf de copt"])) return "flour_baking";
  if (labelHasAny(["zahar", "indulcitor", "sweetener", "stevia"])) return "sugar_sweetener";
  if (hasAny(["croissant", "patiserie", "foietaj"])) return "bakery_pastry";
  if (hasAny(["paine", "bread", "toast", "bagheta"])) return "bread";
  if (hasAny(["supa", "soup", "ciorba"])) return "ready_soup";
  if (hasAny(["sandwich", "salata", "wrap"])) return "sandwich_salad";
  if (text.includes("pizza")) return "pizza";
  if (hasAny(["frozen", "congelat"])) return "frozen";
  if (labelHasAny(["mere", "banane", "portocale", "fructe proaspete"])) return "fresh_fruit";
  if (labelHasAny(["rosii", "tomate", "castraveti", "cartofi", "morcovi", "legume proaspete"])) return "fresh_vegetable";
  if (hasAny(["spread", "crema tartinabila"])) return "spread";
  if (hasAny(["nuci", "alune", "nuts", "seeds", "seminte"])) return "nuts";
  if (hasAny(["lapte praf bebelusi", "infant formula", "baby formula"])) return "baby_formula";
  if (hasAny(["piure bebelusi", "baby puree"])) return "baby_puree";
  if (hasAny(["baby", "bebelus"])) return "baby_food";

  return normalizeCategory(product.category || "");
}

const familyCompatibility = {
  water: ["water"],
  flavoured_water: ["flavoured_water", "water"],
  fruit_juice: ["fruit_juice"],
  tea_drink: ["tea_drink", "fruit_juice"],
  tea_bags: ["tea_bags"],
  sports_drink: ["sports_drink", "energy_drink"],
  carbonated_soft_drink: ["carbonated_soft_drink", "cola"],
  syrup_concentrate: ["syrup_concentrate"],
  cola: ["cola"],
  energy_drink: ["energy_drink", "coffee_drink", "caffeinated_beverage"],
  coffee_drink: ["coffee_drink", "energy_drink", "caffeinated_beverage"],
  coffee_beans: ["coffee_beans"],
  caffeinated_beverage: ["coffee_drink", "energy_drink", "caffeinated_beverage"],
  beer: ["beer"],
  alcoholic_drink: ["alcoholic_drink", "beer"],
  fruit_yogurt: ["fruit_yogurt", "plain_yogurt", "kefir", "plant_yogurt"],
  plain_yogurt: ["plain_yogurt", "fruit_yogurt", "kefir", "plant_yogurt"],
  kefir: ["kefir", "plain_yogurt"],
  butter: ["butter"],
  cream: ["cream"],
  cottage_cheese: ["cottage_cheese", "cheese"],
  cheese: ["cheese"],
  milk: ["milk", "plant_milk", "kefir"],
  plant_milk: ["plant_milk", "milk"],
  plant_yogurt: ["plant_yogurt", "plain_yogurt", "fruit_yogurt"],
  chips: ["chips", "crackers", "popcorn", "salty_snack"],
  crackers: ["crackers", "chips", "popcorn", "salty_snack"],
  popcorn: ["popcorn", "chips", "crackers", "salty_snack"],
  chocolate: ["chocolate"],
  biscuits_wafers: ["biscuits_wafers"],
  candy: ["candy"],
  cakes: ["cakes", "bakery_pastry"],
  breakfast_cereal: ["breakfast_cereal", "oats_granola", "cereal"],
  oats_granola: ["oats_granola", "breakfast_cereal", "cereal"],
  sauce: ["sauce"],
  ketchup: ["ketchup", "mustard", "mayonnaise", "sauce"],
  mustard: ["mustard", "ketchup", "mayonnaise", "sauce"],
  mayonnaise: ["mayonnaise", "ketchup", "mustard", "sauce"],
  oil: ["oil"],
  vinegar: ["vinegar"],
  spices: ["spices"],
  pasta_rice_legumes: ["pasta_rice_legumes", "pasta", "rice", "legumes"],
  pasta: ["pasta"],
  rice: ["rice"],
  legumes: ["legumes"],
  flour_baking: ["flour_baking"],
  sugar_sweetener: ["sugar_sweetener"],
  canned_fish: ["canned_fish", "fish"],
  canned_meat: ["canned_meat", "processed_meat"],
  canned_vegetables: ["canned_vegetables", "pickles_olives"],
  pickles_olives: ["pickles_olives", "canned_vegetables"],
  canned_pickles: ["canned_pickles", "canned_vegetables", "pickles_olives"],
  processed_meat: ["processed_meat"],
  fresh_meat: ["fresh_meat"],
  meat: ["meat", "processed_meat", "fresh_meat"],
  fish: ["fish"],
  eggs: ["eggs"],
  bread: ["bread"],
  bakery_pastry: ["bakery_pastry"],
  ready_soup: ["ready_soup"],
  sandwich_salad: ["sandwich_salad"],
  pizza: ["pizza"],
  frozen: ["frozen", "frozen_vegetable", "frozen_fish", "frozen_meat"],
  frozen_vegetable: ["frozen_vegetable", "frozen"],
  frozen_fish: ["frozen_fish", "fish"],
  frozen_meat: ["frozen_meat", "fresh_meat"],
  fresh_fruit: ["fresh_fruit", "fruit_vegetable"],
  fresh_vegetable: ["fresh_vegetable", "fruit_vegetable"],
  fruit_vegetable: ["fruit_vegetable", "fresh_fruit", "fresh_vegetable"],
  chocolate_spread: ["chocolate_spread", "spread"],
  peanut_butter: ["peanut_butter", "spread", "nuts"],
  jam_honey: ["jam_honey", "spread"],
  spread: ["spread", "chocolate_spread", "peanut_butter", "jam_honey"],
  nuts: ["nuts"],
  baby_food: ["baby_food", "baby_formula", "baby_puree"],
  baby_formula: ["baby_formula"],
  baby_puree: ["baby_puree", "baby_food"],
  instant_noodles: ["instant_noodles"],
};

Object.assign(familyCompatibility, {
  still_water: ["still_water", "water"],
  sparkling_water: ["sparkling_water", "water"],
  lemonade: ["lemonade", "fruit_juice", "carbonated_soft_drink"],
  iced_tea: ["iced_tea", "tea_drink"],
  kombucha: ["kombucha", "tea_drink"],
  orange_soda: ["orange_soda", "carbonated_soft_drink"],
  lemon_lime_soda: ["lemon_lime_soda", "carbonated_soft_drink"],
  tonic_soda: ["tonic_soda", "carbonated_soft_drink"],
  cola_zero: ["cola_zero", "cola", "cola_regular", "zero_energy_drink"],
  cola_regular: ["cola_regular", "cola", "cola_zero"],
  zero_energy_drink: ["zero_energy_drink", "energy_drink", "energy_shot", "caffeinated_beverage", "cola_zero"],
  energy_shot: ["energy_shot", "zero_energy_drink", "energy_drink", "caffeinated_beverage"],
  cocoa_drink: ["cocoa_drink", "coffee_drink", "milk"],
  drinkable_yogurt: ["drinkable_yogurt", "fruit_yogurt", "plain_yogurt", "kefir", "plant_yogurt"],
  protein_yogurt: ["protein_yogurt", "greek_yogurt", "plain_yogurt", "fruit_yogurt", "plant_yogurt"],
  greek_yogurt: ["greek_yogurt", "plain_yogurt", "protein_yogurt", "fruit_yogurt"],
  sour_cream: ["sour_cream", "cream"],
  whipped_cream: ["whipped_cream", "cream"],
  cheese_spread: ["cheese_spread", "processed_cheese", "cheese"],
  processed_cheese: ["processed_cheese", "cheese_spread", "cheese"],
  hard_cheese: ["hard_cheese", "cheese"],
  soft_cheese: ["soft_cheese", "cheese"],
  feta_telemea: ["feta_telemea", "cheese"],
  milk_chocolate: ["milk_chocolate", "filled_chocolate", "chocolate"],
  dark_chocolate: ["dark_chocolate", "chocolate"],
  white_chocolate: ["white_chocolate", "filled_chocolate", "chocolate"],
  filled_chocolate: ["filled_chocolate", "milk_chocolate", "white_chocolate", "chocolate"],
  wafers: ["wafers", "biscuits_wafers", "cookies"],
  cookies: ["cookies", "biscuits_wafers", "wafers"],
  croissant: ["croissant", "sweet_bakery", "bakery_pastry"],
  sweet_bakery: ["sweet_bakery", "croissant", "cakes", "bakery_pastry"],
  cereal_bar: ["cereal_bar", "protein_bar", "breakfast_cereal"],
  protein_bar: ["protein_bar", "cereal_bar", "protein"],
  potato_chips: ["potato_chips", "chips"],
  tortilla_chips: ["tortilla_chips", "chips"],
  puffs: ["puffs", "salty_snack"],
  pretzels: ["pretzels", "crackers", "salty_snack"],
  roasted_nuts: ["roasted_nuts", "nuts"],
  dried_fruit: ["dried_fruit", "nuts"],
  tomato_sauce: ["tomato_sauce", "pasta_sauce", "sauce"],
  hot_sauce: ["hot_sauce", "sauce"],
  soy_sauce: ["soy_sauce", "sauce"],
  salad_dressing: ["salad_dressing", "sauce"],
  pesto_sauce: ["pesto_sauce", "pasta_sauce", "sauce"],
  pasta_sauce: ["pasta_sauce", "tomato_sauce", "pesto_sauce", "sauce"],
  olive_oil: ["olive_oil", "oil"],
  sunflower_oil: ["sunflower_oil", "oil"],
  spaghetti_pasta: ["spaghetti_pasta", "short_pasta", "pasta"],
  short_pasta: ["short_pasta", "spaghetti_pasta", "pasta"],
  basmati_rice: ["basmati_rice", "rice"],
  round_rice: ["round_rice", "rice"],
  wheat_flour: ["wheat_flour", "flour_baking"],
  cornmeal: ["cornmeal", "flour_baking"],
  cocoa_powder: ["cocoa_powder", "flour_baking"],
  yeast_baking: ["yeast_baking", "flour_baking"],
  salami: ["salami", "processed_meat"],
  ham: ["ham", "processed_meat"],
  sausages: ["sausages", "processed_meat"],
  chicken_meat: ["chicken_meat", "fresh_meat"],
  pork_meat: ["pork_meat", "fresh_meat"],
  beef_meat: ["beef_meat", "fresh_meat"],
  turkey_meat: ["turkey_meat", "fresh_meat"],
  minced_meat: ["minced_meat", "fresh_meat"],
  smoked_fish: ["smoked_fish", "fish"],
  frozen_fries: ["frozen_fries", "frozen"],
  frozen_pizza: ["frozen_pizza", "pizza", "frozen"],
  frozen_meal: ["frozen_meal", "ready_meal", "frozen"],
  ready_pasta: ["ready_pasta", "ready_meal", "pasta"],
  ready_salad: ["ready_salad", "sandwich_salad", "ready_meal"],
  hummus: ["hummus", "ready_meal", "plant_based"],
  tomato_canned: ["tomato_canned", "canned_vegetables"],
  corn_canned: ["corn_canned", "canned_vegetables"],
  bean_canned: ["bean_canned", "canned_vegetables", "legumes"],
  tuna_canned: ["tuna_canned", "canned_fish"],
  pate: ["pate", "canned_meat"],
  olives: ["olives", "pickles_olives"],
  pickled_cucumbers: ["pickled_cucumbers", "pickles_olives"],
  baby_puree_fruit: ["baby_puree_fruit", "baby_puree", "baby_food"],
  baby_puree_vegetable: ["baby_puree_vegetable", "baby_puree", "baby_food"],
  apple_juice: ["apple_juice", "fruit_juice", "nectar", "smoothie", "multivitamin_juice"],
  orange_juice: ["orange_juice", "fruit_juice", "nectar", "smoothie", "multivitamin_juice"],
  multivitamin_juice: ["multivitamin_juice", "fruit_juice", "apple_juice", "orange_juice", "nectar", "smoothie"],
  smoothie: ["smoothie", "fruit_juice", "nectar", "apple_juice", "orange_juice", "multivitamin_juice"],
  nectar: ["nectar", "fruit_juice", "apple_juice", "orange_juice", "multivitamin_juice", "smoothie"],
  isotonic_drink: ["isotonic_drink", "sports_drink", "energy_drink", "zero_energy_drink"],
  alcohol_free_beer: ["alcohol_free_beer", "beer", "radler_beer", "lager_beer"],
  radler_beer: ["radler_beer", "beer", "alcohol_free_beer", "lager_beer"],
  lager_beer: ["lager_beer", "beer", "radler_beer", "alcohol_free_beer", "wheat_beer", "dark_beer"],
  wheat_beer: ["wheat_beer", "beer", "lager_beer", "dark_beer"],
  dark_beer: ["dark_beer", "beer", "lager_beer", "wheat_beer"],
  uht_milk: ["uht_milk", "milk", "lactose_free_milk"],
  lactose_free_milk: ["lactose_free_milk", "milk", "uht_milk", "plant_milk"],
  oat_milk: ["oat_milk", "plant_milk", "almond_milk", "soy_milk"],
  almond_milk: ["almond_milk", "plant_milk", "oat_milk", "soy_milk"],
  soy_milk: ["soy_milk", "plant_milk", "oat_milk", "almond_milk"],
  protein_pudding: ["protein_pudding", "pudding", "dairy_dessert", "protein_yogurt"],
  pudding: ["pudding", "protein_pudding", "rice_pudding", "custard_dessert", "dairy_dessert"],
  rice_pudding: ["rice_pudding", "pudding", "custard_dessert", "dairy_dessert"],
  custard_dessert: ["custard_dessert", "pudding", "rice_pudding", "dairy_dessert"],
  ice_cream_bar: ["ice_cream_bar", "ice_cream_cone", "ice_cream_cup", "sorbet", "ice_cream"],
  ice_cream_cone: ["ice_cream_cone", "ice_cream_bar", "ice_cream_cup", "sorbet", "ice_cream"],
  ice_cream_cup: ["ice_cream_cup", "ice_cream_bar", "ice_cream_cone", "sorbet", "ice_cream"],
  sorbet: ["sorbet", "ice_cream", "ice_cream_bar", "ice_cream_cone", "ice_cream_cup"],
  cornflakes: ["cornflakes", "breakfast_cereal", "muesli", "granola"],
  muesli: ["muesli", "breakfast_cereal", "granola", "oats", "cornflakes"],
  granola: ["granola", "breakfast_cereal", "muesli", "oats", "cereal_bar"],
  oats: ["oats", "oats_granola", "muesli", "granola"],
  rice_cakes: ["rice_cakes", "salty_snack", "crackers"],
  sunflower_seeds: ["sunflower_seeds", "pumpkin_seeds", "roasted_nuts", "nuts"],
  pumpkin_seeds: ["pumpkin_seeds", "sunflower_seeds", "roasted_nuts", "nuts"],
  trail_mix: ["trail_mix", "nuts", "roasted_nuts", "dried_fruit"],
  bbq_sauce: ["bbq_sauce", "sauce", "hot_sauce", "tomato_sauce"],
  garlic_sauce: ["garlic_sauce", "sauce", "mayonnaise", "salad_dressing"],
  salsa_sauce: ["salsa_sauce", "sauce", "tomato_sauce", "hot_sauce"],
  sweet_chili_sauce: ["sweet_chili_sauce", "sauce", "hot_sauce"],
  dijon_mustard: ["dijon_mustard", "mustard", "sauce"],
  light_mayonnaise: ["light_mayonnaise", "mayonnaise", "sauce", "salad_dressing"],
  salt: ["salt", "spices"],
  pepper: ["pepper", "spices"],
  paprika: ["paprika", "spices", "spice_mix"],
  spice_mix: ["spice_mix", "spices", "paprika", "stock_cube"],
  stock_cube: ["stock_cube", "spice_mix", "spices"],
  toast_bread: ["toast_bread", "sliced_bread", "wholegrain_bread", "bread"],
  sliced_bread: ["sliced_bread", "toast_bread", "wholegrain_bread", "bread"],
  wholegrain_bread: ["wholegrain_bread", "sliced_bread", "toast_bread", "bread"],
  buns: ["buns", "bread", "toast_bread", "sliced_bread"],
  tortilla_wrap: ["tortilla_wrap", "bread", "bakery_pastry"],
  cup_noodles: ["cup_noodles", "ramen_noodles", "instant_noodles"],
  ramen_noodles: ["ramen_noodles", "cup_noodles", "instant_noodles"],
  whey_protein: ["whey_protein", "protein", "protein_bar"],
  canned_sardines: ["canned_sardines", "canned_fish", "tuna_canned", "canned_mackerel", "fish"],
  canned_mackerel: ["canned_mackerel", "canned_fish", "tuna_canned", "canned_sardines", "fish"],
  canned_peas: ["canned_peas", "canned_vegetables", "canned_chickpeas", "canned_lentils", "legumes"],
  canned_chickpeas: ["canned_chickpeas", "canned_vegetables", "canned_peas", "canned_lentils", "legumes"],
  canned_lentils: ["canned_lentils", "canned_vegetables", "canned_peas", "canned_chickpeas", "legumes"],
  vegetable_spread: ["vegetable_spread", "spread", "hummus", "plant_based"],
  jam: ["jam", "jam_honey", "honey", "spread"],
  honey: ["honey", "jam", "jam_honey", "spread"],
  frozen_fruit: ["frozen_fruit", "frozen"],
  frozen_vegetable_mix: ["frozen_vegetable_mix", "frozen_vegetable", "frozen"],
  frozen_dessert: ["frozen_dessert", "ice_cream", "sorbet", "frozen"],
  baby_biscuits: ["baby_biscuits", "baby_snack", "baby_food"],
  baby_snack: ["baby_snack", "baby_biscuits", "baby_food"],
});

familyCompatibility.fruit_juice = [
  ...new Set([...(familyCompatibility.fruit_juice || []), "apple_juice", "orange_juice", "multivitamin_juice", "smoothie", "nectar"]),
];
familyCompatibility.sports_drink = [...new Set([...(familyCompatibility.sports_drink || []), "isotonic_drink", "zero_energy_drink"])];
familyCompatibility.beer = [...new Set([...(familyCompatibility.beer || []), "alcohol_free_beer", "radler_beer", "lager_beer", "wheat_beer", "dark_beer"])];
familyCompatibility.milk = [...new Set([...(familyCompatibility.milk || []), "uht_milk", "lactose_free_milk", "oat_milk", "almond_milk", "soy_milk"])];
familyCompatibility.plant_milk = [...new Set([...(familyCompatibility.plant_milk || []), "oat_milk", "almond_milk", "soy_milk", "lactose_free_milk"])];
familyCompatibility.dairy_dessert = [...new Set([...(familyCompatibility.dairy_dessert || []), "pudding", "protein_pudding", "rice_pudding", "custard_dessert"])];
familyCompatibility.ice_cream = [...new Set([...(familyCompatibility.ice_cream || []), "ice_cream_bar", "ice_cream_cone", "ice_cream_cup", "sorbet", "frozen_dessert"])];
familyCompatibility.breakfast_cereal = [...new Set([...(familyCompatibility.breakfast_cereal || []), "cornflakes", "muesli", "granola", "oats"])];
familyCompatibility.sauce = [...new Set([...(familyCompatibility.sauce || []), "bbq_sauce", "garlic_sauce", "salsa_sauce", "sweet_chili_sauce", "dijon_mustard", "light_mayonnaise"])];
familyCompatibility.bread = [...new Set([...(familyCompatibility.bread || []), "toast_bread", "sliced_bread", "wholegrain_bread", "buns", "tortilla_wrap"])];
familyCompatibility.instant_noodles = [...new Set([...(familyCompatibility.instant_noodles || []), "cup_noodles", "ramen_noodles"])];
familyCompatibility.spread = [...new Set([...(familyCompatibility.spread || []), "vegetable_spread", "jam", "honey"])];
familyCompatibility.frozen = [...new Set([...(familyCompatibility.frozen || []), "frozen_fruit", "frozen_vegetable_mix", "frozen_dessert"])];

function areCompatibleFamilies(scannedProduct, candidate) {
  if (!scannedProduct) return true;

  const scannedFamily = getProductFamily(scannedProduct);
  const candidateFamily = getProductFamily(candidate);

  if (!scannedFamily || !candidateFamily) return true;
  if (scannedFamily === candidateFamily) return true;

  const allowedFamilies = familyCompatibility[scannedFamily] || [scannedFamily];
  return allowedFamilies.includes(candidateFamily);
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

  if (
    text.includes("alta aroma") ||
    text.includes("alt gust") ||
    text.includes("gust diferit") ||
    text.includes("aroma diferita") ||
    text.includes("alt sortiment") ||
    text.includes("alta varianta")
  ) {
    inferred.push("different_flavor");
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
    return "Scrie puțin mai clar ce cauți.";
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

const flavorKeywords = {
  vanilla: ["vanilie", "vanilla"],
  chocolate: ["ciocolată", "ciocolata", "chocolate", "cacao", "cocoa"],
  strawberry: ["căpșuni", "capsuni", "strawberry"],
  raspberry: ["zmeură", "zmeura", "raspberry"],
  blueberry: ["afine", "blueberry"],
  peach: ["piersică", "piersica", "peach"],
  apricot: ["caise", "apricot"],
  cherry: ["cireșe", "cirese", "vișine", "visine", "cherry"],
  forest_fruit: ["fructe de pădure", "fructe de padure", "berries", "forest fruits"],
  banana: ["banane", "banana"],
  apple: ["măr", "mar", "mere", "apple"],
  orange: ["portocale", "portocală", "portocala", "orange"],
  lemon: ["lămâie", "lamaie", "lemon"],
  lime: ["lime"],
  cola: ["cola"],
  grape: ["struguri", "grape"],
  mango: ["mango"],
  pineapple: ["ananas", "pineapple"],
  coconut: ["cocos", "coconut"],
  caramel: ["caramel"],
  hazelnut: ["alune", "hazelnut"],
  peanut: ["arahide", "peanut"],
  pistachio: ["fistic", "pistachio"],
  bbq: ["bbq", "barbecue"],
  cheese: ["brânză", "branza", "cheese"],
  onion: ["ceapă", "ceapa", "onion"],
  paprika: ["paprika", "boia"],
  spicy: ["picant", "iute", "spicy", "hot"],
  salted: ["sărat", "sarat", "salted"],
  natural: ["natural", "plain", "simplu", "original", "classic", "clasic"],
  zero: ["zero", "fără zahăr", "fara zahar", "no sugar"],
};

function extractProductFlavor(product) {
  const haystack = productSearchText(product);

  for (const [flavor, tokens] of Object.entries(flavorKeywords)) {
    if (tokens.some((token) => haystack.includes(normalizeText(token)))) {
      return flavor;
    }
  }

  return "";
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

function calculateAlternativeScore(products, product, criteriaList, scannedProduct = null) {
  let score = Number(product.recommendationScore ?? product.score) || 0;

  if (product.image) score += 1;
  if (product.category && normalizeCategory(product.category) !== "altele") score += 1;
  if ([product.calories, product.protein, product.sugar, product.fat].some((value) => Number.isFinite(Number(value)))) {
    score += 1;
  }

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

  if (criteriaList.includes("different_flavor") && scannedProduct) {
    const scannedFlavor = extractProductFlavor(scannedProduct);
    const candidateFlavor = extractProductFlavor(product);

    if (scannedFlavor && candidateFlavor && scannedFlavor !== candidateFlavor) {
      score += 14;
    } else if (scannedFlavor && candidateFlavor && scannedFlavor === candidateFlavor) {
      score -= 10;
    }
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

  if (criteriaList.includes("different_flavor") && scannedProduct) {
    const scannedFlavor = extractProductFlavor(scannedProduct);

    if (scannedFlavor) {
      const differentFlavorProducts = filteredProducts.filter((product) => {
        const candidateFlavor = extractProductFlavor(product);
        return candidateFlavor && candidateFlavor !== scannedFlavor;
      });

      if (differentFlavorProducts.length >= 2) {
        filteredProducts = differentFlavorProducts;
      }
    }
  }

  filteredProducts = filteredProducts.sort(
    (a, b) =>
      calculateAlternativeScore(filteredProducts, b, criteriaList, scannedProduct) -
      calculateAlternativeScore(filteredProducts, a, criteriaList, scannedProduct)
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
  const [differentFlavorOnly, setDifferentFlavorOnly] = useState(false);
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
  const manualCriteriaIds = differentFlavorOnly ? ["different_flavor"] : [];
  const combinedCriteriaIds = Array.from(
    new Set([...finalCriteriaIds, ...searchCriteriaIds, ...manualCriteriaIds])
  );
  const combinedCriteriaKey = combinedCriteriaIds.join(",");
  const displayCriteria = combinedCriteriaIds.map(
    (item) => criteriaLabels[item] || item
  );

  async function loadProducts(
    currentScannedProduct,
    criteriaIds = finalCriteriaIds,
    requestText = preferenceRequest,
    preferencesOverride = profilePreferences
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
                preferences: preferencesOverride || null,
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
            "Open Food Facts nu a găsit suficiente variante pentru produsul scanat.";
        } catch (externalError) {
          externalLookupWarning = externalError.message;
        }

        setProducts([]);
        setRecommendationSource("openfoodfacts");
        setErrorMessage("");
        setLookupNotice(
          externalLookupWarning ||
            "Nu am găsit încă suficiente alternative externe pentru produsul scanat."
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

      loadProducts(parsedResult, savedCriteriaIds, savedPreferenceRequest, savedPreferences);

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
        setLookupNotice("Actualizăm alternativele după cererea ta...");
        void loadProducts(
          scannedProduct,
          combinedCriteriaIds,
          [alternativeSearch, differentFlavorOnly ? "altă aromă" : ""].filter(Boolean).join(" "),
          profilePreferences
        );
      } else {
        setLookupNotice("");
        void loadProducts(
          scannedProduct,
          combinedCriteriaIds,
          [preferenceRequest, differentFlavorOnly ? "altă aromă" : ""].filter(Boolean).join(" "),
          profilePreferences
        );
      }
    }, 450);

    return () => window.clearTimeout(timer);
    // Backend-ul trebuie apelat din nou cand textul Pro schimba criteriile.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alternativeSearch, searchWarning, scannedProduct, isPaidPlan, combinedCriteriaKey, differentFlavorOnly]);

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
          request: alternativeSearch || preferenceRequest || displayCriteria.join(", "),
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

          {(displayCriteria.length > 0 || selectedAllergyLabels.length > 0 || selectedAvoidIngredients.length > 0 || customRequest) && (
            <div className="mt-6 rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-5">
              <h2 className="font-bold text-emerald-300">Criterii folosite</h2>

              {displayCriteria.length > 0 && (
                <>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {displayCriteria.map((criteria) => (
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
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDifferentFlavorOnly((value) => !value);
                      setShowMoreAlternatives(false);
                    }}
                    className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-black transition ${
                      differentFlavorOnly
                        ? "border-cyan-300/50 bg-cyan-300/20 text-cyan-100"
                        : "border-white/10 bg-black/25 text-gray-300 hover:border-cyan-300/35 hover:text-cyan-100"
                    }`}
                  >
                    <Shuffle size={16} />
                    Altă aromă
                  </button>
                </div>
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
                  {showMoreAlternatives ? "Arată mai puține" : "Afișează mai multe"}
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

