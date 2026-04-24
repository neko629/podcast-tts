const STORAGE_KEY = 'podcast-tts:character-defaults';

type DefaultsMap = Record<string, string>;

function readAll(): DefaultsMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(map: DefaultsMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // 存储失败（配额或隐私模式）静默忽略
  }
}

export function getCharacterDefault(character: string): string | undefined {
  return readAll()[character];
}

export function getAllCharacterDefaults(): DefaultsMap {
  return readAll();
}

export function setCharacterDefault(character: string, voiceId: string): void {
  const map = readAll();
  map[character] = voiceId;
  writeAll(map);
}

export function clearCharacterDefault(character: string): void {
  const map = readAll();
  delete map[character];
  writeAll(map);
}
