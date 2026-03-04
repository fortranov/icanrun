/**
 * AddWorkoutModal — wraps WorkoutForm for creating a new workout.
 *
 * Pre-fills the date from the clicked calendar cell.
 * On success: closes modal and invalidates workout queries.
 */
"use client";

import { useState } from "react";
import { Modal } from "./Modal";
import { WorkoutForm } from "@/components/workouts/WorkoutForm";
import { useCreateWorkout } from "@/hooks/useWorkouts";
import type { WorkoutCreate } from "@/types";

interface AddWorkoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultDate?: string;
}

export function AddWorkoutModal({
  isOpen,
  onClose,
  defaultDate,
}: AddWorkoutModalProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const { mutateAsync: createWorkout, isPending } = useCreateWorkout();

  const handleSave = async (data: WorkoutCreate) => {
    setServerError(null);
    try {
      await createWorkout(data);
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Не удалось сохранить тренировку";
      setServerError(msg);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Новая тренировка">
      <WorkoutForm
        defaultDate={defaultDate}
        onSave={handleSave}
        onCancel={onClose}
        isLoading={isPending}
        error={serverError}
      />
    </Modal>
  );
}
