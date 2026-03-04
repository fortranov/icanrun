/**
 * AddCompetitionModal — wraps CompetitionForm for creating/viewing competitions.
 *
 * Shows competition details when viewing, or full form when adding.
 */
"use client";

import { useState } from "react";
import { Modal } from "./Modal";
import { CompetitionForm } from "@/components/competitions/CompetitionForm";
import { useCreateCompetition, useDeleteCompetition } from "@/hooks/useCompetitions";
import { cn, formatDate } from "@/lib/utils";
import type { Competition, CompetitionCreate } from "@/types";

// ---------------------------------------------------------------------------
// View mode for existing competitions
// ---------------------------------------------------------------------------

const IMPORTANCE_LABELS: Record<string, string> = {
  key: "Ключевое",
  secondary: "Второстепенное",
};

const COMPETITION_TYPE_LABELS: Record<string, string> = {
  run_5k:        "5 км",
  run_10k:       "10 км",
  half_marathon: "Полумарафон",
  marathon:      "Марафон",
  swimming:      "Плавание",
  cycling:       "Велогонка",
  super_sprint:  "Супер-спринт",
  sprint:        "Спринт",
  olympic:       "Олимпийская",
  half_iron:     "Half Ironman",
  iron:          "Ironman",
};

const SPORT_LABELS: Record<string, string> = {
  running:   "Бег",
  swimming:  "Плавание",
  cycling:   "Велосипед",
  strength:  "Силовые",
  triathlon: "Триатлон",
};

interface CompetitionDetailViewProps {
  competition: Competition;
  onDelete: () => void;
  isDeleting: boolean;
}

function CompetitionDetailView({
  competition,
  onDelete,
  isDeleting,
}: CompetitionDetailViewProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "px-3 py-1 rounded-full text-sm font-semibold",
            competition.importance === "key"
              ? "bg-amber-100 text-amber-800"
              : "bg-gray-100 text-gray-600"
          )}
        >
          {IMPORTANCE_LABELS[competition.importance]}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3">
        <div>
          <dt className="text-xs text-gray-500 mb-0.5">Вид спорта</dt>
          <dd className="text-sm font-medium text-gray-800">
            {SPORT_LABELS[competition.sport_type] ?? competition.sport_type}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500 mb-0.5">Тип</dt>
          <dd className="text-sm font-medium text-gray-800">
            {COMPETITION_TYPE_LABELS[competition.competition_type] ?? competition.competition_type}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500 mb-0.5">Дата</dt>
          <dd className="text-sm font-medium text-gray-800">
            {formatDate(competition.date)}
          </dd>
        </div>
        {competition.distance && (
          <div>
            <dt className="text-xs text-gray-500 mb-0.5">Дистанция</dt>
            <dd className="text-sm font-medium text-gray-800">
              {competition.distance}{" "}
              {competition.sport_type === "swimming" ? "м" : "км"}
            </dd>
          </div>
        )}
      </dl>

      {confirmDelete ? (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 mt-4">
          <p className="text-sm text-red-700 mb-3">Удалить это соревнование?</p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onDelete}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {isDeleting ? "Удаление..." : "Удалить"}
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(false)}
              className="flex-1 px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirmDelete(true)}
          className="mt-2 px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50 transition-colors"
        >
          Удалить
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------

interface AddCompetitionModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** If provided, shows competition details rather than the create form. */
  competition?: Competition | null;
  defaultDate?: string;
}

export function AddCompetitionModal({
  isOpen,
  onClose,
  competition,
  defaultDate,
}: AddCompetitionModalProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const { mutateAsync: createCompetition, isPending } = useCreateCompetition();
  const { mutateAsync: deleteCompetition, isPending: isDeleting } = useDeleteCompetition();

  const handleSave = async (data: CompetitionCreate) => {
    setServerError(null);
    try {
      await createCompetition(data);
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Не удалось сохранить соревнование";
      setServerError(msg);
    }
  };

  const handleDelete = async () => {
    if (!competition) return;
    try {
      await deleteCompetition(competition.id);
      onClose();
    } catch {
      setServerError("Не удалось удалить соревнование");
    }
  };

  const title = competition ? competition.name : "Добавить соревнование";

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      {competition ? (
        <CompetitionDetailView
          competition={competition}
          onDelete={handleDelete}
          isDeleting={isDeleting}
        />
      ) : (
        <CompetitionForm
          defaultDate={defaultDate}
          onSave={handleSave}
          onCancel={onClose}
          isLoading={isPending}
          error={serverError}
        />
      )}
    </Modal>
  );
}
