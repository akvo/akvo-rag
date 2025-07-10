import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function toTitleCase(str) {
  // Array of words that should not be capitalized unless they are the first word
  const minorWords = [
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "up",
    "with",
    "yet",
  ];

  return str
    .replace(/\w\S*/g, function (txt, offset) {
      // Convert to lowercase
      txt = txt.toLowerCase();

      // If it's the first word or not a minor word, capitalize the first letter
      if (offset === 0 || !minorWords.includes(txt)) {
        return txt.charAt(0).toUpperCase() + txt.substr(1);
      } else {
        return txt; // Keep minor words lowercase
      }
    })
    .replace(/['\u2019]\S*/g, function (txt) {
      // Handle apostrophes (e.g., "don't" -> "Don't", "O'Malley" -> "O'Malley")
      return txt.charAt(0) + txt.charAt(1).toUpperCase() + txt.substr(2);
    });
}
