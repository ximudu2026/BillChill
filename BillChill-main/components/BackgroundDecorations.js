// components/BackgroundDecorations.js

export default function BackgroundDecorations() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
      <div className="absolute top-20 left-10 w-64 h-64 bg-teal-200/30 rounded-full blur-3xl animate-pulse mix-blend-multiply"></div>
      <div className="absolute bottom-20 right-10 w-80 h-80 bg-cyan-200/30 rounded-full blur-3xl animate-pulse [animation-delay:2s] mix-blend-multiply"></div>
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-100/40 rounded-full blur-3xl animate-pulse [animation-delay:4s] mix-blend-multiply"></div>
    </div>
  );
}