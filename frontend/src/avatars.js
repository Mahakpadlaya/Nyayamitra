/**
 * Advisor identity + preset user faces (DiceBear — free API, no API key).
 * https://www.dicebear.com
 */

export const ADVISOR = {
  /** Fictional assistant name (not a real person). “Nyaya” ≈ justice/law (Sanskrit). */
  name: "NyayaMitra",
  shortBio: "breaks down Indian law without the snooze — edu only, not a lawyer",
  /**
   * Scales of justice (Wikimedia Commons, gold icon — fits legal theme).
   * https://commons.wikimedia.org/wiki/File:Gold_scales_icon.svg
   */
  avatarUrl:
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Gold_scales_icon.svg/256px-Gold_scales_icon.svg.png",
  avatarAlt: "Scales of justice",
};

const DICE = "https://api.dicebear.com/9.x";

/**
 * Curated looks (DiceBear PNG). `gender` is for UI grouping only.
 * Female: Mahak, Ganga, Kumkum, Sanskriti, Prarthana, Anika, Meera.
 */
export const USER_AVATAR_PRESETS = [
  {
    id: "mahak",
    label: "Mahak",
    gender: "female",
    url: `${DICE}/personas/png?seed=MahakDelhi&size=128&backgroundColor=b6e3f4`,
  },
  {
    id: "ganga",
    label: "Ganga",
    gender: "female",
    url: `${DICE}/personas/png?seed=GangaBLR&size=128&backgroundColor=c0aede`,
  },
  {
    id: "kumkum",
    label: "Kumkum",
    gender: "female",
    url: `${DICE}/personas/png?seed=KumkumMum&size=128&backgroundColor=ffd5dc`,
  },
  {
    id: "sanskriti",
    label: "Sanskriti",
    gender: "female",
    url: `${DICE}/notionists/png?seed=SanskritiLucknow&size=128&backgroundType=gradientLinear`,
  },
  {
    id: "prarthana",
    label: "Prarthana",
    gender: "female",
    url: `${DICE}/personas/png?seed=PrarthanaPune&size=128&backgroundColor=e8d4f0`,
  },
  {
    id: "anika",
    label: "Anika",
    gender: "female",
    url: `${DICE}/notionists/png?seed=AnikaHyd&size=128&backgroundType=gradientLinear`,
  },
  {
    id: "meera",
    label: "Meera",
    gender: "female",
    url: `${DICE}/personas/png?seed=MeeraKOCHI&size=128&backgroundColor=ffdfbf`,
  },
  {
    id: "veer",
    label: "Veer",
    gender: "male",
    url: `${DICE}/adventurer/png?seed=VeerPune&size=128&backgroundColor=d1d4f9`,
  },
  {
    id: "buddy",
    label: "Buddy",
    gender: "male",
    url: `${DICE}/notionists/png?seed=BuddyMumbai&size=128&backgroundType=gradientLinear`,
  },
  {
    id: "dev",
    label: "Dev",
    gender: "male",
    url: `${DICE}/personas/png?seed=DevAmd&size=128&backgroundColor=e0e0e0`,
  },
];

export const STORAGE_USER_AVATAR = "nyayamitra-user-avatar-url";

export function loadSavedUserAvatarUrl() {
  try {
    const v = localStorage.getItem(STORAGE_USER_AVATAR);
    if (v && USER_AVATAR_PRESETS.some((p) => p.url === v)) return v;
  } catch {
    /* ignore */
  }
  return USER_AVATAR_PRESETS[0].url;
}

export function saveUserAvatarUrl(url) {
  try {
    localStorage.setItem(STORAGE_USER_AVATAR, url);
  } catch {
    /* ignore */
  }
}
