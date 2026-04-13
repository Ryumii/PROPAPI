"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

interface SearchFormProps {
  compact?: boolean;
  defaultValue?: string;
}

export default function SearchForm({
  compact = false,
  defaultValue = "",
}: SearchFormProps) {
  const [address, setAddress] = useState(defaultValue);
  const router = useRouter();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = address.trim();
    if (!trimmed) return;
    router.push(`/search?address=${encodeURIComponent(trimmed)}`);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full" role="search">
      <div className="relative">
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="住所 or 座標（例：東京都渋谷区渋谷2-24-12 / 35.659, 139.700）"
          className={`w-full border border-gray-300 rounded-xl shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition ${
            compact
              ? "px-4 py-2 pr-12 text-sm"
              : "px-5 py-4 pr-16 text-lg"
          }`}
          aria-label="住所検索"
        />
        <button
          type="submit"
          disabled={!address.trim()}
          className={`absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-lg transition ${
            compact ? "px-2 py-1" : "px-4 py-2"
          }`}
          aria-label="検索"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={compact ? "h-4 w-4" : "h-5 w-5"}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </button>
      </div>
    </form>
  );
}
