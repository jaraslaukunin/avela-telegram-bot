import { describe, expect, it } from "vitest";

import { dictionaries, detectLocale, locales, translate } from "./index";

describe("i18n", () => {
  it("содержит все локали из спецификации", () => {
    expect(locales).toEqual(["ru", "en", "be-Latn"]);
  });

  it("все языки имеют одинаковый набор ключей", () => {
    const ruKeys = Object.keys(dictionaries.ru).sort();

    for (const locale of locales) {
      expect(Object.keys(dictionaries[locale]).sort()).toEqual(ruKeys);
    }
  });

  it("нет пустых переводов", () => {
    for (const locale of locales) {
      for (const [key, value] of Object.entries(dictionaries[locale])) {
        expect(value.trim(), `${locale}:${key}`).not.toBe("");
      }
    }
  });

  it("detectLocale понимает телеграмные коды", () => {
    expect(detectLocale("be")).toBe("be-Latn");
    expect(detectLocale("en-US")).toBe("en");
    expect(detectLocale("ru")).toBe("ru");
    expect(detectLocale(undefined)).toBe("ru");
  });

  it("translate откатывается на русский и на ключ", () => {
    expect(translate("en", "home.book")).toBe("Book");
    expect(translate("en", "неизвестный-ключ")).toBe("неизвестный-ключ");
  });
});
