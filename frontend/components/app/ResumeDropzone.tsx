"use client";

import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { FileText, Upload, X } from "lucide-react";

import { IconButton } from "@/components/ui";
import { cn } from "@/lib/utils";

// Keep the underlying File so the analyze request can upload its bytes.
export type SelectedFile = { name: string; size: number; file: File };

type ResumeDropzoneProps = {
  file: SelectedFile | null;
  onFileSelect: (file: SelectedFile) => void;
  onClear: () => void;
};

export default function ResumeDropzone({
  file,
  onFileSelect,
  onClear,
}: ResumeDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  // dragenter/dragleave fire as the cursor crosses child elements; counter avoids flicker.
  const dragCounter = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleDragEnter(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragCounter.current += 1;
    if (dragCounter.current === 1) setIsDragOver(true);
  }

  function handleDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragCounter.current -= 1;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setIsDragOver(false);
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragCounter.current = 0;
    setIsDragOver(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) onFileSelect({ name: dropped.name, size: dropped.size, file: dropped });
  }

  function handleFilePicked(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    if (picked) onFileSelect({ name: picked.name, size: picked.size, file: picked });
    // Reset so re-selecting the same file still fires onChange.
    event.target.value = "";
  }

  const sharedClasses = cn(
    "h-[240px] w-full rounded-card border-[1.5px] border-dashed",
    "transition-colors duration-[160ms] ease-out",
    isDragOver
      ? "border-accent bg-bg-secondary"
      : file
        ? "border-border bg-bg-secondary"
        : "border-border hover:bg-bg-secondary/50",
  );

  if (file) {
    return (
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(sharedClasses, "flex items-center justify-center")}
      >
        <div className="flex w-full max-w-[360px] items-center gap-3 px-6">
          <FileText className="size-5 shrink-0 text-text-muted" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate text-body">{file.name}</p>
            <p className="text-caption text-text-muted">
              {formatBytes(file.size)}
            </p>
          </div>
          <IconButton
            icon={<X />}
            aria-label="Remove file"
            onClick={onClear}
          />
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => fileInputRef.current?.click()}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        sharedClasses,
        "flex flex-col items-center justify-center gap-1.5",
        "outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
      )}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        onChange={handleFilePicked}
        className="hidden"
      />
      <Upload className="size-5 text-text-muted" aria-hidden />
      <p className="mt-1 text-body text-text">Drop your resume here</p>
      <p className="text-caption text-text-muted">PDF or DOCX, up to 5MB</p>
      <span className="mt-1 text-caption text-accent">or click to browse</span>
    </button>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
