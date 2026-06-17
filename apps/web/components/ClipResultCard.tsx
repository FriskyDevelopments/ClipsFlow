import Image from "next/image";

type ClipResult = {
  title: string;
  thumbnail: string;
  duration: string;
};

export default function ClipResultCard({
  result,
  onSend,
  onDownload,
  downloadLocked = false,
}: {
  result: ClipResult;
  onSend?: () => void;
  onDownload?: () => void;
  downloadLocked?: boolean;
}) {
  return (
    <div className="mt-4 bg-[#171b26] p-3 rounded border border-white/10">
      <div className="relative w-full aspect-video mb-2">
        <Image
          src={result.thumbnail}
          className="rounded object-cover"
          alt="clip thumbnail"
          fill
          unoptimized
        />
      </div>
      <div>{result.title}</div>
      <div className="text-sm opacity-60">{result.duration}</div>

      {onDownload && (
        <button
          onClick={onDownload}
          className={`mt-3 w-full p-2 rounded font-bold transition-all ${
            downloadLocked
              ? "bg-gradient-to-r from-pink-500 to-cyan-400 text-black hover:opacity-90"
              : "bg-cyan-300 text-black hover:bg-cyan-200"
          }`}
        >
          {downloadLocked ? "Unlock download" : "Download clip"}
        </button>
      )}

      {onSend && (
        <button
          onClick={onSend}
          className="mt-3 w-full p-2 bg-white text-black rounded"
        >
          Send to Telegram
        </button>
      )}
    </div>
  );
}
