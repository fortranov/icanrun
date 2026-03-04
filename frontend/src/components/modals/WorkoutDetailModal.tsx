/**
 * WorkoutDetailModal — view, edit, or delete a workout.
 *
 * Shows full workout info with Edit and Delete actions.
 * Edit mode replaces the view with WorkoutForm inline.
 */
"use client";

import { useState } from "react";
import { Modal } from "./Modal";
import { WorkoutForm } from "@/components/workouts/WorkoutForm";
import { useDeleteWorkout, useUpdateWorkout } from "@/hooks/useWorkouts";
import {
  cn,
  formatDate,
  formatDuration,
  getSportLabel,
  getWorkoutTypeLabel,
} from "@/lib/utils";
import type { Workout, WorkoutCreate } from "@/types";

const SOURCE_LABELS: Record<string, string> = {
  planned: "Запланировано",
  manual:  "Вручную",
  garmin:  "Garmin",
};

const SPORT_COLORS: Record<string, string> = {
  running:   "bg-red-100 text-red-700",
  swimming:  "bg-blue-100 text-blue-700",
  cycling:   "bg-amber-100 text-amber-700",
  strength:  "bg-violet-100 text-violet-700",
  triathlon: "bg-emerald-100 text-emerald-700",
};

interface WorkoutDetailModalProps {
  workout: Workout | null;
  isOpen: boolean;
  onClose: () => void;
}

export function WorkoutDetailModal({
  workout,
  isOpen,
  onClose,
}: WorkoutDetailModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const { mutateAsync: updateWorkout, isPending: isUpdating } = useUpdateWorkout();
  const { mutateAsync: deleteWorkout, isPending: isDeleting } = useDeleteWorkout();

  const handleClose = () => {
    setIsEditing(false);
    setDeleteConfirm(false);
    setServerError(null);
    onClose();
  };

  const handleSave = async (data: WorkoutCreate) => {
    if (!workout) return;
    setServerError(null);
    try {
      await updateWorkout({ id: workout.id, data });
      setIsEditing(false);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Не удалось сохранить изменения";
      setServerError(msg);
    }
  };

  const handleDelete = async () => {
    if (!workout) return;
    try {
      await deleteWorkout(workout.id);
      handleClose();
    } catch {
      setServerError("Не удалось удалить тренировку");
    }
  };

  if (!workout) return null;

  const sportColorClass = SPORT_COLORS[workout.sport_type] ?? "bg-gray-100 text-gray-700";

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? "Редактировать тренировку" : "Тренировка"}
    >
      {isEditing ? (
        <WorkoutForm
          initial={workout}
          onSave={handleSave}
          onCancel={() => setIsEditing(false)}
          isLoading={isUpdating}
          error={serverError}
        />
      ) : (
        <div className="space-y-4">
          {/* Sport + duration header */}
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "px-3 py-1 rounded-full text-sm font-semibold",
                sportColorClass
              )}
            >
              {getSportLabel(workout.sport_type)}
            </span>
            <span className="text-2xl font-bold text-gray-900">
              {formatDuration(workout.duration_minutes)}
            </span>
          </div>

          {/* Details grid */}
          <dl className="grid grid-cols-2 gap-3">
            <div>
              <dt className="text-xs text-gray-500 mb-0.5">Дата</dt>
              <dd className="text-sm font-medium text-gray-800">
                {formatDate(workout.date)}
              </dd>
            </div>

            <div>
              <dt className="text-xs text-gray-500 mb-0.5">Тип</dt>
              <dd className="text-sm font-medium text-gray-800">
                {getWorkoutTypeLabel(workout.workout_type) || "—"}
              </dd>
            </div>

            <div>
              <dt className="text-xs text-gray-500 mb-0.5">Источник</dt>
              <dd className="text-sm font-medium text-gray-800">
                {SOURCE_LABELS[workout.source] ?? workout.source}
              </dd>
            </div>

            <div>
              <dt className="text-xs text-gray-500 mb-0.5">Статус</dt>
              <dd
                className={cn(
                  "text-sm font-medium",
                  workout.is_completed ? "text-green-600" : "text-orange-500"
                )}
              >
                {workout.is_completed ? "Выполнено" : "Не выполнено"}
              </dd>
            </div>
          </dl>

          {/* Comment */}
          {workout.comment && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Комментарий</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg px-3 py-2">
                {workout.comment}
              </p>
            </div>
          )}

          {/* Server error */}
          {serverError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {serverError}
            </div>
          )}

          {/* Actions */}
          {deleteConfirm ? (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4">
              <p className="text-sm text-red-700 mb-3">
                Удалить эту тренировку? Это действие нельзя отменить.
              </p>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {isDeleting ? "Удаление..." : "Удалить"}
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteConfirm(false)}
                  className="flex-1 px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Редактировать
              </button>
              <button
                type="button"
                onClick={() => setDeleteConfirm(true)}
                className="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50 transition-colors"
              >
                Удалить
              </button>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
