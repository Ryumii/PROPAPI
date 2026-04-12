/** Tokyo 23 wards data for SSG. */

export interface Ward {
  prefecture: string;
  prefectureSlug: string;
  city: string;
  citySlug: string;
  lat: number;
  lng: number;
}

export const TOKYO_WARDS: Ward[] = [
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "千代田区", citySlug: "chiyoda", lat: 35.6938, lng: 139.7536 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "中央区", citySlug: "chuo", lat: 35.6707, lng: 139.7722 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "港区", citySlug: "minato", lat: 35.6584, lng: 139.7516 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "新宿区", citySlug: "shinjuku", lat: 35.6938, lng: 139.7036 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "文京区", citySlug: "bunkyo", lat: 35.7082, lng: 139.7524 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "台東区", citySlug: "taito", lat: 35.7126, lng: 139.7801 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "墨田区", citySlug: "sumida", lat: 35.7107, lng: 139.8015 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "江東区", citySlug: "koto", lat: 35.6727, lng: 139.8171 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "品川区", citySlug: "shinagawa", lat: 35.6092, lng: 139.7300 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "目黒区", citySlug: "meguro", lat: 35.6414, lng: 139.6982 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "大田区", citySlug: "ota", lat: 35.5613, lng: 139.7160 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "世田谷区", citySlug: "setagaya", lat: 35.6462, lng: 139.6532 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "渋谷区", citySlug: "shibuya", lat: 35.6640, lng: 139.6982 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "中野区", citySlug: "nakano", lat: 35.7078, lng: 139.6638 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "杉並区", citySlug: "suginami", lat: 35.6994, lng: 139.6365 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "豊島区", citySlug: "toshima", lat: 35.7263, lng: 139.7169 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "北区", citySlug: "kita", lat: 35.7527, lng: 139.7377 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "荒川区", citySlug: "arakawa", lat: 35.7360, lng: 139.7834 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "板橋区", citySlug: "itabashi", lat: 35.7514, lng: 139.7097 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "練馬区", citySlug: "nerima", lat: 35.7355, lng: 139.6517 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "足立区", citySlug: "adachi", lat: 35.7753, lng: 139.8046 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "葛飾区", citySlug: "katsushika", lat: 35.7435, lng: 139.8477 },
  { prefecture: "東京都", prefectureSlug: "tokyo", city: "江戸川区", citySlug: "edogawa", lat: 35.7067, lng: 139.8683 },
];

export function findWard(
  prefSlug: string,
  citySlug: string,
): Ward | undefined {
  return TOKYO_WARDS.find(
    (w) => w.prefectureSlug === prefSlug && w.citySlug === citySlug,
  );
}
