/**
 * Footer — simple footer with tech stack credits.
 */
export default function Footer() {
  return (
    <footer className="border-t border-white/[0.052] py-4 text-center text-[0.74rem] text-slate-600">
      <div>
        <span className="text-slate-500 font-600">Startup Blueprint Generator</span>
        &nbsp;·&nbsp; IBM Granite 4.0 &nbsp;·&nbsp; Groq Llama 3.3 &nbsp;·&nbsp;
        Gemini Flash &nbsp;·&nbsp; CRAG (Yan et al. 2024)
      </div>
      <div className="text-slate-700 mt-1 text-[0.68rem]">
        Built for the Indian startup ecosystem
      </div>
    </footer>
  )
}
