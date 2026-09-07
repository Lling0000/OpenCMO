import { useEffect, useRef, useState, type ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import { getCitation, type KnowledgeCitation } from "../../api/knowledge";
import { useI18n } from "../../i18n";

function codePointOffset(text: string, index: number) {
  let offset = 0;
  for (const character of text) {
    if (index-- <= 0) break;
    offset += character.length;
  }
  return offset;
}

export default function KnowledgeMarkdown(props: ComponentProps<typeof ReactMarkdown>) {
  const { t } = useI18n();
  const [source, setSource] = useState<(KnowledgeCitation & { source_text: string }) | null>(null);
  const [opened, setOpened] = useState(false);
  const [error, setError] = useState(false);
  const [full, setFull] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (opened) dialog.current?.showModal();
    else dialog.current?.close();
  }, [opened]);
  async function openSource(id: string) {
    setSource(null); setError(false); setFull(false); setOpened(true);
    try { setSource(await getCitation(id)); } catch { setError(true); }
  }
  return <>
    <ReactMarkdown {...props} components={{ ...props.components, a: ({ href, children, ...rest }) => {
      const match = href?.match(/^\/api\/v1\/knowledge\/citations\/([a-f0-9-]+)$/);
      return match
        ? <a href={href} onClick={(event) => { event.preventDefault(); void openSource(match[1]!); }}>{children}</a>
        : <a href={href} {...rest}>{children}</a>;
    } }} />
    <dialog ref={dialog} onCancel={() => setOpened(false)}
      className="m-auto w-[min(760px,94vw)] max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-200 p-6 shadow-xl backdrop:bg-slate-900/30">
      <div className="mb-4 flex items-center justify-between gap-4">
        <strong>{source?.title ?? t("knowledge.sources")}</strong>
        <button onClick={() => setOpened(false)} className="rounded-lg border px-3 py-1">{t("knowledge.close")}</button>
      </div>
      {error ? <p role="alert">{t("knowledge.sourceUnavailable")}</p> : !source
        ? <p>{t("knowledge.searching")}</p>
        : <>
          <p className="text-xs text-slate-500">{source.heading} {source.page != null && `${t("knowledge.page")} ${source.page}`}</p>
          {source.generated && <p className="my-2 text-sm text-amber-700">{t("knowledge.generated")}</p>}
          <pre className="my-4 whitespace-pre-wrap break-words font-sans text-sm leading-7">
            {source.source_text.slice(full ? 0 : codePointOffset(source.source_text, Math.max(0, source.start - 250)), codePointOffset(source.source_text, source.start))}
            <mark className="bg-amber-100">{source.quote}</mark>
            {source.source_text.slice(codePointOffset(source.source_text, source.end), full ? undefined : codePointOffset(source.source_text, source.end + 250))}
          </pre>
          <button className="text-sm text-blue-700 underline" onClick={() => setFull(!full)}>{t(full ? "knowledge.excerpt" : "knowledge.fullText")}</button>
        </>}
    </dialog>
  </>;
}
