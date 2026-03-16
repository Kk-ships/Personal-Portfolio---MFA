import { SchemeSearcher } from '@/components/scheme/SchemeSearcher';

export default function SearchPage() {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
                        Search Mutual Funds
                    </h1>
                    <p className="mt-2 text-slate-600 dark:text-slate-400">
                        Search and explore mutual fund schemes
                    </p>
                </div>

                <SchemeSearcher />
            </div>
        </div>
    );
}
