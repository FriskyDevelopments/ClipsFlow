import Image from "next/image";

type ClipResult = {
  title: string;
  thumbnail: string;
  duration: string;
};

export default function ClipResultCard({
  result,
  onSend,
}: {
  result: ClipResult;
  onSend?: () => void;
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
