"use client";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import BackgroundDecorations from "@/components/BackgroundDecorations"; // Adjust path as needed

// Type definition for hospital data
type HospitalResult = {
  name: string;
  address?: string | null;
  phone?: string | null;
  url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  distance_miles?: number | null;
  price_usd?: number | null;
  price_is_estimate?: boolean;
  notes?: string | null;
  maps_url?: string | null;
};

export default function HospitalPage() {
  // State for search UI
  const [isSearching, setIsSearching] = useState(false);
  const [query, setQuery] = useState("");
  const [locationQuery, setLocationQuery] = useState(""); // NEW: Location input state
  
  // State for data fetching
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<HospitalResult[]>([]);
  
  // State for active sort method ('price' is default)
  const [sortBy, setSortBy] = useState<'price' | 'distance'>('price');

  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:5000";

  // Determine if search button should be enabled
  const canSearch = useMemo(() => query.trim().length > 0 && !loading, [query, loading]);

  // Automatically sort results whenever 'results' or 'sortBy' changes
  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => {
      if (sortBy === 'distance') {
        // Primary sort: Distance (asc), Secondary: Price (asc)
        const distA = a.distance_miles ?? Infinity;
        const distB = b.distance_miles ?? Infinity;
        if (distA !== distB) return distA - distB;
        return (a.price_usd ?? Infinity) - (b.price_usd ?? Infinity);
      } else {
        // Primary sort: Price (asc), Secondary: Distance (asc)
        const priceA = a.price_usd ?? Infinity;
        const priceB = b.price_usd ?? Infinity;
        if (priceA !== priceB) return priceA - priceB;
        return (a.distance_miles ?? Infinity) - (b.distance_miles ?? Infinity);
      }
    });
  }, [results, sortBy]);

  // Updated function to fetch hospital data from backend
  const fetchHospitals = useCallback(async (lat: number | null, lon: number | null, locStr: string | null = null) => {
    setLoading(true);
    setError(null);
    try {
      const payload: any = { condition: query.trim() };
      if (locStr) {
          payload.location = locStr;
      } else if (lat !== null && lon !== null) {
          payload.lat = lat;
          payload.lon = lon;
      } else {
          // Should not happen if called correctly, but good as fallback
          throw new Error("No location provided.");
      }

      const resp = await fetch(`${BACKEND_URL}/api/hospitals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data?.error || `Request failed (${resp.status})`);
      }
      setResults(Array.isArray(data?.results) ? data.results : []);
    } catch (e: any) {
      setError(e?.message || "Something went wrong. Please try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, BACKEND_URL]);

  // Updated handler for search action
  const handleSearch = useCallback(() => {
    if (!query.trim()) return;

    // Priority 1: Explicit location input
    if (locationQuery.trim()) {
        fetchHospitals(null, null, locationQuery.trim());
        return;
    }

    // Priority 2: Browser Geolocation
    if (typeof navigator !== "undefined" && navigator.geolocation) {
      setLoading(true);
      setError(null);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          fetchHospitals(pos.coords.latitude, pos.coords.longitude);
        },
        (err) => {
          setLoading(false);
          setError("Location permission denied. Please enter a city or zip code.");
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    } else {
      setError("Geolocation is not supported. Please enter a location manually.");
    }
  }, [query, locationQuery, fetchHospitals]);

  return (
    <main className="min-h-screen bg-slate-50/80 relative">
      <BackgroundDecorations />
      
      <div className="p-6 md:p-12 relative z-10">
        {/* HEADER */}
        <header className="max-w-5xl mx-auto flex justify-between items-center mb-12 md:mb-20 animate-fade-in">
          <Link href="/" className="text-3xl font-black text-teal-600 hover:scale-105 transition-transform tracking-tighter">
            BillChill<span className="text-teal-400">.</span>
          </Link>
          <Link href="/dispute" className="hidden md:flex group bg-white/80 backdrop-blur-sm text-slate-600 px-5 py-2.5 rounded-full text-sm font-bold shadow-sm hover:shadow-md transition-all items-center gap-2 border border-white/50 hover:text-teal-600">
            Need to dispute a bill instead? 
            <span className="group-hover:translate-x-1 transition-transform">→</span>
          </Link>
          <Link href="/dispute" className="md:hidden bg-white/80 backdrop-blur-sm text-teal-600 p-3 rounded-full shadow-sm border border-white/50 active:scale-95 transition-transform">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
               <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
            </svg>
          </Link>
        </header>

        {/* MAIN CONTENT */}
        <section className="max-w-3xl mx-auto">
          <div className="text-center mb-10 animate-fade-in">
            <h1 className="text-4xl md:text-6xl font-black text-slate-800 mb-6 tracking-tight">
              Find Nearby Care
            </h1>
            <p className="text-xl md:text-2xl text-slate-600 max-w-2xl mx-auto font-medium leading-relaxed">
              Stop guessing. See standard prices <span className="text-teal-600 font-bold relative inline-block">before<svg className="absolute -bottom-1 left-0 w-full text-teal-200/50 -z-10" viewBox="0 0 100 15" xmlns="http://www.w3.org/2000/svg"><path d="M0 10 Q 25 0, 50 10 T 100 10" stroke="currentColor" strokeWidth="8" fill="none"/></svg></span> you walk in the door.
            </p>
          </div>

          {/* UPDATED SEARCH BAR CONTAINER */}
          <div 
            className={`
              bg-white p-2 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] flex flex-col md:flex-row md:items-center 
              border-2 transition-all duration-300 mb-16 animate-fade-in [animation-delay:100ms]
              ${isSearching ? 'border-teal-400 shadow-[0_8px_30px_rgb(20,184,166,0.2)] scale-[1.02]' : 'border-transparent'}
            `}
          >
            {/* CONDITION INPUT */}
            <div className="flex-1 flex items-center border-b-2 md:border-b-0 md:border-r-2 border-slate-100 p-2">
                <span className={`pl-2 transition-colors duration-300 ${isSearching ? 'text-teal-500' : 'text-slate-400'}`}>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor" className="w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                </span>
                <input
                  type="text"
                  placeholder="Condition (e.g., MRI, X-Ray)..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && canSearch) handleSearch(); }}
                  onFocus={() => setIsSearching(true)}
                  onBlur={() => setIsSearching(false)}
                  className="w-full p-4 bg-transparent text-lg md:text-xl outline-none text-slate-800 placeholder:text-slate-300 font-bold"
                />
            </div>

            {/* NEW LOCATION INPUT */}
            <div className="flex-1 flex items-center p-2">
                <span className="pl-2 text-slate-400">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor" className="w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                </span>
                <input
                  type="text"
                  placeholder="Current Location (or enter city)"
                  value={locationQuery}
                  onChange={(e) => setLocationQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && canSearch) handleSearch(); }}
                  onFocus={() => setIsSearching(true)}
                  onBlur={() => setIsSearching(false)}
                  className="w-full p-4 bg-transparent text-lg md:text-xl outline-none text-slate-800 placeholder:text-slate-300 font-bold"
                />
            </div>

            {/* SEARCH BUTTON (Desktop) */}
            <button
              onClick={handleSearch}
              disabled={!canSearch}
              className={`hidden md:block px-8 py-4 mx-2 rounded-2xl font-bold transition-all whitespace-nowrap ${canSearch ? "bg-teal-600 text-white hover:bg-teal-500 hover:scale-105 active:scale-95" : "bg-slate-200 text-slate-400 cursor-not-allowed"}`}
            >
              {loading ? "Searching…" : "Search"}
            </button>
             {/* SEARCH BUTTON (Mobile) */}
             <button
              onClick={handleSearch}
              disabled={!canSearch}
              className={`md:hidden w-full py-4 mt-2 rounded-2xl font-bold transition-all ${canSearch ? "bg-teal-600 text-white active:scale-95" : "bg-slate-200 text-slate-400"}`}
            >
              {loading ? "Searching…" : "Search Nearby"}
            </button>
          </div>

          {/* POPULAR SEARCHES */}
          <div className="animate-fade-in [animation-delay:200ms]">
            <p className="text-center text-sm uppercase tracking-widest text-slate-400 mb-6 font-bold">
              Popular right now
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              {["🦴 X-Ray", "🧠 MRI Scan", "🩸 Blood Test", "🚑 Emergency", "🦷 Dental Cleaning"].map((tag, i) => (
                <button 
                  key={tag}
                  style={{ animationDelay: `${i * 0.1}s` }} 
                  onClick={() => { setQuery(tag.replace(/^[^\w]+\s*/, "")); }}
                  className="animate-float px-6 py-3 bg-white rounded-2xl text-slate-700 font-bold border-2 border-slate-100/50 shadow-sm 
                             hover:border-teal-400 hover:text-teal-600 hover:shadow-md hover:-translate-y-1 hover:rotate-1
                             active:scale-95 transition-all duration-200"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* RESULTS AREA */}
          <div className="mt-12 space-y-4">
            {error && (
              <div className="max-w-3xl mx-auto bg-red-50 text-red-700 border border-red-100 rounded-xl p-4 font-medium">
                {error}
              </div>
            )}
            {!error && loading && (
              <div className="max-w-3xl mx-auto bg-white border border-slate-100 rounded-xl p-4 shadow-sm text-slate-600 animate-pulse">
                Searching nearby hospitals and price info…
              </div>
            )}

            {/* SORTING CONTROLS */}
            {!loading && results.length > 0 && !error && (
              <div className="max-w-3xl mx-auto mb-6 flex flex-col sm:flex-row justify-between items-center gap-4 animate-fade-in">
                <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">
                  Found {results.length} matches nearby
                </p>
                <div className="flex items-center bg-white p-1 rounded-xl shadow-sm border border-slate-100">
                   <button
                     onClick={() => setSortBy("price")}
                     className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                       sortBy === 'price' 
                         ? 'bg-teal-50 text-teal-700 shadow-sm' 
                         : 'text-slate-500 hover:text-slate-700'
                     }`}
                   >
                     💲 Lowest Price
                   </button>
                   <button
                     onClick={() => setSortBy("distance")}
                     className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                       sortBy === 'distance' 
                         ? 'bg-teal-50 text-teal-700 shadow-sm' 
                         : 'text-slate-500 hover:text-slate-700'
                     }`}
                   >
                     📍 Nearest
                   </button>
                </div>
              </div>
            )}

            {/* RESULTS LIST */}
            {!loading && sortedResults?.length > 0 && (
              <ul className="max-w-3xl mx-auto divide-y divide-slate-100 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden animate-fade-in">
                {sortedResults.map((r, idx) => (
                  <li key={idx} className="p-5 md:p-6 flex flex-col md:flex-row md:items-center gap-3 hover:bg-slate-50/50 transition-colors">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-lg md:text-xl font-extrabold text-slate-800">{r.name}</h3>
                        {typeof r.distance_miles === "number" && (
                          <span className="text-xs font-bold text-slate-500 bg-slate-100 rounded-full px-2 py-0.5">
                            {r.distance_miles.toFixed(1)} mi
                          </span>
                        )}
                      </div>
                      {r.address && (
                        <p className="text-slate-600 text-sm md:text-base mt-0.5">{r.address}</p>
                      )}
                      <div className="mt-3 flex flex-wrap gap-3 text-sm">
                        {typeof r.price_usd === "number" ? (
                          <span className="font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-2.5 py-1">
                            ${" "+r.price_usd.toFixed(0)} {r.price_is_estimate ? "(est.)" : ""}
                          </span>
                        ) : (
                          <span className="text-slate-500 bg-slate-50 border border-slate-100 rounded-lg px-2.5 py-1">
                            Price unavailable
                          </span>
                        )}
                        {r.phone && (
                          <a href={`tel:${r.phone}`} className="flex items-center gap-1 text-teal-700 font-semibold hover:underline bg-teal-50/50 px-2 py-1 rounded-lg">
                            📞 {r.phone}
                          </a>
                        )}
                      </div>
                      {r.notes && (
                        <p className="mt-3 text-slate-500 text-xs md:text-sm bg-slate-50 p-2 rounded-lg border border-slate-100 italic">
                          📝 {r.notes}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-3 md:mt-0">
                      {r.url && (
                        <a href={r.url} target="_blank" rel="noreferrer" className="px-4 py-2 text-sm font-bold rounded-xl border-2 border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50 transition-all">
                          Website
                        </a>
                      )}
                      {r.maps_url && (
                        <a href={r.maps_url} target="_blank" rel="noreferrer" className="px-4 py-2 text-sm font-bold rounded-xl bg-teal-600 text-white hover:bg-teal-500 hover:shadow-md active:scale-95 transition-all">
                          Directions
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}