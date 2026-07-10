"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "lucide-react";

import ResumeDropzone, {
  type SelectedFile,
} from "@/components/app/ResumeDropzone";
import { Button, Textarea } from "@/components/ui";
import { createAnalysis } from "@/lib/api/analyze";
import { fadeUp } from "@/lib/motion";

export default function AnalyzePage() {
  const router = useRouter();
  const reduced = useReducedMotion() ?? false;
  const [file, setFile] = useState<SelectedFile | null>(null);
  const [jdText, setJdText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isReady = file !== null && jdText.trim().length > 0;

  async function handleAnalyze() {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const runId = await createAnalysis(file.file, jdText);
      router.push(`/running/${runId}`);
    } catch {
      setError("We couldn't start your analysis. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div>
      <motion.div {...fadeUp(0, reduced)}>
        <h1 className="text-h3">Start a new analysis</h1>
        <p className="mt-2 text-body text-text-muted">
          Drop your resume, paste the job description, and we&apos;ll build your
          plan.
        </p>
      </motion.div>

      <motion.div
        {...fadeUp(0.05, reduced)}
        className="mt-8 grid gap-6 md:grid-cols-2"
      >
        <ResumeDropzone
          file={file}
          onFileSelect={setFile}
          onClear={() => setFile(null)}
        />
        <div>
          <label htmlFor="jd" className="block text-body font-medium">
            Job description
          </label>
          <Textarea
            id="jd"
            value={jdText}
            onChange={(event) => setJdText(event.target.value)}
            placeholder="Paste the full job description here..."
            className="mt-2 min-h-[240px]"
          />
          <p className="mt-2 text-caption text-text-muted">
            Tip: include the full posting for the best skill match.
          </p>
        </div>
      </motion.div>

      <motion.div {...fadeUp(0.1, reduced)} className="mt-8">
        <Button
          size="lg"
          rightIcon={<ArrowRight />}
          onClick={handleAnalyze}
          disabled={!isReady || submitting}
          className="w-full md:w-auto"
        >
          {submitting ? "Starting…" : "Analyze the gap"}
        </Button>
        {error && <p className="mt-3 text-caption text-missing-text">{error}</p>}
      </motion.div>
    </div>
  );
}
