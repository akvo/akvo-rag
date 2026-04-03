"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
          <div className="text-center">
            <h1 className="text-6xl font-bold text-gray-900">500</h1>
            <p className="mt-4 text-xl text-gray-600">Something went wrong</p>
            <p className="mt-2 text-gray-500">
              An error occurred while processing your request.
            </p>
            <button
              onClick={reset}
              className="mt-6 inline-block px-6 py-3 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
