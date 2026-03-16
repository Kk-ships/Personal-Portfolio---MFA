'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { searchSchemes } from '@/lib/api';
import Link from 'next/link';

interface SchemeResult {
    amfi_code: string | null;
    isin: string;
    name: string;
    fund_house: string | null;
    category: string | null;
    type: string;
    latest_nav: number | null;
    latest_nav_date: string | null;
    in_portfolio?: boolean;
}

interface SearchResults {
    query: string;
    count: number;
    results: SchemeResult[];
}

export function SchemeSearcher() {
    const [searchQuery, setSearchQuery] = useState('');
    const [results, setResults] = useState<SearchResults | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

    const handleSearch = useCallback(async (query: string) => {
        if (!query || query.trim().length < 2) {
            setResults(null);
            setError(null);
            return;
        }

        setIsSearching(true);
        setError(null);

        try {
            // Get user ID from localStorage if available
            const userId = typeof window !== 'undefined' ? localStorage.getItem('userId') : null;
            const data = await searchSchemes(query, 20, userId || undefined);
            setResults(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Search failed');
            setResults(null);
        } finally {
            setIsSearching(false);
        }
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setSearchQuery(value);
    };

    // Debounce effect
    useEffect(() => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }

        debounceTimerRef.current = setTimeout(() => {
            handleSearch(searchQuery);
        }, 300);

        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, [searchQuery, handleSearch]);

    return (
        <div className="w-full max-w-4xl mx-auto">
            {/* Search Input */}
            <div className="relative mb-6">
                <div className="relative">
                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={handleInputChange}
                        placeholder="Search mutual funds by name..."
                        className="w-full pl-12 pr-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 text-slate-900 dark:text-slate-100 placeholder-slate-400"
                    />
                    {isSearching && (
                        <Loader2 className="absolute right-4 top-1/2 transform -translate-y-1/2 text-indigo-500 w-5 h-5 animate-spin" />
                    )}
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-red-700 dark:text-red-400 text-sm">{error}</p>
                </div>
            )}

            {/* Results */}
            {results && results.count > 0 && (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
                    <div className="px-4 py-3 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            Found {results.count} result{results.count !== 1 ? 's' : ''} for &quot;{results.query}&quot;
                        </p>
                    </div>
                    <div className="divide-y divide-slate-200 dark:divide-slate-700 max-h-[600px] overflow-y-auto">
                        {results.results.map((scheme) => (
                            <Link
                                key={scheme.isin}
                                href={scheme.amfi_code ? `/scheme/${scheme.amfi_code}` : '#'}
                                className={`block px-4 py-4 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${!scheme.amfi_code ? 'opacity-50 cursor-not-allowed' : ''
                                    }`}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                                                {scheme.name}
                                            </h4>
                                            {scheme.in_portfolio && (
                                                <span className="flex-shrink-0 px-2 py-0.5 text-xs font-medium bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded">
                                                    In Portfolio
                                                </span>
                                            )}
                                        </div>
                                        <div className="mt-1 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                                            {scheme.fund_house && (
                                                <span>{scheme.fund_house}</span>
                                            )}
                                            {scheme.category && (
                                                <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded">
                                                    {scheme.category}
                                                </span>
                                            )}
                                        </div>
                                        {scheme.isin && (
                                            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                                                ISIN: {scheme.isin}
                                                {scheme.amfi_code && ` • AMFI: ${scheme.amfi_code}`}
                                            </p>
                                        )}
                                    </div>
                                    {scheme.latest_nav !== null && (
                                        <div className="ml-4 text-right">
                                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                                                ₹{scheme.latest_nav.toFixed(4)}
                                            </p>
                                            {scheme.latest_nav_date && (
                                                <p className="text-xs text-slate-400 dark:text-slate-500">
                                                    {new Date(scheme.latest_nav_date).toLocaleDateString()}
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </Link>
                        ))}
                    </div>
                </div>
            )}

            {/* No Results */}
            {results && results.count === 0 && (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-8 text-center">
                    <p className="text-slate-600 dark:text-slate-400">
                        No mutual funds found for &quot;{results.query}&quot;
                    </p>
                    <p className="text-sm text-slate-500 dark:text-slate-500 mt-2">
                        Try a different search term
                    </p>
                </div>
            )}

            {/* Initial State */}
            {!results && !isSearching && searchQuery.length >= 2 && !error && (
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm p-8 text-center">
                    <Search className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                    <p className="text-slate-600 dark:text-slate-400">
                        Start typing to search for mutual funds
                    </p>
                </div>
            )}
        </div>
    );
}
