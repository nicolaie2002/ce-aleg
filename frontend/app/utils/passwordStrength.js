export const PASSWORD_MIN_LENGTH = 8;

export function getPasswordStrength(password) {
  const value = password || "";
  const suggestions = [];
  let score = 0;

  if (value.length >= PASSWORD_MIN_LENGTH) {
    score += 1;
  } else {
    suggestions.push(`Minimum ${PASSWORD_MIN_LENGTH} caractere.`);
  }

  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) {
    score += 1;
  } else {
    suggestions.push("Combina litere mici si mari.");
  }

  if (/\d/.test(value)) {
    score += 1;
  } else {
    suggestions.push("Adauga cel putin o cifra.");
  }

  if (/[^A-Za-z0-9]/.test(value)) {
    score += 1;
  } else {
    suggestions.push("Adauga un simbol.");
  }

  if (value.length >= 12) {
    score += 1;
  }

  if (value.length < PASSWORD_MIN_LENGTH) {
    return { label: "slaba", score, suggestions, percent: 25, color: "bg-red-400" };
  }

  if (score >= 5) {
    return { label: "puternica", score, suggestions, percent: 100, color: "bg-emerald-400" };
  }

  if (score >= 3) {
    return { label: "medie", score, suggestions, percent: 66, color: "bg-yellow-300" };
  }

  return { label: "slaba", score, suggestions, percent: 35, color: "bg-red-400" };
}

export function getPasswordStrengthLabel(strength, pick) {
  if (strength.label === "puternica") {
    return pick("Puternica", "Strong");
  }

  if (strength.label === "medie") {
    return pick("Medie", "Medium");
  }

  return pick("Slaba", "Weak");
}
