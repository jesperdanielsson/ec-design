import katex from "katex";
import { useMemo } from "react";

export function Tex({ tex, block = false }: { tex: string; block?: boolean }) {
  const html = useMemo(
    () => katex.renderToString(tex, { displayMode: block, throwOnError: false }),
    [tex, block],
  );
  return <span className={block ? "tex-block" : "tex"} dangerouslySetInnerHTML={{ __html: html }} />;
}
