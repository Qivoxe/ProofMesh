import { useRef, useState, useEffect } from "react";
import type { ImageForensicsResponse, CopyMoveAnalysisResponse, OCRBlock } from "../types/analysis";

interface ImageViewerProps {
  file: File;
  imageResults: ImageForensicsResponse | undefined;
  copyMoveResults: CopyMoveAnalysisResponse | undefined;
  ocrBlocks: OCRBlock[] | undefined;
}

interface RegionLike {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  reason: string;
}

export function ImageViewer({ file, imageResults, copyMoveResults, ocrBlocks }: ImageViewerProps) {
  const [showRegions, setShowRegions] = useState(true);
  const [showOcr, setShowOcr] = useState(true);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [renderedSize, setRenderedSize] = useState({ width: 0, height: 0 });
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const imageUrl = URL.createObjectURL(file);

  useEffect(() => {
    return () => URL.revokeObjectURL(imageUrl);
  }, [imageUrl]);

  const handleImageLoad = () => {
    if (imgRef.current) {
      setNaturalSize({
        width: imgRef.current.naturalWidth,
        height: imgRef.current.naturalHeight,
      });
    }
  };

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setRenderedSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const analyzedDimensions = imageResults?.signals.find((s) => s.kind === "Image dimensions")?.details as
    | { width: number; height: number }
    | undefined;
  const analyzedWidth = analyzedDimensions?.width ?? naturalSize.width;
  const analyzedHeight = analyzedDimensions?.height ?? naturalSize.height;

  const scaleX = naturalSize.width > 0 ? renderedSize.width / naturalSize.width : 1;
  const scaleY = naturalSize.height > 0 ? renderedSize.height / naturalSize.height : 1;

  const regionScaleX = analyzedWidth > 0 ? (naturalSize.width / analyzedWidth) * scaleX : scaleX;
  const regionScaleY = analyzedHeight > 0 ? (naturalSize.height / analyzedHeight) * scaleY : scaleY;

  const allRegions: (RegionLike & { type: "image" | "copy-move" })[] = [
    ...(imageResults?.suspicious_regions ?? []).map((r) => ({ ...r, type: "image" as const })),
    ...(copyMoveResults?.suspicious_regions ?? []).map((r) => ({ ...r, type: "copy-move" as const })),
  ];

  const hasOverlays = allRegions.length > 0 || (ocrBlocks && ocrBlocks.length > 0);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Image Evidence</h2>
        {hasOverlays && (
          <div className="flex gap-4 text-xs">
            <label className="flex items-center gap-2 text-slate-300">
              <input
                type="checkbox"
                checked={showRegions}
                onChange={(e) => setShowRegions(e.target.checked)}
                className="rounded border-slate-600 bg-slate-800 text-cyan-400 focus:ring-cyan-400"
              />
              Suspicious regions
            </label>
            <label className="flex items-center gap-2 text-slate-300">
              <input
                type="checkbox"
                checked={showOcr}
                onChange={(e) => setShowOcr(e.target.checked)}
                className="rounded border-slate-600 bg-slate-800 text-cyan-400 focus:ring-cyan-400"
              />
              OCR boxes
            </label>
          </div>
        )}
      </div>

      <div ref={containerRef} className="relative mt-4 inline-block max-w-full">
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Evidence"
          onLoad={handleImageLoad}
          className="block max-w-full h-auto rounded-lg"
        />

        {showRegions &&
          allRegions.map((region, index) => (
            <div
              key={`region-${region.type}-${index}`}
              className="absolute border-2 border-rose-500/80 bg-rose-500/10"
              style={{
                left: region.x * regionScaleX,
                top: region.y * regionScaleY,
                width: region.width * regionScaleX,
                height: region.height * regionScaleY,
              }}
              title={`${region.reason} (${(region.confidence * 100).toFixed(1)}%)`}
            />
          ))}

        {showOcr &&
          ocrBlocks?.map((block, index) => (
            <div
              key={`ocr-${index}`}
              className="absolute border border-cyan-400/60 bg-cyan-400/5"
              style={{
                left: block.x * scaleX,
                top: block.y * scaleY,
                width: block.width * scaleX,
                height: block.height * scaleY,
              }}
              title={`${block.text} (${block.confidence.toFixed(1)}%)`}
            />
          ))}
      </div>
    </div>
  );
}
