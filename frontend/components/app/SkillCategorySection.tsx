"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Plus } from "lucide-react";

import { Card, Chip } from "@/components/ui";
import { ease } from "@/lib/motion";
import { CATEGORY_LABELS, type SkillCategory } from "@/lib/mock-data/skills";

export type DashboardSkill = { id: string; name: string };

type SkillCategorySectionProps = {
  category: SkillCategory;
  initialSkills: DashboardSkill[];
};

export default function SkillCategorySection({
  category,
  initialSkills,
}: SkillCategorySectionProps) {
  const reduced = useReducedMotion() ?? false;
  const [skills, setSkills] = useState<DashboardSkill[]>(initialSkills);
  const [inputOpen, setInputOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const customCounter = useRef(0);

  function removeSkill(id: string) {
    setSkills((prev) => prev.filter((s) => s.id !== id));
  }

  function addSkill() {
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    const id = `custom-${customCounter.current++}`;
    setSkills((prev) => [...prev, { id, name: trimmed }]);
    setInputValue("");
    setInputOpen(false);
  }

  function cancelInput() {
    setInputValue("");
    setInputOpen(false);
  }

  return (
    <Card>
      <h2 className="text-h5">{CATEGORY_LABELS[category]}</h2>
      <motion.div layout className="mt-3 flex flex-wrap items-center gap-2">
        <AnimatePresence mode="popLayout">
          {skills.map((skill) => (
            <motion.div
              key={skill.id}
              layout
              initial={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.9 }}
              animate={reduced ? { opacity: 1 } : { opacity: 1, scale: 1 }}
              exit={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.18, ease: ease.out }}
            >
              <Chip variant="removable" onRemove={() => removeSkill(skill.id)}>
                {skill.name}
              </Chip>
            </motion.div>
          ))}
        </AnimatePresence>

        {inputOpen ? (
          <SkillInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={addSkill}
            onCancel={cancelInput}
          />
        ) : (
          <AddSkillButton onClick={() => setInputOpen(true)} />
        )}
      </motion.div>
    </Card>
  );
}

function AddSkillButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-[26px] items-center gap-1 rounded-pill border border-dashed border-border px-[10px] text-caption text-text-muted outline-none transition-colors duration-[140ms] ease-out hover:border-text-muted hover:text-text focus-visible:ring-2 focus-visible:ring-accent/40"
    >
      <Plus className="size-3" aria-hidden />
      Add skill
    </button>
  );
}

type SkillInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

function SkillInput({ value, onChange, onSubmit, onCancel }: SkillInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      onSubmit();
    } else if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
    }
  }

  return (
    <motion.input
      ref={inputRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.14, ease: ease.out }}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={handleKeyDown}
      placeholder="Skill name"
      className="h-[26px] w-36 rounded-pill border border-border bg-transparent px-[10px] text-caption text-text outline-none transition-colors duration-[140ms] ease-out placeholder:text-text-muted/70 focus:border-accent"
    />
  );
}
