import { useState } from "react";
import { Plus } from "lucide-react";
import { useI18n } from "../../i18n";

export function AddKeywordForm({
  onAdd,
  isLoading,
}: {
  onAdd: (keyword: string) => void;
  isLoading: boolean;
}) {
  const [value, setValue] = useState("");
  const { t } = useI18n();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    onAdd(value.trim());
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={t("keywords.addPlaceholder")}
        className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={isLoading || !value.trim()}
        className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Plus size={14} />
        {t("keywords.add")}
      </button>
    </form>
  );
}
