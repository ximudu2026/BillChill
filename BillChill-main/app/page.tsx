import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-teal-50 via-cyan-50 to-blue-50 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background decoration - floating shapes */}
      <div className="absolute top-20 left-10 w-32 h-32 bg-teal-200 rounded-full opacity-20 blur-3xl animate-pulse"></div>
      <div className="absolute bottom-20 right-10 w-40 h-40 bg-cyan-200 rounded-full opacity-20 blur-3xl animate-pulse [animation-delay:1s]"></div>
      
      {/* HERO TEXT */}
      {/* Adjusted bottom margin for better mobile responsiveness (mb-10 md:mb-16) */}
      <div className="text-center max-w-3xl mb-10 md:mb-16 animate-fade-in z-10">
        <h1 className="text-6xl md:text-7xl font-black mb-6 leading-tight">
          {/* Softened the "Welcome to" color slightly so it doesn't compete with the gradient */}
          <span className="text-slate-700">Welcome to </span>
          <span className="relative inline-block">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-500 via-cyan-500 to-teal-600 animate-gradient">
              BillChill
            </span>
            {/* Underline decoration - Now uses currentColor for easier theming */}
            <svg className="absolute -bottom-2 left-0 w-full text-teal-500" viewBox="0 0 200 12" xmlns="http://www.w3.org/2000/svg">
              <path d="M0 6 Q50 0, 100 6 T200 6" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round"/>
            </svg>
          </span>
        </h1>
        <p className="text-xl md:text-2xl text-slate-600 font-medium">
          {/* Emphasized the problem statement */}
          <span className="font-semibold text-slate-700">Medical costs are confusing.</span> We make them simple. 
          <br />
          <span className="text-teal-600 font-bold mt-2 block md:inline">What do you need help with today?</span>
        </p>
      </div>

      {/* THE TWO PATHS */}
      <div className="grid md:grid-cols-2 gap-6 md:gap-8 max-w-5xl w-full animate-fade-in [animation-delay:200ms] z-10">
        {/* Path 1: Find Hospital */}
        <Link href="/hospital" className="group w-full">
          <div className="bg-white p-8 md:p-10 rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 border-2 border-transparent hover:border-teal-400 h-full flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-teal-50 to-cyan-50 opacity-0 group-hover:opacity-100 transition-opacity rounded-3xl"></div>
            
            <div className="relative z-10 flex flex-col items-center w-full">
              <div className="w-20 h-20 md:w-24 md:h-24 bg-gradient-to-br from-teal-400 to-cyan-500 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="white" className="w-10 h-10 md:w-12 md:h-12">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                </svg>
              </div>
              <h2 className="text-2xl md:text-3xl font-bold text-slate-800 mb-4 group-hover:text-teal-600 transition-colors">
                Find a Hospital
              </h2>
              <p className="text-slate-600 text-base md:text-lg mb-8 max-w-sm">
                Compare prices before you go. Find the most affordable care near you.
              </p>
              {/* Button now wider on mobile (w-full sm:w-auto) */}
              <span className="inline-flex items-center justify-center w-full sm:w-auto gap-2 bg-teal-600 group-hover:bg-teal-700 text-white font-bold px-8 py-4 rounded-xl transition-all group-hover:scale-105 shadow-md">
                Start Search 
                <span className="group-hover:translate-x-1 transition-transform">→</span>
              </span>
            </div>
          </div>
        </Link>

        {/* Path 2: Dispute Bill */}
        <Link href="/dispute" className="group w-full">
          <div className="bg-white p-8 md:p-10 rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 border-2 border-transparent hover:border-teal-400 h-full flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-teal-50 to-cyan-50 opacity-0 group-hover:opacity-100 transition-opacity rounded-3xl"></div>
            
            <div className="relative z-10 flex flex-col items-center w-full">
              <div className="w-20 h-20 md:w-24 md:h-24 bg-gradient-to-br from-teal-400 to-cyan-500 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg">
                {/* UPDATED ICON: Clipboard with magnifying glass (implies investigating/fixing) */}
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="white" className="w-10 h-10 md:w-12 md:h-12">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <h2 className="text-2xl md:text-3xl font-bold text-slate-800 mb-4 group-hover:text-teal-600 transition-colors">
                Dispute a Bill
              </h2>
              <p className="text-slate-600 text-base md:text-lg mb-8 max-w-sm">
                Already went? Upload your confusing bill and let AI find the errors.
              </p>
              {/* Button now wider on mobile (w-full sm:w-auto) */}
              <span className="inline-flex items-center justify-center w-full sm:w-auto gap-2 bg-teal-600 group-hover:bg-teal-700 text-white font-bold px-8 py-4 rounded-xl transition-all group-hover:scale-105 shadow-md">
                Fix My Bill 
                <span className="group-hover:translate-x-1 transition-transform">→</span>
              </span>
            </div>
          </div>
        </Link>
      </div>
    </main>
  );
}