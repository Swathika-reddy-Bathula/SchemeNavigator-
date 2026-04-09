import Chatbot from '@/components/Chatbot';

function App() {
  return (
    <div className='flex min-h-full w-full bg-[radial-gradient(circle_at_top,_rgba(146,179,202,0.18),_transparent_32%),linear-gradient(180deg,_#252525_0%,_#1a1a1a_100%)]'>
      <div className='flex flex-col min-h-full w-full max-w-4xl mx-auto px-4 md:px-6'>
        <header className='sticky top-0 shrink-0 z-20 backdrop-blur bg-[#1E1E1E]/80'>
          <div className='flex flex-col h-full w-full gap-1 pt-6 pb-4'>
            <p className='font-urbanist text-3xl font-semibold tracking-tight text-white'>
              Scheme Navigator
            </p>
            <p className='text-sm text-gray-300'>
              Ask questions against your Astra DB powered RAG knowledge base.
            </p>
          </div>
        </header>
        <div className='grow pb-4'>
          <Chatbot />
        </div>
      </div>
    </div>
  );
}

export default App;
